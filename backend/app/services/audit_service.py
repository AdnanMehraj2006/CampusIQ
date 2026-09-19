"""Append-only audit logging.

The audit table has no update/delete API surface; ``log_action`` is the single
writer. Sensitive actions across the app call this.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.comms import AuditLog


def log_action(
    db: Session,
    *,
    user_id: Optional[int],
    user_name: Optional[str],
    role: Optional[str],
    action: str,
    resource: str,
    resource_id: Optional[Any] = None,
    ip_address: Optional[str] = None,
    details: Optional[Any] = None,
    commit: bool = True,
) -> AuditLog:
    """Write one immutable audit record. Never raises into the request path."""
    try:
        entry = AuditLog(
            user_id=user_id,
            user_name=user_name,
            role=str(role) if role is not None else None,
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip_address=ip_address,
            details=_json_safe(details),
        )
        db.add(entry)
        if commit:
            db.commit()
        else:
            db.flush()
        return entry
    except Exception:
        # Audit logging must never break the primary operation.
        try:
            db.rollback()
        except Exception:
            pass
        return None  # type: ignore[return-value]


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, str, int, float, bool)):
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def log_from_request(db: Session, request, user, action: str, resource: str, **kwargs):
    """ Convenience wrapper that pulls user + ip from a request. """
    ip = kwargs.pop("ip_address", None)
    if ip is None:
        fwd = request.headers.get("x-forwarded-for") if request else None
        ip = fwd.split(",")[0].strip() if fwd else (
            request.client.host if request and request.client else "unknown"
        )
    return log_action(
        db,
        user_id=user.id if user else None,
        user_name=user.name if user else None,
        role=str(user.role) if user else None,
        action=action,
        resource=resource,
        ip_address=ip,
        **kwargs,
    )
