from app.agents.curb_reservation import CurbReservationAgent
from app.agents.delivery_wave import DeliveryWaveAgent
from app.agents.fleet_balancer import FleetBalancerAgent
from app.agents.hub_selection import HubSelectionAgent

ZONES = [
    {"id": "z1", "name": "Kukatpally", "center_lat": 17.4849, "center_lng": 78.4087, "radius_km": 5.0},
    {"id": "z2", "name": "Miyapur", "center_lat": 17.4993, "center_lng": 78.3550, "radius_km": 5.0},
]


def _hubs():
    return [
        {"id": "h1", "name": "Balaji Kirana", "type": "kirana", "lat": 17.4871, "lng": 78.4062,
         "capacity": 90, "occupied": 10, "operating_start": 7, "operating_end": 22, "active": True,
         "accessibility": 0.9, "zone_id": "z1"},
        {"id": "h2", "name": "Metro Locker", "type": "locker", "lat": 17.4947, "lng": 78.4000,
         "capacity": 120, "occupied": 100, "operating_start": 6, "operating_end": 23, "active": True,
         "accessibility": 0.9, "zone_id": "z1"},
        {"id": "h3", "name": "Full Hub", "type": "kirana", "lat": 17.4860, "lng": 78.4090,
         "capacity": 50, "occupied": 50, "operating_start": 7, "operating_end": 22, "active": True,
         "accessibility": 0.8, "zone_id": "z1"},
    ]


def test_hub_selection_prefers_open_near_capacity():
    agent = HubSelectionAgent()
    hub, record = agent.select_hub(
        centroid_lat=17.487, centroid_lng=78.407, required_slots=5,
        hubs=_hubs(), zone_load_fn=lambda z: 0.2, now_hour=14,
    )
    assert hub["id"] == "h1"
    assert record.score > 0
    assert record.reasons  # explainable
    assert record.decision  # human-readable explanation


def test_hub_selection_skips_full_hub():
    agent = HubSelectionAgent()
    hub, record = agent.select_hub(
        centroid_lat=17.486, centroid_lng=78.409, required_slots=10,
        hubs=_hubs(), zone_load_fn=lambda z: 0.1, now_hour=14,
    )
    assert hub is not None
    assert hub["id"] != "h3"  # full hub must never be chosen


def test_delivery_wave_groups_orders():
    orders = [
        {"id": f"o{i}", "customer_lat": 17.4840 + i * 0.0005, "customer_lng": 78.4080 + i * 0.0005,
         "volume_units": 1, "priority": 1, "created_t": 0.0, "zone_id": "z1"}
        for i in range(8)
    ]
    orders += [
        {"id": f"p{i}", "customer_lat": 17.5000 + i * 0.0005, "customer_lng": 78.3550 + i * 0.0005,
         "volume_units": 2, "priority": 1, "created_t": 0.0, "zone_id": "z2"}
        for i in range(6)
    ]
    waves, record = DeliveryWaveAgent().build_waves(orders, ZONES)
    assert len(waves) >= 2
    assert record.impact["orders"] == 14
    assert all(w["total_slots"] >= 1 for w in waves)


def test_fleet_balancer_partitions_wave_across_vehicles():
    waves = [
        {
            "id": "W1", "name": "Wave A", "zone_id": "z1", "centroid": [17.485, 78.408],
            "priority_max": 1, "total_slots": 300,
            "orders": [{"id": f"o{i}", "volume_units": 1} for i in range(300)],
        }
    ]
    vehicles = [
        {"id": f"t{i}", "type": "truck", "capacity": 200, "lat": 17.48, "lng": 78.40, "status": "IDLE", "active": True, "zone_id": "z1"}
        for i in range(2)
    ]
    couriers = [
        {"id": f"c{i}", "mode": "e-scooter", "capacity": 10, "lat": 17.485, "lng": 78.408, "status": "AVAILABLE", "active": True, "zone_id": "z1"}
        for i in range(5)
    ]
    plan, record = FleetBalancerAgent().allocate(waves=waves, vehicles=vehicles, couriers=couriers, zone_load_fn=lambda z: 0.0)
    assigned = [oid for a in plan["bulk_assignments"] for oid in a["order_ids"]]
    assert len(plan["bulk_assignments"]) == 2
    assert len(assigned) == 300
    assert len(set(assigned)) == 300  # no duplicated orders across vehicles


def test_curb_reservation_schedules_without_overlap():
    curbs = [
        {"id": "cb1", "name": "Market Curb", "lat": 17.486, "lng": 78.408, "capacity": 2},
        {"id": "cb2", "name": "Station Curb", "lat": 17.4326, "lng": 78.5014, "capacity": 1},
    ]
    arrivals = [
        {"vehicle_id": "v1", "lat": 17.486, "lng": 78.408, "eta_min": 10.0, "unload_min": 5.0},
        {"vehicle_id": "v2", "lat": 17.486, "lng": 78.408, "eta_min": 12.0, "unload_min": 5.0},
        {"vehicle_id": "v3", "lat": 17.486, "lng": 78.408, "eta_min": 13.0, "unload_min": 5.0},
        {"vehicle_id": "v4", "lat": 17.4326, "lng": 78.5014, "eta_min": 15.0, "unload_min": 5.0},
    ]
    reservations, conflicts, record = CurbReservationAgent().plan(arrivals=arrivals, curb_zones=curbs, now_min=0.0)
    assert len(reservations) == 4
    # never exceed curb capacity at any point in time
    from collections import defaultdict

    capacity = {c["id"]: c["capacity"] for c in curbs}
    per_curb = defaultdict(list)
    for r in reservations:
        per_curb[r["curb_id"]].append((r["starts_at_min"], r["ends_at_min"]))
    for curb_id, intervals in per_curb.items():
        events = []
        for s, e in intervals:
            events.append((s, 1))
            events.append((e, -1))
        events.sort(key=lambda x: (x[0], x[1]))  # ends before starts at equal time
        concurrent = peak = 0
        for _, delta in events:
            concurrent += delta
            peak = max(peak, concurrent)
        assert peak <= capacity[curb_id]
    # v3 arrived at the busy market curb and had to shift later -> counted as a conflict
    assert record.impact["conflicts"] >= 1
    assert conflicts == record.impact["conflicts"]