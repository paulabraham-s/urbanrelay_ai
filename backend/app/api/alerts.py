from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import get_sim_service
from app.core.security import require_auth
from app.database.session import SessionLocal
from app.models.entities import Alert
from app.schemas.entities import AlertOut
from app.schemas.requests import ResolveAlertRequest

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    severity: str | None = None,
    unresolved: bool = False,
    limit: int = Query(100, ge=1, le=500),
) -> list[Alert]:
    db = SessionLocal()
    try:
        q = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        if severity:
            q = q.where(Alert.severity == severity.upper())
        if unresolved:
            q = q.where(Alert.resolved_at.is_(None))
        return list(db.execute(q).scalars())
    finally:
        db.close()


@router.post("/{alert_id}/resolve")
def resolve(alert_id: str, req: ResolveAlertRequest, claims=Depends(require_auth)) -> dict:
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        row = db.get(Alert, alert_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        row.resolved_at = datetime.now(timezone.utc) if req.resolved else None
        db.commit()
        return {"id": alert_id, "resolved": req.resolved}
    finally:
        db.close()