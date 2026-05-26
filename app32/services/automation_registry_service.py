from __future__ import annotations

from collections import Counter
from typing import Any

from models.automation import AutomationExecution
from repositories.automation_registry_repository import AutomationRegistryRepository


class AutomationRegistryService:
    @staticmethod
    def normalize_filters(raw_filters: dict[str, Any] | None = None) -> dict[str, Any]:
        raw_filters = raw_filters or {}
        return {
            "module_key": str(raw_filters.get("module_key") or "").strip().lower() or None,
            "origin_type": str(raw_filters.get("origin_type") or "").strip().lower() or None,
            "status": str(raw_filters.get("status") or "").strip().lower() or None,
            "entity_type": str(raw_filters.get("entity_type") or "").strip().lower() or None,
            "entity_id": raw_filters.get("entity_id"),
            "search": str(raw_filters.get("search") or "").strip() or None,
            "only_error": str(raw_filters.get("only_error") or "").strip().lower() in {"1", "true", "on", "yes", "sim"},
            "only_approval": str(raw_filters.get("only_approval") or "").strip().lower() in {"1", "true", "on", "yes", "sim"},
        }

    @staticmethod
    def _serialize_registry_item(item) -> dict[str, Any]:
        rule = item.rules.first() if hasattr(item, "rules") else None
        last_execution = item.executions.order_by(AutomationExecution.triggered_at.desc(), AutomationExecution.id.desc()).first() if hasattr(item, "executions") else None
        bpms_link = item.bpms_links.first() if hasattr(item, "bpms_links") else None

        payload = item.to_dict()
        payload["rule"] = rule.to_dict() if rule else None
        payload["last_execution"] = last_execution.to_dict() if last_execution else None
        payload["bpms_link"] = bpms_link.to_dict() if bpms_link else None
        return payload

    @staticmethod
    def build_registry_snapshot(company_id: int, raw_filters: dict[str, Any] | None = None, *, limit: int = 200) -> dict[str, Any]:
        filters = AutomationRegistryService.normalize_filters(raw_filters)
        items = AutomationRegistryRepository.list(company_id, filters, limit=limit)

        module_counter: Counter[str] = Counter()
        origin_counter: Counter[str] = Counter()
        status_counter: Counter[str] = Counter()

        serialized = []
        for item in items:
            serialized_item = AutomationRegistryService._serialize_registry_item(item)
            serialized.append(serialized_item)
            module_counter.update([serialized_item.get("module_key") or "unknown"])
            origin_counter.update([serialized_item.get("origin_type") or "unknown"])
            status_counter.update([serialized_item.get("status") or "unknown"])

        return {
            "summary": {
                "total": len(serialized),
                "by_module": dict(module_counter),
                "by_origin": dict(origin_counter),
                "by_status": dict(status_counter),
                "errors": sum(1 for item in serialized if item.get("status") == "error"),
                "approvals": sum(1 for item in serialized if item.get("requires_approval")),
            },
            "filters": filters,
            "automations": serialized,
        }
