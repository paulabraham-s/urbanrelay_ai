import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/api/auth/login", json={"demo": True})
    assert r.status_code == 200
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_ready(client):
    data = client.get("/ready").json()
    assert data["status"] == "ready"
    assert data["simulation"] is True


def test_cities_and_zones(client):
    cities = client.get("/api/cities").json()
    assert len(cities) >= 1
    city_id = cities[0]["id"]
    zones = client.get(f"/api/cities/{city_id}/zones").json()
    assert len(zones) == 3
    names = {z["name"] for z in zones}
    assert names == {"Secunderabad", "Kukatpally", "Miyapur"}


def test_hubs_and_fleet(client):
    hubs = client.get("/api/hubs").json()
    assert len(hubs) >= 20
    vehicles = client.get("/api/vehicles").json()
    assert len(vehicles) == 40
    couriers = client.get("/api/couriers").json()
    assert len(couriers) == 30


def test_scenarios_listed(client):
    scenarios = client.get("/api/simulation/scenarios").json()["scenarios"]
    assert any(s["id"] == "FESTIVAL_SALE" for s in scenarios)


def test_simulation_flow(client, token):
    h = auth_headers(token)
    # start the simulation
    r = client.post("/api/simulation/start", json={"scenario_id": "FESTIVAL_SALE", "seed": 42, "speed": 5.0}, headers=h)
    assert r.status_code == 200
    assert r.json()["running"] is True

    # give the engine a moment to generate orders
    time.sleep(1.5)

    state = client.get("/api/simulation/state").json()
    assert state["status"]["mode"] == "baseline"
    assert state["status"]["orders_generated"] > 0

    kpis = client.get("/api/simulation/kpis").json()
    assert "congestion_index" in kpis

    # activate UrbanRelay AI
    r = client.post("/api/simulation/activate", json={"mode": "urbanrelay"}, headers=h)
    assert r.status_code == 200
    assert r.json()["mode"] == "urbanrelay"

    time.sleep(2.5)

    state2 = client.get("/api/simulation/state").json()
    assert state2["status"]["mode"] == "urbanrelay"

    # dispatch plan should exist for the extension
    plan = client.post("/api/dispatch/optimize", json={}, headers=h)
    assert plan.status_code == 200
    body = plan.json()
    assert "waves" in body and "savings" in body

    # decisions should have been recorded
    decisions = client.get("/api/agents/decisions").json()
    agents = {d["agent"] for d in decisions}
    assert {"HUB_SELECTION", "DELIVERY_WAVE", "FLEET_BALANCER", "CURB_RESERVATION"}.issubset(agents)

    # analytics endpoints respond
    assert client.get("/api/analytics/impact").status_code == 200
    assert client.get("/api/analytics/series").status_code == 200

    # stop
    r = client.post("/api/simulation/stop", headers=h)
    assert r.status_code == 200
    assert r.json()["running"] is False


def test_routing_endpoint(client):
    r = client.post(
        "/api/routes/optimize",
        json={
            "from_lat": 17.4849, "from_lng": 78.4087,
            "to_lat": 17.4399, "to_lng": 78.4983,
            "vehicle_type": "van", "algorithm": "astar",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["distance_km"] > 5
    assert len(data["polyline"]) > 10


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401