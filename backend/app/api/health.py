from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.deps import get_sim_service
from app.database.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "urbanrelay-backend"}


@router.get("/ready")
def ready(sim=Depends(get_sim_service)) -> dict:
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ready" if db_ok and sim.ready else "degraded",
        "database": db_ok,
        "simulation": sim.ready,
        "scenario": sim.state.scenario.get("id") if sim.state.scenario else None,
        "mode": sim.state.mode,
        "running": sim.state.running,
    }