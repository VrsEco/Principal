from __future__ import annotations

from collections import Counter
from typing import Any

from models.agent_menu import AgentMenuOption
from services.ai_automation_registry_service import AIAutomationRegistryService
from services.ai_capability_blueprint_service import AICapabilityBlueprintService
from services.integration_catalog_service import IntegrationCatalogService
from services.sapiens_factory_registry_service import SapiensFactoryRegistryService
from services.tool_first_catalog_service import ToolFirstCatalogService
from src.intelligence.workflows.registry import WorkflowRegistry


class AICapabilityInventoryService:
    """Inventário unificado das capabilities IA/automação do APP32."""

    @classmethod
    def build_inventory(cls, active_company: Any | None = None) -> dict[str, Any]:
        company_id = getattr(active_company, "id", None)
        tool_catalog = ToolFirstCatalogService.build_catalog(active_company)
        integration_catalog = IntegrationCatalogService.build_catalog()
        factory_registry = SapiensFactoryRegistryService.build_registry_snapshot()
        automation_registry = AIAutomationRegistryService.build_registry(active_company)

        try:
            workflow_options = (
                AgentMenuOption.query
                .filter(AgentMenuOption.is_active.is_(True))
                .order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.id.asc())
                .all()
            )
        except Exception:
            workflow_options = []
        workflow_registry = WorkflowRegistry.from_menu_options(workflow_options, preferred_company_id=company_id)

        items: list[dict[str, Any]] = []
        category_counter: Counter[str] = Counter()
        status_counter: Counter[str] = Counter()

        for domain in tool_catalog.get("domains") or []:
            item = {
                "key": f"tool-domain:{domain.get('key')}",
                "title": domain.get("title"),
                "category": "tool_domain",
                "domain": domain.get("key"),
                "status": domain.get("status") or "planned",
                "surface": domain.get("surface"),
                "entrypoint": domain.get("entrypoint"),
                "description": domain.get("description"),
            }
            items.append(item)
            category_counter.update([item["category"]])
            status_counter.update([item["status"]])

        for integration in integration_catalog.get("integrations") or []:
            item = {
                "key": f"integration:{integration.get('key')}",
                "title": integration.get("title"),
                "category": "integration",
                "domain": integration.get("category"),
                "status": integration.get("status") or "planned",
                "surface": integration.get("technical_channel"),
                "entrypoint": "/api-mcp",
                "description": integration.get("summary"),
            }
            items.append(item)
            category_counter.update([item["category"]])
            status_counter.update([item["status"]])

        for capability in factory_registry.get("capabilities") or []:
            item = {
                "key": f"factory:{capability.get('key')}",
                "title": capability.get("title"),
                "category": "factory_capability",
                "domain": capability.get("domain"),
                "status": capability.get("status") or "planned",
                "surface": ",".join(capability.get("layers") or []),
                "entrypoint": "/ai/factory",
                "description": capability.get("description"),
            }
            items.append(item)
            category_counter.update([item["category"]])
            status_counter.update([item["status"]])

        for workflow in workflow_registry.list():
            item = {
                "key": f"workflow:{workflow.code}",
                "title": workflow.title,
                "category": "workflow",
                "domain": workflow.action_key.split(".", 1)[0] if workflow.action_key else "workflow",
                "status": "ready",
                "surface": "workflow",
                "entrypoint": "/workflow",
                "description": workflow.description or workflow.action_key,
            }
            items.append(item)
            category_counter.update([item["category"]])
            status_counter.update([item["status"]])

        for automation in automation_registry.get("automations") or []:
            item = {
                "key": f"automation:{automation.get('key')}",
                "title": automation.get("title"),
                "category": "automation",
                "domain": automation.get("kind"),
                "status": automation.get("status") or "planned",
                "surface": automation.get("surface"),
                "entrypoint": "/ai-automation-mesh",
                "description": automation.get("description"),
            }
            items.append(item)
            category_counter.update([item["category"]])
            status_counter.update([item["status"]])

        items.sort(key=lambda item: (item.get("category") or "", item.get("title") or ""))
        blueprint = AICapabilityBlueprintService.build_blueprint(
            title="Capability padrão APP32",
            domain="platform",
            target_layers=["service", "tool_contract", "rest_mcp", "workflow", "ui_sapiens"],
            risk="medium",
            human_gate_required=True,
            execution_mode="plan",
        )
        return {
            "summary": {
                "capabilities": len(items),
                "categories": len(category_counter),
                "workflow_count": len([item for item in items if item["category"] == "workflow"]),
                "integration_count": len([item for item in items if item["category"] == "integration"]),
                "automation_count": len([item for item in items if item["category"] == "automation"]),
                "by_category": dict(category_counter),
                "by_status": dict(status_counter),
            },
            "items": items,
            "blueprint": blueprint,
        }
