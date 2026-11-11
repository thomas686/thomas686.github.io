"""
tooltip.py
Streamlit popover-based contextual help module.
Provides mandatory ? clickable tooltips for every sidebar input and
main-page control, with Definition / Impact / Recommended / Example text.
UI language: English only.
"""
from __future__ import annotations

import streamlit as st


# -----------------------------------------------------------------------------
# Glossary for the Glossary tab
# -----------------------------------------------------------------------------
GLOSSARY: dict[str, str] = {
    "GSP": "Good Supply Practice — China's pharmaceutical distribution quality standard (GB/T 28842-2021). Mandates strict temperature-tier segregation during storage and transport; cold-chain transit < 24 h for 2-8 °C biologics (GSP §6.4).",
    "FTE": "Full-Time Equivalent = 1 worker × 1 shift = 8 h. For 24/7 DC coverage at 3 shifts/day, total headcount = 3 × FTE. Normalized cost per FTE-shift: 220 CNY permanent, 264 CNY temp (1.2× perm rate).",
    "Cold Chain": "Temperature-controlled supply chain (2-8 °C) for vaccines, insulins, biologics. Per USP <659> and WHO PQS E003/E004.",
    "DBSCAN": "Density-Based Spatial Clustering of Applications with Noise — groups dense regions and marks sparse points as noise.",
    "HDBSCAN": "Hierarchical DBSCAN — variable-density variant, more robust to clusters of different shapes and sizes.",
    "Clarke-Wright": "Classical savings-based vehicle routing heuristic. A 2-opt post-pass is applied to close the typical 5-10% route gap.",
    "RobustScaler": "Scikit-learn scaler using median and IQR, less sensitive to extreme values than StandardScaler.",
    "Silhouette Score": "Cluster cohesion/separation metric in [-1, 1]; higher is better.",
    "Calinski-Harabasz": "Variance-ratio cluster index; higher indicates denser, more separated clusters.",
    "Cart Capacity": "Maximum item/pick count a single picker cart can carry in one picking batch.",
    "Truck Load": "Maximum pallet/cube capacity of a single outbound delivery wave.",
    "OTC": "Over-The-Counter drug — purchasable without prescription.",
    "Rx": "Prescription-only medicine requiring a licensed practitioner authorization.",
    "Bootstrap CI": "Confidence interval obtained by resampling the demand distribution, used to quantify forecast uncertainty.",
    "Outbreak Score": "Composite 0-1 index combining population density, vaccination rate, hospital bed ratio and child share to flag at-risk regions. PH-4: log-linear form with spatial Gaussian smoothing in production.",
    "Scrap Rate": "Share of stock that expires before use. Industry 2-5% (McKinsey 2023); case-study 4.8%. Per-tier FEFO bands apply (severe ≤ 45d, mild ≤ 120d).",
    "Picking Error": "Mis-pick rate (baseline 0.35% of case value). Rises quadratically with staff gap: error = 0.35% × (1 + 3.5 × gap²). Pharma high-precision 0.5-1.7‰.",
    "Three-Shift": "Morning / Afternoon / Night, 8 h each. China Labour Law caps standard day at 8 h, week at 44 h average (art. 36, 41). EU Working Time Directive 2003/88/EC limits night work to ≤ 8 h/24 h.",
    "DC": "Distribution Center — central warehouse shipping to regional clients. The case study represents 1 of 6 such DCs in the network; remaining last-mile is via 856 distribution stations.",
    "H1N1": "Influenza A subtype known for pandemic potential; drives the H1N1 2.5× epidemic preset (aligned with Flu Season scenario_mult=2.5).",
    "Pediatric": "Child-formulated drug with weight-based dosing and dedicated packaging. Shorter shelf life (~65% of adult) and stricter cold-chain handling per WHO PQS E006.",
    "Pallet Cube": "Volumetric capacity of a pallet, used to convert items into truck-load units.",
    "Ambient": "Room-temperature tier (15-25 °C), the least restrictive storage condition.",
    "Frozen": "Ultra-cold tier (-20 °C) for certain vaccines and biologics.",
    "Lead Time": "End-to-end time from order placement to client delivery. Cut-off at 16:00, release-to-door 8-14 h, end-to-end 14-22 h (single DC).",
    "Next-Day Compliance": "Share of orders reaching the client within 24 h of release. Network baseline (6 central warehouses + 856 distribution stations): > 88%. Single central warehouse realistic: 77-85% (long-haul Xinjiang / Northeast can never be next-day from a single inland hub).",
    "Cold Premium": "Multiplier (× ambient cost) for cold-chain transport. Published benchmark 1.5-1.85× (LogisticsIQ 2024). Per-scenario: Normal 1.5, Peak 1.65, Flu 1.85.",
    # ---- PH-7 / LG-7 / HR-6 / WM-7: regulatory citations ----
    "VVM": "Vaccine Vial Monitor (WHO PQS E006) — time-temperature indicator on every vaccine vial; irreversible colour change on cumulative heat exposure.",
    "DSCSA": "Drug Supply Chain Security Act (US FDA, 2013-2023 phase-in) — interoperable, electronic, package-level traceability of prescription drugs in the US market.",
    "EU GDP": "EU Good Distribution Practice (2013/C 343/01) — Chapter 9 covers temperature-controlled transport qualification (annual summer + winter profile tests, vehicle and container qualification records).",
    "MEM": "Moving Epidemic Method (ECDC) — calculates medium / high / very-high intensity bands per ISO epi-week from a multi-year historical baseline. Used in place of a static outbreak threshold (was 1.8×, now per-month band table).",
    "FEFO": "First-Expiry-First-Out picking rule mandated by ChP 2020 §9001 and GB/T 28842-2021 §4.3. Pharma DC scrap rate 2-5% industry (McKinsey 2023).",
    "FTE Ramp-up": "Productivity discount for temporary staff in the first 90 days (Hewitt China HC 2024). Effective FTE = permanent + temp × 0.8. Temp cost 1.2× permanent (10-30% industry premium).",
}


