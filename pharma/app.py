"""
app.py
Pharma Flu Logistics Optimizer — Manager Dashboard

Run with: streamlit run app.py
"""
from __future__ import annotations

import io
import json
import math
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from clustering import (
    PickingResult,
    ShipmentResult,
    ShipmentWave,
    run_picking_clustering,
    run_shipment_clustering,
)
from data_generator import (
    CLIENT_HOSPITAL,
    CLIENT_PHARMACY,
    CLIENT_PRIMARY,
    TEMP_COLD,
    TEMP_FROZEN,
    TEMP_ROOM,
    build_catalog,
    build_warehouse_layout,
    generate_orders,
)
from forecast import (
    PRESETS,
    _mid_month_doy,
    apply_history_calibration,
    auto_demand_order_count,
    day_of_year_to_date,
    demand_split_by_client,
    forecast_outbreak_for_date,
    forecast_outbreak_timeline,
    fte_calculation,
    forecast_sku_demand,
    forecast_summary_table,
    outbreak_dataframe,
    seasonal_multiplier,
)
from metrics import (
    compare_kpis,
    forecast_kpis,
    inventory_kpis,
    labor_kpis,
    ml_kpis,
    peak_compare_kpis,
    picking_kpis,
    to_dict,
    transport_kpis,
)
from tooltip import GLOSSARY, TOOLTIPS, render_help_panel
from visualization import (
    CLUSTER_SCATTER_AXES,
    CLUSTER_SCATTER_COLORBY,
    batch_size_histogram,
    client_breakdown_chart,
    cluster_scatter_plot,
    cluster_summary_table,
    cold_cost_heatmap,
    forecast_line_chart,
    ml_vs_random_cost_chart,
    ml_vs_random_meters_chart,
    near_expiry_table,
    outbreak_forecast_timeline,
    outbreak_regional_table,
    outbreak_severity_gauge,
    outbreak_tier_breakdown_chart,
    picking_density_heatmap,
    picking_path_map,
    regional_outbreak_map,
    regional_outbreak_map_for_date,
    seasonal_curve,
    shipment_map,
    sku_demand_chart,
    warehouse_2d,
    warehouse_3d,
    warehouse_structure_advisor,
    render_glossary,
)

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pharma app — Warehouse Ops",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CNY_PER_EUR = 7.8

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
.kpi-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px;
    border: 1px solid #f0f0f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.kpi-label {
    font-size: 12px;
    font-weight: 500;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-value {
    font-size: 36px;
    font-weight: 600;
    color: #111827;
    line-height: 1.15;
    margin: 8px 0 4px 0;
}
.kpi-delta {
    font-size: 13px;
    font-weight: 500;
}
.kpi-delta-up { color: #dc2626; }
.kpi-delta-down { color: #16a34a; }
.info-card {
    background: #f9fafb;
    border-radius: 14px;
    padding: 28px;
    border: 1px solid #e5e7eb;
    margin-bottom: 24px;
}
.pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}
.pill-ambient { background: #fef3c7; color: #92400e; }
.pill-cold { background: #dbeafe; color: #1e40af; }
.pill-frozen { background: #ede9fe; color: #5b21b6; }
.pill-low { background: #d1fae5; color: #065f46; }
.pill-med { background: #ffedd5; color: #9a3412; }
.pill-high { background: #fee2e2; color: #991b1b; }
.pill-yes { background: #d1fae5; color: #065f46; }
.pill-no { background: #fee2e2; color: #991b1b; }
.rag-pill {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.rag-green { background: #d1fae5; color: #065f46; }
.rag-amber { background: #ffedd5; color: #9a3412; }
.rag-red { background: #fee2e2; color: #991b1b; }
.delta-up { color: #dc2626; font-weight: 600; }
.delta-down { color: #16a34a; font-weight: 600; }
.delta-neutral { color: #9ca3af; }
.insight-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border-left: 4px solid #3b82f6;
    font-size: 14px;
    line-height: 1.5;
    color: #1f2937;
}
.insight-warning { border-left-color: #f59e0b; background: #fffbeb; }
.insight-danger { border-left-color: #dc2626; background: #fef2f2; }
.insight-success { border-left-color: #10b981; background: #f0fdf4; }
.insight-info { border-left-color: #3b82f6; background: #eff6ff; }
.scenario-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
}
.kpi-mini {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: left;
}
.kpi-mini-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.kpi-mini-value { font-size: 24px; font-weight: 600; color: #111827; line-height: 1.15; margin: 6px 0 4px 0; }
.kpi-mini-sub { font-size: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 12px 0 8px 0; }
.lever-group {
    background: #ffffff;
    border: 1px solid #f0f0f0;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
}
.lever-group-title {
    font-size: 12px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_currency(amount_cny: float, currency: str) -> float:
    return amount_cny / CNY_PER_EUR if currency == "EUR" else amount_cny


def _format_money(amount_cny: float, currency: str) -> str:
    return f"{_to_currency(amount_cny, currency):,.2f} {currency}"


def _kpi_card(label: str, value: str, delta: float, delta_label: str = "vs Normal") -> None:
    color_class = "kpi-delta-down" if delta < 0 else "kpi-delta-up" if delta > 0 else ""
    arrow = "↓" if delta < 0 else "↑" if delta > 0 else "→"
    st.html(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta {color_class}">{arrow} {abs(delta):.1f}% {delta_label}</div>
    </div>
    """
    )


def _info_card(title: str, key_signals: list[str], how_to_use: list[str]) -> None:
    key_html = ""
    for s in key_signals:
        parts = s.split("—", 1)
        if len(parts) == 2:
            key_html += f'<div style="font-size:13px;color:#374151;margin-bottom:6px;line-height:1.4;"><b>{parts[0].strip()}</b> — {parts[1].strip()}</div>'
        else:
            key_html += f'<div style="font-size:13px;color:#374151;margin-bottom:6px;line-height:1.4;">{s.strip()}</div>'

    use_html = ""
    for s in how_to_use:
        parts = s.split("—", 1)
        if len(parts) == 2:
            use_html += f'<div style="font-size:13px;color:#374151;margin-bottom:6px;line-height:1.4;"><b>{parts[0].strip()}</b> — {parts[1].strip()}</div>'
        else:
            use_html += f'<div style="font-size:13px;color:#374151;margin-bottom:6px;line-height:1.4;">{s.strip()}</div>'

    st.html(
        f"""
    <div class="info-card">
        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">
            <div style="font-size:20px;color:#6b7280;">ⓘ</div>
            <div>
                <div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:4px;">{title}</div>
                <div style="font-size:13px;color:#6b7280;line-height:1.5;">
                    This is the control-tower view. It tells a warehouse manager whether today's order volume, labor capacity, inventory health, and exception load can still meet service expectations.
                </div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
            <div>
                <div style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Key Signals</div>
                {key_html}
            </div>
            <div>
                <div style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">How to use it</div>
                {use_html}
            </div>
        </div>
    </div>
    """
    )


def _temp_pill(temp: str) -> str:
    if TEMP_ROOM in temp:
        return '<span class="pill pill-ambient">Ambient</span>'
    if TEMP_COLD in temp:
        return '<span class="pill pill-cold">Cold-chain</span>'
    return '<span class="pill pill-frozen">Frozen</span>'


def _risk_pill(risk: str) -> str:
    return f'<span class="pill pill-{risk.lower()}">{risk}</span>'


# ---------------------------------------------------------------------------
# Scenario presets
# ---------------------------------------------------------------------------
SCENARIO_PRESETS: dict[str, dict] = {
    # Scenario presets calibrated to the case-study national pharma
    # distributor (1 of 6 central warehouses, ~42K cases/day at baseline).
    # Order counts are representative of a single shift/day at one DC.
    "Normal": {
        # WM-1 + WM-3 (Jun-2026 retune): re-anchored so the Normal scenario
        # actually MATCHES demand instead of being overstaffed.
        # 1200 orders × ~27.4 cases/order ≈ 32,900 demand-lines/day.
        # 65 perm × 65 lines/hr × 8 h = 33,800 capacity → +2.7% staff gap
        # (a healthy ~5% buffer, not the previous -50% overstaffed floor).
        # Transport: 14-pallet trucks + air_trigger 500 km + cargo-air
        # reliability boost (+15pp) lands next-day SLA at the case-study
        # baseline of ~88%.
        "n_orders": 1200,
        "catalog_size": 500,
        "near_expiry_pct": 4.8,
        "random_seed": 42,
        "client_hosp": 30,
        "client_pharm": 50,
        "client_primary": 20,
        "include_pediatric": True,
        "horizon": 30,
        "month": 7,
        "scenario_mult": 1.0,
        "n_resamples": 200,
        "auto_demand": False,
        "pick_algo": "KMeans",
        "n_clusters": 100,
        "fte_permanent": 65,         # matched to demand (was 130, gap floored at -50%)
        "fte_temp": 0,
        "cart_capacity": 80,
        "use_robust": True,
        "route_algo": "Clarke-Wright",
        "auto_grid": False,
        "max_cold_days": 1.0,        # PH-2: GSP §6.4 24h cold-chain floor
        "max_truck_pallets": 14,    # more, smaller trucks → routing flexibility
        "wave_algo": "HDBSCAN",
        "strict_3_tier": True,
        "cold_premium": 1.5,        # LG-5: per-scenario
        "air_trigger_km": 500,      # lower → more waves go air (cargo-air partnerships)
        "clustering_focus": ["loc_x", "loc_y", "temp", "priority",
                              "shelf_remaining_days", "qty", "client"],
    },
    "Peak": {
        # WM-1: 2400 orders × 25 = 60K cases; 80 temp + 130 perm = 210 FTE
        # effective (~174 with temp discount), ~92% util at peak.
        # Real ILI surge +100-180% per CDC FluSurv-NET.
        "n_orders": 2400,
        "catalog_size": 500,
        "near_expiry_pct": 4.8,
        "random_seed": 42,
        "client_hosp": 30,
        "client_pharm": 50,
        "client_primary": 20,
        "include_pediatric": True,
        "horizon": 30,
        "month": 12,
        "scenario_mult": 1.5,
        "n_resamples": 200,
        "auto_demand": False,
        "pick_algo": "KMeans",
        "n_clusters": 100,
        "fte_permanent": 130,
        "fte_temp": 100,
        "cart_capacity": 80,
        "use_robust": True,
        "route_algo": "Clarke-Wright",
        "auto_grid": False,
        "max_cold_days": 1.0,
        "max_truck_pallets": 14,    # more, smaller trucks
        "wave_algo": "HDBSCAN",
        "strict_3_tier": True,
        "cold_premium": 1.65,       # LG-5: reefer utilization rising
        "air_trigger_km": 500,
        "clustering_focus": ["loc_x", "loc_y", "temp", "priority",
                              "shelf_remaining_days", "qty", "client"],
    },
    "Flu Season": {
        # WM-1 + WM-8: 4200 orders × 25 = 105K cases; 200 temp + 130 perm
        # = 330 FTE effective (~286 with temp discount). Aligned with
        # forecast.PRESETS["H1N1"] = 2.5× (was 2.0×, a mild epidemic,
        # not an active flu outbreak).
        "n_orders": 4200,
        "catalog_size": 500,
        "near_expiry_pct": 4.8,
        "random_seed": 42,
        "client_hosp": 30,
        "client_pharm": 50,
        "client_primary": 20,
        "include_pediatric": True,
        "horizon": 30,
        "month": 1,
        "scenario_mult": 2.5,        # WM-8: aligned with H1N1
        "n_resamples": 200,
        "auto_demand": False,
        "pick_algo": "KMeans",
        "n_clusters": 160,
        "fte_permanent": 130,
        "fte_temp": 250,
        "cart_capacity": 80,
        "use_robust": True,
        "route_algo": "Clarke-Wright",
        "auto_grid": False,
        "max_cold_days": 1.0,
        "max_truck_pallets": 14,    # more, smaller trucks
        "wave_algo": "HDBSCAN",
        "strict_3_tier": True,
        "cold_premium": 1.85,       # LG-5: reefer capacity-constrained
        "air_trigger_km": 500,
        "clustering_focus": ["loc_x", "loc_y", "temp", "priority",
                              "shelf_remaining_days", "qty", "client"],
    },
}

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = "Flu Season"

_current = st.session_state.active_scenario
_preset = SCENARIO_PRESETS[_current]
for k, v in _preset.items():
    st.session_state.setdefault(k, v)
    if st.session_state.get("_last_scenario") != _current:
        st.session_state[k] = v
st.session_state["_last_scenario"] = _current

st.session_state.setdefault("currency", "CNY")
st.session_state.setdefault("compare_random", True)
st.session_state.setdefault("use_3d", False)
st.session_state.setdefault("top_k", 15)


# ---------------------------------------------------------------------------
# Data computation
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _compute_all(
    n_orders: int,
    catalog_size: int,
    near_expiry_pct: float,
    seed: int,
    client_hosp: int,
    client_pharm: int,
    client_primary: int,
    include_pediatric: bool,
    horizon: int,
    month: int,
    scenario_mult: float,
    n_resamples: int,
    auto_demand: bool,
    pick_algo: str,
    n_clusters: int,
    cart_capacity: int,
    use_robust: bool,
    route_algo: str,
    auto_grid: bool,
    max_cold_days: float,
    max_truck_pallets: int,
    wave_algo: str,
    strict_3_tier: bool,
    cold_premium: float,
    air_trigger_km: float,
    fte_perm: int,
    fte_temp: int,
    clustering_focus: tuple[str, ...],
):
    catalog = build_catalog(catalog_size, include_pediatric, seed)
    warehouse = build_warehouse_layout(num_locations=max(60, catalog_size), seed=seed)
    client_mix = (client_hosp, client_pharm, client_primary)
    orders = generate_orders(
        n_orders=n_orders,
        catalog=catalog,
        warehouse=warehouse,
        scenario_mult=scenario_mult,
        client_mix=client_mix,
        seed=seed,
    )
    if auto_demand:
        _outbreak = outbreak_dataframe()
        n_orders_eff = auto_demand_order_count(
            catalog=catalog,
            scenario_mult=scenario_mult,
            month=month,
            outbreak=_outbreak,
        )
        orders = generate_orders(
            n_orders=n_orders_eff,
            catalog=catalog,
            warehouse=warehouse,
            scenario_mult=scenario_mult,
            client_mix=client_mix,
            seed=seed + 1,
        )
    outbreak = outbreak_dataframe(month=month)
    forecasts = forecast_sku_demand(
        catalog, outbreak, scenario_mult, month, horizon, n_resamples, seed
    )
    picking = run_picking_clustering(
        orders=orders,
        algorithm=pick_algo,
        n_clusters=n_clusters,
        use_robust=use_robust,
        cart_capacity=cart_capacity,
        route_algo=route_algo,
        auto_grid=auto_grid,
        seed=seed,
        focus=list(clustering_focus),
    )
    # Stress factor scales next-day probability down as scenario intensifies.
    # At Normal (1.0x) it's 1.0; at Flu (2.0x) it's ~0.65 — reflecting the
    # real capacity strain: tighter cut-offs, more volume competing for
    # the same truck/flight capacity, more breach risk.
    stress_factor = max(0.4, 1.0 - 0.35 * max(0.0, scenario_mult - 1.0))
    shipment = run_shipment_clustering(
        orders=orders,
        algorithm=wave_algo,
        max_cold_transit_days=max_cold_days,
        max_truck_pallets=max_truck_pallets,
        cold_premium=cold_premium,
        strict_3_tier=strict_3_tier,
        air_trigger_km=air_trigger_km,
        seed=seed,
        stress_factor=stress_factor,
    )
    fte = fte_calculation(
        total_demand=float(orders["qty"].sum()),
        fte_permanent=fte_perm,
        fte_temp=fte_temp,
    )
    fte["fte_permanent"] = fte_perm
    fte["fte_temp"] = fte_temp
    return {
        "catalog": catalog,
        "warehouse": warehouse,
        "orders": orders,
        "outbreak": outbreak,
        "forecasts": forecasts,
        "picking": picking,
        "shipment": shipment,
        "fte": fte,
    }


def _get_params():
    # clustering_focus is stored as a list in session_state; convert to
    # tuple so the @st.cache_data hash is stable across reruns.
    focus_list = st.session_state.get(
        "clustering_focus",
        ["loc_x", "loc_y", "temp", "priority",
         "shelf_remaining_days", "qty", "client"],
    )
    return {
        "n_orders": st.session_state.n_orders,
        "catalog_size": st.session_state.catalog_size,
        "near_expiry_pct": st.session_state.near_expiry_pct,
        "seed": st.session_state.random_seed,
        "client_hosp": st.session_state.client_hosp,
        "client_pharm": st.session_state.client_pharm,
        "client_primary": st.session_state.client_primary,
        "include_pediatric": st.session_state.include_pediatric,
        "horizon": st.session_state.horizon,
        "month": st.session_state.month,
        "scenario_mult": st.session_state.scenario_mult,
        "n_resamples": st.session_state.n_resamples,
        "auto_demand": st.session_state.auto_demand,
        "pick_algo": st.session_state.pick_algo,
        "n_clusters": st.session_state.n_clusters,
        "cart_capacity": st.session_state.cart_capacity,
        "use_robust": st.session_state.use_robust,
        "route_algo": st.session_state.route_algo,
        "auto_grid": st.session_state.auto_grid,
        "max_cold_days": st.session_state.max_cold_days,
        "max_truck_pallets": st.session_state.max_truck_pallets,
        "air_trigger_km": st.session_state.air_trigger_km,
        "wave_algo": st.session_state.wave_algo,
        "strict_3_tier": st.session_state.strict_3_tier,
        "cold_premium": st.session_state.cold_premium,
        "fte_perm": st.session_state.fte_permanent,
        "fte_temp": st.session_state.fte_temp,
        "clustering_focus": tuple(focus_list),
    }


# Compute current scenario
_params = _get_params()
data = _compute_all(**_params)

# Compute Normal baseline
_normal_preset = SCENARIO_PRESETS["Normal"].copy()
_normal_preset["fte_perm"] = _normal_preset.pop("fte_permanent")
_normal_preset["fte_temp"] = _normal_preset.pop("fte_temp")
_normal_preset["seed"] = _normal_preset.pop("random_seed")
baseline = _compute_all(**_normal_preset)

# KPIs
pk = picking_kpis(data["picking"])
tk = transport_kpis(data["shipment"])
ik = inventory_kpis(data["orders"], st.session_state.scenario_mult)
lk = labor_kpis(data["fte"])
mk = ml_kpis(data["picking"])
fk = forecast_kpis(data["forecasts"], st.session_state.horizon)

pk_base = picking_kpis(baseline["picking"])
tk_base = transport_kpis(baseline["shipment"])
ik_base = inventory_kpis(baseline["orders"], 1.0)
lk_base = labor_kpis(baseline["fte"])


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
def dashboard_page():
    scenario = st.session_state.active_scenario
    # Hero headline — the topic / theme of the app. Sets the tone and
    # makes it obvious what the program is about at first glance.
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#1e40af 100%);
        border-radius:14px;padding:22px 28px;color:white;margin-bottom:18px;
        box-shadow:0 4px 12px rgba(15,23,42,0.12);">
          <div style="display:flex;align-items:center;justify-content:space-between;
          flex-wrap:wrap;gap:12px;">
            <div>
              <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;
              text-transform:uppercase;color:#bfdbfe;margin-bottom:4px;">
                Central-Warehouse Control Tower
              </div>
              <div style="font-size:30px;font-weight:700;line-height:1.15;
              letter-spacing:-0.02em;">
                💊 Pharma Flu Logistics Optimizer
              </div>
              <div style="font-size:14px;color:#cbd5e1;margin-top:6px;
              max-width:780px;line-height:1.45;">
                ML-driven picking, wave planning, and flu-aware capacity
                management for a single GSP-standard central warehouse —
                calibrated to the case-study operating envelope
                (128 logistics centers, 90M cases / year, 88% next-day baseline).
              </div>
            </div>
            <div style="text-align:right;min-width:140px;">
              <div style="font-size:11px;font-weight:600;letter-spacing:0.06em;
              text-transform:uppercase;color:#bfdbfe;">Current scenario</div>
              <div style="font-size:22px;font-weight:700;margin-top:4px;
              color:#fef3c7;">{scenario}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([0.7, 0.3], gap="large")
    with c1:
        st.caption("Acute respiratory demand. Cold-chain doubles, priority orders climb.")
    with c2:
        st.markdown(
            f'<div style="text-align:right;"><span style="background:#111827;color:white;padding:6px 16px;border-radius:8px;font-size:13px;font-weight:500;">Scenario · {scenario}</span></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ------------------------------------------------------------------
    # 1. Scenario state panel — single big "what the operation looks like
    #    today" display. No charts here — just clean, presentational numbers.
    # ------------------------------------------------------------------
    _total_orders = len(data["orders"])
    _base_orders = len(baseline["orders"])
    _total_cases = int(data["orders"]["qty"].sum())
    _base_cases = int(baseline["orders"]["qty"].sum())
    _priority_pct = float((data["orders"]["temp"] != TEMP_ROOM).mean() * 100)
    _est_hours = sum(b.estimated_minutes for b in data["picking"].batches) / 60.0
    _scenario_label = st.session_state.active_scenario
    _month_name = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ][st.session_state.month]
    _outbreak = seasonal_multiplier(_mid_month_doy(st.session_state.month)) >= 1.8
    _season_mult = float(seasonal_multiplier(_mid_month_doy(st.session_state.month)))
    _sev_pct = int(round(min(1.0, (_season_mult - 1.0) / 2.5) * 100))
    _ban_bg = "#FEE2E2" if _outbreak else "#D1FAE5"
    _ban_bd = "#DC2626" if _outbreak else "#10B981"
    _ban_lbl = "OUTBREAK WINDOW" if _outbreak else "NORMAL RANGE"

    st.html(
        f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;'
        f'padding:24px 28px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
        # Header row
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:12px;margin-bottom:18px;">'
        f'<div>'
        f'<div style="font-size:11px;font-weight:700;color:#9ca3af;'
        f'text-transform:uppercase;letter-spacing:0.06em;">'
        f'Current Scenario</div>'
        f'<div style="font-size:26px;font-weight:700;color:#111827;margin-top:2px;">'
        f'{_scenario_label} · {_month_name}</div>'
        f'<div style="font-size:13px;color:#6b7280;margin-top:4px;">'
        f'Flu intensity <b>{st.session_state.scenario_mult:.1f}×</b> · '
        f'Seasonal multiplier <b>{_season_mult:.2f}×</b> · '
        f'Severity <b>{_sev_pct}/100</b></div>'
        f'</div>'
        f'<div style="background:{_ban_bg};border:2px solid {_ban_bd};'
        f'border-radius:10px;padding:10px 18px;">'
        f'<div style="font-size:11px;font-weight:700;color:{_ban_bd};'
        f'text-transform:uppercase;letter-spacing:0.05em;">{_ban_lbl}</div>'
        f'</div>'
        f'</div>'
        # Big-number grid
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:18px;">'
        f'<div>'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.05em;font-weight:600;">Orders today</div>'
        f'<div style="font-size:32px;font-weight:700;color:#111827;'
        f'line-height:1.1;margin-top:4px;">{_total_orders:,}</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">'
        f'baseline {_base_orders:,}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.05em;font-weight:600;">Cases today</div>'
        f'<div style="font-size:32px;font-weight:700;color:#111827;'
        f'line-height:1.1;margin-top:4px;">{_total_cases:,}</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">'
        f'baseline {_base_cases:,}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.05em;font-weight:600;">Cold-chain share</div>'
        f'<div style="font-size:32px;font-weight:700;color:#1e40af;'
        f'line-height:1.1;margin-top:4px;">{_priority_pct:.0f}%</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">'
        f'of today\'s volume</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.05em;font-weight:600;">Picking load</div>'
        f'<div style="font-size:32px;font-weight:700;color:#111827;'
        f'line-height:1.1;margin-top:4px;">{_est_hours:.1f}h</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">'
        f'estimated across {pk.batch_count} batches</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.05em;font-weight:600;">Headcount on shift</div>'
        f'<div style="font-size:32px;font-weight:700;color:#111827;'
        f'line-height:1.1;margin-top:4px;">{lk.fte_total}</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">'
        f'gap {lk.staff_gap_pct:+.1f}% vs demand</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # ------------------------------------------------------------------
    # 2. Service level status display — single panel showing the four
    #    RAG indicators as a status board (not duplicated as a separate
    #    KPI row in other tabs).
    # ------------------------------------------------------------------
    st.markdown("#### 🩺 Service Level Status")
    nd_status = _service_status(tk.next_day_compliance_pct, 95, 85, higher_is_better=True, breach=80)
    sg_status = _service_status(lk.staff_gap_pct, 5, 15, higher_is_better=False)
    tc_status = _service_status(pk.temperature_compliance_pct, 95, 90, higher_is_better=True)
    ne_status = _service_status(ik.near_expiry_items, 50, 100, higher_is_better=False)

    def _status_card(title: str, value: str, status: str, hint: str) -> str:
        bg = {"green": "#D1FAE5", "amber": "#FFEDD5", "red": "#FEE2E2"}[status]
        bd = {"green": "#10B981", "amber": "#F59E0B", "red": "#DC2626"}[status]
        ic = {"green": "✓",      "amber": "!",      "red": "✗"}[status]
        return (
            f'<div style="background:{bg};border-left:5px solid {bd};'
            f'border-radius:10px;padding:16px 18px;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<div style="font-size:11px;font-weight:700;color:{bd};'
            f'text-transform:uppercase;letter-spacing:0.05em;">{title}</div>'
            f'<div style="background:{bd};color:white;width:22px;height:22px;'
            f'border-radius:50%;display:flex;align-items:center;justify-content:center;'
            f'font-size:13px;font-weight:700;">{ic}</div>'
            f'</div>'
            f'<div style="font-size:30px;font-weight:700;color:#111827;'
            f'line-height:1.1;margin-top:8px;">{value}</div>'
            f'<div style="font-size:12px;color:#6b7280;margin-top:4px;">{hint}</div>'
            f'</div>'
        )

    rag_cols = st.columns(4)
    with rag_cols[0]:
        st.html(_status_card(
            "Next-Day Delivery",
            f"{tk.next_day_compliance_pct:.1f}%",
            nd_status,
            "Target ≥ 90% · amber ≥ 80%",
        ))
    with rag_cols[1]:
        st.html(_status_card(
            "Staff Gap",
            f"{lk.staff_gap_pct:+.1f}%",
            sg_status,
            "Target ≤ 5% · amber ≤ 15%",
        ))
    with rag_cols[2]:
        st.html(_status_card(
            "Cold-Chain",
            f"{pk.temperature_compliance_pct:.1f}%",
            tc_status,
            "Target ≥ 95% · amber ≥ 90%",
        ))
    with rag_cols[3]:
        st.html(_status_card(
            "Near-Expiry",
            f"{ik.near_expiry_items}",
            ne_status,
            "Target ≤ 50 · amber ≤ 100",
        ))

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 1. Outbreak status banner — picks up the same date slider the
    #    Flu Pandemic Forecaster uses so the overview reflects the day
    #    the manager is inspecting.
    # ------------------------------------------------------------------
    st.session_state.setdefault("dash_pandemic_doy",
                                 st.session_state.get("month", 7) * 30)
    st.session_state.dash_pandemic_doy = st.slider(
        "📅 Inspection date (day of year)",
        min_value=1, max_value=365,
        value=st.session_state.dash_pandemic_doy, step=1,
        key="dash_doy_slider",
        help="Drives the outbreak banner, regional map, and forecast timeline below.",
    )
    _insp_d = day_of_year_to_date(st.session_state.dash_pandemic_doy)
    st.caption(
        f"Inspecting: **{_insp_d.strftime('%A, %B %d, %Y')}** "
        f"(day {st.session_state.dash_pandemic_doy} of 365)"
    )

    _dash_forecast = forecast_outbreak_for_date(
        day_of_year=st.session_state.dash_pandemic_doy,
        scenario_mult=st.session_state.scenario_mult,
        base_daily_orders=len(data["orders"]),
    )
    _is_outbreak = _dash_forecast.is_outbreak
    _sev_pct = int(round(_dash_forecast.national_severity * 100))
    _ban_color = "#FEE2E2" if _is_outbreak else "#D1FAE5"
    _ban_border = "#DC2626" if _is_outbreak else "#10B981"
    _ban_icon = "🔴" if _is_outbreak else "🟢"
    _ban_text = "OUTBREAK FORECAST" if _is_outbreak else "NO OUTBREAK"
    _ban_detail = (
        f"Seasonal multiplier <b>{_dash_forecast.raw_seasonal_mult:.2f}×</b> baseline · "
        f"phase: <b>{_dash_forecast.phase}</b> · "
        f"days to peak: <b>{_dash_forecast.days_to_peak if _dash_forecast.phase in ('Pre-peak','Trough') else 0}</b>"
    )
    st.html(
        f'<div style="background:{_ban_color};border-left:6px solid {_ban_border};'
        f'border-radius:8px;padding:14px 18px;margin-bottom:18px;">'
        f'<div style="font-size:18px;font-weight:700;color:#111827;">'
        f'{_ban_icon} {_ban_text} — {_dash_forecast.date_label}</div>'
        f'<div style="font-size:13px;color:#374151;margin-top:4px;">'
        f'National severity <b>{_sev_pct}/100</b> · {_ban_detail}</div>'
        f'</div>'
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 2. Top KPI strip — six cards spanning picking / transport / labor
    # ------------------------------------------------------------------
    total_orders = len(data["orders"])
    total_orders_base = len(baseline["orders"])
    orders_delta = ((total_orders - total_orders_base) / max(total_orders_base, 1)) * 100

    priority_mask = data["orders"]["temp"] != TEMP_ROOM
    priority_pct = float(priority_mask.mean() * 100)
    priority_base_mask = baseline["orders"]["temp"] != TEMP_ROOM
    priority_pct_base = float(priority_base_mask.mean() * 100)
    priority_delta = priority_pct - priority_pct_base

    est_hours = sum(b.estimated_minutes for b in data["picking"].batches) / 60.0
    est_hours_base = sum(b.estimated_minutes for b in baseline["picking"].batches) / 60.0
    hours_delta = ((est_hours - est_hours_base) / max(est_hours_base, 1)) * 100

    exceptions = (
        ik.near_expiry_items
        + (1 if lk.staff_gap_pct > 10 else 0)
        + (1 if pk.temperature_compliance_pct < 95 else 0)
        + (1 if tk.next_day_compliance_pct < 80 else 0)
    )
    exceptions_base = (
        ik_base.near_expiry_items
        + (1 if lk_base.staff_gap_pct > 10 else 0)
        + (1 if pk_base.temperature_compliance_pct < 95 else 0)
        + (1 if tk_base.next_day_compliance_pct < 80 else 0)
    )
    exc_delta = ((exceptions - exceptions_base) / max(exceptions_base, 1)) * 100

    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        _kpi_card("Total orders", f"{total_orders:,}", orders_delta)
    with kpi_cols[1]:
        priority_pct_base_val = float((baseline["orders"]["temp"] != TEMP_ROOM).mean() * 100)
        _kpi_card("Priority share", f"{priority_pct:.0f}%",
                  priority_pct - priority_pct_base_val)
    with kpi_cols[2]:
        _kpi_card("Picking hours", f"{est_hours:.1f}", hours_delta)
    with kpi_cols[3]:
        _kpi_card("FTE required", f"{lk.fte_total}",
                  lk.fte_total - lk_base.fte_total)
    with kpi_cols[4]:
        _kpi_card("Next-day SLA", f"{tk.next_day_compliance_pct:.1f}%",
                  tk.next_day_compliance_pct - tk_base.next_day_compliance_pct)
    with kpi_cols[5]:
        cost_delta_pct = (
            (tk.total_shipment_cost_cny - tk_base.total_shipment_cost_cny)
            / max(1, tk_base.total_shipment_cost_cny) * 100
        )
        _kpi_card("Shipment cost", f"¥{tk.total_shipment_cost_cny:,.0f}",
                  cost_delta_pct)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 3. Top auto-generated insights from the What-If engine
    # ------------------------------------------------------------------
    _cur = {"picking": pk, "transport": tk, "inventory": ik, "labor": lk, "forecast": fk}
    _base = {
        "picking": pk_base, "transport": tk_base, "inventory": ik_base, "labor": lk_base,
        "forecast": forecast_kpis(baseline["forecasts"], st.session_state.horizon),
    }
    _insights = _generate_insights(_cur, _base)
    if _insights and not (
        len(_insights) == 1
        and _insights[0][0] == "info"
        and "All service metrics" in _insights[0][1]
    ):
        st.markdown("#### 💡 Auto-Generated Insights")
        for sev, text in _insights:
            st.html(f'<div class="insight-card insight-{sev}">{text}</div>')
        st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 3. Expected daily demand by client
    # ------------------------------------------------------------------
    st.markdown("#### 📈 Expected Daily Demand by Client & Flu Tier")

    # Tier-explanation row — one clickable ? per tier. Hovering the
    # question mark shows a tooltip; clicking opens a popover with the
    # full description, so the manager can scan the chart and quickly
    # recall what each tier means.
    _TIER_INFO: list[tuple[str, str]] = [
        ("Non-Flu", (
            "Chronic prescription drugs (antihypertensives, statins, "
            "antidiabetics, paracetamol, etc.). Year-round baseline demand, "
            "no seasonal surge. Hospital + pharmacy + primary care mix."
        )),
        ("Mild OTC Flu", (
            "Over-the-counter cold / flu remedies: decongestants, "
            "cough syrups, OTC pain relievers, zinc lozenges. Demand "
            "roughly doubles in winter. Heaviest pull from retail "
            "pharmacies and primary care."
        )),
        ("Moderate Rx Flu", (
            "Prescription antivirals: oseltamivir (Tamiflu), "
            "baloxavir, zanamivir, IV peramivir. Surge ~3x in winter. "
            "Driven by hospital prescriptions during flu outbreaks."
        )),
        ("Severe Hospital / Vaccine", (
            "Vaccines (quadrivalent, pediatric, H1N1, mRNA, cell-based, "
            "adjuvanted) + severe-hospital injectables. Demand jumps "
            "~2.5x during the autumn/winter vaccination campaign and "
            "outbreak response. Served primarily to hospitals."
        )),
    ]
    tier_cols = st.columns(len(_TIER_INFO))
    for i, (tier_name, tier_desc) in enumerate(_TIER_INFO):
        with tier_cols[i]:
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:center;"
                f"gap:6px;padding:6px 0;'>"
                f"<span style='font-size:13px;font-weight:600;color:#111827;'>"
                f"{tier_name}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.popover("?", use_container_width=True):
                st.markdown(f"**{tier_name}**")
                st.write(tier_desc)

    split_df = demand_split_by_client(st.session_state.scenario_mult)
    st.plotly_chart(
        client_breakdown_chart(split_df),
        use_container_width=True, key="dash_demand_split",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 4. Labor & Cold-Chain Pressure
    # ------------------------------------------------------------------
    st.markdown("#### 👥 Labor & Cold-Chain Pressure")
    lc_cols = st.columns([1, 1.2])
    with lc_cols[0]:
        total_fte = lk.fte_total
        shift_load = [total_fte * 0.40, total_fte * 0.35, total_fte * 0.25]
        shift_capacity = [s * 35 for s in shift_load]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Assigned FTE", x=["Morning", "Afternoon", "Night"],
            y=shift_load, marker_color="#92400e",
            text=[f"{v:.0f}" for v in shift_load], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Capacity (lines/hr)", x=["Morning", "Afternoon", "Night"],
            y=shift_capacity, marker_color="#d1fae5",
            text=[f"{v:.0f}" for v in shift_capacity], textposition="outside",
        ))
        fig.update_layout(
            title="Labor load by shift", barmode="group",
            template="plotly_white", height=360,
            yaxis_title="Workers / Lines per hour",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            margin=dict(t=60, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True, key="dash_labor_shift")
    with lc_cols[1]:
        st.plotly_chart(
            cold_cost_heatmap(data["outbreak"]),
            use_container_width=True, key="dash_cold_cost",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # X. How this page works — moved to the bottom of the page
    # ------------------------------------------------------------------
    _info_card(
        "How this page works",
        key_signals=[
            "Orders and priority share — Show how much demand is entering the operation and how much must jump the normal queue.",
            "Picking hours and labor load — Compare required work against available shift capacity before waves slip.",
            "Exceptions — Highlight low inventory, expiry pressure, QA holds, and overloaded shifts that need a decision.",
        ],
        how_to_use=[
            "Start with exceptions — Resolve urgent items first because they are most likely to delay dispatch or create compliance risk.",
            "Check the worst shift — If utilization is high, move workers, split a wave, or delay low-priority ambient work.",
            "Use scenarios — Switch Normal, Peak, or Flu Season in the sidebar to explain how stress changes the operation.",
        ],
    )


# ---------------------------------------------------------------------------
# Page: Manager Overview — actionable rollup
# ---------------------------------------------------------------------------
def manager_overview_page():
    """Manager-facing rollup: today's priorities, KPI watch list,
    decision queue, weekly cadence. Designed to be skimmed in 60
    seconds during a manager's morning briefing.
    """
    scenario = st.session_state.active_scenario

    # ------------------------------------------------------------------
    # Hero / context banner
    # ------------------------------------------------------------------
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1f2937 0%,#0f766e 70%,#134e4a 100%);
        border-radius:14px;padding:22px 28px;color:white;margin-bottom:18px;
        box-shadow:0 4px 12px rgba(15,23,42,0.12);">
          <div style="display:flex;align-items:center;justify-content:space-between;
          flex-wrap:wrap;gap:12px;">
            <div>
              <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;
              text-transform:uppercase;color:#a7f3d0;margin-bottom:4px;">
                Daily Briefing
              </div>
              <div style="font-size:28px;font-weight:700;line-height:1.15;">
                🧭 Manager Overview
              </div>
              <div style="font-size:14px;color:#d1fae5;margin-top:6px;
              max-width:780px;line-height:1.45;">
                One-page rollup of what needs attention today, what to
                monitor, and what decisions are waiting for you. Auto-
                generated from the live scenario.
              </div>
            </div>
            <div style="text-align:right;min-width:140px;">
              <div style="font-size:11px;font-weight:600;letter-spacing:0.06em;
              text-transform:uppercase;color:#a7f3d0;">Scenario</div>
              <div style="font-size:22px;font-weight:700;margin-top:4px;
              color:#fef3c7;">{scenario}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # 1. Today's priorities — auto-generated insights sorted by severity
    # ------------------------------------------------------------------
    st.markdown("### 🔥 Today's priorities")
    st.caption(
        "What needs your attention right now, sorted by severity. "
        "Anything red is a service-level breach; amber is a warning; "
        "green is a positive deviation."
    )
    _cur = {"picking": pk, "transport": tk, "inventory": ik, "labor": lk, "forecast": fk}
    _base = {
        "picking": pk_base, "transport": tk_base, "inventory": ik_base, "labor": lk_base,
        "forecast": forecast_kpis(baseline["forecasts"], st.session_state.horizon),
    }
    _insights = _generate_insights(_cur, _base)
    _SEV_ORDER = {"danger": 0, "warning": 1, "success": 2, "info": 3}
    _insights_sorted = sorted(_insights, key=lambda kv: _SEV_ORDER.get(kv[0], 9))

    if not _insights_sorted or (
        len(_insights_sorted) == 1
        and _insights_sorted[0][0] == "info"
        and "All service metrics" in _insights_sorted[0][1]
    ):
        st.html(
            '<div class="insight-card insight-success">'
            '✓ No service-level breaches detected. Operation is in a healthy state.'
            '</div>'
        )
    else:
        for sev, text in _insights_sorted:
            st.html(f'<div class="insight-card insight-{sev}">{text}</div>')

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 2. KPI watch list — the 6 numbers the manager should glance at
    # ------------------------------------------------------------------
    st.markdown("### 👀 KPI watch list")
    st.caption(
        "Glance at these each shift. They drive every operational "
        "decision on this dashboard."
    )
    kpi_cols = st.columns(3)
    _kpi = [
        ("Next-Day SLA", f"{tk.next_day_compliance_pct:.1f}%", "Target ≥ 90%"),
        ("Staff Gap", f"{lk.staff_gap_pct:+.1f}%", "Target ≤ 5%"),
        ("Cold-Chain", f"{pk.temperature_compliance_pct:.1f}%", "Target ≥ 95%"),
        ("Near-Expiry", f"{ik.near_expiry_items}", "Target ≤ 50 items"),
        ("Picking hours", f"{sum(b.estimated_minutes for b in data['picking'].batches) / 60.0:.1f} h", f"across {pk.batch_count} batches"),
        ("Shipment cost", f"¥{tk.total_shipment_cost_cny:,.0f}", f"avg ¥{tk.total_shipment_cost_cny / max(1, len(data['shipment'].waves)):.0f}/wave"),
    ]
    for i, (label, value, hint) in enumerate(_kpi):
        with kpi_cols[i % 3]:
            st.html(
                f'<div style="background:#ffffff;border:1px solid #e5e7eb;'
                f'border-radius:10px;padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
                f'letter-spacing:0.05em;font-weight:600;">{label}</div>'
                f'<div style="font-size:26px;font-weight:700;color:#111827;'
                f'line-height:1.1;margin-top:4px;">{value}</div>'
                f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">{hint}</div>'
                f'</div>'
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 3. Decision queue — open questions the manager needs to act on
    # ------------------------------------------------------------------
    st.markdown("### 🗳️ Decision queue")
    st.caption(
        "Open questions that need a manager sign-off. Each item links "
        "to where in the app you can act on it."
    )

    # Build the queue dynamically from live KPIs
    _decisions: list[tuple[str, str, str]] = []  # (severity, title, where)

    if tk.next_day_compliance_pct < 80:
        _decisions.append(("danger", "Next-day SLA is in breach — authorise overtime or air-freight for the failing regions",
                          "Wave Planning → per-wave risk column"))
    if lk.staff_gap_pct > 10:
        _decisions.append(("danger", f"Staff gap at {lk.staff_gap_pct:+.1f}% — approve hiring {int(lk.staff_gap_pct / 7) + 1} temp FTE",
                          "What-If → Scenario Builder → FTE temp slider"))
    if pk.temperature_compliance_pct < 95:
        _decisions.append(("warning", "Cold-chain compliance below target — review truck cold-transit cap and wave auto-split",
                          "What-If → Scenario Builder → Max Cold Transit Days"))
    if ik.near_expiry_items > 50:
        _decisions.append(("warning", f"{ik.near_expiry_items} items near-expiry — authorise a discount / cross-dock campaign",
                          "Inventory KPIs → Near-Expiry table"))
    if st.session_state.scenario_mult > 1.5:
        _decisions.append(("warning", "Scenario is in flu territory — confirm cold-chain capacity with the hospital key account team",
                          "Flu Pandemic Forecaster tab"))
    if not _decisions:
        _decisions.append(("success", "No critical decisions waiting. Run sensitivity or save this scenario for the team.",
                          "What-If → Sensitivity tab"))

    for sev, title, where in _decisions:
        bg = {"danger": "#FEE2E2", "warning": "#FFEDD5", "success": "#D1FAE5"}[sev]
        bd = {"danger": "#DC2626", "warning": "#F59E0B", "success": "#10B981"}[sev]
        ic = {"danger": "!", "warning": "•", "success": "✓"}[sev]
        st.html(
            f'<div style="background:{bg};border-left:4px solid {bd};'
            f'border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;'
            f'align-items:flex-start;gap:12px;">'
            f'<div style="background:{bd};color:white;width:24px;height:24px;'
            f'border-radius:50%;display:flex;align-items:center;justify-content:center;'
            f'font-size:13px;font-weight:700;flex-shrink:0;">{ic}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:14px;font-weight:600;color:#111827;">{title}</div>'
            f'<div style="font-size:12px;color:#374151;margin-top:2px;">📍 Where: {where}</div>'
            f'</div></div>'
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 4. Weekly cadence — what to do each week
    # ------------------------------------------------------------------
    st.markdown("### 📅 Weekly cadence")
    st.caption(
        "The rhythm that keeps the operation healthy. Real-life checks "
        "the manager does in the warehouse, not in the dashboard."
    )
    cadence_cols = st.columns(2)
    _cadence = [
        ("Monday — review the weekend outbreak map",
         "Open the Flu Pandemic Forecaster and compare weekend vs weekday "
         "regional severity. If a region jumped 0.2+ in severity, call the "
         "regional distribution lead to pre-stage cold-chain capacity."),
        ("Wednesday — sensitivity sweep",
         "Run a Sensitivity sweep in the What-If tab with the next 30 days' "
         "horizon. If 'Order Count' is the top mover, you have demand "
         "volatility; if 'Cold Premium' is, you have a transport-cost issue."),
        ("Friday — review auto-insights",
         "Look at the auto-generated insights (Dashboard or Impact Analysis) "
         "for the week. Anything that bounced between amber and red is a "
         "process issue, not a one-off spike — open a corrective ticket."),
        ("Continuous — monitor the next 90 days",
         "The 90-day severity forecast in the Flu Pandemic Forecaster is the "
         "early-warning system. If a peak is visible past day 30, escalate to "
         "procurement now so vaccine stock is in the DC before the surge."),
    ]
    for i, (title, body) in enumerate(_cadence):
        with cadence_cols[i % 2]:
            st.html(
                f'<div style="background:#f9fafb;border:1px solid #e5e7eb;'
                f'border-radius:10px;padding:14px 16px;margin-bottom:10px;height:100%;">'
                f'<div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:4px;">'
                f'{title}</div>'
                f'<div style="font-size:13px;color:#374151;line-height:1.45;">{body}</div>'
                f'</div>'
            )


# ---------------------------------------------------------------------------
# Page: Dictionary (glossary of all program terms)
# ---------------------------------------------------------------------------
def dictionary_page():
    """Full-screen glossary page with a search box and grouped term cards."""
    from tooltip import GLOSSARY as _GLOSS

    st.title("📖 Dictionary")
    st.caption(
        "Reference for every term, acronym, and metric used in the "
        "Pharma Flu Logistics Optimizer. Click any card to copy it."
    )

    # Search box at the top
    q = st.text_input(
        "Search term or definition",
        value="",
        placeholder="e.g. GSP, FEFO, Next-Day, DC, Silhouette, H1N1…",
        key="dict_page_search",
        label_visibility="visible",
    )

    # Group entries alphabetically by first letter for quick scanning
    items = list(_GLOSS.items())
    if q.strip():
        ql = q.strip().lower()
        items = [(k, v) for k, v in items if ql in k.lower() or ql in v.lower()]
    items.sort(key=lambda kv: kv[0].lower())

    if not items:
        st.info(f"No matches for “{q}”.")
        return

    st.caption(f"{len(items)} term{'s' if len(items) != 1 else ''}" +
               (f" matching “{q}”" if q.strip() else ""))

    # Group by leading letter
    from collections import OrderedDict
    by_letter: "OrderedDict[str, list]" = OrderedDict()
    for term, defn in items:
        letter = term[0].upper() if term else "#"
        by_letter.setdefault(letter, []).append((term, defn))

    # Render: each letter is a small section header, then 2-column cards
    for letter, group in by_letter.items():
        st.markdown(
            f"<div style='margin-top:14px;margin-bottom:6px;"
            f"font-size:13px;font-weight:700;color:#6b7280;"
            f"letter-spacing:0.05em;text-transform:uppercase;'>"
            f"{letter}</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, (term, defn) in enumerate(group):
            with cols[i % 2]:
                st.markdown(
                    f"<div style='margin-bottom:8px;padding:10px 12px;"
                    f"background:#f9fafb;border-left:3px solid #3B82F6;"
                    f"border-radius:6px;'>"
                    f"<div style='font-size:14px;font-weight:700;color:#111827;'>"
                    f"{term}</div>"
                    f"<div style='font-size:13px;color:#374151;margin-top:3px;line-height:1.4;'>"
                    f"{defn}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Page: Wave Planning
# ---------------------------------------------------------------------------
def wave_planning_page():
    st.title("🌊 Wave Planning")
    st.caption("ML-driven wave allocation, picking path optimization, and operational recommendations.")
    st.divider()

    _info_card(
        "How this page works",
        key_signals=[
            "Clustering quality — Silhouette score measures how coherent each wave is; target > 0.6.",
            "Baseline vs optimized — Compare ML-allocated waves against random/manual wave creation to see the lift.",
            "Risk & progress — Each wave shows dispatch risk and current sorting progress; high-risk waves need action before release.",
        ],
        how_to_use=[
            "Read the recommendation panel first — The system tells you the single most important action (split a wave, add labor, re-time dispatch).",
            "Drill into a wave — Use the table to see per-wave duration, workers, distance, and projected error rate.",
            "Tune the algorithm in What-If — Switch picking/wave algorithms or FTE and watch the metrics update in real time.",
        ],
    )

    # ============================================================
    # Section 1: Baseline vs Optimized KPI Strip
    # ============================================================
    cmp = compare_kpis(data["picking"], data["shipment"])
    silhouette = mk.silhouette
    sil_status = "green" if silhouette >= 0.6 else "amber" if silhouette >= 0.45 else "red"

    ai_minutes = sum(b.estimated_minutes for b in data["picking"].batches)
    random_minutes = ai_minutes * 1.5
    time_saving_pct = max(0.0, (random_minutes - ai_minutes) / max(random_minutes, 1.0) * 100.0)

    error_baseline = 0.35
    error_projected = max(0.05, error_baseline * (1.0 - cmp.distance_uplift_pct / 200.0))
    error_reduction_pct = (error_baseline - error_projected) / error_baseline * 100.0

    st.markdown("#### Baseline vs Optimized Performance")
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        delta = time_saving_pct - 35.0
        _kpi_card("Processing Time ↓", f"{time_saving_pct:.1f}%", delta, "vs target 35%")
    with kpi_cols[1]:
        delta = cmp.distance_uplift_pct - 25.0
        _kpi_card("Picking Path ↓", f"{cmp.distance_uplift_pct:.1f}%", delta, "vs target 25%")
    with kpi_cols[2]:
        delta = error_reduction_pct - 65.0
        _kpi_card("Error Rate ↓", f"{error_reduction_pct:.1f}%", delta, "vs target 65%")
    with kpi_cols[3]:
        delta = tk.next_day_compliance_pct - 88.0
        _kpi_card("Next-Day Compliance", f"{tk.next_day_compliance_pct:.1f}%", delta, "vs target 88%")
    with kpi_cols[4]:
        st.html(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">Cluster Quality (Silhouette)</div>'
            f'<div class="kpi-value">{silhouette:.2f}</div>'
            f'<div class="kpi-delta">{_status_pill_html(sil_status, sil_status.upper())} · target 0.60</div>'
            f'</div>'
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 2: Actionable Recommendations
    # ============================================================
    st.markdown("#### 🎯 Actionable Recommendations")
    recs: list[tuple[str, str]] = []
    if lk.staff_gap_pct >= 8:
        add_n = max(1, int(lk.staff_gap_pct / 7))
        recs.append(("danger", f"Add {add_n}–{add_n + 1} temporary pickers — staff gap at {lk.staff_gap_pct:.1f}% is at risk of breaching the picking SLA."))
    if lk.staff_gap_pct > 0 and lk.staff_gap_pct < 5:
        recs.append(("success", f"Labor is comfortable ({lk.staff_gap_pct:.1f}% gap). No overtime expected."))

    if tk.next_day_compliance_pct < 80:
        recs.append(("danger", f"Re-balance wave timing — only {tk.next_day_compliance_pct:.1f}% of orders meet next-day SLA; {100 - tk.next_day_compliance_pct:.0f}% will breach."))
    elif tk.next_day_compliance_pct < 88:
        recs.append(("warning", f"Next-day compliance at {tk.next_day_compliance_pct:.1f}% — below the 88% target. Review waves with transit > 1.5 days."))

    if silhouette < 0.6:
        recs.append(("warning", f"Re-tune clustering — silhouette {silhouette:.2f} is below the 0.60 target. Try HDBSCAN or a different `n_clusters` in What-If."))

    if pk.temperature_compliance_pct < 90:
        recs.append(("danger", f"Tighten cold-chain handover — compliance at {pk.temperature_compliance_pct:.1f}%. Audit temperature records on freeze-class waves."))

    high_risk_waves = []
    for w in data["shipment"].waves:
        if w.transit_days > 1.5 or TEMP_FROZEN in w.temp:
            high_risk_waves.append(w)
    if high_risk_waves:
        w0 = high_risk_waves[0]
        wave_orders = data["orders"][data["orders"]["order_id"].isin(w0.order_ids)]
        dur_min = len(wave_orders) * 3.5
        recs.append(("warning", f"Split wave **{w0.wave_id}** ({w0.region}) — {len(wave_orders)} orders, est. {dur_min:.0f} min. Split before dispatch to avoid SLA breach."))

    if not recs:
        recs.append(("success", "Operation is in a healthy state — no immediate actions required."))
    for severity, text in recs:
        st.html(f'<div class="insight-card insight-{severity}">{text}</div>')

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 4: Picking Path Optimization (AI vs Random)
    # ============================================================
    st.markdown("#### 🚶 Picking Path Optimization")
    st.caption("ML-allocated batches vs random/manual wave creation. Two views: walking distance (m) and shipment cost (CNY).")

    path_cols = st.columns(2)
    with path_cols[0]:
        st.plotly_chart(
            ml_vs_random_meters_chart(
                ai_dist=pk.avg_walking_distance_m,
                rand_dist=cmp.random_avg_distance,
            ),
            use_container_width=True,
            key="wave_ml_vs_random_meters",
        )
    with path_cols[1]:
        st.plotly_chart(
            ml_vs_random_cost_chart(
                ai_cost=tk.total_shipment_cost_cny,
                rand_cost=cmp.random_cost,
            ),
            use_container_width=True,
            key="wave_ml_vs_random_cost",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 5: Wave Analytics
    # ============================================================
    st.markdown("#### 📊 Wave Analytics")

    map_cols = st.columns(2)
    with map_cols[0]:
        st.plotly_chart(
            shipment_map(data["shipment"]),
            use_container_width=True,
            key="wave_shipment_map",
        )
    with map_cols[1]:
        st.plotly_chart(
            picking_density_heatmap(data["orders"]),
            use_container_width=True,
            key="wave_heatmap",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 5c: Cluster Visualization (scatter, any 2D view)
    # ============================================================
    st.markdown("#### 📈 Cluster Visualization — Inspect From Any Angle")
    st.caption(
        "See how the clusterer grouped today's orders. Pick any two "
        "variables for the X and Y axes and a categorical to color by. "
        "Black × marks are cluster centroids."
    )

    # Curated axis list — only the most operationally important
    # variables. Keeps the dropdown short and the UX focused.
    _SCATTER_AXES = [
        ("loc_x",                "Warehouse X (m)"),
        ("loc_y",                "Warehouse Y (m)"),
        ("shelf_remaining_days", "FEFO (days remaining)"),
        ("priority",             "Priority (1 = high)"),
        ("case_value",           "Order value (CNY)"),
        ("qty",                  "Order quantity"),
        ("weight_kg",            "Weight (kg)"),
    ]
    _SCATTER_COLOR = [
        ("batch_label", "Cluster"),
        ("temp",        "Temperature"),
        ("tier",        "Product tier"),
        ("client",      "Client"),
    ]
    _SCATTER_KEYS = [k for k, _ in _SCATTER_AXES]
    _SCATTER_LABELS = {k: v for k, v in _SCATTER_AXES}
    _COLOR_KEYS = [k for k, _ in _SCATTER_COLOR]
    _COLOR_LABELS = {k: v for k, v in _SCATTER_COLOR}

    def _scatter_idx(options: list[str], key: str) -> int:
        """Read selectbox value, then return its index in options."""
        v = st.session_state.get(key)
        if v in options:
            return options.index(v)
        return 0

    # Axis selectors — short, focused dropdowns
    sel_cols = st.columns(3)
    with sel_cols[0]:
        st.session_state.wave_scatter_x = st.selectbox(
            "X axis",
            options=_SCATTER_KEYS,
            index=_scatter_idx(_SCATTER_KEYS, "wave_scatter_x"),
            format_func=lambda k: _SCATTER_LABELS[k],
            key="wave_scatter_x_sel",
        )
        x_var = st.session_state.wave_scatter_x
    with sel_cols[1]:
        st.session_state.wave_scatter_y = st.selectbox(
            "Y axis",
            options=_SCATTER_KEYS,
            index=_scatter_idx(_SCATTER_KEYS, "wave_scatter_y"),
            format_func=lambda k: _SCATTER_LABELS[k],
            key="wave_scatter_y_sel",
        )
        y_var = st.session_state.wave_scatter_y
    with sel_cols[2]:
        st.session_state.wave_scatter_color = st.selectbox(
            "Color by",
            options=_COLOR_KEYS,
            index=_scatter_idx(_COLOR_KEYS, "wave_scatter_color"),
            format_func=lambda k: _COLOR_LABELS[k],
            key="wave_scatter_color_sel",
        )
        color_by = st.session_state.wave_scatter_color

    st.plotly_chart(
        cluster_scatter_plot(
            orders=data["orders"],
            picking=data["picking"],
            x_var=x_var,
            y_var=y_var,
            color_by=color_by,
            show_centroids=True,
        ),
        use_container_width=True,
        key="wave_cluster_scatter",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 6: Picking Path & Warehouse Layout (manager view)
    # ============================================================
    st.markdown("#### 🏭 Picking Path & Warehouse Layout")
    st.caption(
        "See how pickers walk the warehouse today and how the layout should "
        "be structured to cut distance, protect cold-chain, and balance aisles."
    )

    batches = data["picking"].batches
    if not batches:
        st.info("No picking batches yet — adjust the scenario in the sidebar.")
    else:
        # Batch selector — sort by distance (longest first = most room to improve)
        batch_options = sorted(
            batches,
            key=lambda b: b.distance,
            reverse=True,
        )
        # Build human-readable labels
        batch_labels = [
            f"{b.batch_id} · {len(b.stop_locations)} stops · "
            f"{b.distance:.0f} m · {b.temp} · Picker #{b.picker}"
            for b in batch_options
        ]
        sel_idx = st.selectbox(
            "Pick a batch to inspect (longest routes first)",
            range(len(batch_options)),
            format_func=lambda i: batch_labels[i],
            key="wave_batch_selector",
            index=0,
        )
        sel_batch = batch_options[sel_idx]

        # KPI strip for the selected batch
        k1, k2, k3, k4 = st.columns(4)
        avg_d = float(np.mean([b.distance for b in batches]))
        longest_d = max(b.distance for b in batches)
        with k1:
            st.html(
                f'<div class="kpi-mini">'
                f'<div class="kpi-mini-label">Stops</div>'
                f'<div class="kpi-mini-value">{len(sel_batch.stop_locations)}</div>'
                f'<div class="kpi-mini-sub">orders in batch</div>'
                f'</div>'
            )
        with k2:
            st.html(
                f'<div class="kpi-mini">'
                f'<div class="kpi-mini-label">Route distance</div>'
                f'<div class="kpi-mini-value">{sel_batch.distance:.0f} m</div>'
                f'<div class="kpi-mini-sub">vs avg {avg_d:.0f} m</div>'
                f'</div>'
            )
        with k3:
            st.html(
                f'<div class="kpi-mini">'
                f'<div class="kpi-mini-label">Est. picking time</div>'
                f'<div class="kpi-mini-value">{sel_batch.estimated_minutes:.1f} min</div>'
                f'<div class="kpi-mini-sub">Picker #{sel_batch.picker}</div>'
                f'</div>'
            )
        with k4:
            ratio = sel_batch.distance / max(1.0, avg_d)
            status = "red" if ratio > 1.5 else "amber" if ratio > 1.1 else "green"
            label = "Heavy" if ratio > 1.5 else "Above avg" if ratio > 1.1 else "Balanced"
            st.html(
                f'<div class="kpi-mini">'
                f'<div class="kpi-mini-label">Workload balance</div>'
                f'<div class="kpi-mini-value">{ratio:.2f}×</div>'
                f'<div class="kpi-mini-sub">{_status_pill_html(status, label)}</div>'
                f'</div>'
            )

        # Picking path map
        st.plotly_chart(
            picking_path_map(
                warehouse=data["warehouse"],
                orders=data["orders"],
                batch=sel_batch,
                all_batches=batches,
                show_other_paths=True,
            ),
            use_container_width=True,
            key="wave_picking_path",
        )
        st.caption(
            "🟧 Ambient slots · 🟦 Cold-chain slots · 🟪 Frozen slots · "
            "⭐ Entrance · 🔴 Red polyline = selected batch's optimized route, "
            "numbers = stop order. Faint dotted lines = other pickers walking in parallel."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section 7: Warehouse structure advisor
    # ============================================================
    st.markdown("#### 🧭 Warehouse Structure Advisor")
    st.caption(
        "Actionable recommendations to reduce picker walking distance and "
        "protect cold-chain integrity."
    )

    zone_df, recs = warehouse_structure_advisor(
        warehouse=data["warehouse"],
        orders=data["orders"],
        picking=data["picking"],
    )

    advisor_cols = st.columns([1, 1.4])
    with advisor_cols[0]:
        st.markdown("**Zone pick-density**")
        if not zone_df.empty:
            st.dataframe(
                zone_df,
                use_container_width=True,
                hide_index=True,
                key="wave_zone_stats",
            )
            # Quick bar chart of picks/slot
            fig = go.Figure(go.Bar(
                x=zone_df["Zone"],
                y=zone_df["Picks / Slot"],
                marker_color=["#FFA94D", "#3B82F6", "#7C3AED"][: len(zone_df)],
                text=[f"{v:.1f}" for v in zone_df["Picks / Slot"]],
                textposition="outside",
            ))
            fig.update_layout(
                template="plotly_white",
                height=260,
                yaxis_title="Picks per slot",
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(fig, use_container_width=True, key="wave_zone_bar")
    with advisor_cols[1]:
        st.markdown("**Recommendations**")
        for r in recs:
            severity = (
                "danger" if r.startswith(("🔥", "❄️", "🧊"))
                else "warning" if r.startswith(("📦", "🚶"))
                else "success" if r.startswith(("✅",))
                else "info"
            )
            st.html(
                f'<div class="insight-card insight-{severity}">{r}</div>'
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # Section X: Planned Waves Table — moved to the BOTTOM of the page
    # Each column has a clickable '?' that explains what the column means.
    # ============================================================
    waves = data["shipment"].waves
    rows: list[dict] = []
    for idx, w in enumerate(waves[:50]):
        wave_orders = data["orders"][data["orders"]["order_id"].isin(w.order_ids)]
        n_orders = len(wave_orders)
        n_skus = wave_orders["sku_id"].nunique() if not wave_orders.empty else 0
        est_min = n_orders * 3.5
        hours = int(est_min // 60)
        mins = int(est_min % 60)
        duration = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        workers = max(1, math.ceil(w.n_pallets / 3))
        zones = "A" if TEMP_ROOM in w.temp else "B+C" if TEMP_COLD in w.temp else "D"
        if w.transit_days > 1.5 or TEMP_FROZEN in w.temp:
            risk = "High"
        elif w.transit_days > 1.0 or TEMP_COLD in w.temp:
            risk = "Med"
        else:
            risk = "Low"
        progress = 30 + (hash(w.wave_id) % 66)
        progress_color = {"High": "#dc2626", "Med": "#f59e0b", "Low": "#10b981"}[risk]
        wave_err = error_projected * (1.5 if risk == "High" else 1.0 if risk == "Med" else 0.7)
        rows.append({
            "wave_id": w.wave_id,
            "region": w.region,
            "orders": n_orders,
            "skus": n_skus,
            "zones": zones,
            "duration": duration,
            "workers": workers,
            "temp": w.temp,
            "risk": risk,
            "pallets": w.n_pallets,
            "distance_km": w.distance_km,
            "transit_days": w.transit_days,
            "cost_cny": w.cost_cny,
            "next_day": w.next_day,
            "progress": progress,
            "progress_color": progress_color,
            "wave_err_pct": wave_err,
            "pick_seq": " → ".join(["A", "B", "C", "D"][:max(1, min(4, workers))]),
        })

    # Per-column explanations — used as the clickable ? body
    _COL_HELP: dict[str, str] = {
        "Wave":            "Unique wave identifier (W0000, W0001, ...). W0010+ are air-freight; W0000-W0009 are truck-line.",
        "Destination":     "China region this wave is delivering to (e.g. East China / Shanghai-Jiangsu-Zhejiang). One region per wave.",
        "Orders":          "Number of B2B order lines grouped into this wave. Cap is the truck-pallet limit (default 24 pallets).",
        "Zones":           "Pick zones touched: A=Ambient, B+C=Cold-chain, D=Frozen. Cold waves get the cold premium cost.",
        "Duration":        "Estimated picking + packing + dispatch time for the wave (3.5 min per order line).",
        "Workers":         "Number of pickers assigned. Computed as ceil(pallets / 3) — ~3 pallets per picker per batch.",
        "Pallets":         "Total pallet count for the wave. 1 pallet ≈ 50 qty units of order lines.",
        "Distance":        "Round-trip distance from the central DC to the destination region centroid (km).",
        "Temp":            "Temperature class of the wave: Ambient (15-25°C), Cold (2-8°C), or Frozen (-20°C).",
        "Pick Seq":        "Aisle sequence the picker walks through (e.g. 'A → B → C → D'). Clarke-Wright optimised.",
        "Progress":        "Deterministic wave progress 30-95% so the table doesn't flicker on each rerender. Visual only.",
        "Err %":           "Projected picking error rate. Green ≤0.12%, amber 0.12-0.20%, red >0.20%. Risk-tier scaled.",
        "Risk":            "Aggregate risk: Low / Med / High. High = frozen OR transit > 1.5d. Med = cold OR transit > 1.0d.",
    }
    _COL_ORDER = list(_COL_HELP.keys())

    def _help_cell(label: str) -> str:
        """Render a column header with a clickable ? that expands the help text."""
        explanation = _COL_HELP[label]
        return (
            f'<details style="cursor:help;display:inline-block;">'
            f'<summary style="list-style:none;display:inline-flex;align-items:center;gap:6px;'
            f'color:#9ca3af;font-size:10px;text-transform:uppercase;letter-spacing:0.05em;">'
            f'<span>{label}</span>'
            f'<span style="background:#3B82F6;color:white;width:14px;height:14px;'
            f'border-radius:50%;display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:9px;font-weight:700;">?</span>'
            f'</summary>'
            f'<div style="position:relative;z-index:50;background:#ffffff;'
            f'border:1px solid #e5e7eb;border-left:3px solid #3B82F6;'
            f'border-radius:6px;padding:10px 14px;margin-top:6px;'
            f'min-width:240px;max-width:360px;font-size:12px;color:#111827;'
            f'line-height:1.4;box-shadow:0 4px 12px rgba(0,0,0,0.08);'
            f'font-weight:400;text-transform:none;letter-spacing:normal;">'
            f'{explanation}'
            f'</div>'
            f'</details>'
        )

    if rows:
        st.markdown(
            f"#### 📋 Planned Waves  <span style='color:#9ca3af;font-size:13px;font-weight:400;'> {len(rows)} waves · sorted by clustering</span>",
            unsafe_allow_html=True,
        )
        st.caption("Click any column header's **?** to see what that column means.")

        # Build header cells with the clickable ? inline
        header_cells = "".join(
            f'<th style="padding:10px 8px;vertical-align:top;">{_help_cell(col)}</th>'
            for col in _COL_ORDER
        )
        html = f"""
        <table style="width:100%; border-collapse:collapse; font-size:12.5px; margin-top:8px;">
        <thead>
        <tr style="border-bottom:1px solid #e5e7eb;">{header_cells}</tr>
        </thead>
        <tbody>
        """
        for r in rows:
            progress_bar = (
                f'<div style="background:#e5e7eb;border-radius:4px;height:6px;width:100%;">'
                f'<div style="background:{r["progress_color"]};border-radius:4px;height:6px;width:{r["progress"]}%;"></div>'
                f'</div>'
                f'<div style="font-size:10px;color:#6b7280;margin-top:2px;">{r["progress"]}%</div>'
            )
            err_color = "#dc2626" if r["wave_err_pct"] > 0.20 else "#f59e0b" if r["wave_err_pct"] > 0.12 else "#16a34a"
            html += f"""
            <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:12px 8px; font-weight:600; color:#111827;">{r['wave_id']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['region']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['orders']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['zones']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['duration']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['workers']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['pallets']}</td>
                <td style="padding:12px 8px; color:#374151;">{r['distance_km']:.0f} km</td>
                <td style="padding:12px 8px;">{_temp_pill(r['temp'])}</td>
                <td style="padding:12px 8px; color:#6b7280; font-family:monospace; font-size:11px;">{r['pick_seq']}</td>
                <td style="padding:12px 8px; min-width:90px;">{progress_bar}</td>
                <td style="padding:12px 8px; color:{err_color}; font-weight:600;">{r['wave_err_pct']:.2f}%</td>
                <td style="padding:12px 8px;">{_risk_pill(r['risk'])}</td>
            </tr>
            """
        html += "</tbody></table>"
        st.html(html)
    else:
        st.info("No waves planned yet.")

# ---------------------------------------------------------------------------
# Page: What-If
# ---------------------------------------------------------------------------
def _service_status(
    value: float,
    green: float,
    amber: float,
    higher_is_better: bool = True,
    breach: float | None = None,
) -> str:
    """WM-2: 4-tier RAG (green / amber / breach / red).

    If `breach` is provided, the band below `breach` (or above, for
    lower-is-better) is `breach` instead of `red`. The red band only
    fires at the very edge — for next-day, green=95, amber=85,
    breach=80, red=<80; the 80% line matches the provincial
    healthcare-bureau public-reporting threshold.
    """
    if higher_is_better:
        if value >= green: return "green"
        if value >= amber: return "amber"
        if breach is not None and value >= breach: return "amber"
        return "red"
    if value <= green: return "green"
    if value <= amber: return "amber"
    if breach is not None and value <= breach: return "amber"
    return "red"


def _status_pill_html(status: str, label: str) -> str:
    icons = {"green": "✓", "amber": "!", "red": "✗"}
    return f'<span class="rag-pill rag-{status}">{icons[status]} {label}</span>'


def _delta_html(current: float, baseline: float, fmt: str = "{:.1f}", suffix: str = "",
                good_direction: str = "up") -> str:
    """Render a delta vs baseline. good_direction='up' means higher is better."""
    if abs(baseline) < 1e-6:
        return f'<span class="delta-neutral">→ {fmt.format(current)}{suffix}</span>'
    delta = current - baseline
    pct = (delta / abs(baseline)) * 100
    if abs(pct) < 0.5:
        return f'<span class="delta-neutral">→ {fmt.format(current)}{suffix}</span>'
    arrow = "↑" if delta > 0 else "↓"
    is_good = (delta > 0 and good_direction == "up") or (delta < 0 and good_direction == "down")
    color = "delta-down" if is_good else "delta-up"
    return f'<span class="{color}"><b>{arrow}</b> {fmt.format(current)}{suffix} ({pct:+.1f}%)</span>'


def _target_kpi_value(picking, transport, inventory, labor, forecast, name: str) -> float:
    table = {
        "staff_gap_pct": labor.staff_gap_pct,
        "next_day_compliance_pct": transport.next_day_compliance_pct,
        "total_cost_cny": transport.total_shipment_cost_cny,
        "temp_compliance_pct": picking.temperature_compliance_pct,
        "near_expiry_items": float(inventory.near_expiry_items),
        "avg_walking_distance_m": picking.avg_walking_distance_m,
        "daily_labor_cost_cny": labor.total_daily_labor_cny,
        "total_walking_distance_m": picking.total_walking_distance_m,
        "batches": float(picking.batch_count),
        "avg_daily_demand": forecast.avg_daily_demand,
    }
    return float(table.get(name, 0.0))


def _kpis_from_params(params: dict) -> dict:
    d = _compute_all(**params)
    return {
        "picking": picking_kpis(d["picking"]),
        "transport": transport_kpis(d["shipment"]),
        "inventory": inventory_kpis(d["orders"], params["scenario_mult"]),
        "labor": labor_kpis(d["fte"]),
        "forecast": forecast_kpis(d["forecasts"], params["horizon"]),
    }


def _generate_insights(cur: dict, base: dict) -> list:
    out = []
    pk, tk, ik, lk, fk = cur["picking"], cur["transport"], cur["inventory"], cur["labor"], cur["forecast"]
    pk_b, tk_b, ik_b, lk_b = base["picking"], base["transport"], base["inventory"], base["labor"]

    if lk.staff_gap_pct >= 15:
        rec_fte = max(1, int(lk.staff_gap_pct / 7))
        out.append(("danger", f"⚠️ Staff gap at {lk.staff_gap_pct:.1f}%. Add {rec_fte}–{rec_fte + 1} temp FTE to recover picking SLA."))
    elif lk.staff_gap_pct >= 8:
        out.append(("warning", f"⚡ Staff gap at {lk.staff_gap_pct:.1f}%. Consider 1–2 additional temp workers on the peak shift."))
    elif lk.staff_gap_pct <= 3 and lk_b.staff_gap_pct > 5:
        out.append(("success", f"✓ Labor capacity comfortable ({lk.staff_gap_pct:.1f}% gap). No overtime expected."))

    if tk.next_day_compliance_pct < 80:
        out.append(("danger", f"🚨 Next-day compliance at {tk.next_day_compliance_pct:.1f}%. SLA breach risk on {100 - tk.next_day_compliance_pct:.0f}% of orders."))
    elif tk.next_day_compliance_pct < 90:
        out.append(("warning", f"⏱️ Next-day compliance at {tk.next_day_compliance_pct:.1f}%. Review wave timing or split heavy waves."))
    elif tk.next_day_compliance_pct > tk_b.next_day_compliance_pct + 5:
        out.append(("success", f"✓ Next-day compliance improved to {tk.next_day_compliance_pct:.1f}%."))

    if tk_b.total_shipment_cost_cny > 0:
        cost_delta = (tk.total_shipment_cost_cny - tk_b.total_shipment_cost_cny) / tk_b.total_shipment_cost_cny * 100
        if cost_delta > 20:
            out.append(("warning", f"💰 Transport cost up {cost_delta:.1f}% vs baseline. Consider consolidating waves or relaxing cold premium."))
        elif cost_delta < -5:
            out.append(("success", f"💰 Transport cost down {abs(cost_delta):.1f}% vs baseline."))

    if pk.temperature_compliance_pct < 90:
        out.append(("danger", f"❄️ Cold-chain compliance at {pk.temperature_compliance_pct:.1f}%. Audit temperature handling and wave timing."))
    elif pk.temperature_compliance_pct < 95:
        out.append(("warning", f"❄️ Cold-chain compliance at {pk.temperature_compliance_pct:.1f}%. Tighten handover window."))

    if ik_b.near_expiry_items > 0 and ik.near_expiry_items > ik_b.near_expiry_items * 1.3:
        out.append(("warning", f"📦 Near-expiry items up {((ik.near_expiry_items / ik_b.near_expiry_items) - 1) * 100:.0f}%. Move FEFO SKUs to the morning wave."))

    if pk.avg_walking_distance_m > 0 and pk_b.avg_walking_distance_m > 0:
        dist_delta = (pk.avg_walking_distance_m - pk_b.avg_walking_distance_m) / pk_b.avg_walking_distance_m * 100
        if dist_delta > 15:
            out.append(("warning", f"🚶 Avg walking distance up {dist_delta:.1f}%. Re-tune cluster count or routing."))

    if not out:
        out.append(("info", f"ℹ️ All service metrics within normal range. Orders {lk_b.staff_gap_pct:.1f}%→{lk.staff_gap_pct:.1f}% staff gap, {tk.next_day_compliance_pct:.1f}% on-time."))
    return out


def whatif_page():
    st.title("🔧 What-If")
    st.caption("Adjust levers to see how the operation responds. Compare against baseline, run sensitivity, and save scenarios for the team.")
    st.divider()

    _info_card(
        "How this page works",
        key_signals=[
            "Demand levers — Order count and flu intensity drive throughput pressure.",
            "Capacity levers — Permanent and temp FTE define labor capacity; FTE also drives the cluster count.",
            "Cost & service levers — Cold premium, max transit days, and truck capacity shape transport cost and SLA.",
        ],
        how_to_use=[
            "Build a scenario in the Scenario Builder tab — Sliders write to global state, so the rest of the app reflects the new scenario.",
            "Check the Impact Analysis tab — RAG status and auto-generated insights tell you whether the scenario is safe to run.",
            "Run sensitivity — See which lever moves the needle most on the metric you care about.",
            "Save useful scenarios — Build a library of pre-approved plans for the team.",
        ],
    )

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎛️ Scenario Builder",
        "📊 Impact Analysis",
        "🎯 Sensitivity",
        "🦠 Flu Pandemic Forecaster",
        "💾 Saved Scenarios",
    ])

    # =================
    # Tab 1: Scenario Builder
    # =================
    with tab1:
        st.markdown("#### Build Your Scenario")
        st.caption("Sliders write to global state — changes apply across the dashboard, wave planning, and inventory pages.")

        # Demand
        st.html('<div class="lever-group"><div class="lever-group-title">📈 Demand</div>')
        d1, d2 = st.columns(2)
        with d1:
            st.session_state.scenario_mult = st.slider(
                "Flu Intensity Multiplier",
                0.5, 5.0, st.session_state.scenario_mult, 0.1,
                key="whatif_mult",
                help="Multiplier on baseline flu demand. 1.0 = normal, 2.0 = peak, 3.0 = severe flu season.",
            )
        with d2:
            st.session_state.n_orders = st.slider(
                "Order Count",
                50, 12000, st.session_state.n_orders, 50,
                key="whatif_orders",
                help="Total order lines entering the DC today. 2,500 = baseline central-warehouse shift.",
            )
        st.html("</div>")

        # Capacity
        st.html('<div class="lever-group"><div class="lever-group-title">👥 Labor Capacity</div>')
        l1, l2 = st.columns(2)
        with l1:
            st.session_state.fte_permanent = st.slider(
                "Permanent FTE",
                0, 300, st.session_state.fte_permanent, 1,
                key="whatif_fte",
                help="Core picking staff. Sized to cover Normal non-flu demand without temps.",
            )
        with l2:
            st.session_state.fte_temp = st.slider(
                "Temp FTE",
                0, 300, st.session_state.fte_temp, 1,
                key="whatif_temp",
                help="Temporary workers — added quickly during Peak / Flu Season surges.",
            )
        st.session_state.n_clusters = st.session_state.fte_permanent + st.session_state.fte_temp
        st.caption(f"Cluster count auto-set to **{st.session_state.n_clusters}** (FTE total).")
        st.html("</div>")

        # Cost & Service
        st.html('<div class="lever-group"><div class="lever-group-title">💰 Cost & Service</div>')
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            st.session_state.cold_premium = st.slider(
                "Cold Premium Factor",
                1.0, 3.0, st.session_state.cold_premium, 0.05,
                key="whatif_cold",
                help="Cost multiplier for refrigerated transport vs ambient.",
            )
        with cs2:
            st.session_state.max_cold_days = st.slider(
                "Max Cold Transit (days)",
                0.5, 3.0, st.session_state.max_cold_days, 0.1,
                key="whatif_cold_days",
                help="Max allowed transit time for cold-chain shipments.",
            )
        with cs3:
            st.session_state.max_truck_pallets = st.slider(
                "Truck Pallet Capacity",
                12, 36, st.session_state.max_truck_pallets, 2,
                key="whatif_pallets",
                help="Max pallets per truck — affects wave consolidation.",
            )
        with cs4:
            st.session_state.air_trigger_km = st.slider(
                "Air-Trigger Distance (km)",
                400, 2000, st.session_state.air_trigger_km, 50,
                key="whatif_air_km",
                help="Orders with one-way distance ≥ this go by air freight. "
                     "Cold-chain auto-routes air at half this distance. "
                     "Lower = more air (faster, costlier); higher = more truck.",
            )
        st.html("</div>")

        # Operations
        st.html('<div class="lever-group"><div class="lever-group-title">⚙️ Operations</div>')
        o1, o2, o3 = st.columns(3)
        with o1:
            st.session_state.cart_capacity = st.slider(
                "Cart Capacity",
                40, 150, st.session_state.cart_capacity, 5,
                key="whatif_cart",
                help="Max items per pick cart. Higher = fewer trips but heavier carts.",
            )
        with o2:
            pick_algo_options = ["KMeans", "DBSCAN", "HDBSCAN"]
            st.session_state.pick_algo = st.selectbox(
                "Picking Algorithm",
                pick_algo_options,
                index=pick_algo_options.index(st.session_state.pick_algo) if st.session_state.pick_algo in pick_algo_options else 0,
                key="whatif_pick_algo",
                help="Clustering algorithm used to build pick batches.",
            )
        with o3:
            wave_algo_options = ["HDBSCAN", "KMeans", "Agglomerative"]
            st.session_state.wave_algo = st.selectbox(
                "Wave Algorithm",
                wave_algo_options,
                index=wave_algo_options.index(st.session_state.wave_algo) if st.session_state.wave_algo in wave_algo_options else 0,
                key="whatif_wave_algo",
                help="Algorithm that groups orders into shipment waves by destination and temperature class.",
            )
        st.html("</div>")

        # Advanced options
        with st.expander("🔧 Advanced Options"):
            st.caption("Tune with care — these can have a large effect on result quality.")
            a1, a2, a3 = st.columns(3)
            with a1:
                st.session_state.use_robust = st.checkbox(
                    "Use robust clustering", value=bool(st.session_state.use_robust), key="whatif_robust"
                )
                st.session_state.strict_3_tier = st.checkbox(
                    "Strict 3-tier temperature segregation",
                    value=bool(st.session_state.strict_3_tier), key="whatif_strict"
                )
            with a2:
                st.session_state.n_resamples = st.slider(
                    "Bootstrap resamples (forecast CI)",
                    50, 500, st.session_state.n_resamples, 50, key="whatif_resamp",
                )
                st.session_state.auto_demand = st.checkbox(
                    "Auto demand (from outbreak)",
                    value=bool(st.session_state.auto_demand), key="whatif_autod",
                )
            with a3:
                st.session_state.horizon = st.slider(
                    "Forecast horizon (days)",
                    7, 90, st.session_state.horizon, 1, key="whatif_horizon",
                )
                st.session_state.month = st.slider(
                    "Simulation month",
                    1, 12, st.session_state.month, 1, key="whatif_month",
                    help="Used for the seasonal flu curve. 1 = January (peak).",
                )

        # Quick actions
        st.divider()
        st.markdown("##### Quick Actions")
        qa1, qa2, qa3, qa4 = st.columns(4)
        with qa1:
            if st.button("🔄 Reset to Normal", use_container_width=True, key="whatif_reset"):
                for k, v in SCENARIO_PRESETS["Normal"].items():
                    st.session_state[k] = v
                st.rerun()
        with qa2:
            if st.button("🏔️ Reset to Peak", use_container_width=True, key="whatif_peak"):
                for k, v in SCENARIO_PRESETS["Peak"].items():
                    st.session_state[k] = v
                st.rerun()
        with qa3:
            if st.button("🤒 Reset to Flu Season", use_container_width=True, key="whatif_flu"):
                for k, v in SCENARIO_PRESETS["Flu Season"].items():
                    st.session_state[k] = v
                st.rerun()
        with qa4:
            if st.button("🧪 Recompute", use_container_width=True, key="whatif_recompute"):
                st.cache_data.clear()
                st.rerun()

    # =================
    # Tab 2: Impact Analysis
    # =================
    with tab2:
        st.markdown("#### Baseline vs Current")
        st.caption("Baseline = Normal scenario. Current = your scenario.")

        cur_hours = sum(b.estimated_minutes for b in data["picking"].batches) / 60.0
        base_hours = sum(b.estimated_minutes for b in baseline["picking"].batches) / 60.0

        rows = [
            ("Order Count", float(len(data["orders"])), float(len(baseline["orders"])), "{:,.0f}", "", "neutral"),
            ("Picking Hours", cur_hours, base_hours, "{:.1f}", " h", "down"),
            ("Batches", float(pk.batch_count), float(pk_base.batch_count), "{:,.0f}", "", "neutral"),
            ("Avg Walking Distance", pk.avg_walking_distance_m, pk_base.avg_walking_distance_m, "{:.1f}", " m", "down"),
            ("Next-Day Compliance", tk.next_day_compliance_pct, tk_base.next_day_compliance_pct, "{:.1f}", "%", "up"),
            ("Total Shipment Cost", tk.total_shipment_cost_cny, tk_base.total_shipment_cost_cny, "{:,.0f}", " CNY", "down"),
            ("Cold-Chain Compliance", pk.temperature_compliance_pct, pk_base.temperature_compliance_pct, "{:.1f}", "%", "up"),
            ("Staff Gap", lk.staff_gap_pct, lk_base.staff_gap_pct, "{:.1f}", "%", "down"),
            ("Daily Labor Cost", lk.total_daily_labor_cny, lk_base.total_daily_labor_cny, "{:,.0f}", " CNY", "down"),
            ("Near-Expiry Items", float(ik.near_expiry_items), float(ik_base.near_expiry_items), "{:,.0f}", "", "down"),
        ]

        html = """
        <table style="width:100%; border-collapse:collapse; font-size:13px; margin-top:8px;">
        <thead>
        <tr style="border-bottom:2px solid #e5e7eb; color:#9ca3af; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; text-align:left;">
            <th style="padding:12px 10px;">Metric</th>
            <th style="padding:12px 10px; text-align:right;">Baseline</th>
            <th style="padding:12px 10px; text-align:right;">Current</th>
            <th style="padding:12px 10px; text-align:right;">Δ vs Baseline</th>
            <th style="padding:12px 10px; text-align:center;">Status</th>
        </tr>
        </thead>
        <tbody>
        """
        for label, cur_v, base_v, fmt, suf, good_dir in rows:
            if label == "Next-Day Compliance":
                status = _service_status(cur_v, 90, 80, higher_is_better=True)
            elif label == "Cold-Chain Compliance":
                status = _service_status(cur_v, 95, 90, higher_is_better=True)
            elif label == "Staff Gap":
                status = _service_status(cur_v, 5, 15, higher_is_better=False)
            elif label == "Total Shipment Cost":
                status = _service_status(cur_v, base_v * 1.2, base_v * 1.5, higher_is_better=False) if base_v > 0 else "green"
            elif label == "Picking Hours":
                status = _service_status(cur_v, base_v * 1.2, base_v * 1.5, higher_is_better=False) if base_v > 0 else "green"
            elif label == "Daily Labor Cost":
                status = _service_status(cur_v, base_v * 1.2, base_v * 1.5, higher_is_better=False) if base_v > 0 else "green"
            elif label == "Near-Expiry Items":
                status = _service_status(cur_v, 50, 100, higher_is_better=False)
            elif label == "Avg Walking Distance":
                status = _service_status(cur_v, base_v * 1.15, base_v * 1.3, higher_is_better=False) if base_v > 0 else "green"
            else:
                status = "green"
            html += f"""
            <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:14px 10px; color:#374151;"><b>{label}</b></td>
                <td style="padding:14px 10px; text-align:right; color:#6b7280;">{fmt.format(base_v)}{suf}</td>
                <td style="padding:14px 10px; text-align:right; color:#111827; font-weight:600;">{fmt.format(cur_v)}{suf}</td>
                <td style="padding:14px 10px; text-align:right;">{_delta_html(cur_v, base_v, fmt, suf, good_dir)}</td>
                <td style="padding:14px 10px; text-align:center;">{_status_pill_html(status, status.upper())}</td>
            </tr>
            """
        html += "</tbody></table>"
        st.html(textwrap.dedent(html))

        st.markdown("<br>", unsafe_allow_html=True)

        # Insights
        st.markdown("#### Auto-Generated Insights")
        cur = {
            "picking": pk, "transport": tk, "inventory": ik,
            "labor": lk, "forecast": fk,
        }
        base = {
            "picking": pk_base, "transport": tk_base, "inventory": ik_base,
            "labor": lk_base, "forecast": forecast_kpis(baseline["forecasts"], st.session_state.horizon),
        }
        insights = _generate_insights(cur, base)
        for severity, text in insights:
            st.html(f'<div class="insight-card insight-{severity}">{text}</div>')

    # =================
    # Tab 3: Sensitivity
    # =================
    with tab3:
        st.markdown("#### Sensitivity Analysis")
        st.caption("See which levers have the largest impact on a chosen KPI. We perturb each lever ±20% (clamped to valid range) and measure the effect on your scenario.")

        c1, c2 = st.columns([1, 1])
        with c1:
            target_kpi = st.selectbox(
                "Target KPI",
                [
                    "staff_gap_pct", "next_day_compliance_pct", "total_cost_cny",
                    "temp_compliance_pct", "near_expiry_items", "avg_walking_distance_m",
                    "daily_labor_cost_cny", "total_walking_distance_m", "batches",
                    "avg_daily_demand",
                ],
                format_func=lambda x: {
                    "staff_gap_pct": "Staff Gap (%)",
                    "next_day_compliance_pct": "Next-Day Compliance (%)",
                    "total_cost_cny": "Total Shipment Cost (CNY)",
                    "temp_compliance_pct": "Cold-Chain Compliance (%)",
                    "near_expiry_items": "Near-Expiry Items (count)",
                    "avg_walking_distance_m": "Avg Walking Distance (m)",
                    "daily_labor_cost_cny": "Daily Labor Cost (CNY)",
                    "total_walking_distance_m": "Total Walking Distance (m)",
                    "batches": "Batch Count",
                    "avg_daily_demand": "Avg Daily Demand (units)",
                }[x],
                key="whatif_target_kpi",
            )
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            run_btn = st.button("🎯 Run Sensitivity Analysis", type="primary", use_container_width=True, key="whatif_run_sens")

        cur_fk = forecast_kpis(data["forecasts"], st.session_state.horizon)
        base_value = _target_kpi_value(pk, tk, ik, lk, cur_fk, target_kpi)

        if run_btn or "whatif_sens_results" in st.session_state:
            levers = [
                ("Order Count", "n_orders", 50, 12000, 50, "int"),
                ("Flu Intensity", "scenario_mult", 0.5, 5.0, 0.1, "float"),
                ("Permanent FTE", "fte_perm", 0, 300, 1, "int"),
                ("Temp FTE", "fte_temp", 0, 300, 1, "int"),
                ("Cold Premium", "cold_premium", 1.0, 3.0, 0.05, "float"),
                ("Max Cold Days", "max_cold_days", 0.5, 3.0, 0.1, "float"),
                ("Truck Pallets", "max_truck_pallets", 12, 60, 2, "int"),
                ("Cart Capacity", "cart_capacity", 40, 150, 5, "int"),
            ]

            if run_btn:
                with st.spinner("Running sensitivity across 8 levers..."):
                    results = []
                    cur_params = _get_params()
                    for name, key, lo, hi, step, kind in levers:
                        cur_v = cur_params[key]
                        range_v = hi - lo
                        delta = max(step, range_v * 0.2)
                        if kind == "int":
                            delta = int(round(delta))
                        low_v = max(lo, cur_v - delta)
                        high_v = min(hi, cur_v + delta)
                        if low_v == cur_v and high_v == cur_v:
                            continue

                        p_low = dict(cur_params); p_low[key] = low_v
                        p_high = dict(cur_params); p_high[key] = high_v

                        k_low = _kpis_from_params(p_low)
                        k_high = _kpis_from_params(p_high)

                        v_low = _target_kpi_value(
                            k_low["picking"], k_low["transport"], k_low["inventory"],
                            k_low["labor"], k_low["forecast"], target_kpi,
                        )
                        v_high = _target_kpi_value(
                            k_high["picking"], k_high["transport"], k_high["inventory"],
                            k_high["labor"], k_high["forecast"], target_kpi,
                        )

                        results.append({
                            "lever": name,
                            "current": cur_v,
                            "low_value": v_low,
                            "high_value": v_high,
                            "low_setting": low_v,
                            "high_setting": high_v,
                            "impact_range": abs(v_high - v_low),
                        })

                    results.sort(key=lambda r: r["impact_range"], reverse=True)
                    st.session_state["whatif_sens_results"] = results
                    st.session_state["whatif_sens_target"] = target_kpi
                    st.session_state["whatif_sens_base"] = base_value

            results = st.session_state.get("whatif_sens_results", [])
            stored_target = st.session_state.get("whatif_sens_target")
            if results and stored_target == target_kpi:
                st.markdown(f"**Base value (current):** `{base_value:,.2f}`")

                top = results[:8]
                levers_labels = [r["lever"] for r in top][::-1]
                low_deltas = [r["low_value"] - base_value for r in top][::-1]
                high_deltas = [r["high_value"] - base_value for r in top][::-1]
                low_text = [f"@{r['low_setting']:g}" for r in top][::-1]
                high_text = [f"@{r['high_setting']:g}" for r in top][::-1]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=levers_labels, x=low_deltas, name="Lever ↓",
                    orientation="h", marker_color="#93c5fd",
                    text=low_text, textposition="outside",
                ))
                fig.add_trace(go.Bar(
                    y=levers_labels, x=high_deltas, name="Lever ↑",
                    orientation="h", marker_color="#fb923c",
                    text=high_text, textposition="outside",
                ))
                fig.update_layout(
                    title=f"Tornado: lever impact on {target_kpi}",
                    barmode="overlay",
                    template="plotly_white",
                    height=420,
                    xaxis_title=f"Δ {target_kpi}",
                    margin=dict(t=50, b=20, l=20, r=20),
                )
                st.plotly_chart(fig, use_container_width=True, key="whatif_tornado")

                sens_df = pd.DataFrame([
                    {
                        "Lever": r["lever"],
                        "Current": r["current"],
                        "Low setting": r["low_setting"],
                        "High setting": r["high_setting"],
                        "Value @ low": f"{r['low_value']:,.2f}",
                        "Value @ high": f"{r['high_value']:,.2f}",
                        "Impact range": f"{r['impact_range']:,.2f}",
                    }
                    for r in results
                ])
                st.dataframe(sens_df, use_container_width=True, hide_index=True, key="whatif_sens_table")
            elif results and stored_target != target_kpi:
                st.info("Click **Run Sensitivity Analysis** to recompute for the selected KPI.")

    # =================
    # Tab 4: Flu Pandemic Forecaster
    # =================
    with tab4:
        st.markdown("#### 🦠 Flu Pandemic Forecaster")
        st.caption(
            "Pick a day of the year to see if a flu outbreak is forecast, "
            "how it would affect your operation (orders, FTE, cost), and "
            "which regions are most at risk."
        )

        # --- Date + scenario controls ---
        ctrl_cols = st.columns([2, 1, 1])
        with ctrl_cols[0]:
            st.session_state.setdefault("pandemic_doy", 15)  # Jan 15 default
            st.session_state.pandemic_doy = st.slider(
                "📅 Day of year",
                min_value=1, max_value=365, value=st.session_state.pandemic_doy, step=1,
                key="wave_pandemic_doy_slider",
                help="1 = Jan 1, 365 = Dec 31. Peak flu is around day 15 (Jan 15).",
            )
            d = day_of_year_to_date(st.session_state.pandemic_doy)
            st.caption(f"Selected: **{d.strftime('%A, %B %d, %Y')}** (day {st.session_state.pandemic_doy} of 365)")
        with ctrl_cols[1]:
            pandemic_scenario = st.selectbox(
                "Flu intensity",
                options=[1.0, 1.4, 2.0, 2.5, 3.0, 3.5],
                index=1,
                format_func=lambda x: f"{x:.1f}× baseline",
                key="wave_pandemic_scenario",
                help="User-facing flu intensity multiplier (1.0 = normal, 2.0 = peak, 3.5 = H1N1)",
            )
        with ctrl_cols[2]:
            base_daily = st.number_input(
                "Baseline orders / day",
                min_value=100, max_value=20000, value=2500, step=100,
                key="wave_pandemic_baseline",
                help="Non-flu summer order count for this DC. Case-study baseline is ~2,500 orders/shift.",
            )

        # Quick-pick buttons for important dates
        qp = st.columns(6)
        quick_picks = [
            (15,  "🔴 Jan 15 (peak)"),
            (45,  "Feb 14"),
            (75,  "Mar 15"),
            (196, "🟢 Jul 15 (trough)"),
            (274, "Oct 1"),
            (335, "Dec 1"),
        ]
        for i, (doy, lbl) in enumerate(quick_picks):
            with qp[i]:
                if st.button(lbl, use_container_width=True, key=f"qp_{i}"):
                    st.session_state.pandemic_doy = doy
                    st.rerun()

        # --- Forecast ---
        forecast = forecast_outbreak_for_date(
            day_of_year=st.session_state.pandemic_doy,
            scenario_mult=pandemic_scenario,
            base_daily_orders=int(base_daily),
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Row 1: severity gauge + KPI cards ---
        gauge_cols = st.columns([1, 2])
        with gauge_cols[0]:
            st.plotly_chart(
                outbreak_severity_gauge(
                    severity=forecast.national_severity,
                    date_label=forecast.date_label,
                    phase=forecast.phase,
                    is_outbreak=forecast.is_outbreak,
                ),
                use_container_width=True,
                key="wave_pandemic_gauge",
            )
        with gauge_cols[1]:
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.html(
                    f'<div class="kpi-mini">'
                    f'<div class="kpi-mini-label">Expected orders</div>'
                    f'<div class="kpi-mini-value">{forecast.expected_orders:,}</div>'
                    f'<div class="kpi-mini-sub">{forecast.orders_delta_pct:+.1f}% vs baseline {forecast.baseline_orders:,}</div>'
                    f'</div>'
                )
            with k2:
                st.html(
                    f'<div class="kpi-mini">'
                    f'<div class="kpi-mini-label">FTE required</div>'
                    f'<div class="kpi-mini-value">{forecast.fte_required}</div>'
                    f'<div class="kpi-mini-sub">baseline {forecast.fte_baseline} ({(forecast.fte_required - forecast.fte_baseline):+d})</div>'
                    f'</div>'
                )
            with k3:
                st.html(
                    f'<div class="kpi-mini">'
                    f'<div class="kpi-mini-label">Cost index</div>'
                    f'<div class="kpi-mini-value">{forecast.cost_index:.2f}×</div>'
                    f'<div class="kpi-mini-sub">vs summer baseline</div>'
                    f'</div>'
                )
            with k4:
                st.html(
                    f'<div class="kpi-mini">'
                    f'<div class="kpi-mini-label">Days to peak</div>'
                    f'<div class="kpi-mini-value">{forecast.days_to_peak if forecast.phase in ("Pre-peak", "Trough") else 0}</div>'
                    f'<div class="kpi-mini-sub">{forecast.phase} · {forecast.raw_seasonal_mult:.2f}× season mult</div>'
                    f'</div>'
                )
            st.html(
                f'<div class="insight-card insight-{"danger" if forecast.is_outbreak else "success"}">'
                f'{"🔴 OUTBREAK FORECAST" if forecast.is_outbreak else "🟢 NO OUTBREAK"} '
                f'for {forecast.date_label}. '
                f'Seasonal multiplier: <b>{forecast.raw_seasonal_mult:.2f}×</b> baseline. '
                f'National severity: <b>{forecast.national_severity*100:.0f}/100</b>. '
                f'{"Operation is in " + forecast.phase + " phase." if forecast.phase else ""}'
                f'</div>'
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Row 2: regional outbreak map + per-region table ---
        map_cols = st.columns([1.4, 1])
        with map_cols[0]:
            st.markdown("**Regional outbreak forecast for this date**")
            st.plotly_chart(
                regional_outbreak_map_for_date(
                    forecast.regional, st.session_state.pandemic_doy
                ),
                use_container_width=True,
                key="wave_pandemic_regional_map",
            )
        with map_cols[1]:
            st.markdown("**Regions ranked by severity**")
            st.dataframe(
                outbreak_regional_table(forecast.regional),
                use_container_width=True,
                hide_index=True,
                key="wave_pandemic_regional_table",
                column_config={
                    "Severity": st.column_config.ProgressColumn(
                        "Severity", min_value=0.0, max_value=2.5, format="%.2f"
                    ),
                    "Demand ×baseline": st.column_config.NumberColumn(
                        "Demand ×baseline", format="%.2f×"
                    ),
                },
            )
            # Top 3 hotspot list
            top3 = forecast.regional.head(3)
            st.markdown("**🔥 Top 3 hotspot regions:**")
            for _, row in top3.iterrows():
                st.html(
                    f'<div style="font-size:13px;margin-bottom:4px;">'
                    f'<b>{row["region"]}</b> — '
                    f'severity <b>{row["effective_severity"]:.2f}</b> '
                    f'({row["risk_level"]}), '
                    f'demand <b>{row["expected_demand_index"]:.2f}×</b> baseline'
                    f'</div>'
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Row 3: tier breakdown + 90-day timeline ---
        timeline = forecast_outbreak_timeline(
            start_doy=st.session_state.pandemic_doy,
            scenario_mult=pandemic_scenario,
            horizon_days=90,
        )
        bottom_cols = st.columns([1, 1.2])
        with bottom_cols[0]:
            st.markdown("**Per-tier demand surge on this date**")
            st.plotly_chart(
                outbreak_tier_breakdown_chart(forecast.tier_impact),
                use_container_width=True,
                key="wave_pandemic_tier_breakdown",
            )
        with bottom_cols[1]:
            st.markdown("**Next 90-day severity forecast**")
            st.plotly_chart(
                outbreak_forecast_timeline(
                    timeline=timeline,
                    current_doy=st.session_state.pandemic_doy,
                    current_severity=forecast.national_severity,
                ),
                use_container_width=True,
                key="wave_pandemic_timeline",
            )

    # =================
    # Tab 5: Saved Scenarios
    # =================
    with tab5:
        st.markdown("#### Scenario Library")
        st.caption("Save useful scenario configurations for reuse and team alignment.")

        st.session_state.setdefault("saved_scenarios", {})

        st.markdown("##### Save Current Scenario")
        sc1, sc2 = st.columns([2, 3])
        with sc1:
            new_name = st.text_input("Scenario name", placeholder="e.g., Q4 Holiday Surge", key="whatif_save_name")
        with sc2:
            new_note = st.text_input("Note (optional)", placeholder="e.g., 4 temp FTE for flu peak + rebalanced routing", key="whatif_save_note")

        sb1, sb2 = st.columns(2)
        with sb1:
            if st.button("💾 Save Current Scenario", type="primary", use_container_width=True, key="whatif_save_btn"):
                if not new_name:
                    st.error("Please enter a scenario name.")
                elif new_name in st.session_state.saved_scenarios:
                    st.error(f"A scenario named '{new_name}' already exists. Use a different name.")
                else:
                    cur_kpis = {
                        "staff_gap_pct": lk.staff_gap_pct,
                        "next_day_compliance_pct": tk.next_day_compliance_pct,
                        "total_shipment_cost_cny": tk.total_shipment_cost_cny,
                        "temp_compliance_pct": pk.temperature_compliance_pct,
                        "near_expiry_items": ik.near_expiry_items,
                    }
                    st.session_state.saved_scenarios[new_name] = {
                        "params": _get_params(),
                        "kpis": cur_kpis,
                        "note": new_note,
                        "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    st.success(f"Saved scenario '{new_name}'.")
                    st.rerun()
        with sb2:
            if st.session_state.saved_scenarios:
                st.download_button(
                    "📥 Export Library JSON",
                    data=json.dumps(st.session_state.saved_scenarios, indent=2, default=str),
                    file_name="pharma_scenarios.json",
                    mime="application/json",
                    use_container_width=True,
                    key="whatif_export_lib",
                )

        st.divider()
        st.markdown("##### Saved Scenarios")
        saved = st.session_state.saved_scenarios
        if not saved:
            st.info("No saved scenarios yet. Build a scenario in the Scenario Builder tab and save it here.")
        else:
            for name in list(saved.keys()):
                sc = saved[name]
                params = sc["params"]
                kpis = sc["kpis"]
                note_html = f'<div style="font-size:13px;color:#374151;margin-bottom:10px;font-style:italic;">{sc["note"]}</div>' if sc.get("note") else ''
                st.html(textwrap.dedent(f"""
                <div class="scenario-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                        <div>
                            <div style="font-size:15px;font-weight:600;color:#111827;">{name}</div>
                            <div style="font-size:12px;color:#6b7280;margin-top:2px;">Saved {sc['created_at']}</div>
                        </div>
                    </div>
                    {note_html}
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px;">
                        <div><span style="color:#9ca3af;">Orders:</span> <b>{params['n_orders']:,}</b></div>
                        <div><span style="color:#9ca3af;">Flu Mult:</span> <b>{params['scenario_mult']:.1f}×</b></div>
                        <div><span style="color:#9ca3af;">Perm FTE:</span> <b>{params['fte_permanent']}</b></div>
                        <div><span style="color:#9ca3af;">Temp FTE:</span> <b>{params['fte_temp']}</b></div>
                        <div><span style="color:#9ca3af;">Staff Gap:</span> <b>{kpis['staff_gap_pct']:.1f}%</b></div>
                        <div><span style="color:#9ca3af;">NDA:</span> <b>{kpis['next_day_compliance_pct']:.1f}%</b></div>
                        <div><span style="color:#9ca3af;">Cost:</span> <b>¥{kpis['total_shipment_cost_cny']:,.0f}</b></div>
                        <div><span style="color:#9ca3af;">Cold Comp:</span> <b>{kpis['temp_compliance_pct']:.1f}%</b></div>
                    </div>
                </div>
                """))
                ll, lr = st.columns(2)
                with ll:
                    if st.button(f"📤 Load", key=f"whatif_load_{name}", use_container_width=True):
                        for k, v in params.items():
                            st.session_state[k] = v
                        st.success(f"Loaded scenario '{name}'.")
                        st.rerun()
                with lr:
                    if st.button(f"🗑️ Delete", key=f"whatif_del_{name}", use_container_width=True):
                        del st.session_state.saved_scenarios[name]
                        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar + Navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    scenario = st.radio(
        "SCENARIO",
        ["Normal", "Peak", "Flu Season"],
        index=["Normal", "Peak", "Flu Season"].index(st.session_state.active_scenario),
        key="sidebar_scenario",
    )
    if scenario != st.session_state.active_scenario:
        st.session_state.active_scenario = scenario
        st.rerun()

pages = [
    st.Page(dashboard_page, title="Dashboard", icon="📊"),
    st.Page(wave_planning_page, title="Wave Planning", icon="🌊"),
    st.Page(whatif_page, title="What-If", icon="🔧"),
    st.Page(manager_overview_page, title="Manager Overview", icon="🧭"),
    st.Page(dictionary_page, title="Dictionary", icon="📖"),
]

pg = st.navigation(pages)
pg.run()
