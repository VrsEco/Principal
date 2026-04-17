from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import inspect, text

from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class MutationLimitPolicy:
    create_limit: int
    update_limit: int
    delete_limit: int
    restore_limit: int
    window_hours: int

    def get_limit(self, action: str) -> int:
        normalized = str(action or "").strip().lower()
        if normalized == "create":
            return self.create_limit
        if normalized == "update":
            return self.update_limit
        if normalized == "delete":
            return self.delete_limit
        if normalized == "restore":
            return self.restore_limit
        return self.update_limit


@dataclass(frozen=True)
class MutationLimitDecision:
    allowed: bool
    action: str
    count: int
    limit: int
    window_hours: int
    reason: str


def load_mutation_limit_policy() -> MutationLimitPolicy:
    return MutationLimitPolicy(
        create_limit=_coerce_positive_int(os.environ.get("APP32_MCP_CREATE_LIMIT"), 20),
        update_limit=_coerce_positive_int(os.environ.get("APP32_MCP_UPDATE_LIMIT"), 50),
        delete_limit=_coerce_positive_int(os.environ.get("APP32_MCP_DELETE_LIMIT"), 10),
        restore_limit=_coerce_positive_int(os.environ.get("APP32_MCP_RESTORE_LIMIT"), 10),
        window_hours=_coerce_positive_int(os.environ.get("APP32_MCP_MUTATION_WINDOW_HOURS"), 24),
    )


def _event_type_for_action(action: str) -> str:
    return f"mcp.mutation.{str(action or '').strip().lower()}.success"


def count_recent_mutations(
    *,
    action: str,
    company_id: int,
    user_id: int,
    now: datetime | None = None,
) -> int:
    from models import db

    if not company_id or not user_id:
        return 0

    policy = load_mutation_limit_policy()
    anchor = now or datetime.now(timezone.utc)
    since = anchor - timedelta(hours=policy.window_hours)
    table_name = "ai_mcp_audit_events"

    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        return 0

    row = db.session.execute(
        text(
            f"""
            SELECT COUNT(*) AS total
            FROM {table_name}
            WHERE event_type = :event_type
              AND status = 'success'
              AND company_id = :company_id
              AND user_id = :user_id
              AND occurred_at >= :since
            """
        ),
        {
            "event_type": _event_type_for_action(action),
            "company_id": int(company_id),
            "user_id": int(user_id),
            "since": since,
        },
    ).scalar_one()
    return int(row or 0)


def evaluate_mutation_limit(
    *,
    action: str,
    company_id: int | None,
    user_id: int | None,
    now: datetime | None = None,
) -> MutationLimitDecision:
    normalized_action = str(action or "").strip().lower()
    policy = load_mutation_limit_policy()
    limit = policy.get_limit(normalized_action)

    if not company_id or not user_id:
        return MutationLimitDecision(
            allowed=False,
            action=normalized_action,
            count=0,
            limit=limit,
            window_hours=policy.window_hours,
            reason="mutações MCP exigem usuário associado e company_id resolvido",
        )

    count = count_recent_mutations(
        action=normalized_action,
        company_id=int(company_id),
        user_id=int(user_id),
        now=now,
    )
    if count >= limit:
        return MutationLimitDecision(
            allowed=False,
            action=normalized_action,
            count=count,
            limit=limit,
            window_hours=policy.window_hours,
            reason=(
                f"limite de mutações para '{normalized_action}' atingido: "
                f"{count}/{limit} nas últimas {policy.window_hours}h"
            ),
        )

    return MutationLimitDecision(
        allowed=True,
        action=normalized_action,
        count=count,
        limit=limit,
        window_hours=policy.window_hours,
        reason="ok",
    )


def record_mutation_success(
    *,
    action: str,
    company_id: int,
    user_id: int,
    tool_name: str,
    domain: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = build_ai_execution_audit_record(
        event_type=_event_type_for_action(action),
        runtime="mcp",
        status="success",
        domain=domain,
        operation=action,
        tool_name=tool_name,
        scope="mcp",
        company_id=company_id,
        user_id=user_id,
        metadata=metadata or {},
    )
    return emit_ai_execution_audit_event(record)

