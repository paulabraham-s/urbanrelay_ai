from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.core.security import require_auth
from app.database.session import SessionLocal
from app.models.entities import CurbZone
from app.schemas.entities import CurbZoneOut
from app.schemas.requests import ReserveCurbRequest

router = APIRouter(prefix="/api", tags=["curb"])


@router.get("/curb-zones", response_model=list[CurbZoneOut])
def list_curb_zones(sim=Depends(get_sim_service)) -> list[dict]:
    db = SessionLocal()
    try:
        rows = list(db.execute(select(CurbZone).order_by(CurbZone.name)).scalars())
        out = []
        for r in rows:
            d = CurbZoneOut.model_validate(r).model_dump()
            zone = next((z for z in sim.state.zones if z["id"] == r.zone_id), None)
            d["zone_name"] = zone["name"] if zone else None
            d["active_reservations"] = sum(
                1 for res in sim.state.curb_reservations if res["curb_id"] == r.id
            )
            out.append(d)
        return out
    finally:
        db.close()


@router.get("/curb-reservations")
def list_reservations(sim=Depends(get_sim_service)) -> dict:
    now_min = sim.state.t / 60.0
    return {
        "now_min": round(now_min, 1),
        "reservations": sim.state.curb_reservations[-80:],
    }


@router.post("/curb-zones/reserve")
def reserve_curb(req: ReserveCurbRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    from app.algorithms.geo import haversine_km

    zones = sorted(sim.state.curb_zones, key=lambda c: haversine_km(req.lat, req.lng, c["lat"], c["lng"]))
    if not zones:
        return {"status": "no curb zones configured"}
    curb = zones[0]
    reservation = {
        "curb_id": curb["id"],
        "curb_name": curb["name"],
        "vehicle_id": req.vehicle_label,
        "starts_at_min": round(sim.state.t / 60.0 + req.eta_min, 1),
        "ends_at_min": round(sim.state.t / 60.0 + req.eta_min + req.unload_min, 1),
        "requested_at_min": round(sim.state.t / 60.0, 1),
    }
    sim.state.curb_reservations.append(reservation)
    return {"status": "reserved", "reservation": reservation}