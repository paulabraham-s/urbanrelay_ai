from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import get_sim_service
from app.database.session import SessionLocal
from app.models.entities import Order

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/impact")
def impact(sim=Depends(get_sim_service)) -> dict:
    return sim.before_after()


@router.get("/series")
def series(limit: int = Query(600, ge=10, le=4000), sim=Depends(get_sim_service)) -> dict:
    return {"history": sim.history(limit)}


@router.get("/orders")
def order_stats(mode: str | None = None) -> dict:
    db = SessionLocal()
    try:
        q = select(Order.status, func.count()).group_by(Order.status)
        if mode:
            q = q.where(Order.mode == mode)
        by_status = {row[0]: row[1] for row in db.execute(q).all()}
        q2 = select(Order.platform, func.count()).group_by(Order.platform)
        by_platform = {row[0]: row[1] for row in db.execute(q2).all()}
        q3 = select(Order.mode, func.count()).group_by(Order.mode)
        by_mode = {row[0]: row[1] for row in db.execute(q3).all()}
        return {"by_status": by_status, "by_platform": by_platform, "by_mode": by_mode}
    finally:
        db.close()