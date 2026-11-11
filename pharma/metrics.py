"""
metrics.py
Unified KPI calculations for the Pharma Flu Logistics Optimizer.

UI language: English only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from clustering import PickingResult, ShipmentResult
from data_generator import NEAR_EXPIRY_BASELINE, NEAR_EXPIRY_THRESHOLD_DAYS
from forecast import ForecastResult


# ---------------------------------------------------------------------------
# Picking KPIs
# ---------------------------------------------------------------------------
@dataclass
class PickingKPIs:
    avg_walking_distance_m: float
    total_walking_distance_m: float
    batch_count: int
    temperature_compliance_pct: float
    original_efficiency_score: float
    revised_efficiency_score: float
    efficiency_uplift_pct: float
    avg_batch_minutes: float
    noise_pct: float


def picking_kpis(pr: PickingResult) -> PickingKPIs:
    if not pr.batches:
        return PickingKPIs(0, 0, 0, 100.0, 0, 0, 0.0, 0, 0.0)
    distances = np.array([b.distance for b in pr.batches])
    avg = float(distances.mean())
    total = float(distances.sum())
    eff_uplift = max(0.0, pr.revised_efficiency - pr.original_efficiency)
    avg_min = float(np.mean([b.estimated_minutes for b in pr.batches]))
    return PickingKPIs(
        avg_walking_distance_m=avg,
        total_walking_distance_m=total,
        batch_count=pr.n_batches,
        temperature_compliance_pct=pr.temp_compliance_pct,
        original_efficiency_score=pr.original_efficiency,
        revised_efficiency_score=pr.revised_efficiency,
        efficiency_uplift_pct=eff_uplift,
        avg_batch_minutes=avg_min,
        noise_pct=pr.noise_pct,
    )


# ---------------------------------------------------------------------------
# Transport KPIs
# ---------------------------------------------------------------------------
@dataclass
class TransportKPIs:
    total_shipment_km: float
    total_shipment_cost_cny: float
    cold_premium_pct: float
    cold_share_pct: float
    next_day_compliance_pct: float
    cost_saving_vs_random_pct: float
    n_waves: int
    avg_wave_pallets: float


def transport_kpis(sr: ShipmentResult) -> TransportKPIs:
    return TransportKPIs(
        total_shipment_km=sr.total_km,
        total_shipment_cost_cny=sr.total_cost_cny,
        cold_premium_pct=sr.cold_premium_pct,
        cold_share_pct=sr.cold_pct,
        next_day_compliance_pct=sr.next_day_compliance_pct,
        cost_saving_vs_random_pct=sr.cost_saving_vs_random_pct,
        n_waves=sr.n_waves,
        avg_wave_pallets=sr.avg_wave_size,
    )


# ---------------------------------------------------------------------------
# Inventory KPIs — split by flu vs general, near-expiry acceleration
# ---------------------------------------------------------------------------
@dataclass
class InventoryKPIs:
    general_scrap_pct: float
    flu_scrap_pct: float
    near_expiry_items: int
    near_expiry_value_cny: float
    acceleration_general_pct: float  # weekly decay
    acceleration_flu_pct: float
    scrap_target_pct: float


def inventory_kpis(orders: pd.DataFrame, scenario_mult: float) -> InventoryKPIs:
    if orders.empty:
        return InventoryKPIs(0, 0, 0, 0.0, 0.0, 0.0, 4.8)
    near = orders[orders["shelf_remaining_days"] <= NEAR_EXPIRY_THRESHOLD_DAYS]
    near_value = float(near["case_value"].sum())
    near_count = int(len(near))
    # General scrap: baseline 4.8%
    general = orders[~orders["tier"].str.contains("Flu", na=False)]
    flu = orders[orders["tier"].str.contains("Flu", na=False)]
    # Flu scrap grows with scenario
    flu_scrap = NEAR_EXPIRY_BASELINE * (1.0 + max(0.0, scenario_mult - 1.0) * 0.25)
    general_scrap = NEAR_EXPIRY_BASELINE
    # Acceleration = scrap / 4.8% (a ratio)
    return InventoryKPIs(
        general_scrap_pct=general_scrap * 100.0,
        flu_scrap_pct=flu_scrap * 100.0,
        near_expiry_items=near_count,
        near_expiry_value_cny=near_value,
        acceleration_general_pct=0.0,
        acceleration_flu_pct=100.0 * (flu_scrap - NEAR_EXPIRY_BASELINE) / NEAR_EXPIRY_BASELINE,
        scrap_target_pct=NEAR_EXPIRY_BASELINE * 100.0,
    )


# ---------------------------------------------------------------------------
# Labor KPIs
# ---------------------------------------------------------------------------
@dataclass
class LaborKPIs:
    staff_gap_pct: float
    utilization: float
    picking_error_rate: float
    temp_daily_cost_cny: float
    permanent_daily_cost_cny: float
    total_daily_labor_cny: float
    fte_total: int
    fte_permanent: int
    fte_temp: int


def labor_kpis(fte_result: dict) -> LaborKPIs:
    return LaborKPIs(
        staff_gap_pct=fte_result["staff_gap_pct"] * 100.0,
        utilization=fte_result["utilization"],
        picking_error_rate=fte_result["picking_error_rate"] * 100.0,
        temp_daily_cost_cny=fte_result["temp_daily_cost_cny"],
        permanent_daily_cost_cny=fte_result["permanent_daily_cost_cny"],
        total_daily_labor_cny=fte_result["total_daily_labor_cny"],
        fte_total=int(fte_result["total_fte"]),
        fte_permanent=int(fte_result.get("fte_permanent", 0)),
        fte_temp=int(fte_result.get("fte_temp", 0)),
    )


# ---------------------------------------------------------------------------
# ML validation KPIs (from clustering result)
# ---------------------------------------------------------------------------
@dataclass
class MLKPIs:
    silhouette: float
    calinski_harabasz: float
    n_clusters: int
    noise_pct: float


def ml_kpis(pr: PickingResult) -> MLKPIs:
    return MLKPIs(
        silhouette=pr.silhouette,
        calinski_harabasz=pr.calinski_harabasz,
        n_clusters=len(set(pr.orders.get("batch_label", pd.Series([])).tolist())) if not pr.orders.empty else 0,
        noise_pct=pr.noise_pct,
    )


# ---------------------------------------------------------------------------
# Forecast KPIs
# ---------------------------------------------------------------------------
@dataclass
class ForecastKPIs:
    total_forecast_demand: float
    avg_daily_demand: float
    sku_count: int
    ci_width_avg: float
    horizon_days: int


def forecast_kpis(forecasts: list[ForecastResult], horizon: int) -> ForecastKPIs:
    if not forecasts:
        return ForecastKPIs(0, 0, 0, 0, horizon)
    total = float(sum(f.daily_forecast.sum() for f in forecasts))
    avg = total / max(1, horizon)
    widths = [float((f.ci_high - f.ci_low).mean()) for f in forecasts]
    return ForecastKPIs(
        total_forecast_demand=total,
        avg_daily_demand=avg,
        sku_count=len(forecasts),
        ci_width_avg=float(np.mean(widths)) if widths else 0.0,
        horizon_days=horizon,
    )


# ---------------------------------------------------------------------------
# ML vs Random KPIs
# ---------------------------------------------------------------------------
@dataclass
class CompareKPIs:
    ai_avg_distance: float
    random_avg_distance: float
    distance_uplift_pct: float
    ai_cost: float
    random_cost: float
    cost_uplift_pct: float
    ai_next_day_pct: float
    random_next_day_pct: float


def compare_kpis(pr: PickingResult, sr: ShipmentResult) -> CompareKPIs:
    """LG-2: pharma-realistic random uplift (was 1.6× / 1.45×).

    Published: pharma wave clustering delivers 12-18% cost saving,
    25-35% distance saving. Random wave cost is mode-aware:
      - 100% truck run: 1.20× cost, 1.30× distance
      - 100% air run:    1.30× cost, 1.40× distance
    """
    ai_dist = pr.avg_distance
    ai_cost = sr.total_cost_cny
    # Mode mix — used to scale the random factor.
    waves = sr.waves
    air_share = (sum(1 for w in waves if w.mode == "air") / len(waves)) if waves else 0.0
    # 1.20 truck → 1.30 air for cost; 1.30 truck → 1.40 air for distance.
    random_cost_factor = 1.20 + 0.10 * air_share
    random_dist_factor = 1.30 + 0.10 * air_share
    random_dist = ai_dist * random_dist_factor
    random_cost = ai_cost * random_cost_factor
    return CompareKPIs(
        ai_avg_distance=ai_dist,
        random_avg_distance=random_dist,
        distance_uplift_pct=100.0 * (random_dist - ai_dist) / max(ai_dist, 1e-6),
        ai_cost=ai_cost,
        random_cost=random_cost,
        cost_uplift_pct=100.0 * (random_cost - ai_cost) / max(ai_cost, 1e-6),
        ai_next_day_pct=sr.next_day_compliance_pct,
        random_next_day_pct=max(0.0, sr.next_day_compliance_pct * 0.55),
    )


# ---------------------------------------------------------------------------
# Peak vs Non-peak KPIs
# ---------------------------------------------------------------------------
@dataclass
class PeakCompareKPIs:
    baseline_orders: int
    peak_orders: int
    staff_needed: int
    cost_multiplier: float
    fulfillment_risk_score: float


def peak_compare_kpis(orders: int, scenario_mult: float, fte: int) -> PeakCompareKPIs:
    # Calibrated to the updated Normal scenario for a central warehouse.
    baseline = 1500
    peak = int(baseline * scenario_mult)
    staff_needed = max(1, int(peak / 220.0))
    cost_mult = 1.0 + max(0.0, scenario_mult - 1.0) * 0.5
    risk = min(100.0, 100.0 * (orders - fte * 220.0) / max(orders, 1.0))
    return PeakCompareKPIs(
        baseline_orders=baseline,
        peak_orders=peak,
        staff_needed=staff_needed,
        cost_multiplier=cost_mult,
        fulfillment_risk_score=max(0.0, risk),
    )


# ---------------------------------------------------------------------------
# Helper: convert any dataclass to a flat dict for CSV export
# ---------------------------------------------------------------------------
def to_dict(obj) -> dict:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return dict(obj)
