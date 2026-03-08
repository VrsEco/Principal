from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS = 24


def parse_workflow_approval_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def get_workflow_approval_expires_at(action: Any, *, ttl_hours: int = DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS) -> Optional[datetime]:
    payload = dict(getattr(action, "payload", None) or {})
    explicit = parse_workflow_approval_datetime(payload.get("approval_expires_at"))
    if explicit is not None:
        return explicit
    created_at = getattr(action, "created_at", None)
    if created_at is None:
        return None
    return created_at + timedelta(hours=max(int(ttl_hours or DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS), 1))


def is_workflow_approval_expired(action: Any, *, now: Optional[datetime] = None, ttl_hours: int = DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS) -> bool:
    if str(getattr(action, "status", None) or "").strip().lower() != "pending":
        return False
    expires_at = get_workflow_approval_expires_at(action, ttl_hours=ttl_hours)
    if expires_at is None:
        return False
    reference = now or datetime.utcnow()
    return expires_at <= reference
