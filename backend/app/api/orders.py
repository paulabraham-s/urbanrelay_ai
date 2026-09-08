from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.core.security import require_auth
from app.database.session import SessionLocal
from app.models.entities import Order
from app.schemas.entities import OrderOut
from app.schemas.requests import OrderCreateRequest, OptimizeRequest

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(
    status: str | None = None,
    zone: str | None = None,
    mode: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = 0,
) -> list[Order]:
    db = SessionLocal()
    try:
        q = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
        if status:
            q = q.where(Order.status == status.upper())
        if zone:
            q = q.where(Order.zone_id == zone)
        if mode:
            q = q.where(Order.mode == mode)
        return list(db.execute(q).scalars())
    finally:
        db.close()


@router.post("")
def create_order(req: OrderCreateRequest, claims: dict = Depends(require_auth), sim=Depends(get_sim_service)):
    s = sim.state
    if not s.running:
        raise HTTPException(status_code=409, detail="Start the simulation first")
    zone = None
    if req.zone_id:
        zone = next((z for z in s.zones if z["id"] == req.zone_id), None)
    if zone is None:
        from app.algorithms.geo import nearest_zone

        zone = nearest_zone(s.zones, req.customer_lat, req.customer_lng)
    if zone is None:
        raise HTTPException(status_code=422, detail="Coordinates not inside any demo zone")

    import uuid

    order = {
        "id": str(uuid.uuid4()),
        "platform": req.platform,
        "zone_id": zone["id"],
        "zone_name": zone["name"],
        "customer_lat": req.customer_lat,
        "customer_lng": req.customer_lng,
        "customer_name": "Manual Ingest",
        "address": f"Manual order @ {req.customer_lat:.4f}, {req.customer_lng:.4f}",
        "weight_kg": req.weight_kg,
        "volume_units": req.volume_units,
        "priority": req.priority,
        "created_t": s.t,
    }
    order["created_t"] = s.t
    from app.simulation.state import OrderState

    order_state = OrderState(**order)
    order_state.warehouse = sim.engine._nearest_warehouse(order_state.customer_lat, order_state.customer_lng)
    s.orders[order_state.id] = order_state
    s.pending_ids.append(order_state.id)
    s.orders_generated += 1
    sim.persist.order_created(s, order_state)
    return {"id": order_state.id, "status": "PENDING", "zone": zone["name"]}


@router.post("/optimize")
def optimize_orders(req: OptimizeRequest | None = None, sim=Depends(get_sim_service)):
    plan = sim.plan_dispatch(req.order_ids if req else None)
    return plan