"""Populate the complete UrbanRelay demo environment.

Run from repo root:
    python backend/scripts/seed_demo.py

Creates (idempotently if the DB is empty):
  - demo users (admin/operator/dispatcher/hubowner/courier, password demo1234)
  - every city in data/seed/cities.json (Hyderabad, Visakhapatnam)
  - zones calibrated from data/seed/city_area_calibration.csv where available:
      * base_demand_rate scaled by the dataset's daily-demand ratio
      * road_capacity validated against the dataset's traffic volume
  - micro-hubs, curb/loading zones, warehouses, vehicles and couriers per city
  - emission factors
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.api.auth import seed_users  # noqa: E402
from app.core.constants import EMISSION_FACTORS_G_PER_KM  # noqa: E402
from app.database.session import SessionLocal, init_db  # noqa: E402
from app.models.entities import (  # noqa: E402
    City,
    Courier,
    CurbZone,
    EmissionFactor,
    MicroHub,
    Vehicle,
    Zone,
)
from app.services.city_dataset import find_area, zone_calibration  # noqa: E402

SEED_DIR = ROOT / "data" / "seed"

VEHICLE_PLAN = [
    ("truck", 6, "T"),
    ("van", 8, "V"),
    ("motorcycle", 10, "M"),
    ("e-scooter", 10, "E"),
    ("bicycle", 6, "B"),
]
VEHICLE_CAPACITY = {"truck": 200, "van": 80, "motorcycle": 15, "e-scooter": 10, "bicycle": 6}
VEHICLE_SPEED = {"truck": 28, "van": 34, "motorcycle": 30, "e-scooter": 24, "bicycle": 15}

COURIER_PLAN = [
    ("e-scooter", 10),
    ("motorcycle", 8),
    ("bicycle", 7),
    ("walking", 5),
]
COURIER_CAPACITY = {"e-scooter": 10, "motorcycle": 15, "bicycle": 6, "walking": 3}

FIRST_NAMES = [
    "Arjun", "Ravi", "Kiran", "Suresh", "Naveen", "Prakash", "Anil", "Mahesh", "Srinivas", "Vikram",
    "Priya", "Sneha", "Divya", "Pooja", "Neha", "Kavita", "Meena", "Lakshmi", "Shalini", "Sunita",
]
LAST_NAMES = ["Reddy", "Sharma", "Rao", "Kumar", "Naidu", "Verma", "Das", "Nair", "Gupta", "Patel"]


def load_json(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def jitter(rng: random.Random, base: tuple[float, float], deg: float = 0.004) -> tuple[float, float]:
    return base[0] + rng.uniform(-deg, deg), base[1] + rng.uniform(-deg, deg)


def calibrated_zones(city_json: dict) -> list[dict]:
    """Merge cities.json zone geometry with calibration-dataset parameters.

    Demand: rates scale proportionally to the dataset's avg_daily_demand_orders,
    normalized so the busiest zone keeps its hand-tuned peak rate (the demo
    compresses a day, so absolute rates stay demo-tuned while relative demand
    across zones is real data).
    Capacity: the dataset's hourly traffic volume implies a concurrent-vehicle
    ceiling (volume/25); the zone keeps max(JSON value, derived value).
    """
    cal_city = city_json.get("calibration_city")
    zones = [dict(z) for z in city_json["zones"]]
    if not cal_city:
        return zones

    rows = {z["calibration_area"]: find_area(cal_city, z["calibration_area"]) for z in zones}
    # pick the dominant demand row as the normalization anchor
    rates = [r["daily_demand_orders"] for r in rows.values() if r]
    if not rates:
        return zones
    max_daily = max(rates)
    for z in zones:
        row = rows.get(z["calibration_area"])
        if not row:
            continue
        cal = zone_calibration(row)
        if max_daily > 0:
            z["base_demand_rate"] = round(z["base_demand_rate"] * row["daily_demand_orders"] / max_daily, 1)
        z["road_capacity"] = max(z["road_capacity"], cal["road_capacity"])
        z["calibrated_from"] = row["area_id"]
    return zones


def seed_city(db, city_json: dict, hubs_all: list, curbs_all: list, warehouses_all: list, rng: random.Random) -> dict:
    code = city_json["code"]
    city = City(
        name=city_json["name"], code=code,
        center_lat=city_json["center_lat"], center_lng=city_json["center_lng"],
    )
    db.add(city)
    db.flush()

    zones: dict[str, Zone] = {}
    for z in calibrated_zones(city_json):
        zone = Zone(
            city_id=city.id, name=z["name"], code=z["code"],
            center_lat=z["center_lat"], center_lng=z["center_lng"],
            radius_km=z["radius_km"], base_demand_rate=z["base_demand_rate"],
            road_capacity=z["road_capacity"], color=z["color"],
        )
        db.add(zone)
        zones[z["code"]] = zone
    db.flush()

    zone_centers = [(z["center_lat"], z["center_lng"]) for z in city_json["zones"]]

    # ---- hubs
    hub_count = 0
    for h in hubs_all:
        if h.get("city", "hyderabad") != code:
            continue
        zone = zones.get(h["zone_code"])
        if zone is None:
            continue
        db.add(
            MicroHub(
                city_id=city.id, zone_id=zone.id, name=h["name"], type=h["type"],
                lat=h["lat"], lng=h["lng"], capacity=h["capacity"],
                operating_start=h["operating_start"], operating_end=h["operating_end"],
                accessibility=h["accessibility"], address=h["address"], owner_name=h["owner_name"],
            )
        )
        hub_count += 1

    # ---- curb zones
    curb_count = 0
    for c in curbs_all:
        if c.get("city", "hyderabad") != code:
            continue
        zone = zones.get(c["zone_code"])
        if zone is None:
            continue
        db.add(
            CurbZone(
                city_id=city.id, zone_id=zone.id, name=c["name"],
                lat=c["lat"], lng=c["lng"], capacity=c["capacity"],
                operating_start=c["operating_start"], operating_end=c["operating_end"],
            )
        )
        curb_count += 1

    # ---- vehicles (trucks park at this city's warehouses)
    whs = [w for w in warehouses_all if w.get("city", "hyderabad") == code]
    veh_count = 0
    for vtype, count, prefix in VEHICLE_PLAN:
        for i in range(count):
            if vtype == "truck" and whs:
                wh = whs[i % len(whs)]
                lat, lng = jitter(rng, (wh["lat"], wh["lng"]), 0.008)
            else:
                clat, clng = zone_centers[i % len(zone_centers)]
                lat, lng = jitter(rng, (clat, clng), 0.006 if vtype == "van" else 0.01)
            db.add(
                Vehicle(
                    city_id=city.id, name=f"{code[:2].upper()}{prefix}-{100 + i}", type=vtype,
                    capacity=VEHICLE_CAPACITY[vtype], speed_kph=VEHICLE_SPEED[vtype],
                    lat=lat, lng=lng, battery=round(rng.uniform(60, 100), 1), status="IDLE",
                )
            )
            veh_count += 1

    # ---- couriers
    idx = 0
    cour_count = 0
    for cmode, count in COURIER_PLAN:
        for i in range(count):
            clat, clng = zone_centers[i % len(zone_centers)]
            lat, lng = jitter(rng, (clat, clng), 0.008)
            name = f"{FIRST_NAMES[idx % len(FIRST_NAMES)]} {LAST_NAMES[idx % len(LAST_NAMES)]}"
            idx += 1
            db.add(
                Courier(
                    city_id=city.id, name=name, mode=cmode,
                    capacity=COURIER_CAPACITY[cmode],
                    lat=lat, lng=lng, status="AVAILABLE",
                )
            )
            cour_count += 1

    db.flush()
    return {"city": city, "zones": zones, "hubs": hub_count, "curbs": curb_count,
            "vehicles": veh_count, "couriers": cour_count}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(City).count() > 0:
            print("City data already present — run scripts/reset_demo.py to reseed from scratch.")
            return

        rng = random.Random(7)
        cities_data = load_json("cities.json")["cities"]
        hubs_all = load_json("hubs.json")
        curbs_all = load_json("curb_zones.json")
        warehouses_all = load_json("warehouses.json")

        results = []
        for i, city_json in enumerate(cities_data):
            r = seed_city(db, city_json, hubs_all, curbs_all, warehouses_all, rng)
            r["city"].active = i == 0  # only the first city starts active
            results.append(r)

        # ---- emission factors
        for mode, gco2 in EMISSION_FACTORS_G_PER_KM.items():
            db.add(EmissionFactor(mode=mode, gco2_per_km=gco2, source="Configured estimate — see DATASETS.md"))

        # ---- users
        seed_users(db)

        db.commit()
        print("Seeded demo environment:")
        for r in results:
            print(f"  {r['city'].name}: zones={len(r['zones'])} hubs={r['hubs']} "
                  f"curbs={r['curbs']} vehicles={r['vehicles']} couriers={r['couriers']}")
        print("  users: admin / operator / dispatcher / hubowner / courier (password: demo1234)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
