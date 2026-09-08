from fastapi import APIRouter, Depends

from app.api.deps import get_sim_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis")
def kpis(sim=Depends(get_sim_service)) -> dict:
    return sim.kpis()


@router.get("/ai-recommendations")
def recommendations(sim=Depends(get_sim_service)) -> dict:
    return {"recommendations": sim.recommendations()}


@router.get("/map")
def map_data(sim=Depends(get_sim_service)) -> dict:
    s = sim.state
    return {
        "zones": s.zones,
        "warehouses": s.warehouses,
        "hubs": [
            {"id": h["id"], "name": h["name"], "type": h["type"], "lat": h["lat"], "lng": h["lng"],
             "occupied": h["occupied"], "capacity": h["capacity"], "active": h["active"]}
            for h in s.hubs.values()
        ],
        "curb_zones": [
            {"id": c["id"], "name": c["name"], "lat": c["lat"], "lng": c["lng"], "capacity": c["capacity"]}
            for c in s.curb_zones
        ],
        "vehicles": [
            {"id": v.id, "type": v.type, "status": v.status, "lat": round(v.position()[0], 6), "lng": round(v.position()[1], 6), "mode": v.mode}
            for v in s.vehicles.values()
        ],
        "couriers": [
            {"id": c.id, "mode": c.mode, "status": c.status, "lat": round(c.position()[0], 6), "lng": round(c.position()[1], 6)}
            for c in s.couriers.values()
        ],
        "mode": s.mode,
        "scenario": s.scenario.get("id"),
        "running": s.running,
        "t": round(s.t, 1),
    }