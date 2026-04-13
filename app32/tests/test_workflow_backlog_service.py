import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workflow_backlog_service import WorkflowBacklogService


def test_workflow_backlog_service_creates_manual_request(monkeypatch):
    created = {}
    monkeypatch.setattr(
        "services.workflow_backlog_service.ProjectTaskService.create_project_task",
        lambda **kwargs: (
            created.update(kwargs)
            or {
                "task": SimpleNamespace(
                    id=1001,
                    stage=kwargs["stage"],
                    code="AA.J.31.1001",
                    what=kwargs["task_name"],
                    notes=kwargs["notes"],
                    created_at=None,
                    updated_at=None,
                )
            },
            None,
        ),
    )

    payload = WorkflowBacklogService.create_request(
        {
            "title": "fechamento_financeiro_guiado",
            "business_domain": "Financeiro",
            "objective": "Conduzir fechamento com coleta, validação e confirmação.",
            "problem_statement": "Hoje o fechamento depende de idas e vindas manuais e pode perder etapas críticas.",
            "target_users": "Financeiro e Sapiens",
            "desired_channels": "web, whatsapp",
            "expected_result": "Coleta guiada, checklist validado e execução segura do fechamento.",
            "user_examples": "Quero fechar o financeiro da empresa X do período Y; valide se está tudo pronto.",
            "known_inputs": "empresa, período",
            "data_summary": "empresa, período, checkpoints, aprovações",
        },
        company_id=31,
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert created["stage"] == "inbox"
    assert payload["title"] == "fechamento_financeiro_guiado"
    assert payload["backlog_task_code"] == "AA.J.31.1001"
    assert "desired_channels=web, whatsapp" in created["notes"]
    assert "suggested_action_key=" in created["notes"]
    assert "Checklist esperado para especificação da IA" in created["description"]


def test_workflow_backlog_service_lists_existing_requests(monkeypatch):
    monkeypatch.setattr(
        "services.workflow_backlog_service.WorkflowBacklogService._list_manual_request_tasks",
        lambda: [
            SimpleNamespace(
                id=1002,
                stage="executing",
                code="AA.J.31.1002",
                what="[Novo Workflow] followup_operacional",
                notes="source_channel=workflow_request_ui\nbusiness_domain=Rotina\nurgency=high",
                created_at=None,
                updated_at=None,
            )
        ],
    )
    monkeypatch.setattr(
        "services.workflow_backlog_service.WorkflowBacklogService._list_gap_candidates",
        lambda active_company=None: [],
    )

    items = WorkflowBacklogService.list_requests(requester_user_id=9, requester_name="Fabiano")

    assert len(items) == 1
    assert items[0]["title"] == "followup_operacional"
    assert items[0]["status"] == "executing"
    assert items[0]["business_domain"] == "Rotina"


def test_workflow_backlog_service_includes_gap_candidates(monkeypatch):
    monkeypatch.setattr(
        "services.workflow_backlog_service.WorkflowBacklogService._list_manual_request_tasks",
        lambda: [],
    )
    monkeypatch.setattr(
        "services.workflow_backlog_service.WorkflowBacklogService._list_gap_candidates",
        lambda active_company=None: [
            SimpleNamespace(
                id=11,
                suggested_flow_name="followup_financeiro",
                title="[FLOW GAP][web] followup financeiro",
                normalized_intent="followup financeiro",
                app_task_id=777,
                app_task_code="AA.J.31.777",
                created_at=None,
                updated_at=None,
                task=SimpleNamespace(stage="pending"),
            )
        ],
    )

    items = WorkflowBacklogService.list_requests(requester_user_id=9, requester_name="Fabiano")

    assert len(items) == 1
    assert items[0]["source_kind"] == "gap_candidate"
    assert items[0]["backlog_task_code"] == "AA.J.31.777"