# -----------------------------------------------------------------------------
# Tooltip definitions keyed by widget label
# Each entry: { "def": ..., "impact": ..., "recommended": ..., "example": ... }
# -----------------------------------------------------------------------------
TOOLTIPS: dict[str, dict[str, str]] = {
    # ----- Data Generation panel -----
    "Number of Orders": {
        "def": "Total order lines generated for the simulation day.",
        "impact": "Higher order counts increase compute time but improve statistical significance of KPIs.",
        "recommended": "2,000-3,000 for a central-warehouse shift, 6,000-10,000 for epidemic peaks.",
        "example": "2,500 orders -> roughly 40,000 cases/day at a central DC.",
    },
    "Drug Catalog Size": {
        "def": "Number of distinct SKU lines in the simulated catalog subset.",
        "impact": "Larger catalogs dilute per-SKU demand and create longer picking routes.",
        "recommended": "300-1,000 SKUs as a representative slice of a 70K central-warehouse catalog.",
        "example": "500 SKUs across 4 clinical tiers.",
    },
    "Near-Expiry Base %": {
        "def": "Share of stock with <=90 days remaining shelf life at simulation start.",
        "impact": "Higher values raise scrap risk and inventory carrying cost.",
        "recommended": "4.5-5.0% matches industry baseline (4.8%).",
        "example": "5.0% of total stock will be near-expiry flagged.",
    },
    "Random Seed": {
        "def": "Integer seed for reproducible order generation and clustering.",
        "impact": "Same seed always produces the same dataset, enabling A/B comparisons.",
        "recommended": "42 is a common default; pick any integer for new runs.",
        "example": "seed=42 -> reproducible across runs.",
    },
    "Client Mix": {
        "def": "Distribution of orders across Hospital / Independent Pharmacy / Primary Care.",
        "impact": "Hospitals drive large cold-chain batches; pharmacies drive small ambient orders.",
        "recommended": "Hosp 30% / Indep Pharm 50% / Primary Care 20% for a balanced B2B mix.",
        "example": "[0.30, 0.50, 0.20] is auto-normalized.",
    },
    "Include Pediatric SKUs": {
        "def": "Add child-formulated SKUs to the catalog.",
        "impact": "Pediatric items add labor surcharges and shorter expiry windows.",
        "recommended": "Enable for realism; disable to isolate adult-only operations.",
        "example": "Pediatric syrups and chewable tablets.",
    },

    # ----- Flu Forecasting panel -----
    "Forecast Horizon (days)": {
        "def": "Number of days projected forward from today.",
        "impact": "Longer horizons widen the 95% confidence band and reduce SKU-level reliability.",
        "recommended": "7d for replenishment, 30d for capacity, 90d for procurement planning.",
        "example": "30 days -> typical monthly cycle.",
    },
    "Season Month": {
        "def": "Calendar month used to anchor the seasonal flu curve.",
        "impact": "Dec-Feb multiplies demand 2-3x; Jun-Aug suppresses demand.",
        "recommended": "Pick the month you are simulating for.",
        "example": "Month=1 (January) -> peak China flu season.",
    },
    "Flu Intensity Multiplier": {
        "def": "Global scalar applied on top of the seasonal curve.",
        "impact": "1.0 = baseline, 2.8 = peak season, 3.5 = H1N1-style epidemic.",
        "recommended": "Use a preset button rather than manual tuning.",
        "example": "1.45 = moderate outbreak per data-generator rules.",
    },
    "Bootstrap Resamples": {
        "def": "Number of resamples used to compute the 95% confidence interval.",
        "impact": "More resamples -> tighter CI at higher compute cost.",
        "recommended": "200-400 for interactive use, 1000 for publication.",
        "example": "200 resamples takes ~0.5s for 30 SKUs.",
    },
    "Auto-Demand Override": {
        "def": "If enabled, the forecast result replaces the manual order-count slider.",
        "impact": "Removes double-counting between manual and predicted demand.",
        "recommended": "On for forecast-driven scenarios, off for stress testing.",
        "example": "Forecast 612 -> slider is locked at 612.",
    },
    "Upload Historical CSV": {
        "def": "Optional CSV of past orders used to recalibrate baseline order count and flu multipliers.",
        "impact": "Improves realism but adds a few seconds of compute.",
        "recommended": "Provide at least 30 days of history with date + order_count columns.",
        "example": "Columns: date, orders, region, sku, qty.",
    },

    # ----- Picking Clustering panel -----
    "Clustering Algorithm": {
        "def": "Algorithm used for intra-warehouse picking batch generation.",
        "impact": "KMeans needs k; DBSCAN/HDBSCAN find noise that is then re-assigned.",
        "recommended": "HDBSCAN for variable-density DCs; KMeans for uniform layouts.",
        "example": "HDBSCAN -> min_cluster_size=20.",
    },
    "Number of Pickers (FTE)": {
        "def": "Total picking staff available for the simulated shift.",
        "impact": "Lower FTE raises picking error and slows the line. In Normal non-flu season the permanent roster alone should cover demand.",
        "recommended": "Size permanent staff to Normal demand; add temps for Peak / Flu Season only.",
        "example": "90 permanent + 0 temp = comfortable Normal coverage at a central DC.",
    },
    "Cart Capacity": {
        "def": "Maximum item lines a single pick cart can carry in one batch.",
        "impact": "Smaller carts split into more batches -> longer total walking distance.",
        "recommended": "60-100 lines per cart for mid-size DCs.",
        "example": "Cap=80 -> batch with 95 lines auto-splits.",
    },
    "RobustScaler": {
        "def": "Scale features by median and IQR instead of mean and std.",
        "impact": "More resistant to extreme outliers (bulk orders).",
        "recommended": "On when order sizes have heavy tails.",
        "example": "On -> DBSCAN no longer dominated by 1 huge order.",
    },
    "Route Algorithm": {
        "def": "Heuristic used to sequence stops within each batch.",
        "impact": "Clarke-Wright typically saves 10-20% vs Nearest Neighbor.",
        "recommended": "Clarke-Wright for production runs.",
        "example": "Nearest Neighbor: greedy walk to closest stop.",
    },
    "Auto Hyperparameter Grid": {
        "def": "Search over (eps, min_samples) for DBSCAN/HDBSCAN to maximize efficiency.",
        "impact": "Adds 3-10s of compute but finds better clusters.",
        "recommended": "On for final runs, off for fast iteration.",
        "example": "Search 12 candidate configs.",
    },

    # ----- Shipment Wave panel -----
    "Max Cold-Chain Transit Days": {
        "def": "Hard cap on days a cold-chain delivery may travel before the truck is split.",
        "impact": "Longer trips raise spoilage risk and reduce next-day compliance.",
        "recommended": "1-2 days for cold chain, 3 days for ambient.",
        "example": "Cap=1.5 days -> wave auto-splits above 1.5d.",
    },
    "Max Truck Load (pallets)": {
        "def": "Maximum pallet count per outbound truck wave.",
        "impact": "Oversize waves split into multiple trucks, raising fixed cost.",
        "recommended": "20-26 pallets for standard 12m truck.",
        "example": "Cap=24 -> 30-pallet wave splits to 24 + 6.",
    },
    "Wave Algorithm": {
        "def": "Clustering algorithm used for cross-regional shipment waves.",
        "impact": "HDBSCAN handles irregular Chinese geography better than KMeans.",
        "recommended": "HDBSCAN for nationwide networks.",
        "example": "HDBSCAN -> auto-discovers province-sized waves.",
    },
    "Strict 3-Tier Segregation": {
        "def": "Enforce GB/T 28842 — frozen/cold/ambient cannot mix in one wave.",
        "impact": "Strict mode is regulatory-compliant but may add waves.",
        "recommended": "Always on; off only for theoretical experiments.",
        "example": "Frozen + ambient order -> split into 2 waves.",
    },
    "Cold Premium Factor": {
        "def": "Multiplier for cold-chain transport cost relative to ambient.",
        "impact": "Higher premium better reflects real reefer truck cost.",
        "recommended": "1.4-1.8 for typical Chinese long-haul rates.",
        "example": "1.6 -> cold wave costs 1.6x ambient wave.",
    },

    # ----- What-If & Display panel -----
    "Currency": {
        "def": "Display currency for all monetary KPIs.",
        "impact": "EUR/CNY toggle only changes display, fixed 7.8 rate.",
        "recommended": "CNY for domestic reports, EUR for HQ roll-ups.",
        "example": "10000 CNY -> 1282 EUR at rate 7.8.",
    },
    "Compare vs Random": {
        "def": "Run a fully random baseline to benchmark AI performance.",
        "impact": "Adds ~1s of compute per tab refresh.",
        "recommended": "On for executive dashboards, off for daily ops.",
        "example": "AI saves 23% distance vs random.",
    },
    "Scenario Preset": {
        "def": "One-click load of a pre-defined flu scenario.",
        "impact": "Overwrites the manual flu multiplier and order sliders.",
        "recommended": "Pick the closest match to your real situation.",
        "example": "Standard Peak Flu = +280% volume.",
    },
    "Use 3D Warehouse View": {
        "def": "Toggle between 2D top-down and 3D isometric warehouse map.",
        "impact": "3D uses more GPU but reveals multi-tier rack stacking.",
        "recommended": "2D for screenshare, 3D for deep-dive analysis.",
        "example": "3D shows frozen mezzanine above ambient floor.",
    },
    "Top-K SKUs": {
        "def": "Number of top SKUs shown in detail charts.",
        "impact": "More SKUs = busier charts but better coverage.",
        "recommended": "10-20 SKUs.",
        "example": "Top 15 SKUs by forecast demand.",
    },
    "Export KPIs CSV": {
        "def": "Download button for the current KPI snapshot.",
        "impact": "Enables offline Excel / Power BI follow-up.",
        "recommended": "Export after each scenario run.",
        "example": "kpis_2026-06-04.csv.",
    },
    "Export Raw Orders CSV": {
        "def": "Download button for the generated order list.",
        "impact": "Useful for QA and ad-hoc SQL joins.",
        "recommended": "Export when a bug is suspected.",
        "example": "orders_2026-06-04.csv.",
    },
    "Save Preset": {
        "def": "Persist all sidebar parameters to a JSON file.",
        "impact": "Enables reproducible what-if comparisons.",
        "recommended": "Save before any non-trivial scenario change.",
        "example": "preset_h1n1_epidemic.json.",
    },
    "Load Preset": {
        "def": "Restore all sidebar parameters from a saved JSON file.",
        "impact": "Removes manual re-entry and human error.",
        "recommended": "Load before sharing results with stakeholders.",
        "example": "preset_baseline.json -> one-click restore.",
    },
}


