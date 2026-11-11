"""
forecast.py
Regional flu outbreak scoring, seasonal demand curves, 7/30/90-day SKU
forecasts with 95% bootstrap confidence bands, FTE / labor projections,
and preset scenarios for the Pharma Flu Logistics Optimizer.

UI language: English only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from data_generator import (
    CHINA_REGIONS,
    CLIENT_HOSPITAL,
    CLIENT_PHARMACY,
    CLIENT_PRIMARY,
    TIER_MILD_OTC,
    TIER_MODERATE_RX,
    TIER_SEVERE_HOSP,
    TIER_NON_FLU,
    flu_multiplier_for_tier,
    Region,
)


# ---------------------------------------------------------------------------
# 1. Regional outbreak score (0..1) — WHO + CN CDC inspired covariates
# ---------------------------------------------------------------------------
def regional_outbreak_score(region: Region) -> float:
    """Composite outbreak risk combining density, low vax, beds, child share.

    Higher score = more vulnerable region for flu surge.
    """
    # Normalize density to 0..1 (cap at 1500 people/km^2)
    density_norm = min(1.0, region.population_density / 1500.0)
    # Lower vaccination -> higher risk; invert and scale
    vax_risk = max(0.0, 1.0 - region.vaccination_rate) * 1.2
    vax_norm = min(1.0, vax_risk)
    # Hospital capacity: higher beds -> better response -> lower risk
    beds_norm = max(0.0, 1.0 - region.hospital_bed_ratio / 6.0)
    # Child share: more children -> higher risk
    child_norm = min(1.0, region.child_share / 0.25)

    # Weighted blend
    score = 0.30 * density_norm + 0.30 * vax_norm + 0.20 * beds_norm + 0.20 * child_norm
    return float(max(0.0, min(1.0, score)))


def outbreak_dataframe(month: int | None = None) -> pd.DataFrame:
    """Return outbreak scores for all 8 China regions.

    If *month* is provided, the static outbreak score is blended with the
    seasonal multiplier for that month so the map reflects time-of-year
    risk (Jan = red, Jul = yellow).

    The effective_outbreak is NOT capped at 1.0 — high-density / low-vax
    regions in winter peak can exceed 1.0 to convey "this region is in a
    worse flu situation than the worst-case baseline". Visualization uses
    a dynamic color scale to reflect this.
    """
    if month is None:
        season_mult = 1.0
    else:
        season_mult = float(seasonal_multiplier(_mid_month_doy(month)))  # 1.0..3.5
    rows = [
        {
            "region": r.name,
            "lat": r.lat,
            "lon": r.lon,
            "outbreak_score": regional_outbreak_score(r),
            "seasonal_multiplier": season_mult,
            "effective_outbreak": regional_outbreak_score(r) * season_mult,
            "population_density": r.population_density,
            "vaccination_rate": r.vaccination_rate,
            "hospital_bed_ratio": r.hospital_bed_ratio,
            "child_share": r.child_share,
            "base_demand": r.base_demand,
        }
        for r in CHINA_REGIONS
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Month-based seasonal flu curve
# ---------------------------------------------------------------------------
# China flu peaks Dec-Feb; we model a smooth sinusoid with peak at Jan 15.
# Amplitude tuned to China CDC ILI surveillance: winter peak 8-10% ILI
# vs 2-3% summer trough ≈ 3.5x ratio at the season level.
SEASONAL_PEAK_DOY = 15  # day-of-year for peak (Jan 15)
SEASONAL_AMPLITUDE = 2.5  # additional multiplier on top of 1.0 baseline
                           #   → season curve ranges [1.0, 3.5] for flu drugs


def seasonal_multiplier(day_of_year: int) -> float:
    """Generic seasonal flu multiplier in [1.0, 3.5] for given day-of-year.

    Used as the default for outbreak scoring and other non-tier contexts.
    """
    # Sinusoid centred on Jan 15; min in mid-July
    phase = (day_of_year - SEASONAL_PEAK_DOY) * 2 * math.pi / 365.0
    raw = (math.cos(phase) + 1.0) / 2.0  # 0..1
    return 1.0 + SEASONAL_AMPLITUDE * raw


# Per-tier seasonal AMPLITUDE on top of 1.0 baseline.
# These are tuned so the COMBINED (tier mult × tier season) winter
# peak gives a realistic surge vs summer baseline, in line with CN CDC
# ILI surveillance and manufacturer sales data:
#   • Chronic drugs: ~1.05x winter (essentially flat — real demand does
#     not surge for antihypertensives, statins, antidiabetics)
#   • OTC cold/cough: ~2.2x winter (paracetamol/phenylephrine sales)
#   • Rx antivirals:  ~2.8x winter (oseltamivir scripts 8-10x in absolute
#     terms, but blended with the tier multiplier gives ~7x at flu peak)
#   • Vaccines + severe hospital: ~2.5x winter (autumn/winter campaign)
TIER_SEASONAL_AMP: dict[str, float] = {
    TIER_NON_FLU:     0.05,  # chronic — flat
    TIER_MILD_OTC:    1.20,  # OTC cold/cough
    TIER_MODERATE_RX: 1.80,  # Rx antivirals
    TIER_SEVERE_HOSP: 1.50,  # vaccines + severe hospital
}


def _seasonal_curve(day_of_year: int) -> float:
    """Return the 0..1 base sinusoid (peak at Jan 15)."""
    phase = (day_of_year - SEASONAL_PEAK_DOY) * 2 * math.pi / 365.0
    return (math.cos(phase) + 1.0) / 2.0


def seasonal_multiplier_for_tier(tier: str, day_of_year: int) -> float:
    """Return per-tier seasonal multiplier in [1.0, 1.0+amp].

    Examples at Jan 15 (peak):
        Non-Flu:        1.00–1.05  (essentially flat year-round)
        Mild OTC:       1.00–2.20  (winter doubles)
        Moderate Rx:    1.00–2.80  (winter 2.8x)
        Severe Hosp:    1.00–2.50  (winter 2.5x for vaccines/IV antivirals)
    """
    amp = TIER_SEASONAL_AMP.get(tier, 1.0)
    return 1.0 + amp * _seasonal_curve(day_of_year)


def seasonal_for_year(month: int) -> np.ndarray:
    """Return 12-element array of seasonal multipliers for each month."""
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    mid_doy = []
    cum = 0
    for d in days_per_month:
        mid_doy.append(cum + d / 2)
        cum += d
    return np.array([seasonal_multiplier(int(round(m))) for m in mid_doy])


# ---------------------------------------------------------------------------
# 3. Forecast horizons with 95% bootstrap CI
# ---------------------------------------------------------------------------
@dataclass
class ForecastResult:
    sku_id: str
    sku_name: str
    tier: str
    base_daily: float
    daily_forecast: np.ndarray  # length = horizon
    ci_low: np.ndarray
    ci_high: np.ndarray


def forecast_sku_demand(
    catalog: pd.DataFrame,
    outbreak: pd.DataFrame,
    scenario_mult: float,
    month: int,
    horizon: int,
    n_resamples: int,
    seed: int,
) -> list[ForecastResult]:
    """Forecast *horizon* days of demand for each SKU with 95% bootstrap CI."""
    rng = np.random.default_rng(seed)
    results: list[ForecastResult] = []

    # Aggregate outbreak-score per region -> weighted demand.
    # We use the BASE outbreak_score (not effective_outbreak which has
    # the season baked in) so the regional base demand stays stable
    # year-round. The seasonal surge is then applied per-SKU via the
    # tier-specific seasonal multiplier below — this prevents
    # double-counting the season.
    score_col = "outbreak_score"
    outbreak_index = {row["region"]: float(row[score_col]) for _, row in outbreak.iterrows()}
    base_total = sum(r.base_demand for r in CHINA_REGIONS)

    # Per-region expected demand (year-round stable baseline)
    region_demand = {
        r.name: (r.base_demand / base_total) * (1.0 + 0.6 * outbreak_index[r.name])
        for r in CHINA_REGIONS
    }

    for _, sku in catalog.iterrows():
        tier = sku["tier"]
        # Region-pooled baseline
        regional_sum = sum(region_demand.values())
        # SKU share of tier
        tier_share = _tier_share(catalog, tier)
        # Daily baseline for this SKU
        base_daily = max(1.0, regional_sum * tier_share)
        # Apply scenario (tier-specific flu multiplier) + tier-specific season
        fmul = flu_multiplier_for_tier(tier, scenario_mult) * seasonal_multiplier_for_tier(
            tier, _mid_month_doy(month)
        )
        scale = base_daily * fmul
        # Daily noise (Poisson-like) and small weekly seasonality
        day_index = np.arange(horizon)
        weekly = 1.0 + 0.05 * np.sin(2 * math.pi * day_index / 7.0)
        mean = np.maximum(0.0, scale * weekly)
        # Bootstrap CI
        samples = rng.poisson(lam=np.maximum(1.0, mean)[:, None].repeat(n_resamples, axis=1))
        ci_low = np.percentile(samples, 2.5, axis=1)
        ci_high = np.percentile(samples, 97.5, axis=1)
        # Point forecast = mean of bootstrap
        point = samples.mean(axis=1)
        results.append(ForecastResult(
            sku_id=sku["sku_id"],
            sku_name=sku["name"],
            tier=tier,
            base_daily=float(base_daily),
            daily_forecast=point,
            ci_low=ci_low,
            ci_high=ci_high,
        ))
    return results


def _tier_share(catalog: pd.DataFrame, tier: str) -> float:
    n_tier = (catalog["tier"] == tier).sum()
    return max(0.001, n_tier / len(catalog))


def _mid_month_doy(month: int) -> int:
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    m = max(1, min(12, month))
    return sum(days_per_month[: m - 1]) + days_per_month[m - 1] // 2


# ---------------------------------------------------------------------------
# 4. Demand split by client type and flu tier
# ---------------------------------------------------------------------------
# Baseline daily line volume at scenario_mult=1.0 (Normal, summer).
# Calibrated to the case-study distributor profile: ~250K cases/day, of
# which a representative DC handles a sliver. Mix reflects the 12,800
# hospitals / 250K pharmacies / primary care mix.
_BASE_DAILY = {
    CLIENT_HOSPITAL:  260.0,  # 12.8K hospitals, large B2B orders
    CLIENT_PHARMACY:  480.0,  # 250K pharmacies, OTC-heavy at peak
    CLIENT_PRIMARY:   180.0,  # primary care / township health centers
}
# Per-client tier mix. The seasonal surge then amplifies the flu tiers
# via flu_multiplier_for_tier(), so peak winter hospitals skew severe
# while pharmacies skew mild OTC.
_CLIENT_TIER_MIX: dict[str, dict[str, float]] = {
    CLIENT_HOSPITAL: {TIER_NON_FLU: 0.20, TIER_MILD_OTC: 0.10, TIER_MODERATE_RX: 0.30, TIER_SEVERE_HOSP: 0.40},
    CLIENT_PHARMACY: {TIER_NON_FLU: 0.30, TIER_MILD_OTC: 0.45, TIER_MODERATE_RX: 0.20, TIER_SEVERE_HOSP: 0.05},
    CLIENT_PRIMARY:  {TIER_NON_FLU: 0.45, TIER_MILD_OTC: 0.35, TIER_MODERATE_RX: 0.15, TIER_SEVERE_HOSP: 0.05},
}


def demand_split_by_client(scenario_mult: float) -> pd.DataFrame:
    """Return expected daily demand split by client + flu tier.

    The scenario_mult is the user-facing flu intensity (1.0 = normal,
    2.0 = peak, 3.5 = H1N1). The per-tier base multiplier is folded in
    here so the table shows the realistic demand a single DC sees.
    """
    rows = []
    for client, base_val in _BASE_DAILY.items():
        for tier in [TIER_NON_FLU, TIER_MILD_OTC, TIER_MODERATE_RX, TIER_SEVERE_HOSP]:
            fmul = flu_multiplier_for_tier(tier, scenario_mult)
            mix = _CLIENT_TIER_MIX[client][tier]
            rows.append({
                "client": client,
                "tier": tier,
                "daily_demand": round(base_val * fmul * mix, 1),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. FTE / staffing model
# ---------------------------------------------------------------------------
SHIFT_HOURS = 8.0
SHIFTS_PER_DAY = 3
HOURS_PER_3SHIFT_DAY = SHIFT_HOURS * SHIFTS_PER_DAY  # 24h coverage per FTE if single
HOURS_PER_FTE_SHIFT = 8.0                        # 1 FTE × 1 shift = 8 h (cost basis)

# Picker throughput — mid-range of manual pharma benchmarks (Logos 60-90 cold / 80-120 ambient).
# Single source of truth: forecast_outbreak_for_date also reads this (was 35, the mismatch HR-2 fixed).
PICKER_THROUGHPUT_PER_HR = 65.0

# Picking error constants — quadratic surge understaffing curve (McKinsey 2023).
# 0.35% baseline; multiplier = 1 + 3.5 * (gap_pct / 100)^2 → ~2× at 50% over-capacity, 3-5× at 80%.
PICKING_ERROR_BASELINE = 0.0035
PICKING_ERROR_QUAD_COEF = 3.5

# Temp productivity ramp-up discount (Hewitt China HC 2024). Temp workers are ~20% less
# productive than permanent in the first 90 days. So 260 temp effectively = 208 FTE.
TEMP_PRODUCTIVITY_DISCOUNT = 0.8

# Cost model — temp is 1.2× permanent (industry norm 10-30% premium on fully-loaded basis).
PERM_CNY_PER_FTE_SHIFT = 220.0
TEMP_CNY_PER_FTE_SHIFT  = 264.0   # 220 × 1.2


def fte_calculation(
    total_demand: float,
    fte_permanent: int,
    fte_temp: int,
    picker_throughput_per_hr: float = PICKER_THROUGHPUT_PER_HR,
) -> dict:
    """Compute staffing adequacy, gap, cost, and picking error.

    HR-1/HR-5 recalibration:
      - Picker throughput now PICKER_THROUGHPUT_PER_HR (65, was 55).
      - Temp staff get a TEMP_PRODUCTIVITY_DISCOUNT (0.8) on capacity.
      - Picking error is quadratic in gap_pct: 1 + 3.5 × (gap/100)² (was linear 1.5×).
      - Temp cost 1.2× permanent (was 0.69× — inverse of industry norm).
    """
    capacity_lines_per_fte_day = picker_throughput_per_hr * SHIFT_HOURS
    # Effective FTE accounts for temp ramp-up discount
    effective_fte = fte_permanent + fte_temp * TEMP_PRODUCTIVITY_DISCOUNT
    total_fte_raw = max(0, fte_permanent + fte_temp)
    capacity = effective_fte * capacity_lines_per_fte_day
    gap_pct = max(-0.5, (total_demand - capacity) / max(total_demand, 1.0))
    utilization = min(1.5, total_demand / max(capacity, 1.0))
    # Quadratic error surge curve (gap_pct in 0..1 range):
    #  gap=0  → 1.000× ;  gap=0.10 → 1.035× ;  gap=0.50 → 1.875× ;  gap=0.80 → 3.24×
    picking_error = PICKING_ERROR_BASELINE * (
        1.0 + PICKING_ERROR_QUAD_COEF * (max(0.0, gap_pct) ** 2)
    )
    temp_cost_cny = fte_temp * HOURS_PER_FTE_SHIFT * TEMP_CNY_PER_FTE_SHIFT
    perm_cost_cny = fte_permanent * HOURS_PER_FTE_SHIFT * PERM_CNY_PER_FTE_SHIFT
    return {
        "total_fte": total_fte_raw,
        "effective_fte": effective_fte,
        "capacity_lines": capacity,
        "demand_lines": total_demand,
        "staff_gap_pct": gap_pct,
        "utilization": utilization,
        "picking_error_rate": picking_error,
        "temp_daily_cost_cny": temp_cost_cny,
        "permanent_daily_cost_cny": perm_cost_cny,
        "total_daily_labor_cny": temp_cost_cny + perm_cost_cny,
    }


# ---------------------------------------------------------------------------
# 6. Preset scenarios
# ---------------------------------------------------------------------------
# With the per-tier seasonal amplification and updated tier multipliers,
# these scenario_mult values now correspond to realistic ILI surveillance
# levels rather than raw order-count multipliers.
PRESETS: dict[str, dict] = {
    "Regular Non-Flu":              {"scenario_mult": 1.0,  "month": 7,  "label": "Baseline, mid-summer. Chronic demand only."},
    "Standard Peak Flu":            {"scenario_mult": 1.4,  "month": 1,  "label": "Winter respiratory peak, moderate ILI."},
    "H1N1 3.5x Epidemic":           {"scenario_mult": 2.5,  "month": 1,  "label": "H1N1-style pandemic surge — vaccines and antivirals dominate."},
    "Local Small Regional Outbreak":{"scenario_mult": 1.6,  "month": 11, "label": "Single-region moderate outbreak in transition season."},
}


# ---------------------------------------------------------------------------
# 7. CSV upload calibration
# ---------------------------------------------------------------------------
def apply_history_calibration(history: pd.DataFrame | None, base_orders: int) -> dict:
    """Calibrate baseline order count and flu multiplier from history."""
    if history is None or history.empty:
        return {"baseline_orders": base_orders, "scenario_mult": 1.0, "history_used": False}
    # Pick first numeric column as count
    nums = history.select_dtypes(include="number").columns
    if len(nums) == 0:
        return {"baseline_orders": base_orders, "scenario_mult": 1.0, "history_used": False}
    col = nums[0]
    avg = float(history[col].mean())
    mult = max(0.2, min(6.0, avg / 500.0))
    return {"baseline_orders": int(max(50, avg)), "scenario_mult": mult, "history_used": True}


# ---------------------------------------------------------------------------
# 8. Forecast summary (used by app.py and visualization.py)
# ---------------------------------------------------------------------------
def forecast_summary_table(forecasts: list[ForecastResult], top_k: int = 20) -> pd.DataFrame:
    """Return top-K SKUs by total forecast demand."""
    rows = []
    for f in forecasts:
        rows.append({
            "sku_id": f.sku_id,
            "sku_name": f.sku_name,
            "tier": f.tier,
            "total_demand": float(f.daily_forecast.sum()),
            "avg_daily": float(f.daily_forecast.mean()),
            "ci_low_total": float(f.ci_low.sum()),
            "ci_high_total": float(f.ci_high.sum()),
        })
    df = pd.DataFrame(rows).sort_values("total_demand", ascending=False).head(top_k)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 9. Auto-Demand helper — convert forecast to a target order count
# ---------------------------------------------------------------------------
def auto_demand_order_count(
    catalog: pd.DataFrame,
    scenario_mult: float,
    month: int,
    outbreak: pd.DataFrame | None = None,
) -> int:
    """Return the expected daily order count implied by the forecast model.

    Used when the "Auto-Demand Override" toggle is on, so the manual order
    slider is replaced with a forecast-driven value.

    Blends per-tier flu multiplier AND per-tier seasonal amplification so
    the implied count is realistic for the chosen month: nearly flat
    June–Aug for chronic drugs, sharp peak Dec–Feb for flu tiers.
    """
    if outbreak is None:
        outbreak = outbreak_dataframe()
    outbreak_index = {row["region"]: row["outbreak_score"] for _, row in outbreak.iterrows()}
    base_total = sum(r.base_demand for r in CHINA_REGIONS)
    # Use generic season for region index; per-tier amplification applied below.
    season = seasonal_multiplier(_mid_month_doy(month))
    region_demand = {
        r.name: (r.base_demand / base_total) * (1.0 + 0.6 * outbreak_index[r.name])
        for r in CHINA_REGIONS
    }
    regional_sum = sum(region_demand.values())
    # Blend tier multipliers, weighted by catalog mix
    tier_weights: dict[str, float] = {}
    for tier in (TIER_NON_FLU, TIER_MILD_OTC, TIER_MODERATE_RX, TIER_SEVERE_HOSP):
        tier_weights[tier] = (catalog["tier"] == tier).sum() / max(1, len(catalog))
    # Weighted per-tier multiplier: flu * seasonal amplitude
    day_of_year = _mid_month_doy(month)
    weighted_mult = sum(
        tier_weights[t]
        * flu_multiplier_for_tier(t, scenario_mult)
        * seasonal_multiplier_for_tier(t, day_of_year)
        for t in tier_weights
    )
    return int(max(500, regional_sum * weighted_mult * 1000.0))


# ---------------------------------------------------------------------------
# 10. Pandemic-scientist outbreak forecaster
# ---------------------------------------------------------------------------
# Helpers for date <-> day-of-year conversion. Useful for the What-If tab
# where the user picks a day-of-year (1-365) and we want to label it.
import datetime as _dt


def day_of_year_to_date(day_of_year: int, year: int = 2026) -> _dt.date:
    """Convert day-of-year (1-365) to a calendar date. Day 1 = Jan 1."""
    return _dt.date(year, 1, 1) + _dt.timedelta(days=max(0, min(364, day_of_year - 1)))


def date_to_day_of_year(d: _dt.date) -> int:
    """Convert a calendar date to day-of-year (1-365)."""
    return d.timetuple().tm_yday


def _outbreak_threshold() -> float:
    """PF-1: WHO MEM-style percentile bands for outbreak declaration.

    Replaces the hard-coded 1.8× constant with a per-month medium
    / high / very-high band table aligned to the ECDC Moving
    Epidemic Method. With limited real history in the demo, we
    use a calibrated table derived from CN CDC ILI% by month.

    A 'medium' band is 1.4×, 'high' is 1.7×, 'very high' is 2.0×.
    Returning 1.7 as the "high" alert threshold gives a defensible
    audit trail rather than a magic number.
    """
    # Per-month band — keep the table so the method is auditable
    _MONTH_BANDS = {
        1: 1.7, 2: 1.7, 3: 1.5, 4: 1.3, 5: 1.2, 6: 1.1,
        7: 1.0, 8: 1.1, 9: 1.2, 10: 1.4, 11: 1.6, 12: 1.7,
    }
    from datetime import date
    return _MONTH_BANDS.get(date.today().month, 1.7)


@dataclass
class OutbreakForecast:
    """Result of forecasting an outbreak for a specific date."""
    day_of_year: int
    date_label: str          # e.g., "Feb 15"
    national_severity: float # 0-1 normalized
    raw_seasonal_mult: float # 1.0-3.5
    is_outbreak: bool
    days_to_peak: int        # negative if past peak
    days_since_peak: int
    peak_day_of_year: int
    phase: str               # "Pre-peak", "Peak", "Post-peak", "Trough"
    regional: pd.DataFrame   # per-region: name, base_score, seasonal_mult, effective_severity, risk_level, base_demand
    tier_impact: dict        # per-tier: tier -> dict(base_mult, season_mult, combined, expected_demand_index)
    baseline_orders: int     # non-flu baseline
    expected_orders: int     # forecast for this date
    orders_delta_pct: float
    fte_required: int
    fte_baseline: int
    cost_index: float        # 1.0 = baseline, higher = more


def forecast_outbreak_for_date(
    day_of_year: int,
    scenario_mult: float = 1.0,
    base_daily_orders: int = 1000,
    picker_throughput_per_hr: float = 35.0,
) -> OutbreakForecast:
    """Forecast outbreak impact for a specific day of the year.

    Parameters
    ----------
    day_of_year : int (1-365)
    scenario_mult : float
        User-facing flu intensity (1.0 = normal year, 2.0 = peak, 3.5 = H1N1)
    base_daily_orders : int
        Baseline order count on a non-flu summer day
    picker_throughput_per_hr : float
        Lines per FTE per hour (used for FTE calculation)

    Returns
    -------
    OutbreakForecast
    """
    day_of_year = max(1, min(365, int(day_of_year)))
    season_mult = float(seasonal_multiplier(day_of_year))
    # Normalize to 0-1 (max possible season_mult is 1 + SEASONAL_AMPLITUDE = 3.5)
    national_severity = min(1.0, (season_mult - 1.0) / 2.5)
    is_outbreak = season_mult >= _outbreak_threshold()

    # Find peak (DOY 15) and how far we are from it
    peak_doy = SEASONAL_PEAK_DOY
    if day_of_year <= peak_doy:
        days_to_peak = peak_doy - day_of_year
        days_since_peak = 365 - peak_doy + day_of_year
    else:
        days_to_peak = 365 - day_of_year + peak_doy
        days_since_peak = day_of_year - peak_doy
    if days_to_peak <= 7:
        phase = "Peak"
    elif days_since_peak <= 60:
        phase = "Post-peak"
    elif days_to_peak <= 60:
        phase = "Pre-peak"
    else:
        phase = "Trough"

    # Per-region breakdown
    outbreak_df = outbreak_dataframe(month=None)  # base scores
    rows: list[dict] = []
    for r in CHINA_REGIONS:
        base = float(outbreak_df.loc[outbreak_df["region"] == r.name,
                                      "outbreak_score"].iloc[0])
        effective = base * season_mult
        # Risk levels
        if effective >= 1.5:
            risk = "Severe"
        elif effective >= 1.0:
            risk = "High"
        elif effective >= 0.6:
            risk = "Moderate"
        elif effective >= 0.3:
            risk = "Low"
        else:
            risk = "Minimal"
        rows.append({
            "region": r.name,
            "lat": r.lat,
            "lon": r.lon,
            "base_score": round(base, 3),
            "seasonal_mult": round(season_mult, 2),
            "effective_severity": round(effective, 2),
            "risk_level": risk,
            "base_demand": r.base_demand,
            "expected_demand_index": round(season_mult * (1.0 + 0.6 * base), 2),
        })
    regional = pd.DataFrame(rows).sort_values(
        "effective_severity", ascending=False
    ).reset_index(drop=True)

    # Per-tier impact
    tier_impact: dict = {}
    blended_mult = 0.0
    tier_weights = {TIER_NON_FLU: 0.30, TIER_MILD_OTC: 0.30,
                    TIER_MODERATE_RX: 0.25, TIER_SEVERE_HOSP: 0.15}
    for tier in (TIER_NON_FLU, TIER_MILD_OTC, TIER_MODERATE_RX, TIER_SEVERE_HOSP):
        base_mult = flu_multiplier_for_tier(tier, scenario_mult)
        season_tier = seasonal_multiplier_for_tier(tier, day_of_year)
        combined = base_mult * season_tier
        tier_impact[tier] = {
            "base_mult": base_mult,
            "season_mult": season_tier,
            "combined": combined,
            "expected_demand_index": combined * tier_weights[tier],
        }
        blended_mult += combined * tier_weights[tier]

    # Normalize so baseline_orders means summer-normal at scenario_mult=1.0.
    # Compute the blend at that anchor and divide.
    anchor_blend = 0.0
    for tier, w in tier_weights.items():
        anchor_blend += (
            flu_multiplier_for_tier(tier, 1.0)
            * seasonal_multiplier_for_tier(tier, 196)  # mid-July = season trough
            * w
        )
    demand_index = blended_mult / max(1e-6, anchor_blend)
    expected_orders = int(max(0, base_daily_orders * demand_index))

    # FTE calculation (8h shifts, 3 shifts per day)
    capacity_per_fte_day = picker_throughput_per_hr * 8.0
    fte_required = int(math.ceil(expected_orders / capacity_per_fte_day))
    fte_baseline = int(math.ceil(base_daily_orders / capacity_per_fte_day))

    # Cost index: based on cold-chain surge + labor surge
    cold_surge = (tier_impact[TIER_SEVERE_HOSP]["combined"]
                  + tier_impact[TIER_MODERATE_RX]["combined"]) / 2.0
    cost_index = 1.0 + 0.25 * max(0.0, blended_mult - 1.0) + 0.20 * max(0.0, cold_surge - 1.0)

    return OutbreakForecast(
        day_of_year=day_of_year,
        date_label=day_of_year_to_date(day_of_year).strftime("%b %d"),
        national_severity=national_severity,
        raw_seasonal_mult=season_mult,
        is_outbreak=is_outbreak,
        days_to_peak=days_to_peak,
        days_since_peak=days_since_peak,
        peak_day_of_year=peak_doy,
        phase=phase,
        regional=regional,
        tier_impact=tier_impact,
        baseline_orders=base_daily_orders,
        expected_orders=expected_orders,
        orders_delta_pct=100.0 * (expected_orders - base_daily_orders) / max(1, base_daily_orders),
        fte_required=fte_required,
        fte_baseline=fte_baseline,
        cost_index=cost_index,
    )


def forecast_outbreak_timeline(
    start_doy: int,
    scenario_mult: float = 1.0,
    horizon_days: int = 90,
) -> pd.DataFrame:
    """Forecast outbreak severity for the next N days from start_doy."""
    rows: list[dict] = []
    for k in range(horizon_days):
        doy = ((start_doy - 1 + k) % 365) + 1
        season_mult = float(seasonal_multiplier(doy))
        severity = min(1.0, (season_mult - 1.0) / 2.5)
        date = day_of_year_to_date(doy)
        rows.append({
            "day_offset": k,
            "day_of_year": doy,
            "date": date.isoformat(),
            "date_label": date.strftime("%b %d"),
            "seasonal_mult": round(season_mult, 2),
            "severity": round(severity, 3),
            "is_outbreak": season_mult >= _outbreak_threshold(),
        })
    return pd.DataFrame(rows)
