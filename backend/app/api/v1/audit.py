"""Audit log access (admin only, read-only and immutable)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import pagination_params, require_permission
from app.core.permissions import Permission
from app.database import get_db
from app.models.comms import AuditLog
from app.models.user import User
from app.schemas.common import paginated

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=dict)
def list_audit_logs(
    user_id: int | None = None,
    action: str | None = None,
    resource: str | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
):
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource:
        q = q.filter(AuditLog.resource == resource)
    if page_params["q"]:
        q = q.filter(AuditLog.user_name.ilike(f"%{page_params['q']}%") | AuditLog.action.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(AuditLog.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated(
        [
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_name": r.user_name,
                "role": r.role,
                "action": r.action,
                "resource": r.resource,
                "resource_id": r.resource_id,
                "ip_address": r.ip_address,
                "details": r.details,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        page_params["page"], page_params["page_size"], total,
    )


@router.get("/actions", response_model=list)
def list_audit_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
):
    rows = db.query(AuditLog.action).distinct().all()
    return sorted(r[0] for r in rows)
