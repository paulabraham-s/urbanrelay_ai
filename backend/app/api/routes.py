from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_sim_service
from app.core.constants import VEHICLE_TYPES
from app.schemas.requests import RouteOptimizeRequest

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.post("/optimize")
def optimize_route(req: RouteOptimizeRequest, sim=Depends(get_sim_service)) -> dict:
    if sim.graph is None:
        raise HTTPException(status_code=503, detail="Routing graph not loaded")
    speed = req.speed_kph or VEHICLE_TYPES.get(req.vehicle_type, {}).get("speed_kph", 30)
    result = sim.graph.route(
        req.from_lat, req.from_lng, req.to_lat, req.to_lng,
        vehicle_speed_kph=speed,
        vehicle_type=req.vehicle_type,
        congestion=sim.state.zone_load,
        algorithm=req.algorithm if req.algorithm in ("dijkstra", "astar") else "dijkstra",
    )
    if not result.polyline:
        raise HTTPException(status_code=422, detail="No route found between the given points")
    return {
        "algorithm": result.algorithm,
        "distance_m": round(result.distance_m, 1),
        "distance_km": round(result.distance_m / 1000.0, 2),
        "duration_min": round(result.duration_min, 1),
        "cost": round(result.cost, 3),
        "nodes": result.node_count,
        "polyline": result.polyline[:800],
        "note": "Cost = 1.0/km + 1/60 per second, scaled by live zone congestion.",
    }