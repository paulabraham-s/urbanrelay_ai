from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.database.session import SessionLocal
from app.models.entities import City, Zone
from app.schemas.entities import CityOut, ZoneOut
from app.services.sim_service import SimulationService

router = APIRouter(prefix="/api/cities", tags=["cities"])


@router.get("", response_model=list[CityOut])
def list_cities() -> list[City]:
    db = SessionLocal()
    try:
        return list(db.execute(select(City).order_by(City.name)).scalars())
    finally:
        db.close()


@router.get("/{city_id}/zones", response_model=list[ZoneOut])
def city_zones(city_id: str) -> list[Zone]:
    db = SessionLocal()
    try:
        return list(db.execute(select(Zone).where(Zone.city_id == city_id).order_by(Zone.name)).scalars())
    finally:
        db.close()


@router.post("/{city_id}/activate")
async def activate_city(city_id: str, sim: SimulationService = Depends(get_sim_service)) -> dict:
    """Switch the simulation to another city: reloads zones, fleet, hubs and
    the city's bundled road graph. Stops any running simulation."""
    try:
        return await sim.switch_city(city_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{city_id}")
def city_detail(city_id: str) -> dict:
    db = SessionLocal()
    try:
        city = db.get(City, city_id)
        if city is None:
            raise HTTPException(status_code=404, detail="City not found")
        zones = db.execute(select(Zone).where(Zone.city_id == city_id)).scalars().all()
        return {
            "city": CityOut.model_validate(city).model_dump(),
            "zones": [ZoneOut.model_validate(z).model_dump() for z in zones],
        }
    finally:
        db.close()