from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import or_

from models.agent_menu import AgentMenuOption
from models.workflow_gap import WorkflowGapCandidate
from models.workflow_usage import WorkflowExecutionLog
from services.workflow_catalog_service import build_workflow_catalog


class WorkflowWorkspaceService:
    @classmethod
    def build_catalog(
        cls,
        active_company: Any | None = None,
        *,
        include_inactive: bool = False,
        include_global: bool = True,
        limit: int = 500,
    ) -> dict[str, Any]:
        active_company_id = getattr(active_company, "id", None)

        option_query = AgentMenuOption.query
        if active_company_id is not None:
            company_filters = [AgentMenuOption.company_id == active_company_id]
            if include_global:
                company_filters.append(AgentMenuOption.company_id.is_(None))
            option_query = option_query.filter(or_(*company_filters))
        elif not include_global:
            option_query = option_query.filter(AgentMenuOption.company_id.isnot(None))

        if not include_inactive:
            option_query = option_query.filter_by(is_active=True)

        options = option_query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all()

        usage_logs = []
        gap_candidates = []
        if options:
            usage_query = WorkflowExecutionLog.query
            if active_company_id is not None:
                usage_query = usage_query.filter_by(company_id=active_company_id)
            usage_logs = usage_query.order_by(WorkflowExecutionLog.updated_at.desc()).limit(limit).all()

            gap_query = WorkflowGapCandidate.query
            if active_company_id is not None:
                gap_query = gap_query.filter(
                    or_(
                        WorkflowGapCandidate.company_id == active_company_id,
                        WorkflowGapCandidate.company_id.is_(None),
                    )
                )
            gap_candidates = gap_query.order_by(WorkflowGapCandidate.created_at.desc()).limit(limit).all()

        catalog = build_workflow_catalog(
            options=options,
            usage_logs=usage_logs,
            gap_candidates=gap_candidates,
            preferred_company_id=active_company_id,
        )

        parent_counter = Counter()
        for item in catalog.get("workflows") or []:
            parent_counter[str(item.get("parent_title") or "Geral")] += 1

        catalog["summary"] = {
            **(catalog.get("summary") or {}),
            "active_workflow_count": sum(1 for item in catalog.get("workflows") or [] if item.get("is_active")),
            "domains": [
                {"title": title, "count": count}
                for title, count in sorted(parent_counter.items(), key=lambda pair: (-pair[1], pair[0]))
            ],
        }
        return catalog
