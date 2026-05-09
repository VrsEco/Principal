import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.engineering_suggestion_request_service import EngineeringSuggestionRequestService


def test_engineering_suggestion_service_creates_backlog_card(monkeypatch):
    created_payload = {}

    monkeypatch.setattr(
        "services.engineering_suggestion_request_service.ProjectTaskService.create_project_task",
        lambda **kwargs: (
            created_payload.update(kwargs)
            or {
                "task": SimpleNamespace(
                    id=913,
                    what=kwargs["task_name"],
                    stage=kwargs["stage"],
                    code="AA.J.1.913",
                    created_at=None,
                    updated_at=None,
                    notes=kwargs["notes"],
                )
            },
            None,
        ),
    )

    payload = EngineeringSuggestionRequestService.create_request(
        {
            "title": "Macroprocesso com responsável",
            "suggestion_type": "improvement",
            "scope_label": "Processos",
            "objective": "Permitir registrar e atualizar o responsável do macroprocesso via MCP.",
            "evidence_summary": "Empresa AY / Poly Chargers não consegue atribuir owner/responsible.",
            "notes": "Necessário criar card no backlog de produção.",
        },
        company_id=12,
        company_name="Poly Chargers",
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert created_payload["project_code"] == EngineeringSuggestionRequestService.BACKLOG_PROJECT_CODE
    assert created_payload["task_name"] == "[Sugestão Engenharia] Macroprocesso com responsável"
    assert "requester_company_id=12" in created_payload["notes"]
    assert payload["backlog_task_code"] == "AA.J.1.913"
    assert payload["suggestion_type"] == "improvement"


def test_engineering_suggestion_service_lists_only_requester_items(monkeypatch):
    sample_task = SimpleNamespace(
        id=914,
        what="[Sugestão Engenharia] Ajustar intake MCP",
        stage="executing",
        code="AA.J.1.914",
        created_at=None,
        updated_at=None,
        notes=(
            "source_channel=engineering_suggestion_mcp\n"
            "suggestion_type=observation\n"
            "scope_label=MCP\n"
            "urgency=medium\n"
            "source_origin=mcp\n"
            "requester_company_id=12\n"
            "requester_user_id=9"
        ),
    )

    query_stub = SimpleNamespace(
        filter=lambda *args: query_stub,
        order_by=lambda *args: query_stub,
        limit=lambda *args: query_stub,
        all=lambda: [sample_task],
    )

    monkeypatch.setattr(
        "services.engineering_suggestion_request_service.EngineeringSuggestionRequestService._project_id",
        lambda: 31,
    )
    monkeypatch.setattr(
        "services.engineering_suggestion_request_service.ProjectTask",
        SimpleNamespace(
            project_id=object(),
            notes=SimpleNamespace(isnot=lambda value: object(), contains=lambda value: object()),
            updated_at=SimpleNamespace(desc=lambda: object()),
            id=SimpleNamespace(desc=lambda: object()),
            query=query_stub,
        ),
    )

    records = EngineeringSuggestionRequestService.list_requests(
        company_id=12,
        requester_user_id=9,
        limit=5,
    )

    assert len(records) == 1
    assert records[0]["title"] == "Ajustar intake MCP"
    assert records[0]["status_label"] == "Executando"
    assert records[0]["requester_company_id"] == 12
