import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.tool_backlog_service import ToolBacklogService


def test_tool_backlog_service_creates_missing_cards(monkeypatch):
    created = []

    monkeypatch.setattr(
        "services.tool_backlog_service.ToolBacklogService._find_backlog_task",
        lambda domain_key, tool_name: None,
    )
    monkeypatch.setattr(
        "services.tool_backlog_service.ToolFirstCatalogService.build_catalog",
        lambda active_company=None: {
            "domains": [
                {
                    "key": "engineering",
                    "title": "Squad de Engenharia",
                    "surface": "engineering",
                    "status": "canonical",
                    "description": "Diagnóstico técnico.",
                    "governance": ["MCP First"],
                    "planned_tools": [
                        {"name": "publish_tool_contract", "status": "planned"},
                        {"name": "review_route_surface", "status": "planned"},
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(
        "services.tool_backlog_service.ProjectTaskService.create_project_task",
        lambda **kwargs: (
            created.append(kwargs)
            or {
                "task": SimpleNamespace(
                    id=700 + len(created),
                    stage=kwargs["stage"],
                    code=f"AA.J.31.{700 + len(created)}",
                    created_at=None,
                    updated_at=None,
                )
            },
            None,
        ),
    )

    items = ToolBacklogService.ensure_catalog_backlog_tasks(
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert len(created) == 2
    assert all(entry["stage"] == "pending" for entry in created)
    assert {item["title"] for item in items} == {"publish_tool_contract", "review_route_surface"}


def test_tool_backlog_service_uses_existing_task_stage(monkeypatch):
    monkeypatch.setattr(
        "services.tool_backlog_service.ToolBacklogService._list_manual_request_tasks",
        lambda: [],
    )
    monkeypatch.setattr(
        "services.tool_backlog_service.ToolFirstCatalogService.build_catalog",
        lambda active_company=None: {
            "domains": [
                {
                    "key": "engineering",
                    "title": "Squad de Engenharia",
                    "surface": "engineering",
                    "status": "canonical",
                    "description": "Diagnóstico técnico.",
                    "governance": ["MCP First"],
                    "planned_tools": [{"name": "publish_tool_contract", "status": "planned"}],
                }
            ]
        },
    )
    monkeypatch.setattr(
        "services.tool_backlog_service.ToolBacklogService._find_backlog_task",
        lambda domain_key, tool_name: SimpleNamespace(
            id=888,
            stage="executing",
            code="AA.J.31.888",
            created_at=None,
            updated_at=None,
        ),
    )

    items = ToolBacklogService.list_requests(requester_user_id=9, requester_name="Fabiano")

    assert len(items) == 1
    assert items[0]["status"] == "executing"
    assert items[0]["status_label"] == "Executando"
    assert items[0]["backlog_task_code"] == "AA.J.31.888"


def test_tool_backlog_service_creates_manual_request(monkeypatch):
    created = {}
    monkeypatch.setattr(
        "services.tool_backlog_service.ProjectTaskService.create_project_task",
        lambda **kwargs: (
            created.update(kwargs)
            or {
                "task": SimpleNamespace(
                    id=999,
                    stage=kwargs["stage"],
                    code="AA.J.31.999",
                    what=kwargs["task_name"],
                    notes=kwargs["notes"],
                    created_at=None,
                    updated_at=None,
                )
            },
            None,
        ),
    )

    payload = ToolBacklogService.create_request(
        {
            "title": "calculate_budget_variance",
            "business_domain": "Financeiro",
            "objective": "Comparar orçamento e realizado por centro de resultado.",
            "data_summary": "budget_id, period, cost_center_id",
            "urgency": "high",
        },
        company_id=31,
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert created["stage"] == "inbox"
    assert created["priority"] == "high"
    assert payload["title"] == "calculate_budget_variance"
    assert payload["backlog_task_code"] == "AA.J.31.999"
