from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.database.session import SessionLocal
from app.models.entities import Courier, Vehicle
from app.schemas.entities import CourierOut, VehicleOut

router = APIRouter(prefix="/api", tags=["fleet"])


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(sim=Depends(get_sim_service)) -> list[dict]:
    db = SessionLocal()
    try:
        rows = list(db.execute(select(Vehicle).order_by(Vehicle.type, Vehicle.name)).scalars())
        live = sim.state.vehicles
        out = []
        for r in rows:
            d = VehicleOut.model_validate(r).model_dump()
            state = live.get(r.id)
            if state:
                d["status"] = state.status
                d["lat"] = round(state.position()[0], 6)
                d["lng"] = round(state.position()[1], 6)
                d["cargo"] = len(state.cargo)
                d["progress"] = round(state.progress, 3)
                d["route"] = state.route
                d["mode"] = state.mode
            out.append(d)
        return out
    finally:
        db.close()


@router.get("/couriers", response_model=list[CourierOut])
def list_couriers(sim=Depends(get_sim_service)) -> list[dict]:
    db = SessionLocal()
    try:
        rows = list(db.execute(select(Courier).order_by(Courier.mode, Courier.name)).scalars())
        live = sim.state.couriers
        out = []
        for r in rows:
            d = CourierOut.model_validate(r).model_dump()
            state = live.get(r.id)
            if state:
                d["status"] = state.status
                d["lat"] = round(state.position()[0], 6)
                d["lng"] = round(state.position()[1], 6)
                d["cargo"] = len(state.cargo)
                d["progress"] = round(state.progress, 3)
                d["route"] = state.route
                d["target_order_id"] = state.target_order_id
                d["earnings"] = round(state.earnings, 2)
            out.append(d)
        return out
    finally:
        db.close()