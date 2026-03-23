import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.conversation_regression_backlog_service import ConversationRegressionBacklogService


def test_v6_update_existing_task_anexa_logs_e_notas():
    task = SimpleNamespace(id=10, code="AA.J.31.10", status="planned", stage="inbox", notes="", logs=[])
    item = {
        "case_id": "aa_j_31_999",
        "chapter": "a_consultar",
        "failure_class": "routing",
        "workflow_gap_id": 999,
        "status": "planned",
        "stage": "waiting",
        "app_task_code": "AA.J.31.10",
    }

    updated = ConversationRegressionBacklogService.update_existing_task(task, item)

    assert updated.stage == "waiting"
    assert "case_id=aa_j_31_999" in updated.notes
    assert updated.logs[-1]["action"] == "updated"


def test_v6_apply_sync_payload_atualiza_card_existente(monkeypatch):
    task = SimpleNamespace(id=12, code="AA.J.31.12", status="planned", stage="inbox", notes="", logs=[])
    monkeypatch.setattr(
        ConversationRegressionBacklogService,
        "find_existing_task_by_code",
        staticmethod(lambda task_code: task if task_code == "AA.J.31.12" else None),
    )
    monkeypatch.setattr(
        "services.conversation_regression_backlog_service.db.session.commit",
        lambda: None,
    )

    payload = {
        "project_code": "AA.J.31",
        "integration": "conversation_regression_v6",
        "items": [
            {
                "case_id": "aa_j_31_912",
                "chapter": "a_consultar",
                "failure_class": "routing",
                "workflow_gap_id": 912,
                "app_task_code": "AA.J.31.12",
                "status": "planned",
                "stage": "inbox",
            }
        ],
    }

    result = ConversationRegressionBacklogService.apply_sync_payload(payload, user_id=1, persist=True)

    assert result["processed"] == 1
    assert result["results"][0]["action"] == "updated"


def test_v6_apply_sync_payload_cria_card_quando_nao_existe(monkeypatch):
    monkeypatch.setattr(
        ConversationRegressionBacklogService,
        "find_existing_task_by_code",
        staticmethod(lambda task_code: None),
    )
    monkeypatch.setattr(
        "services.conversation_regression_backlog_service.db.session.commit",
        lambda: None,
    )
    monkeypatch.setattr(
        ConversationRegressionBacklogService,
        "create_new_task",
        staticmethod(
            lambda item, project_code, user_id: (
                SimpleNamespace(id=77, code="AA.J.31.77", logs=[]),
                None,
            )
        ),
    )

    payload = {
        "project_code": "AA.J.31",
        "items": [
            {
                "case_id": "aa_j_31_913",
                "chapter": "d_analisar",
                "failure_class": "multi_turn",
                "workflow_gap_id": 913,
                "app_task_code": None,
                "status": "planned",
                "stage": "inbox",
            }
        ],
    }

    result = ConversationRegressionBacklogService.apply_sync_payload(payload, user_id=1, persist=True)

    assert result["results"][0]["action"] == "created"
    assert result["results"][0]["task_code"] == "AA.J.31.77"


def test_v6_update_existing_task_preenche_completion_date_quando_fechado():
    task = SimpleNamespace(
        id=13,
        code="AA.J.31.13",
        status="planned",
        stage="inbox",
        notes="",
        logs=[],
        completion_date=None,
    )
    item = {
        "case_id": "aa_j_31_914",
        "chapter": "a_consultar",
        "failure_class": "routing",
        "workflow_gap_id": 914,
        "status": "completed",
        "stage": "completed",
        "app_task_code": "AA.J.31.13",
    }

    updated = ConversationRegressionBacklogService.update_existing_task(task, item)

    assert updated.completion_date is not None
