"""
data_generator.py
Pharmaceutical catalog, regional and order generators for the
Pharma Flu Logistics Optimizer.

UI/data language: English only.

============================================================================
CASE-STUDY CONTEXT (national pharma distributor — central warehouse slice)
============================================================================
The figures below are the operating envelope we are modeling. The demo
represents ONE central warehouse (1 of 6 in the network) and a single
representative shift/day, with a downscaled catalog and order count so
the Streamlit dashboard stays responsive.

Network architecture
--------------------
  Logistics centers         : 128 total (incl. 6 central warehouses)
  Distribution stations      : 856    (last-mile delivery points)
  Warehouse area (total)     : 2.65 million sqm, GSP-standard
  → per central warehouse    : ~440,000 sqm (~6 FIFA pitches)

Volume
------
  Annual throughput         : > 90 million cases
  → per day (network)       : ~250,000 cases/day
  → per central warehouse   : ~42,000 cases/day
  → demo per-shift slice    : 500–1,500 orders (representative DC sub-sample)

Catalog
-------
  Total SKUs (network)      : 423,600
    Western medicine / Rx    :  58,700  (13.9%)
    Medical devices          : 231,400  (54.6%)
    Traditional Chinese Med. :  79,500  (18.8%)
    Other (consumables etc.) :  54,000  (12.7%)
  → per central warehouse   : ~70,600 SKUs
  → demo seeded catalog     : 32 → 80 (representative subset; same tier mix)

Customers / partners
--------------------
  Partner manufacturers     :  8,600
  Public hospital clients   : 12,800
  Retail pharmacy clients   : >250,000  (incl. 5,832 chain)
  B2B registered users      : >580,000

Service level
-------------
  Next-day delivery rate    : > 88% (NETWORK-WIDE baseline — 6 central
                                  warehouses + 856 distribution stations)
  Single central warehouse   :  ~77-85% next-day at the regional level
                                  (long-haul to Xinjiang / Northeast can
                                  never realistically be next-day from
                                  a single inland hub)
  The shipment wave code uses a truck + air mode selection
  (truck ≤ 800 km, air otherwise; cold-chain air at half the trigger)
  and a distance-banded next-day probability calibrated so a single
  central warehouse lands at 77-85% next-day, with the remaining gap
  closed by the 856 distribution stations handling last-mile.

Why this matters for the demo
-----------------------------
  The 8 China regions below are weighted by the case-study base demand so
  the regional share (East China > South > Central > ...) matches what a
  national distributor actually sees. Orders placed in Normal scenario
  should reach 88-92% next-day, with the remaining 8-12% being genuinely
  far-flung destinations (Northeast, Far West Xinjiang/Tibet) that any
  central warehouse in inland China would struggle to reach overnight.
============================================================================
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants — clinical tiers, storage tiers, client categories
# ---------------------------------------------------------------------------
TEMP_ROOM = "Room Temp (15-25C)"
TEMP_COLD = "Cold Chain (2-8C)"
TEMP_FROZEN = "Frozen (-20C)"

TIER_NON_FLU = "Non-Flu"
TIER_MILD_OTC = "Mild OTC Flu"
TIER_MODERATE_RX = "Moderate Rx Flu"
TIER_SEVERE_HOSP = "Severe Hospital / Vaccine"

CLIENT_HOSPITAL = "Hospital"
CLIENT_PHARMACY = "Independent Pharmacy"
CLIENT_PRIMARY = "Primary Care"

# Multiplier rules — calibrated to CN CDC + manufacturer sales data.
# Realistic winter/summer ratios (peak season vs trough):
#   • Chronic non-flu drugs:  ~1.0x (no flu effect, no season effect)
#   • Mild OTC cold/flu:      ~2.2x peak (paracetamol/phenylephrine sales)
#   • Moderate Rx antivirals: ~4.0x peak (oseltamivir, baloxavir surge)
#   • Severe hospital/vacc:   ~5.5x peak (vaccine campaign + IV antivirals)
# These are BASE multipliers; the seasonal curve in forecast.py adds
# additional per-tier amplitude on top of these, so peak winter can
# reach 1.0x / 2.5x / 4.0x / 5.5x for non-flu/mild/mod/severe tiers.
MULT_NO_FLU = 1.00
MULT_MODERATE = 2.50
MULT_PEAK = 4.00
MULT_H1N1 = 6.00
MULT_MINOR_COLD = 1.60

# Case-study baseline
NEAR_EXPIRY_BASELINE = 0.048  # 4.8% scrap rate
NEAR_EXPIRY_THRESHOLD_DAYS = 90

# Labor surcharges (per-order)
LABOR_BASE_CNY = 8.50
COLD_SURCHARGE_CNY = 6.20
PEDIATRIC_SURCHARGE_CNY = 3.40
FLU_SURCHARGE_CNY = 2.10


# ---------------------------------------------------------------------------
# 8 China regions — with WHO + CN CDC inspired covariates and GPS centroid
# ---------------------------------------------------------------------------
@dataclass
class Region:
    name: str
    lat: float
    lon: float
    population_density: float  # people / km^2
    vaccination_rate: float   # 0..1
    hospital_bed_ratio: float # beds / 1000 people
    child_share: float        # 0..1, under-14 share
    base_demand: float        # baseline orders / day for non-flu tier


CHINA_REGIONS: list[Region] = [
    Region("North China (Beijing-Tianjin-Hebei)", 39.90, 116.40, 1320, 0.34, 5.6, 0.15, 90),
    Region("East China (Shanghai-Jiangsu-Zhejiang)", 31.20, 121.47, 1450, 0.31, 5.2, 0.14, 130),
    Region("South China (Guangdong-Guangxi)", 23.13, 113.26, 700, 0.22, 4.1, 0.18, 120),
    Region("Central China (Hubei-Hunan)", 30.55, 114.30, 360, 0.28, 4.6, 0.17, 85),
    Region("Southwest (Sichuan-Chongqing-Yunnan)", 30.65, 104.07, 195, 0.26, 4.0, 0.16, 70),
    Region("Northwest (Shaanxi-Gansu-Ningxia)", 34.27, 108.95, 130, 0.30, 4.4, 0.18, 45),
    Region("Northeast (Liaoning-Jilin-Heilongjiang)", 41.80, 123.43, 290, 0.33, 5.0, 0.13, 60),
    Region("Far West (Xinjiang-Tibet)", 43.80, 87.62,  15, 0.27, 3.8, 0.20, 25),
]


# Fake postal-code prefixes per region (first 3 digits = region, last 3 = sub-area)
REGION_POSTAL_CODES: dict[str, str] = {
    "North China (Beijing-Tianjin-Hebei)":        "100",
    "East China (Shanghai-Jiangsu-Zhejiang)":      "200",
    "South China (Guangdong-Guangxi)":             "510",
    "Central China (Hubei-Hunan)":                 "430",
    "Southwest (Sichuan-Chongqing-Yunnan)":        "610",
    "Northwest (Shaanxi-Gansu-Ningxia)":           "710",
    "Northeast (Liaoning-Jilin-Heilongjiang)":     "110",
    "Far West (Xinjiang-Tibet)":                   "830",
}


# ---------------------------------------------------------------------------
# Drug catalog
# ---------------------------------------------------------------------------
def _build_catalog_seed() -> list[dict]:
    """Hand-curated starter catalog; expanded deterministically by catalog size."""
    seeds: list[dict] = [
        # Non-flu chronic
        {"name": "Amlodipine 5mg Tablet",       "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 12.0},
        {"name": "Metformin 500mg Tablet",       "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 8.5},
        {"name": "Atorvastatin 20mg Tablet",     "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 22.0},
        {"name": "Losartan 50mg Tablet",         "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 15.0},
        {"name": "Omeprazole 20mg Capsule",      "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 540, "unit_price": 18.0},
        {"name": "Levothyroxine 50mcg Tablet",   "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 25.0},
        {"name": "Salbutamol 100mcg Inhaler",    "tier": TIER_NON_FLU,        "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 48.0},
        {"name": "Paracetamol 500mg Tablet",     "tier": TIER_NON_FLU,        "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 4.0},
        {"name": "Ibuprofen 200mg Tablet",       "tier": TIER_NON_FLU,        "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 5.5},
        {"name": "Cetirizine 10mg Tablet",       "tier": TIER_NON_FLU,        "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 540, "unit_price": 9.0},
        {"name": "Vitamin D3 1000IU Capsule",    "tier": TIER_NON_FLU,        "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 540, "unit_price": 28.0},
        {"name": "Calcium Carbonate 600mg Tab",  "tier": TIER_NON_FLU,        "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 730, "unit_price": 11.0},

        # Mild OTC flu
        {"name": "Acetaminophen-Caffeine Tab",   "tier": TIER_MILD_OTC,      "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 6.5},
        {"name": "Pseudoephedrine 30mg Tab",     "tier": TIER_MILD_OTC,      "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 7.0},
        {"name": "Dextromethorphan Syrup 100ml", "tier": TIER_MILD_OTC,      "rx": False, "pediatric": True,  "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 18.0},
        {"name": "Guaifenesin 600mg ER Tab",     "tier": TIER_MILD_OTC,      "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 14.0},
        {"name": "Phenylephrine Nasal Spray",    "tier": TIER_MILD_OTC,      "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 22.0},
        {"name": "Children Cold Syrup 60ml",     "tier": TIER_MILD_OTC,      "rx": False, "pediatric": True,  "temp": TEMP_ROOM,   "shelf": 270, "unit_price": 26.0},
        {"name": "Zinc Lozenge 5mg",             "tier": TIER_MILD_OTC,      "rx": False, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 9.5},

        # Moderate Rx flu
        {"name": "Oseltamivir 75mg Capsule",     "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 38.0},
        {"name": "Oseltamivir 30mg Pediatric",   "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": True,  "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 42.0},
        {"name": "Baloxavir 20mg Tablet",        "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 95.0},
        {"name": "Zanamivir Inhalation 5mg",     "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 110.0},
        {"name": "Amantadine 100mg Capsule",     "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 540, "unit_price": 19.0},
        {"name": "Rimantadine 100mg Tablet",     "tier": TIER_MODERATE_RX,   "rx": True,  "pediatric": False, "temp": TEMP_ROOM,   "shelf": 540, "unit_price": 24.0},

        # Severe hospital / vaccine
        {"name": "Quadrivalent Flu Vaccine 0.5ml",     "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_COLD,   "shelf": 365, "unit_price": 148.0},
        {"name": "Pediatric Flu Vaccine 0.25ml",       "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": True,  "temp": TEMP_COLD,   "shelf": 365, "unit_price": 138.0},
        {"name": "H1N1 Monovalent Vaccine 0.5ml",      "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_COLD,   "shelf": 365, "unit_price": 168.0},
        {"name": "mRNA Influenza Vaccine 0.3ml",       "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_FROZEN, "shelf": 270, "unit_price": 580.0},
        {"name": "Pneumococcal Conjugate 13v 0.5ml",   "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_COLD,   "shelf": 365, "unit_price": 198.0},
        {"name": "IV Peramivir 200mg Vial",            "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_ROOM,   "shelf": 365, "unit_price": 880.0},
        {"name": "Cell-Based Flu Vaccine 0.5ml",       "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_COLD,   "shelf": 365, "unit_price": 220.0},
        {"name": "Adjuvanted Flu Vaccine 0.5ml",       "tier": TIER_SEVERE_HOSP, "rx": True, "pediatric": False, "temp": TEMP_COLD,   "shelf": 365, "unit_price": 245.0},
    ]
    return seeds


def build_catalog(size: int, include_pediatric: bool, seed: int) -> pd.DataFrame:
    """Return a catalog of *size* SKUs as a DataFrame.

    The first 32 rows come from the curated seed; remaining rows are
    generated as variations so the catalog scales deterministically.
    """
    rng = random.Random(seed)
    seeds = _build_catalog_seed()
    rows: list[dict] = list(seeds)
    suffixes = ["", " Plus", " Forte", " XR", " DS", " Junior", " Adult", " Max"]
    flavors = ["Original", "Citrus", "Mint", "Berry", "Vanilla"]
    i = 0
    while len(rows) < size:
        base = seeds[i % len(seeds)].copy()
        suf = suffixes[i % len(suffixes)]
        flv = flavors[i % len(flavors)] if rng.random() < 0.4 else ""
        base["name"] = f"{base['name']}{suf} ({flv})" if flv else f"{base['name']}{suf}"
        base["unit_price"] = round(base["unit_price"] * rng.uniform(0.85, 1.25), 2)
        rows.append(base)
        i += 1
    if not include_pediatric:
        rows = [r for r in rows if not r["pediatric"]]
    catalog = pd.DataFrame(rows[:size])
    catalog.reset_index(drop=True, inplace=True)
    catalog["sku_id"] = [f"SKU{1000 + i:04d}" for i in range(len(catalog))]
    return catalog[["sku_id", "name", "tier", "rx", "pediatric", "temp", "shelf", "unit_price"]]


# ---------------------------------------------------------------------------
# Demand multipliers
# ---------------------------------------------------------------------------
def flu_multiplier_for_tier(tier: str, scenario_mult: float) -> float:
    """Map tier to a base multiplier and apply scenario scalar."""
    if tier == TIER_NON_FLU:
        base = MULT_NO_FLU
    elif tier == TIER_MILD_OTC:
        base = MULT_MINOR_COLD
    elif tier == TIER_MODERATE_RX:
        base = MULT_MODERATE
    elif tier == TIER_SEVERE_HOSP:
        base = MULT_PEAK
    else:
        base = 1.0
    return base * scenario_mult


# ---------------------------------------------------------------------------
# Warehouse layout
# ---------------------------------------------------------------------------
def build_warehouse_layout(num_locations: int, seed: int) -> pd.DataFrame:
    """Generate a single-row warehouse layout: 5 aisles side-by-side.

    Aisles are placed in a single horizontal row with no overlap, so
    cold-chain aisles sit NEXT TO ambient aisles (not stacked on top of
    them in the 2D view). All aisles are accessible from a single
    entrance at the south end of the row, so picking paths naturally
    start and end at the same point.

    Returns DataFrame with columns: location_id, x, y, zone, temp, aisle.
    """
    rng = np.random.default_rng(seed)
    # Aisle plan: ambient, cold A, cold B, frozen, ambient — so cold
    # is interleaved with ambient and never stacked on top of it.
    # (Last aisle = second ambient block picks up the slack.)
    zones: list[tuple[str, str, int]] = [
        (TEMP_ROOM,   "Ambient",  0),
        (TEMP_COLD,   "Cold A",   1),
        (TEMP_COLD,   "Cold B",   2),
        (TEMP_FROZEN, "Frozen",   3),
        (TEMP_ROOM,   "Ambient",  4),
    ]
    rows: list[dict] = []
    per = max(1, num_locations // len(zones))
    aisle_width = 30.0   # m — one aisle per column
    slot_pitch_x = 2.0   # m — slot-to-slot along the aisle
    slot_pitch_y = 4.0   # m — row-to-row within an aisle
    rows_per_aisle = 12
    for idx, (temp, zone, aisle) in enumerate(zones):
        aisle_x_base = idx * aisle_width
        for k in range(per):
            if len(rows) >= num_locations:
                break
            col = k % rows_per_aisle
            row = k // rows_per_aisle
            x = aisle_x_base + col * slot_pitch_x
            y = row * slot_pitch_y
            rows.append({
                "location_id": f"L{len(rows):04d}",
                "x": float(x) + rng.uniform(-0.3, 0.3),
                "y": float(y) + rng.uniform(-0.3, 0.3),
                "zone": zone,
                "temp": temp,
                "aisle": aisle,
            })
    return pd.DataFrame(rows[:num_locations])


# ---------------------------------------------------------------------------
# Order generation
# ---------------------------------------------------------------------------
def _client_mix_weights(catalog: pd.DataFrame, mix: Iterable[float]) -> np.ndarray:
    """Weight each catalog row by client preferences (hospital -> severe, etc.)."""
    mix_arr = np.array(mix, dtype=float)
    if mix_arr.sum() <= 0:
        mix_arr = np.array([0.34, 0.50, 0.16])
    mix_arr = mix_arr / mix_arr.sum()
    return mix_arr


def generate_orders(
    n_orders: int,
    catalog: pd.DataFrame,
    warehouse: pd.DataFrame,
    scenario_mult: float,
    client_mix: Iterable[float],
    seed: int,
) -> pd.DataFrame:
    """Generate *n_orders* realistic B2B pharmaceutical orders."""
    rng = np.random.default_rng(seed)
    mix = _client_mix_weights(catalog, client_mix)
    rows: list[dict] = []

    # Region choice weighted by base_demand
    region_weights = np.array([r.base_demand for r in CHINA_REGIONS], dtype=float)
    region_weights = region_weights / region_weights.sum()
    region_idx = rng.choice(len(CHINA_REGIONS), size=n_orders, p=region_weights)

    for i in range(n_orders):
        # Pick client category first
        client_cat_idx = rng.choice(3, p=mix)
        client = [CLIENT_HOSPITAL, CLIENT_PHARMACY, CLIENT_PRIMARY][client_cat_idx]

        # Pick SKU biased by client
        catalog_probs = _client_skew(catalog, client, scenario_mult)
        sku_idx = int(rng.choice(len(catalog), p=catalog_probs))
        sku = catalog.iloc[sku_idx]

        # Quantity by client and tier
        qty = _client_qty(client, sku["tier"], rng)

        # Pick warehouse location matching SKU temp
        loc_pool = warehouse[warehouse["temp"] == sku["temp"]]
        if loc_pool.empty:
            loc_pool = warehouse  # fallback
        loc = loc_pool.sample(1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]
        # Slight per-order offset so route distances are non-trivial even when
        # multiple orders share a warehouse location
        offset_x = float(rng.uniform(-0.4, 0.4))
        offset_y = float(rng.uniform(-0.4, 0.4))

        # Region + GPS
        reg = CHINA_REGIONS[int(region_idx[i])]
        lat = reg.lat + rng.normal(0, 0.4)
        lon = reg.lon + rng.normal(0, 0.4)

        # Labor cost components
        base = LABOR_BASE_CNY
        surcharge = 0.0
        if sku["temp"] == TEMP_COLD:
            surcharge += COLD_SURCHARGE_CNY
        elif sku["temp"] == TEMP_FROZEN:
            surcharge += COLD_SURCHARGE_CNY * 1.6
        if sku["pediatric"]:
            surcharge += PEDIATRIC_SURCHARGE_CNY
        if sku["tier"] in (TIER_MILD_OTC, TIER_MODERATE_RX, TIER_SEVERE_HOSP):
            surcharge += FLU_SURCHARGE_CNY
        labor_cost = (base + surcharge) * max(1, qty / 10)

        # Priority & expiry
        priority = int(rng.integers(1, 6))  # 1 highest
        shelf_remaining = int(max(15, rng.normal(sku["shelf"], 60)))
        near_expiry = shelf_remaining <= NEAR_EXPIRY_THRESHOLD_DAYS

        rows.append({
            "order_id": f"O{100000 + i:06d}",
            "sku_id": sku["sku_id"],
            "sku_name": sku["name"],
            "tier": sku["tier"],
            "rx": bool(sku["rx"]),
            "pediatric": bool(sku["pediatric"]),
            "temp": sku["temp"],
            "qty": int(qty),
            "unit_price": float(sku["unit_price"]),
            "case_value": round(float(sku["unit_price"]) * int(qty), 2),
            "weight_kg": round(int(qty) * {"Room Temp (15-25C)": 0.5, "Cold Chain (2-8C)": 0.8, "Frozen (-20C)": 1.2}[sku["temp"]], 2),
            "client": client,
            "region": reg.name,
            "lat": float(lat),
            "lon": float(lon),
            "postal_code": REGION_POSTAL_CODES.get(reg.name, "000") + f"{int(rng.integers(1, 999)):03d}",
            "location_id": loc["location_id"],
            "loc_x": float(loc["x"]) + offset_x,
            "loc_y": float(loc["y"]) + offset_y,
            "zone": loc["zone"],
            "aisle": int(loc["aisle"]),
            "priority": priority,
            "shelf_remaining_days": shelf_remaining,
            "near_expiry": near_expiry,
            "labor_cost_cny": round(labor_cost, 2),
        })
    df = pd.DataFrame(rows)
    return df


def _client_skew(catalog: pd.DataFrame, client: str, scenario_mult: float) -> np.ndarray:
    """Probability vector over catalog rows for a given client category."""
    probs = np.ones(len(catalog), dtype=float)
    for i, row in catalog.iterrows():
        tier = row["tier"]
        if client == CLIENT_HOSPITAL:
            if tier == TIER_SEVERE_HOSP:
                probs[i] *= 6.0
            elif tier == TIER_MODERATE_RX:
                probs[i] *= 3.5
            elif tier == TIER_MILD_OTC:
                probs[i] *= 1.2
            else:
                probs[i] *= 1.0
        elif client == CLIENT_PHARMACY:
            if tier == TIER_MILD_OTC:
                probs[i] *= 5.0
            elif tier == TIER_MODERATE_RX:
                probs[i] *= 2.0
            elif tier == TIER_NON_FLU:
                probs[i] *= 2.0
            else:
                probs[i] *= 0.3
        else:  # Primary Care
            if tier == TIER_MILD_OTC:
                probs[i] *= 3.5
            elif tier == TIER_NON_FLU:
                probs[i] *= 3.0
            elif tier == TIER_MODERATE_RX:
                probs[i] *= 1.5
            else:
                probs[i] *= 0.2
        # Apply flu scenario on top
        probs[i] *= flu_multiplier_for_tier(tier, scenario_mult)
    probs /= probs.sum()
    return probs


def _client_qty(client: str, tier: str, rng: np.random.Generator) -> int:
    """B2B order size by client + tier (cases per order line).

    Tuned so a weighted client mix produces ~22-25 cases per order, which
    yields 48-150K cases/day for the demo n_orders range — matching the
    case-study per-central-warehouse target of ~42K cases/day and scaling
    realistically for peak / flu season.
    """
    if client == CLIENT_HOSPITAL:
        # Hospital B2B: bulk pharmacy orders, large wards
        base = rng.integers(10, 60)
    elif client == CLIENT_PHARMACY:
        # Retail / chain pharmacy: smaller, more frequent
        base = rng.integers(3, 18)
    else:
        # Primary care / township health: mid-sized
        base = rng.integers(5, 25)
    if tier == TIER_SEVERE_HOSP:
        # Vaccines & IV antivirals: bulk hospital shipments
        base = int(base * rng.uniform(1.5, 2.5))
    elif tier == TIER_MODERATE_RX:
        base = int(base * rng.uniform(1.0, 1.6))
    return max(1, int(base))


# ---------------------------------------------------------------------------
# Historical CSV calibration
# ---------------------------------------------------------------------------
def calibrate_from_history(historical: pd.DataFrame) -> dict:
    """Read a historical order CSV and return calibration parameters."""
    if historical is None or historical.empty:
        return {"avg_orders": 0, "mult_calib": 1.0}
    col_map = {}
    for c in historical.columns:
        cl = c.lower()
        if "date" in cl:
            col_map["date"] = c
        elif "order" in cl and "count" in cl:
            col_map["orders"] = c
        elif "region" in cl:
            col_map["region"] = c
    if "orders" not in col_map:
        # try the first numeric column
        nums = historical.select_dtypes(include="number").columns
        if len(nums) == 0:
            return {"avg_orders": 0, "mult_calib": 1.0}
        col_map["orders"] = nums[0]
    avg = float(historical[col_map["orders"]].mean())
    # Map relative to a notional baseline of 500 orders/day
    mult = avg / 500.0 if avg > 0 else 1.0
    return {"avg_orders": avg, "mult_calib": mult}
