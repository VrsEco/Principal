from __future__ import annotations

from typing import Any

from models.agent_action import AgentAction


FINAL_ACTION_STATUSES = {"approved", "rejected", "executed", "failed", "rolled_back"}
PENDING_ACTION_STATUSES = {"pending", "awaiting_approval"}
APPROVAL_ACTION_TYPES = {"workflow_approval_request", "approval_request"}


def list_pending_actions(
    company_ids: list[int] | tuple[int, ...],
) -> tuple[list[AgentAction], list[dict[str, Any]]]:
    if not company_ids:
        return [], []

    actions = (
        AgentAction.query.filter(
            AgentAction.company_id.in_(list(company_ids)),
            AgentAction.status.in_(list(PENDING_ACTION_STATUSES)),
            AgentAction.type.in_(list(APPROVAL_ACTION_TYPES)),
        )
        .order_by(AgentAction.created_at.asc())
        .all()
    )

    suppressed: list[dict[str, Any]] = []
    return actions, suppressed
