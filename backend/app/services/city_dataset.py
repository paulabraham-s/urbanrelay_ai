"""Per-area calibration dataset service.

Source: ``data/seed/city_area_calibration.csv`` — a cleaned dataset of 150
urban areas across 10 Indian cities (Mumbai, Delhi, Bengaluru, Hyderabad,
Ahmedabad, Chennai, Kolkata, Pune, Jaipur, Visakhapatnam). Each row carries
measured/calibrated demand and infrastructure figures for one area:

    area_id, city, state, area_name,
    total_road_length_km, num_intersections,
    avg_traffic_volume_per_hr, avg_traffic_speed_kmph, congestion_level,
    num_micro_hubs, total_hub_storage_capacity, avg_hub_utilization_pct,
    num_delivery_orders_monthly, avg_package_weight_kg,
    num_vehicles_fleet, most_common_vehicle_type,
    num_couriers, avg_courier_capacity_kg,
    avg_daily_demand_orders, num_curb_zones, total_curb_capacity_vehicles

The dataset was prepared in ``docs/notebooks/UrbanRelay_AI_Data_Pipeline.ipynb``
(loading, cleaning, visualization, feature selection and a congestion-level
classifier — see ``backend/scripts/train_congestion_model.py``).

Everything the simulation seeds (hubs per zone, curb capacity, fleet mix,
couriers, demand rates) is *calibrated from these rows* instead of being
hand-invented. Real OpenStreetMap road geometry supplies the network; this
dataset supplies the logistics parameters. Labels: CALIBRATED / SIMULATED.
"""

import csv
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

CONGESTION_FACTOR = {
    "Low": 0.8,
    "Moderate": 1.0,
    "High": 1.3,
    "Severe": 1.6,
}


@lru_cache
def _dataset_path() -> Path:
    return Path(get_settings().seed_dir) / "city_area_calibration.csv"


def _to_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@lru_cache(maxsize=4)
def load_areas(city: str | None = None) -> tuple[dict, ...]:
    """Load calibration rows, optionally filtered by city name (case-insensitive).

    Returns a tuple (hashable) so the loader can be cached across calls.
    """
    path = _dataset_path()
    if not path.exists():
        return ()
    out: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if city and row.get("city", "").strip().lower() != city.strip().lower():
                continue
            level = row.get("congestion_level", "Moderate").strip()
            out.append(
                {
                    "area_id": row.get("area_id", ""),
                    "city": row.get("city", ""),
                    "state": row.get("state", ""),
                    "area_name": row.get("area_name", ""),
                    "road_length_km": _to_float(row.get("total_road_length_km")),
                    "intersections": _to_int(row.get("num_intersections")),
                    "traffic_volume_hr": _to_int(row.get("avg_traffic_volume_per_hr")),
                    "traffic_speed_kmph": _to_float(row.get("avg_traffic_speed_kmph")),
                    "congestion_level": level,
                    "congestion_factor": CONGESTION_FACTOR.get(level, 1.0),
                    "num_micro_hubs": _to_int(row.get("num_micro_hubs")),
                    "hub_storage_capacity": _to_int(row.get("total_hub_storage_capacity")),
                    "hub_utilization_pct": _to_float(row.get("avg_hub_utilization_pct")),
                    "orders_monthly": _to_int(row.get("num_delivery_orders_monthly")),
                    "avg_package_weight_kg": _to_float(row.get("avg_package_weight_kg")),
                    "num_vehicles": _to_int(row.get("num_vehicles_fleet")),
                    "common_vehicle": row.get("most_common_vehicle_type", "Two-Wheeler"),
                    "num_couriers": _to_int(row.get("num_couriers")),
                    "courier_capacity_kg": _to_float(row.get("avg_courier_capacity_kg")),
                    "daily_demand_orders": _to_int(row.get("avg_daily_demand_orders")),
                    "num_curb_zones": _to_int(row.get("num_curb_zones")),
                    "curb_capacity_vehicles": _to_int(row.get("total_curb_capacity_vehicles")),
                }
            )
    return tuple(out)


def cities_in_dataset() -> list[str]:
    """Sorted list of city names present in the calibration dataset."""
    return sorted({a["city"] for a in load_areas()})


def find_area(city: str, area_name: str) -> dict | None:
    """Case-insensitive lookup of one area row."""
    target = area_name.strip().lower()
    for area in load_areas(city):
        if area["area_name"].strip().lower() == target:
            return area
    return None


def zone_calibration(area: dict) -> dict:
    """Translate one area row into simulation zone parameters.

    - base_demand_rate: hourly order rate. The dataset gives daily demand;
      deliveries peak sharply in a few hours, so hourly peak ≈ daily/8.
    - road_capacity: sustainable concurrent vehicles ≈ hourly traffic volume
      crossing the area / ~25 (one vehicle leaves the local network every
      few seconds at observed speeds), clamped to a sane demo band.
    - congestion baseline feeds scenario multipliers via congestion_factor.
    """
    daily = max(area["daily_demand_orders"], 10)
    base_rate = round(daily / 8.0, 1)
    capacity = max(12, min(90, int(area["traffic_volume_hr"] / 25) or 12))
    return {
        "base_demand_rate": base_rate,
        "road_capacity": capacity,
        "congestion_factor": area["congestion_factor"],
        "hub_count": max(2, min(12, area["num_micro_hubs"])),
        "hub_capacity_avg": max(
            40, min(160, (area["hub_storage_capacity"] // max(area["num_micro_hubs"], 1)) or 80)
        ),
        "curb_zone_count": area["num_curb_zones"],
        "curb_capacity": area["curb_capacity_vehicles"],
        "courier_count": max(6, min(24, area["num_couriers"])),
        "vehicle_count": max(8, min(30, area["num_vehicles"])),
        "common_vehicle": area["common_vehicle"],
        "package_weight_kg": area["avg_package_weight_kg"] or 2.0,
        "calibrated": True,
    }


def city_rollup(city: str) -> dict:
    """Aggregate calibration figures for a whole city (used on city cards)."""
    areas = load_areas(city)
    if not areas:
        return {}
    n = len(areas)
    return {
        "city": city,
        "areas": n,
        "total_hubs": sum(a["num_micro_hubs"] for a in areas),
        "total_curb_zones": sum(a["num_curb_zones"] for a in areas),
        "daily_orders": sum(a["daily_demand_orders"] for a in areas),
        "monthly_orders": sum(a["orders_monthly"] for a in areas),
        "vehicles": sum(a["num_vehicles"] for a in areas),
        "couriers": sum(a["num_couriers"] for a in areas),
        "severe_areas": sum(1 for a in areas if a["congestion_level"] == "Severe"),
    }
