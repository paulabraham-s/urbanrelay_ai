from fastapi import APIRouter, Depends

from app.api.deps import get_sim_service
from app.core.security import require_roles
from app.schemas.requests import OptimizeRequest

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


@router.post("/optimize")
def optimize_dispatch(
    req: OptimizeRequest | None = None,
    claims=Depends(require_roles("ADMIN", "MUNICIPAL_OPERATOR", "DISPATCHER")),
    sim=Depends(get_sim_service),
) -> dict:
    """Optimize dispatch for pending (or selected) orders.

    Consumed by the Chrome dispatcher extension. Returns grouped delivery
    waves, hub assignments, fleet assignments, route previews and real
    expected savings computed by routing the orders both ways.
    """
    plan = sim.plan_dispatch(req.order_ids if req else None)
    plan["requested_by"] = claims["username"]
    plan["role"] = claims["role"]
    return plan