def help_button(label: str, key: str | None = None) -> None:
    """Render a clickable ? button that pops the tooltip for *label*.

    Uses st.popover so the help text appears inline next to the input.
    """
    info = TOOLTIPS.get(label)
    if not info:
        return
    pop_key = f"hlp_{key or label}"
    try:
        with st.popover("?", help=info["def"], use_container_width=False):
            st.markdown(f"**{label}**")
            st.markdown(f"*Definition:* {info['def']}")
            st.markdown(f"*Impact:* {info['impact']}")
            st.markdown(f"*Recommended:* {info['recommended']}")
            st.markdown(f"*Example:* {info['example']}")
    except Exception:
        # Streamlit < 1.30 fallback
        st.caption(f"{label}: {info['def']}")


def label_with_help(label: str, key: str | None = None) -> str:
    """Return the label string; intended for use cases where a popover is rendered separately."""
    return label


def render_help_panel() -> None:
    """Render a collapsible panel listing every tooltip — useful for the Glossary tab."""
    st.markdown("### Contextual Help — All Tooltips")
    for label, info in TOOLTIPS.items():
        with st.expander(label, expanded=False):
            st.markdown(f"**Definition:** {info['def']}")
            st.markdown(f"**Impact:** {info['impact']}")
            st.markdown(f"**Recommended:** {info['recommended']}")
            st.markdown(f"**Example:** {info['example']}")
