from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from models.automation import AutomationRegistry


class AutomationRegistryRepository:
    @staticmethod
    def _base_query(company_id: int):
        return AutomationRegistry.query.filter(AutomationRegistry.company_id == int(company_id))

    @staticmethod
    def list(company_id: int, filters: dict[str, Any] | None = None, *, limit: int = 200):
        filters = filters or {}
        query = AutomationRegistryRepository._base_query(company_id)

        module_key = str(filters.get("module_key") or "").strip().lower()
        if module_key:
            query = query.filter(AutomationRegistry.module_key == module_key)

        origin_type = str(filters.get("origin_type") or "").strip().lower()
        if origin_type:
            query = query.filter(AutomationRegistry.origin_type == origin_type)

        status = str(filters.get("status") or "").strip().lower()
        if status:
            query = query.filter(AutomationRegistry.status == status)

        entity_type = str(filters.get("entity_type") or "").strip().lower()
        if entity_type:
            query = query.filter(AutomationRegistry.entity_type == entity_type)

        entity_id = filters.get("entity_id")
        if entity_id not in (None, ""):
            try:
                query = query.filter(AutomationRegistry.entity_id == int(entity_id))
            except (TypeError, ValueError):
                pass

        search = str(filters.get("search") or "").strip()
        if search:
            ilike = f"%{search}%"
            query = query.filter(
                or_(
                    AutomationRegistry.name.ilike(ilike),
                    AutomationRegistry.module_key.ilike(ilike),
                    AutomationRegistry.entity_type.ilike(ilike),
                    AutomationRegistry.action_type.ilike(ilike),
                )
            )

        if bool(filters.get("only_approval")):
            query = query.filter(
                or_(
                    AutomationRegistry.requires_approval.is_(True),
                    AutomationRegistry.status == "waiting_approval",
                )
            )

        if bool(filters.get("only_error")):
            query = query.filter(AutomationRegistry.status == "error")

        return (
            query.order_by(
                AutomationRegistry.next_execution_at.asc().nullslast(),
                AutomationRegistry.name.asc(),
            )
            .limit(max(1, min(int(limit or 200), 500)))
            .all()
        )
