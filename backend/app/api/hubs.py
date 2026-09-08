from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.core.security import require_auth, require_roles
from app.database.session import SessionLocal
from app.models.entities import MicroHub
from app.schemas.entities import HubOut
from app.schemas.requests import HubReserveRequest, HubUpdateRequest

router = APIRouter(prefix="/api/hubs", tags=["hubs"])


def _hub_row(hub_id: str) -> MicroHub:
    db = SessionLocal()
    try:
        row = db.get(MicroHub, hub_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Hub not found")
        return row
    finally:
        db.close()


@router.get("", response_model=list[HubOut])
def list_hubs(sim=Depends(get_sim_service)) -> list[dict]:
    db = SessionLocal()
    try:
        rows = list(db.execute(select(MicroHub).order_by(MicroHub.name)).scalars())
        live = sim.state.hubs
        out = []
        for r in rows:
            d = HubOut.model_validate(r).model_dump()
            if r.id in live:
                d["occupied"] = live[r.id]["occupied"]
            d["utilization"] = round(d["occupied"] / max(d["capacity"], 1), 3)
            d["incoming"] = sum(1 for o in sim.state.orders.values() if o.hub_id == r.id and o.status in ("PICKED_UP", "WAVE_ASSIGNED"))
            d["outgoing"] = sum(1 for o in sim.state.orders.values() if o.hub_id == r.id and o.status in ("AT_HUB", "OUT_FOR_DELIVERY"))
            out.append(d)
        return out
    finally:
        db.close()


@router.get("/{hub_id}")
def hub_detail(hub_id: str, sim=Depends(get_sim_service)) -> dict:
    row = _hub_row(hub_id)
    d = HubOut.model_validate(row).model_dump()
    live = sim.state.hubs.get(hub_id)
    if live:
        d["occupied"] = live["occupied"]
    d["utilization"] = round(d["occupied"] / max(d["capacity"], 1), 3)
    zone = next((z for z in sim.state.zones if z["id"] == row.zone_id), None)
    if zone:
        d["zone_name"] = zone["name"]
        d["zone_congestion"] = round(sim.state.zone_load(zone["id"]), 3)
    return d


@router.patch("/{hub_id}")
def update_hub(hub_id: str, req: HubUpdateRequest, claims=Depends(require_roles("ADMIN", "MUNICIPAL_OPERATOR", "HUB_OPERATOR")), sim=Depends(get_sim_service)):
    db = SessionLocal()
    try:
        row = db.get(MicroHub, hub_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Hub not found")
        for field in ("capacity", "active", "operating_start", "operating_end"):
            value = getattr(req, field)
            if value is not None:
                setattr(row, field, value)
        db.commit()
        live = sim.state.hubs.get(hub_id)
        if live:
            if req.capacity is not None:
                live["capacity"] = req.capacity
            if req.active is not None:
                live["active"] = req.active
            if req.operating_start is not None:
                live["operating_start"] = req.operating_start
            if req.operating_end is not None:
                live["operating_end"] = req.operating_end
        return {"id": hub_id, "status": "updated"}
    finally:
        db.close()


@router.post("/{hub_id}/reserve")
def reserve_hub(hub_id: str, req: HubReserveRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    live = sim.state.hubs.get(hub_id)
    if live is None:
        raise HTTPException(status_code=404, detail="Hub not in active topology")
    if live["occupied"] + req.slots > live["capacity"]:
        raise HTTPException(status_code=409, detail=f"Only {live['capacity'] - live['occupied']} slots free")
    live["occupied"] += req.slots
    return {"hub_id": hub_id, "reserved": req.slots, "occupied": live["occupied"]}