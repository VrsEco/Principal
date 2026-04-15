import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ai_capability_inventory_service import AICapabilityInventoryService


def test_inventory_service_consolidates_categories(monkeypatch):
    monkeypatch.setattr(
        "services.ai_capability_inventory_service.ToolFirstCatalogService.build_catalog",
        lambda active_company=None: {
            "domains": [
                {"key": "engineering", "title": "Engineering", "status": "canonical", "surface": "engineering", "entrypoint": "/sapiens", "description": "desc"}
            ]
        },
    )
    monkeypatch.setattr(
        "services.ai_capability_inventory_service.IntegrationCatalogService.build_catalog",
        lambda: {"integrations": [{"key": "open_finance", "title": "Open Finance", "category": "Financeiro", "status": "planned", "technical_channel": "api_mcp", "summary": "desc"}]},
    )
    monkeypatch.setattr(
        "services.ai_capability_inventory_service.SapiensFactoryRegistryService.build_registry_snapshot",
        lambda: {"capabilities": [{"key": "factory_cap", "title": "Factory", "domain": "engineering", "status": "ready", "layers": ["service"], "description": "desc"}]},
    )
    monkeypatch.setattr(
        "services.ai_capability_inventory_service.AIAutomationRegistryService.build_registry",
        lambda active_company=None: {"automations": [{"key": "job", "title": "Job", "kind": "scheduler_core", "status": "ready", "surface": "scheduler", "description": "desc"}]},
    )

    class _FakeWorkflow:
        def __init__(self):
            self.code = "wf.code"
            self.title = "Workflow"
            self.action_key = "engineering.action"
            self.description = "desc"

    monkeypatch.setattr(
        "services.ai_capability_inventory_service.AgentMenuOption",
        SimpleNamespace(
            query=SimpleNamespace(filter=lambda *args, **kwargs: SimpleNamespace(order_by=lambda *a, **k: SimpleNamespace(all=lambda: []))),
            is_active=SimpleNamespace(is_=lambda value: value),
            sort_order=SimpleNamespace(asc=lambda: None),
            id=SimpleNamespace(asc=lambda: None),
        ),
    )
    monkeypatch.setattr(
        "services.ai_capability_inventory_service.WorkflowRegistry.from_menu_options",
        lambda options, preferred_company_id=None: SimpleNamespace(list=lambda: [_FakeWorkflow()]),
    )

    payload = AICapabilityInventoryService.build_inventory(SimpleNamespace(id=31))

    assert payload["summary"]["capabilities"] == 5
    assert payload["summary"]["categories"] >= 4
    assert payload["summary"]["workflow_count"] == 1
    assert payload["blueprint"]["human_gate_required"] is True
