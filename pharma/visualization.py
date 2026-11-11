"""
visualization.py
All Plotly-based charts for the Pharma Flu Logistics Optimizer.

UI language: English only.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from clustering import PickingResult, PickBatch, ShipmentResult
from data_generator import (
    TEMP_COLD,
    TEMP_FROZEN,
    TEMP_ROOM,
    TIER_MILD_OTC,
    TIER_MODERATE_RX,
    TIER_NON_FLU,
    TIER_SEVERE_HOSP,
    NEAR_EXPIRY_THRESHOLD_DAYS,
)
from forecast import ForecastResult
from tooltip import GLOSSARY


# Color palettes
TEMP_COLORS = {
    TEMP_ROOM:   "#FFA94D",  # ambient orange
    TEMP_COLD:   "#3B82F6",  # cold blue
    TEMP_FROZEN: "#7C3AED",  # frozen purple
}
TIER_COLORS = {
    TIER_NON_FLU:        "#94A3B8",
    TIER_MILD_OTC:       "#22C55E",
    TIER_MODERATE_RX:    "#F59E0B",
    TIER_SEVERE_HOSP:    "#EF4444",
}
NEAR_EXPIRY_COLORS = {
    "red":    "#EF4444",   # <30 days
    "amber":  "#F59E0B",   # 30-60
    "yellow": "#FACC15",   # 60-90
    "green":  "#22C55E",   # >90
}
CHINA_CENTER = dict(lon=104, lat=35)
EUROPE_CENTER = dict(lon=10, lat=50)


# ---------------------------------------------------------------------------
# 2D warehouse map
# ---------------------------------------------------------------------------
def warehouse_2d(warehouse: pd.DataFrame, orders: pd.DataFrame, color_by: str = "Temperature") -> go.Figure:
    fig = go.Figure()
    if color_by == "Temperature":
        for t, color in TEMP_COLORS.items():
            sub = warehouse[warehouse["temp"] == t]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers",
                marker=dict(size=9, color=color, symbol="square", line=dict(color="black", width=0.5)),
                name=t, hovertemplate=f"<b>{t}</b><br>Location: %{{text}}<extra></extra>",
                text=sub["location_id"],
            ))
    elif color_by == "Zone":
        for zone, sub in warehouse.groupby("zone"):
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers",
                marker=dict(size=9, symbol="square", line=dict(color="black", width=0.5)),
                name=zone, hovertemplate=f"<b>{zone}</b><br>%{{text}}<extra></extra>",
                text=sub["location_id"],
            ))
    else:  # Aisle
        for a, sub in warehouse.groupby("aisle"):
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers",
                marker=dict(size=9, symbol="square"),
                name=f"Aisle {a}", text=sub["location_id"], hovertemplate="<b>%{text}</b><extra></extra>",
            ))
    # Order pickpoints
    if not orders.empty:
        fig.add_trace(go.Scatter(
            x=orders["loc_x"], y=orders["loc_y"], mode="markers",
            marker=dict(size=4, color="rgba(0,0,0,0.45)"),
            name="Order picks", hoverinfo="skip",
        ))
    fig.update_layout(
        title=f"Warehouse 2D Map — color by {color_by}",
        xaxis_title="X (m)", yaxis_title="Y (m)",
        template="plotly_white", height=520, legend_title=color_by,
    )
    return fig


# ---------------------------------------------------------------------------
# 3D warehouse map
# ---------------------------------------------------------------------------
def warehouse_3d(warehouse: pd.DataFrame, color_by: str = "Temperature") -> go.Figure:
    if color_by == "Temperature":
        colors = warehouse["temp"].map(TEMP_COLORS).fillna("#94A3B8")
    else:
        colors = warehouse["zone"].map({"Ambient": "#FFA94D", "Cold A": "#3B82F6", "Cold B": "#60A5FA", "Frozen": "#7C3AED"}).fillna("#94A3B8")
    fig = go.Figure(data=[go.Scatter3d(
        x=warehouse["x"], y=warehouse["y"], z=warehouse["aisle"],
        mode="markers",
        marker=dict(size=6, color=colors, line=dict(color="black", width=0.3)),
        text=warehouse["location_id"] + " (" + warehouse["temp"] + ")",
        hovertemplate="<b>%{text}</b><extra></extra>",
    )])
    fig.update_layout(
        title=f"Warehouse 3D Map — color by {color_by}",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Aisle"),
        template="plotly_white", height=600,
    )
    return fig


# ---------------------------------------------------------------------------
# China regional flu choropleth
# ---------------------------------------------------------------------------
def regional_outbreak_map(
    outbreak: pd.DataFrame,
    month: int | None = None,
    day_of_year: int | None = None,
    title_prefix: str = "China Regional Flu Outbreak — Seasonal View",
) -> go.Figure:
    fig = go.Figure()
    # Use the seasonal-aware score so the map actually changes with month
    color_col = "effective_outbreak" if "effective_outbreak" in outbreak.columns else "outbreak_score"
    season_mult = float(outbreak["seasonal_multiplier"].iloc[0]) if "seasonal_multiplier" in outbreak.columns else 1.0

    label_suffix = ""
    if month is not None:
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        label_suffix = f" — {month_names[month]} (season x{season_mult:.2f})"
    elif day_of_year is not None:
        from forecast import day_of_year_to_date
        d = day_of_year_to_date(day_of_year)
        label_suffix = f" — {d.strftime('%b %d')} (day {day_of_year}, season x{season_mult:.2f})"

    # Dynamic cmax so the color scale reflects actual relative risk.
    cmax = float(outbreak[color_col].max())
    if cmax < 0.6:
        cmax = 0.6
    cmax = round(cmax * 1.05, 2)

    # Bubble size = base demand, color = effective outbreak
    fig.add_trace(go.Scattergeo(
        lon=outbreak["lon"], lat=outbreak["lat"],
        text=outbreak["region"],
        mode="markers",
        marker=dict(
            size=outbreak["base_demand"],
            sizemode="area", sizeref=2.0 * max(outbreak["base_demand"]) / (60.0 ** 2),
            sizemin=10,
            color=outbreak[color_col],
            colorscale="YlOrRd",
            cmin=0, cmax=cmax,
            colorbar=dict(title=f"Effective<br>Outbreak<br>(0–{cmax:.1f})"),
            line=dict(color="black", width=0.6),
            opacity=0.85,
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Effective outbreak: %{marker.color:.2f}<br>"
            "Base demand: %{marker.size}<br>"
            "Season mult: " + f"{season_mult:.2f}"
            "<extra></extra>"
        ),
        name="Region",
    ))
    fig.update_geos(
        center=CHINA_CENTER, projection_scale=3.4,
        showcountries=True, countrycolor="lightgray",
        showland=True, landcolor="#FAFAFA",
        lataxis_range=[18, 54], lonaxis_range=[73, 135],
    )
    fig.update_layout(
        title=f"{title_prefix}{label_suffix}",
        template="plotly_white", height=560,
    )
    return fig


# ---------------------------------------------------------------------------
# Shipment geo-map
# ---------------------------------------------------------------------------
def shipment_map(sr: ShipmentResult, dc_lat: float = 30.55, dc_lon: float = 114.30) -> go.Figure:
    """Geo map of shipment waves: one colored line per wave from DC to destination,
    grouped by temperature tier, plus a destination cluster per tier."""
    fig = go.Figure()

    if not sr.waves:
        # Still draw the DC for orientation
        fig.add_trace(go.Scattergeo(
            lon=[dc_lon], lat=[dc_lat], mode="markers",
            marker=dict(size=18, color="gold", symbol="star", line=dict(color="black", width=1)),
            name="Distribution Center",
        ))
        fig.update_geos(
            center=CHINA_CENTER, projection_scale=3.4,
            showcountries=True, countrycolor="lightgray",
            lataxis_range=[18, 54], lonaxis_range=[73, 135],
        )
        fig.update_layout(title="Shipment Waves Map (no data yet)", template="plotly_white", height=560)
        return fig

    # Group waves by temperature tier
    tiers = [
        (TEMP_ROOM,   "Ambient (15-25C)",  "#FFA94D", "solid"),
        (TEMP_COLD,   "Cold Chain (2-8C)",  "#3B82F6", "dash"),
        (TEMP_FROZEN, "Frozen (-20C)",     "#7C3AED", "dot"),
    ]

    # Per-tier: build line segments and a destination cluster
    for temp_key, label, color, dash in tiers:
        tier_waves = [w for w in sr.waves if w.temp == temp_key]
        if not tier_waves:
            continue
        # All line segments for this tier
        line_lons, line_lats = [], []
        for w in tier_waves:
            line_lons.extend([dc_lon, w.dest_lon, None])
            line_lats.extend([dc_lat, w.dest_lat, None])
        # Build hover text per segment
        hover_texts = []
        for w in tier_waves:
            seg_text = (
                f"<b>{w.wave_id}</b><br>"
                f"Tier: {label}<br>"
                f"Region: {w.region}<br>"
                f"Orders: {len(w.order_ids)}<br>"
                f"Pallets: {w.n_pallets:.1f}<br>"
                f"Distance: {w.distance_km:.0f} km<br>"
                f"Transit: {w.transit_days:.2f} d<br>"
                f"Cost: {w.cost_cny:,.0f} CNY<br>"
                f"Next-day: {'Yes' if w.next_day else 'No'}"
                f"<extra></extra>"
            )
            hover_texts.extend([seg_text, seg_text, None])
        fig.add_trace(go.Scattergeo(
            lon=line_lons, lat=line_lats,
            mode="lines",
            line=dict(width=2, color=color, dash=dash),
            name=f"{label} route ({len(tier_waves)} waves)",
            hoverinfo="text", text=hover_texts,
        ))
        # Destination cluster for this tier
        fig.add_trace(go.Scattergeo(
            lon=[w.dest_lon for w in tier_waves],
            lat=[w.dest_lat for w in tier_waves],
            mode="markers",
            marker=dict(
                size=[max(6, min(18, w.n_pallets * 0.8)) for w in tier_waves],
                color=color,
                symbol="circle",
                line=dict(color="black", width=0.5),
                opacity=0.75,
            ),
            name=f"{label} destination",
            hovertext=[
                f"<b>{w.wave_id}</b><br>Region: {w.region}<br>Pallets: {w.n_pallets:.1f}"
                for w in tier_waves
            ],
            hoverinfo="text",
        ))

    # Distribution Center marker (drawn last so it sits on top)
    fig.add_trace(go.Scattergeo(
        lon=[dc_lon], lat=[dc_lat], mode="markers",
        marker=dict(size=20, color="gold", symbol="star", line=dict(color="black", width=1.5)),
        name="Distribution Center (DC)",
        hovertemplate="<b>Wuhan DC</b><br>Hub for all shipment waves<extra></extra>",
    ))

    fig.update_geos(
        center=CHINA_CENTER, projection_scale=3.4,
        showcountries=True, countrycolor="lightgray",
        showland=True, landcolor="#FAFAFA",
        lataxis_range=[18, 54], lonaxis_range=[73, 135],
    )
    fig.update_layout(
        title=(
            f"Shipment Waves Map — {sr.n_waves} waves, "
            f"{sr.total_km:,.0f} km, "
            f"{sr.next_day_compliance_pct:.1f}% next-day"
        ),
        template="plotly_white", height=600,
        legend=dict(
            title=dict(text="Legend"),
            orientation="v", x=0.01, y=0.99, xanchor="left", yanchor="top",
            bgcolor="rgba(255,255,255,0.85)", bordercolor="lightgray", borderwidth=1,
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# SKU demand bar with 95% CI error bars
# ---------------------------------------------------------------------------
def sku_demand_chart(forecasts: list[ForecastResult], top_k: int = 15) -> go.Figure:
    forecasts = sorted(forecasts, key=lambda f: f.daily_forecast.sum(), reverse=True)[:top_k]
    names = [f.sku_name for f in forecasts]
    means = [float(f.daily_forecast.mean()) for f in forecasts]
    lows = [float(f.ci_low.mean()) for f in forecasts]
    highs = [float(f.ci_high.mean()) for f in forecasts]
    err_minus = [max(0.0, m - l) for m, l in zip(means, lows)]
    err_plus = [max(0.0, h - m) for m, h in zip(means, highs)]
    colors = [TIER_COLORS.get(f.tier, "#94A3B8") for f in forecasts]
    fig = go.Figure(go.Bar(
        x=means, y=names, orientation="h",
        error_x=dict(type="data", array=err_plus, arrayminus=err_minus, color="rgba(0,0,0,0.4)"),
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Mean: %{x:.1f}<br>95%% CI: ±%{error_x.array}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Top {len(names)} SKU Daily Demand with 95% CI",
        xaxis_title="Daily Demand (lines)", yaxis_title="",
        template="plotly_white", height=520,
    )
    return fig


# ---------------------------------------------------------------------------
# Client-type breakdown
# ---------------------------------------------------------------------------
def client_breakdown_chart(split_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        split_df, x="client", y="daily_demand", color="tier",
        color_discrete_map=TIER_COLORS,
        barmode="group",
        title="Expected Daily Demand by Client & Flu Tier",
    )
    fig.update_layout(template="plotly_white", height=460)
    return fig


# ---------------------------------------------------------------------------
# Cold cost heatmap by region
# ---------------------------------------------------------------------------
def cold_cost_heatmap(outbreak: pd.DataFrame) -> go.Figure:
    df = outbreak.copy()
    df["cold_cost_index"] = (df["outbreak_score"] * 1000.0 * (1.0 + df["base_demand"] / 100.0)).round(1)
    fig = go.Figure(go.Bar(
        x=df["region"], y=df["cold_cost_index"],
        marker=dict(
            color=df["cold_cost_index"],
            colorscale="Blues",
            showscale=True,
            colorbar=dict(title="Cold-cost<br>index"),
        ),
        hovertemplate="<b>%{x}</b><br>Cold-cost index: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        title="Regional Cold-Chain Cost Pressure",
        xaxis_title="", yaxis_title="Cold-cost index",
        template="plotly_white", height=460,
    )
    return fig


# ---------------------------------------------------------------------------
# Near-expiry color-coded table
# ---------------------------------------------------------------------------
def near_expiry_table(orders: pd.DataFrame, max_rows: int = 50) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame()
    near = orders[orders["shelf_remaining_days"] <= NEAR_EXPIRY_THRESHOLD_DAYS].copy()
    near = near.sort_values("shelf_remaining_days").head(max_rows)

    def _color(days: int) -> str:
        if days < 30:
            return "red"
        if days < 60:
            return "amber"
        if days < 90:
            return "yellow"
        return "green"

    near["bucket"] = near["shelf_remaining_days"].apply(_color)
    near["bucket_color"] = near["bucket"].map(NEAR_EXPIRY_COLORS)
    return near[["order_id", "sku_name", "tier", "client", "shelf_remaining_days", "case_value", "bucket", "bucket_color"]]


# ---------------------------------------------------------------------------
# Batch / wave size histogram
# ---------------------------------------------------------------------------
def batch_size_histogram(pr: PickingResult) -> go.Figure:
    if not pr.batches:
        return go.Figure().update_layout(title="No picking batches", template="plotly_white")
    sizes = [len(b.order_ids) for b in pr.batches]
    temps = [b.temp for b in pr.batches]
    fig = px.histogram(
        x=sizes, color=temps, nbins=20,
        color_discrete_map=TEMP_COLORS,
        title="Picking Batch Size Distribution",
    )
    fig.update_layout(xaxis_title="Orders per Batch", yaxis_title="Count", template="plotly_white", height=440)
    return fig


def wave_size_histogram(sr: ShipmentResult) -> go.Figure:
    if not sr.waves:
        return go.Figure().update_layout(title="No shipment waves", template="plotly_white")
    sizes = [w.n_pallets for w in sr.waves]
    temps = [w.temp for w in sr.waves]
    fig = px.histogram(
        x=sizes, color=temps, nbins=20,
        color_discrete_map=TEMP_COLORS,
        title="Shipment Wave Size Distribution (pallets)",
    )
    fig.update_layout(xaxis_title="Pallets per Wave", yaxis_title="Count", template="plotly_white", height=440)
    return fig


# ---------------------------------------------------------------------------
# Picking density heatmap
# ---------------------------------------------------------------------------
def picking_density_heatmap(orders: pd.DataFrame) -> go.Figure:
    if orders.empty:
        return go.Figure().update_layout(title="No orders to plot", template="plotly_white")
    fig = px.density_heatmap(
        orders, x="loc_x", y="loc_y", nbinsx=30, nbinsy=20,
        color_continuous_scale="YlOrRd",
        title="Picking Density Heatmap",
    )
    fig.update_layout(xaxis_title="X (m)", yaxis_title="Y (m)", template="plotly_white", height=460)
    return fig


# ---------------------------------------------------------------------------
# Cluster quality charts
# ---------------------------------------------------------------------------
def cluster_quality_chart(pr: PickingResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Silhouette", "Calinski-Harabasz (norm)"],
        y=[pr.silhouette, min(1.0, pr.calinski_harabasz / 1000.0)],
        marker_color=["#3B82F6", "#10B981"],
        text=[f"{pr.silhouette:.3f}", f"{pr.calinski_harabasz:.1f}"],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Cluster Quality — {pr.algorithm}",
        yaxis_title="Score (Calinski-Harabasz normalized to 0-1)",
        template="plotly_white", height=380, yaxis_range=[0, 1.1],
    )
    return fig


# ---------------------------------------------------------------------------
# Forecast line chart
# ---------------------------------------------------------------------------
def forecast_line_chart(forecasts: list[ForecastResult], top_k: int = 5) -> go.Figure:
    forecasts = sorted(forecasts, key=lambda f: f.daily_forecast.sum(), reverse=True)[:top_k]
    fig = go.Figure()
    for f in forecasts:
        color = TIER_COLORS.get(f.tier, "#94A3B8")
        x = list(range(len(f.daily_forecast)))
        fig.add_trace(go.Scatter(
            x=x, y=f.daily_forecast, mode="lines+markers", name=f.sku_name,
            line=dict(color=color, width=2),
            marker=dict(size=4),
        ))
        fig.add_trace(go.Scatter(
            x=x + x[::-1],
            y=list(f.ci_high) + list(f.ci_low[::-1]),
            fill="toself", showlegend=False,
            line=dict(color="rgba(0,0,0,0)"),
            fillcolor=color.replace(")", ", 0.15)").replace("rgb", "rgba") if color.startswith("rgb") else "rgba(100,116,139,0.15)",
            hoverinfo="skip",
        ))
    fig.update_layout(
        title=f"Top {len(forecasts)} SKU Demand Forecast with 95% CI",
        xaxis_title="Day", yaxis_title="Daily Demand",
        template="plotly_white", height=480,
    )
    return fig


# ---------------------------------------------------------------------------
# Seasonal curve
# ---------------------------------------------------------------------------
def seasonal_curve(month: int) -> go.Figure:
    days = list(range(1, 366))
    from forecast import seasonal_multiplier
    vals = [seasonal_multiplier(d) for d in days]
    fig = go.Figure(go.Scatter(x=days, y=vals, mode="lines", line=dict(color="#EF4444", width=2.5)))
    fig.add_vline(x=15, line_dash="dash", line_color="gray", annotation_text="Jan 15 peak")
    fig.update_layout(
        title="China Flu Seasonal Multiplier (1.0=baseline, 2.0=peak)",
        xaxis_title="Day of year", yaxis_title="Seasonal multiplier",
        template="plotly_white", height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# ML vs Random comparison
# ---------------------------------------------------------------------------
def ml_vs_random_meters_chart(ai_dist: float, rand_dist: float) -> go.Figure:
    """Single-metric comparison: AI vs Random on WALKING DISTANCE (m).

    Y-axis is distance in meters so the bars are easy to read at a
    glance. The % saving vs random is annotated on top of the
    random bar in green.
    """
    uplift = 100.0 * (rand_dist - ai_dist) / max(rand_dist, 1e-6)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="AI Optimized",
        x=["AI"], y=[ai_dist],
        marker_color="#3B82F6",
        text=[f"{ai_dist:.0f} m"], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Random Baseline",
        x=["Random"], y=[rand_dist],
        marker_color="#94A3B8",
        text=[f"{rand_dist:.0f} m"], textposition="outside",
    ))
    fig.add_annotation(
        x="Random", y=rand_dist,
        text=f"<b>−{uplift:.0f}%</b><br>vs random",
        showarrow=False, yshift=32,
        font=dict(color="#16A34A", size=13),
    )
    fig.update_layout(
        title="Walking distance (m) — AI vs Random",
        barmode="group", template="plotly_white", height=420,
        yaxis_title="Distance (m)",
        legend=dict(orientation="h", yanchor="bottom", y=1.05,
                    xanchor="right", x=1),
        margin=dict(t=80, b=40, l=50, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
def ml_vs_random_cost_chart(ai_cost: float, rand_cost: float) -> go.Figure:
    """Single-metric comparison: AI vs Random on SHIPMENT COST (CNY).

    Y-axis is cost in CNY. Distance is in the companion chart.
    """
    uplift = 100.0 * (rand_cost - ai_cost) / max(rand_cost, 1e-6)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="AI Optimized",
        x=["AI"], y=[ai_cost],
        marker_color="#3B82F6",
        text=[f"¥{ai_cost:,.0f}"], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Random Baseline",
        x=["Random"], y=[rand_cost],
        marker_color="#94A3B8",
        text=[f"¥{rand_cost:,.0f}"], textposition="outside",
    ))
    fig.add_annotation(
        x="Random", y=rand_cost,
        text=f"<b>−{uplift:.0f}%</b><br>vs random",
        showarrow=False, yshift=32,
        font=dict(color="#16A34A", size=13),
    )
    fig.update_layout(
        title="Shipment cost (CNY) — AI vs Random",
        barmode="group", template="plotly_white", height=420,
        yaxis_title="Cost (CNY)",
        legend=dict(orientation="h", yanchor="bottom", y=1.05,
                    xanchor="right", x=1),
        margin=dict(t=80, b=40, l=60, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Cluster scatter plot — see how orders group together in any 2D view
# ---------------------------------------------------------------------------
# Maps internal variable name -> (column in orders df, axis label)
CLUSTER_SCATTER_AXES: dict[str, tuple[str, str]] = {
    # Spatial — the warehouse itself
    "loc_x":                ("loc_x", "Warehouse X (m)"),
    "loc_y":                ("loc_y", "Warehouse Y (m)"),
    "aisle":                ("aisle", "Aisle"),
    # FEFO / expiry
    "shelf_remaining_days": ("shelf_remaining_days", "Shelf remaining (days)"),
    # Operational
    "priority":             ("priority", "Priority (1 = high)"),
    "qty":                  ("qty", "Order quantity"),
    "case_value":           ("case_value", "Case value (CNY)"),
    "weight_kg":            ("weight_kg", "Weight (kg)"),
    # Product
    "temp_code":            ("temp", "Temperature"),
    "tier_code":            ("tier", "Product tier"),
    "rx_code":              ("rx", "Rx vs OTC"),
    "ped_code":             ("pediatric", "Pediatric"),
    # Customer
    "client_code":          ("client", "Client"),
}

CLUSTER_SCATTER_COLORBY: dict[str, tuple[str, str]] = {
    "batch_label":  ("batch_label", "Cluster"),
    "temp":         ("temp", "Temperature"),
    "tier":         ("tier", "Product tier"),
    "client":       ("client", "Client"),
    "priority":     ("priority", "Priority"),
    "aisle":        ("aisle", "Aisle"),
}


def cluster_scatter_plot(
    orders: pd.DataFrame,
    picking: PickingResult,
    x_var: str = "loc_x",
    y_var: str = "loc_y",
    color_by: str = "batch_label",
    show_centroids: bool = True,
) -> go.Figure:
    """2D scatter of orders colored by cluster (or other categorical var).

    The manager picks the X and Y axes from CLUSTER_SCATTER_AXES so they
    can inspect the clusters from any angle:
      - (loc_x, loc_y)   — physical warehouse layout
      - (shelf, priority) — FEFO urgency view
      - (qty, case_value) — economic / cart-load view
      - (case_value, weight_kg) — logistics-cost view
    """
    fig = go.Figure()
    # The orders DataFrame may not have batch_label; use picking.orders
    # which has the cluster assignment added by the clusterer.
    work_orders = picking.orders if picking.orders is not None and not picking.orders.empty else orders
    if work_orders.empty or not picking.batches:
        return fig.update_layout(
            title="No cluster data yet",
            template="plotly_white", height=420,
        )

    # Resolve axis columns
    x_col, x_label = CLUSTER_SCATTER_AXES.get(x_var, ("loc_x", x_var))
    y_col, y_label = CLUSTER_SCATTER_AXES.get(y_var, ("loc_y", y_var))
    color_col, color_label = CLUSTER_SCATTER_COLORBY.get(color_by, ("batch_label", color_by))

    if x_col not in work_orders.columns or y_col not in work_orders.columns:
        return fig.update_layout(
            title=f"Columns {x_col}/{y_col} not in orders",
            template="plotly_white", height=420,
        )

    # Color palettes
    palettes = {
        "batch_label": px.colors.qualitative.Set2,
        "temp":        {"Room Temp (15-25C)": "#FFA94D",
                        "Cold Chain (2-8C)":  "#3B82F6",
                        "Frozen (-20C)":     "#7C3AED"},
        "tier":        {"Non-Flu": "#94A3B8", "Mild OTC Flu": "#22C55E",
                        "Moderate Rx Flu":   "#F59E0B",
                        "Severe Hospital / Vaccine": "#EF4444"},
        "client":      {"Hospital": "#3B82F6",
                        "Independent Pharmacy": "#22C55E",
                        "Primary Care": "#F59E0B"},
        "priority":    {1: "#EF4444", 2: "#F59E0B", 3: "#FACC15",
                        4: "#22C55E", 5: "#3B82F6"},
        "aisle":       None,  # discrete
    }

    palette = palettes.get(color_by)
    if palette is None:
        cats = sorted(work_orders[color_col].dropna().unique(), key=str)
        palette = {c: px.colors.qualitative.Set2[i % len(px.colors.qualitative.Set2)]
                   for i, c in enumerate(cats)}

    # Normalise palette to a dict for uniform iteration
    if isinstance(palette, list):
        cats = sorted(work_orders[color_col].dropna().unique(), key=str)
        palette = {c: palette[i % len(palette)] for i, c in enumerate(cats)}

    # Plot each category
    for cat, color in palette.items():
        sub = work_orders[work_orders[color_col] == cat]
        if sub.empty:
            continue
        label = (f"Cluster {cat}" if color_by == "batch_label"
                 else f"{color_label}: {cat}")
        fig.add_trace(go.Scatter(
            x=sub[x_col], y=sub[y_col],
            mode="markers",
            marker=dict(size=6, color=color, opacity=0.65,
                        line=dict(color="white", width=0.3)),
            name=label,
            hovertemplate=(
                f"<b>{label}</b><br>"
                f"{x_label}: %{{x}}<br>"
                f"{y_label}: %{{y}}<br>"
                f"Order: %{{customdata[0]}}<extra></extra>"
            ),
            customdata=sub[["order_id"]].values,
        ))

    # Centroids
    if show_centroids and color_by == "batch_label" and "batch_label" in work_orders.columns:
        for cat in work_orders["batch_label"].unique():
            sub = work_orders[work_orders["batch_label"] == cat]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=[sub[x_col].mean()], y=[sub[y_col].mean()],
                mode="markers",
                marker=dict(size=18, color="black", symbol="x",
                            line=dict(color="white", width=1)),
                name=f"Centroid {cat}",
                hovertemplate=(
                    f"<b>Cluster {cat} centroid</b><br>"
                    f"{x_label}: {sub[x_col].mean():.1f}<br>"
                    f"{y_label}: {sub[y_col].mean():.1f}<br>"
                    f"Size: {len(sub)}<extra></extra>"
                ),
                showlegend=False,
            ))

    fig.update_layout(
        title=f"Cluster view — {x_label} vs {y_label} (color: {color_label})",
        xaxis_title=x_label, yaxis_title=y_label,
        template="plotly_white", height=540,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=10)),
        margin=dict(t=70, b=20, l=20, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Per-cluster summary table
# ---------------------------------------------------------------------------
def cluster_summary_table(
    orders: pd.DataFrame,
    picking: PickingResult,
) -> pd.DataFrame:
    """Return one row per cluster with: size, avg FEFO, avg priority,
    dominant temp / client / tier, spatial spread (x and y), and the
    cluster's average walking distance from the cluster route.
    """
    work_orders = picking.orders if picking.orders is not None and not picking.orders.empty else orders
    if work_orders.empty or not picking.batches or "batch_label" not in work_orders.columns:
        return pd.DataFrame()

    # Map batch_id (B0001) -> batch metadata
    by_label: dict[int, dict] = {}
    for b in picking.batches:
        try:
            label = int(b.batch_id.replace("B", "").lstrip("0") or "0")
        except ValueError:
            continue
        by_label[label] = {
            "distance_m": b.distance,
            "estimated_minutes": b.estimated_minutes,
            "picker": b.picker,
            "temp": b.temp,
        }

    rows: list[dict] = []
    for label, sub in work_orders.groupby("batch_label"):
        if sub.empty:
            continue
        meta = by_label.get(int(label), {})
        # Dominant categorical
        def _mode(s: pd.Series) -> str:
            m = s.mode()
            return str(m.iloc[0]) if not m.empty else "—"
        rows.append({
            "Cluster":           f"B{int(label):04d}",
            "Size":              len(sub),
            "Avg FEFO (days)":   round(float(sub["shelf_remaining_days"].mean()), 0) if "shelf_remaining_days" in sub.columns else 0,
            "Min FEFO (days)":   int(sub["shelf_remaining_days"].min()) if "shelf_remaining_days" in sub.columns else 0,
            "Avg priority":      round(float(sub["priority"].mean()), 2) if "priority" in sub.columns else 0,
            "Dominant temp":     _mode(sub["temp"]) if "temp" in sub.columns else "—",
            "Dominant client":   _mode(sub["client"]) if "client" in sub.columns else "—",
            "Dominant tier":     _mode(sub["tier"]) if "tier" in sub.columns else "—",
            "X range (m)":       round(float(sub["loc_x"].max() - sub["loc_x"].min()), 1) if "loc_x" in sub.columns else 0,
            "Y range (m)":       round(float(sub["loc_y"].max() - sub["loc_y"].min()), 1) if "loc_y" in sub.columns else 0,
            "Route distance (m)": round(float(meta.get("distance_m", 0.0)), 1),
            "Est. min":          round(float(meta.get("estimated_minutes", 0.0)), 1),
            "Picker":            int(meta.get("picker", 0)),
        })
    df = pd.DataFrame(rows).sort_values("Size", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Picking-path map — how a single picker walks the warehouse
# ---------------------------------------------------------------------------
def picking_path_map(
    warehouse: pd.DataFrame,
    orders: pd.DataFrame,
    batch: PickBatch,
    all_batches: list[PickBatch] | None = None,
    show_other_paths: bool = True,
) -> go.Figure:
    """2D warehouse map with the selected batch's picking path overlaid.

    All pickers start at the warehouse ENTRANCE (south of the slot row,
    at the aisle block) and return to it after their last stop. This is
    how a real DC works — single dispatch + receiving point.

    - Background: warehouse locations colored by temperature (ambient / cold / frozen).
    - Faded dots: pickpoints from orders not in the selected batch.
    - Bold polyline: this batch's optimized route, with stop numbers.
    - Star: warehouse entrance (start + end of route).
    - Optional faint polylines: every other batch's path, so the manager can
      see pickers walking in parallel without crossing each other.
    """
    fig = go.Figure()

    # Warehouse entrance = south of the slot row, at the centre of the
    # aisle block. The warehouse X is centred, and the entrance sits
    # just below the lowest slot row.
    if not warehouse.empty:
        wx_min, wx_max = float(warehouse["x"].min()), float(warehouse["x"].max())
        wy_min = float(warehouse["y"].min())
    else:
        wx_min, wx_max, wy_min = 0.0, 0.0, 0.0
    entrance_x = (wx_min + wx_max) / 2.0
    entrance_y = wy_min - 4.0   # 4 m below the first slot row

    # 1. Warehouse locations, colored by temperature
    for t, color in TEMP_COLORS.items():
        sub = warehouse[warehouse["temp"] == t]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers",
            marker=dict(size=11, color=color, symbol="square",
                        line=dict(color="black", width=0.6), opacity=0.55),
            name=f"{t} (slot)", hovertemplate=(
                f"<b>{t}</b><br>Slot: %{{text}}<extra></extra>"
            ),
            text=sub["location_id"],
        ))

    # 2. Faint polylines for other batches (manager sees the swarm)
    if show_other_paths and all_batches:
        palette = ["rgba(148,163,184,0.35)", "rgba(100,116,139,0.35)",
                   "rgba(203,213,225,0.35)", "rgba(71,85,105,0.35)"]
        for i, b in enumerate(all_batches):
            if b.batch_id == batch.batch_id or len(b.stop_locations) < 2:
                continue
            # Other batches: entrance -> stops -> entrance
            xs = [entrance_x] + [p[0] for p in b.stop_locations] + [entrance_x]
            ys = [entrance_y] + [p[1] for p in b.stop_locations] + [entrance_y]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(width=1, color=palette[i % len(palette)], dash="dot"),
                name=f"Other batch {b.batch_id}", hoverinfo="skip",
                showlegend=False,
            ))

    # 3. Faint dots for orders NOT in this batch
    if not orders.empty and "batch_label" in orders.columns:
        other_ids = set(batch.order_ids)
        other = orders[~orders["order_id"].isin(other_ids)]
        if not other.empty:
            fig.add_trace(go.Scatter(
                x=other["loc_x"], y=other["loc_y"], mode="markers",
                marker=dict(size=4, color="rgba(100,116,139,0.35)"),
                name="Other pickers' stops", hoverinfo="skip",
            ))

    # 4. This batch's path: entrance -> stop 1 -> ... -> stop N -> entrance
    stops = batch.stop_locations
    if len(stops) >= 1:
        path_x = [entrance_x] + [s[0] for s in stops] + [entrance_x]
        path_y = [entrance_y] + [s[1] for s in stops] + [entrance_y]
        fig.add_trace(go.Scatter(
            x=path_x, y=path_y, mode="lines",
            line=dict(width=4, color="#DC2626"),
            name=f"Batch {batch.batch_id} route",
            hoverinfo="skip",
        ))
        # Stop markers with sequence numbers
        fig.add_trace(go.Scatter(
            x=[s[0] for s in stops],
            y=[s[1] for s in stops],
            mode="markers+text",
            marker=dict(size=14, color="#DC2626", symbol="circle",
                        line=dict(color="white", width=2)),
            text=[f"<b>{i+1}</b>" for i in range(len(stops))],
            textposition="middle center",
            textfont=dict(color="white", size=10),
            name=f"Stop sequence ({batch.batch_id})",
            hovertemplate=(
                "<b>Stop %{text}</b><br>"
                f"Batch: {batch.batch_id}<br>"
                f"Picker: #{batch.picker}<br>"
                f"Temp: {batch.temp}<br>"
                f"Distance: {batch.distance:.1f} m<extra></extra>"
            ),
        ))

    # 5. Warehouse entrance marker (always at the south of the row)
    fig.add_trace(go.Scatter(
        x=[entrance_x], y=[entrance_y], mode="markers+text",
        marker=dict(size=24, color="#FACC15", symbol="star",
                    line=dict(color="black", width=1.5)),
        text=["<b>ENTRANCE</b>"],
        textposition="bottom center",
        textfont=dict(color="#111827", size=11),
        name="Warehouse entrance (start + end)",
        hovertemplate="<b>Warehouse entrance / dispatch dock</b><extra></extra>",
    ))

    fig.update_layout(
        title=f"Batch {batch.batch_id} — {len(stops)} stops, "
              f"{batch.distance:.1f} m, est. {batch.estimated_minutes:.1f} min "
              f"(Picker #{batch.picker}, {batch.temp})",
        xaxis_title="X (m)", yaxis_title="Y (m)",
        template="plotly_white", height=540,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=10)),
        margin=dict(t=70, b=20, l=20, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Warehouse structure advisor — actionable layout recommendations
# ---------------------------------------------------------------------------
def warehouse_structure_advisor(
    warehouse: pd.DataFrame,
    orders: pd.DataFrame,
    picking: PickingResult,
) -> tuple[pd.DataFrame, list[str]]:
    """Compute layout metrics and return (zone_stats_df, recommendations).

    Recommendations are short actionable strings for the manager:
    - Cold-chain scattering
    - Hot zones
    - Underused aisles
    - Aisle-level distance imbalance
    """
    recs: list[str] = []
    if orders.empty or warehouse.empty:
        return pd.DataFrame(), ["No data available yet — run a scenario."]

    # Zone-level pick density
    zone_stats: list[dict] = []
    for temp_key, label in [
        (TEMP_ROOM, "Ambient (15-25C)"),
        (TEMP_COLD, "Cold-chain (2-8C)"),
        (TEMP_FROZEN, "Frozen (-20C)"),
    ]:
        wh_z = warehouse[warehouse["temp"] == temp_key]
        ords_z = orders[orders["temp"] == temp_key]
        if wh_z.empty:
            continue
        n_slots = len(wh_z)
        n_picks = len(ords_z)
        # Pct of picks that fall in this zone's slots (proximity-based)
        wh_centroid = (wh_z["x"].mean(), wh_z["y"].mean())
        if not ords_z.empty:
            d = np.hypot(ords_z["loc_x"] - wh_centroid[0],
                         ords_z["loc_y"] - wh_centroid[1])
            proximity_pct = 100.0 * (d < 30.0).mean()
        else:
            proximity_pct = 0.0
        zone_stats.append({
            "Zone": label,
            "Slots": n_slots,
            "Picks": n_picks,
            "Picks / Slot": round(n_picks / max(1, n_slots), 2),
            "Local picks (%)": round(proximity_pct, 1),
        })

    df = pd.DataFrame(zone_stats)

    # Aisle-level distance and pick count
    aisle_stats = (
        orders.groupby("aisle")
        .agg(
            picks=("order_id", "count"),
            avg_x=("loc_x", "mean"),
            avg_y=("loc_y", "mean"),
        )
        .reset_index()
        .sort_values("picks", ascending=False)
    )

    # Hot-zone detection: aisle with > 2.5x median picks
    if not aisle_stats.empty and len(aisle_stats) >= 3:
        median_picks = aisle_stats["picks"].median()
        hot = aisle_stats[aisle_stats["picks"] > 2.5 * median_picks]
        if not hot.empty:
            for _, row in hot.head(3).iterrows():
                recs.append(
                    f"🔥 Aisle {int(row['aisle'])} is a hot zone — "
                    f"{int(row['picks'])} picks vs. median {median_picks:.0f}. "
                    f"Add a forward-pick face or relocate fast-movers here."
                )

    # Cold-chain scattering: do cold picks live close to cold slots?
    if TEMP_COLD in orders["temp"].values:
        cold = orders[orders["temp"] == TEMP_COLD]
        cold_wh = warehouse[warehouse["temp"] == TEMP_COLD]
        if not cold.empty and not cold_wh.empty:
            # For each cold pick, distance to nearest cold slot
            cx = cold_wh["x"].to_numpy()
            cy = cold_wh["y"].to_numpy()
            ox = cold["loc_x"].to_numpy()
            oy = cold["loc_y"].to_numpy()
            # Vectorised nearest-slot distance
            d_min = np.empty(len(ox))
            for i in range(len(ox)):
                d_min[i] = np.min(np.hypot(cx - ox[i], cy - oy[i]))
            median_d = float(np.median(d_min))
            if median_d > 12.0:
                recs.append(
                    f"❄️ Cold-chain picks are scattered — median distance to "
                    f"a cold slot is {median_d:.1f} m. Group cold SKUs in a "
                    f"single aisle block to cut walking distance and exposure time."
                )
            elif median_d < 6.0:
                recs.append(
                    f"✅ Cold-chain layout is tight — median distance to cold "
                    f"slot is {median_d:.1f} m. Maintain this zoning."
                )

    # Frozen: should be near the loading dock (entrance at x=0, y=0 typically)
    if TEMP_FROZEN in orders["temp"].values:
        frozen = orders[orders["temp"] == TEMP_FROZEN]
        if not frozen.empty:
            mean_x = float(frozen["loc_x"].mean())
            if mean_x > 60.0:
                recs.append(
                    f"🧊 Frozen picks average x={mean_x:.1f} m — far from the "
                    f"loading dock. Move frozen slots to aisle 0–1 to minimize "
                    f"transit time and protect cold-chain integrity."
                )

    # Underused aisles
    if not aisle_stats.empty:
        low = aisle_stats[aisle_stats["picks"] <= max(1, aisle_stats["picks"].quantile(0.25))]
        if len(low) >= 2:
            aisle_list = ", ".join(str(int(a)) for a in low["aisle"].head(4).tolist())
            recs.append(
                f"📦 Aisle(s) {aisle_list} are underused (bottom 25% of picks). "
                f"Consolidate slow-movers here to free prime slots near the entrance."
            )

    # Total walking distance summary
    if picking.batches:
        avg_d = float(np.mean([b.distance for b in picking.batches]))
        longest = max(picking.batches, key=lambda b: b.distance)
        recs.append(
            f"🚶 Avg picker distance: <b>{avg_d:.1f} m</b> per batch. "
            f"Longest route: <b>{longest.batch_id}</b> at {longest.distance:.1f} m. "
            f"Re-cluster if longest > 2× average."
        )

    if not recs:
        recs.append("✅ No layout issues detected — current zoning is well balanced.")
    return df, recs


# ---------------------------------------------------------------------------
# Glossary tab
# ---------------------------------------------------------------------------
def render_glossary() -> None:
    import streamlit as st
    cols = st.columns(2)
    items = list(GLOSSARY.items())
    half = (len(items) + 1) // 2
    for i, (term, defn) in enumerate(items):
        col = cols[0] if i < half else cols[1]
        with col:
            st.markdown(f"**{term}** — {defn}")


# ---------------------------------------------------------------------------
# Flu pandemic forecaster — visualisations
# ---------------------------------------------------------------------------
# Severity bands, in the same 0-100 units as the gauge axis.
# Plotly's Step expects a dict with a `range` (a [start, end] tuple) and a
# `color`. Earlier versions used [value, color] lists — that was the bug.
_SEVERITY_STOPS = [
    {"range": [0, 20],  "color": "#22C55E"},  # trough
    {"range": [20, 40], "color": "#FACC15"},  # rising
    {"range": [40, 60], "color": "#F59E0B"},  # outbreak
    {"range": [60, 80], "color": "#EF4444"},  # severe
    {"range": [80, 100], "color": "#7F1D1D"},  # extreme
]


def outbreak_severity_gauge(severity: float, date_label: str, phase: str,
                             is_outbreak: bool) -> go.Figure:
    """Half-doughnut gauge showing national outbreak severity 0–1."""
    color = (
        "#7F1D1D" if severity >= 0.80
        else "#EF4444" if severity >= 0.60
        else "#F59E0B" if severity >= 0.40
        else "#FACC15" if severity >= 0.20
        else "#22C55E"
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=severity * 100,
        number=dict(suffix=" / 100", font=dict(size=28, color=color)),
        title=dict(
            text=f"<b>{date_label}</b> — {phase}<br>"
                 f"<span style='font-size:12px;color:#6b7280;'>"
                 f"{'🔴 OUTBREAK DECLARED' if is_outbreak else '🟢 Normal range'}</span>",
        ),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#E5E7EB"),
            bar=dict(color=color, thickness=0.35),
            bgcolor="white",
            borderwidth=0,
            steps=_SEVERITY_STOPS,
            threshold=dict(
                thickness=0.8, value=severity * 100, line=dict(color="black", width=2)
            ),
        ),
    ))
    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(t=80, b=20, l=20, r=20),
    )
    return fig


def outbreak_forecast_timeline(
    timeline: pd.DataFrame,
    current_doy: int,
    current_severity: float,
) -> go.Figure:
    """90-day outbreak severity forecast starting from current_doy.

    X-axis is numeric day_offset (0 = today, 89 = +89 days) so that
    add_vline works cleanly. Tick labels show the date every 14 days.
    """
    fig = go.Figure()
    # Filled area (numeric x so vline math is safe)
    fig.add_trace(go.Scatter(
        x=timeline["day_offset"], y=timeline["severity"],
        mode="lines",
        line=dict(color="#EF4444", width=2),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.18)",
        name="Severity",
        hovertemplate=(
            "<b>%{customdata}</b><br>"
            "Severity: %{y:.2f}<extra></extra>"
        ),
        customdata=timeline["date_label"],
    ))
    # Outbreak threshold line
    fig.add_hline(
        y=0.32, line_dash="dot", line_color="#9CA3AF",
        annotation_text="Outbreak threshold (0.32)",
        annotation_position="right",
    )
    # Mark current day (x=0 is always "today" by construction)
    fig.add_vline(
        x=0,
        line_dash="dash", line_color="#111827",
        annotation_text=f"Today ({current_severity:.2f})",
        annotation_position="top left",
    )
    # Sparse date tick labels every ~14 days
    tick_positions = list(range(0, len(timeline), 14))
    if (len(timeline) - 1) not in tick_positions:
        tick_positions.append(len(timeline) - 1)
    tick_labels = [timeline.iloc[i]["date_label"] for i in tick_positions]
    fig.update_layout(
        title="90-Day Outbreak Severity Forecast",
        xaxis=dict(
            title="Days from today",
            tickmode="array",
            tickvals=tick_positions,
            ticktext=tick_labels,
            range=[-2, len(timeline) + 1],
        ),
        yaxis=dict(title="Severity (0 = trough, 1 = peak)", range=[0, 1.05]),
        template="plotly_white", height=360,
        margin=dict(t=50, b=40, l=40, r=20),
    )
    return fig


def outbreak_tier_breakdown_chart(tier_impact: dict) -> go.Figure:
    """Bar chart showing per-tier demand multiplier on the selected date."""
    tier_labels = list(tier_impact.keys())
    combined = [tier_impact[t]["combined"] for t in tier_labels]
    base = [tier_impact[t]["base_mult"] for t in tier_labels]
    season = [tier_impact[t]["season_mult"] for t in tier_labels]
    # Grouped: base (faded) vs season (highlighted) for each tier
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Base flu mult", x=tier_labels, y=base,
        marker_color="rgba(100,116,139,0.45)",
        text=[f"{v:.1f}x" for v in base], textposition="inside",
    ))
    fig.add_trace(go.Bar(
        name="With seasonal surge", x=tier_labels, y=combined,
        marker_color=["#94A3B8", "#22C55E", "#F59E0B", "#EF4444"],
        text=[f"{v:.1f}x" for v in combined], textposition="outside",
    ))
    fig.update_layout(
        title="Per-Tier Demand Surge (multiplier vs non-flu baseline)",
        barmode="group",
        template="plotly_white", height=360,
        yaxis_title="Multiplier (× baseline)",
        xaxis_title="Product tier",
        margin=dict(t=50, b=40, l=40, r=20),
    )
    return fig


def outbreak_regional_table(regional: pd.DataFrame) -> pd.DataFrame:
    """Return a manager-friendly table of regional outbreak risk."""
    if regional.empty:
        return regional
    out = regional[[
        "region", "effective_severity", "risk_level", "expected_demand_index"
    ]].copy()
    out.columns = ["Region", "Severity", "Risk level", "Demand ×baseline"]
    return out


def regional_outbreak_map_for_date(
    regional_df: pd.DataFrame,
    day_of_year: int,
) -> go.Figure:
    """Map of regional outbreak severity for a single day.

    The regional_df must have columns: region, lat, lon, effective_severity,
    base_demand, risk_level.
    """
    from forecast import day_of_year_to_date
    d = day_of_year_to_date(day_of_year)
    cmax = float(regional_df["effective_severity"].max())
    if cmax < 0.6:
        cmax = 0.6
    cmax = round(cmax * 1.05, 2)

    # Color per risk level
    risk_colors = {
        "Severe":  "#7F1D1D",
        "High":    "#EF4444",
        "Moderate":"#F59E0B",
        "Low":     "#FACC15",
        "Minimal": "#22C55E",
    }
    regional_df = regional_df.copy()
    regional_df["color"] = regional_df["risk_level"].map(risk_colors).fillna("#94A3B8")

    fig = go.Figure()
    for risk, color in risk_colors.items():
        sub = regional_df[regional_df["risk_level"] == risk]
        if sub.empty:
            continue
        fig.add_trace(go.Scattergeo(
            lon=sub["lon"], lat=sub["lat"],
            text=sub["region"],
            mode="markers",
            marker=dict(
                size=sub["base_demand"],
                sizemode="area",
                sizeref=2.0 * max(regional_df["base_demand"]) / (60.0 ** 2),
                sizemin=12,
                color=color,
                line=dict(color="black", width=0.6),
                opacity=0.85,
            ),
            name=risk,
            hovertemplate=(
                f"<b>%{{text}}</b><br>"
                f"Risk: {risk}<br>"
                f"Severity: %{{customdata[0]:.2f}}<br>"
                f"Demand ×baseline: %{{customdata[1]:.2f}}<extra></extra>"
            ),
            customdata=sub[["effective_severity", "expected_demand_index"]].values,
        ))
    fig.update_geos(
        center=CHINA_CENTER, projection_scale=3.4,
        showcountries=True, countrycolor="lightgray",
        showland=True, landcolor="#FAFAFA",
        lataxis_range=[18, 54], lonaxis_range=[73, 135],
    )
    fig.update_layout(
        title=f"Regional Outbreak Forecast — {d.strftime('%b %d')} (day {day_of_year})",
        template="plotly_white", height=540,
        legend=dict(title="Risk level", orientation="v",
                    x=0.01, y=0.99, xanchor="left", yanchor="top",
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="lightgray", borderwidth=1),
        margin=dict(t=70, b=20, l=20, r=20),
    )
    return fig
