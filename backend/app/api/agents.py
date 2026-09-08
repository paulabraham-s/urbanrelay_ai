from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.database.session import SessionLocal
from app.models.entities import AIDecision
from app.schemas.entities import AIDecisionOut

router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENTS = ["HUB_SELECTION", "DELIVERY_WAVE", "FLEET_BALANCER", "CURB_RESERVATION"]


@router.get("/decisions", response_model=list[AIDecisionOut])
def decisions(agent: str | None = None, limit: int = Query(50, ge=1, le=200), sim=Depends(get_sim_service)) -> list[AIDecision]:
    db = SessionLocal()
    try:
        q = select(AIDecision).order_by(AIDecision.created_at.desc()).limit(limit)
        if agent:
            q = q.where(AIDecision.agent == agent.upper())
        return list(db.execute(q).scalars())
    finally:
        db.close()


@router.get("/{agent}/explain")
def explain(agent: str, sim=Depends(get_sim_service)) -> dict:
    if agent.upper() not in AGENTS:
        return {"agent": agent, "error": f"Unknown agent. Known agents: {AGENTS}"}
    db = SessionLocal()
    try:
        row = db.execute(
            select(AIDecision).where(AIDecision.agent == agent.upper()).order_by(AIDecision.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        if row is None:
            return {"agent": agent, "decision": None, "message": "No decisions recorded yet — run the simulation."}
        return {
            "agent": agent,
            "decision": row.decision,
            "reasons": row.reasons,
            "inputs": row.inputs,
            "score": row.score,
            "impact": row.impact,
            "created_at": row.created_at.isoformat(),
        }
    finally:
        db.close()