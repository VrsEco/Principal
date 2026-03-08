import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import workflow_gap_service as gap_service


def test_extract_candidate_codes_from_discovery_trace():
    telemetry = {
        "workflow_discovery": {
            "selected_code": "3.1",
            "top_matches": [
                {"code": "3.1", "score": 30},
                {"code": "3.2", "score": 22},
            ],
            "confidence": {"candidate_codes": ["3.1", "3.2", "3.3"]},
        }
    }

    codes = gap_service._extract_candidate_codes(telemetry)

    assert codes == ["3.1", "3.2", "3.3"]


def test_create_gap_candidate_persists_and_links_project_card(monkeypatch):
    events = []

    class FakeSession:
        def add(self, obj):
            events.append(("add", obj))
            if getattr(obj, "id", None) is None:
                obj.id = 501

        def flush(self):
            events.append(("flush", None))

        def commit(self):
            events.append(("commit", None))

        def rollback(self):
            events.append(("rollback", None))

    fake_db = SimpleNamespace(session=FakeSession())
    monkeypatch.setattr(gap_service, "db", fake_db)

    fake_task = SimpleNamespace(id=204, project_id=31, code="AA.J.31.204")

    def fake_create_project_task(**kwargs):
        events.append(("project_task", kwargs))
        return {"task": fake_task}, None

    monkeypatch.setattr(gap_service.ProjectTaskService, "create_project_task", fake_create_project_task)

    gap = gap_service.WorkflowGapService.create_gap_candidate(
        user_id=3,
        company_id=9,
        channel="whatsapp",
        thread_id="wa_7199",
        request_text="Preciso da ocupação do usuário X nesta semana",
        response_text="Posso levantar manualmente estes dados.",
        telemetry={
            "workflow_discovery": {
                "strategy": "hybrid",
                "confidence": {"route": "no_match", "candidate_codes": ["3.1"]},
            }
        },
    )

    assert gap is not None
    assert gap.id == 501
    assert gap.app_task_id == 204
    assert gap.app_task_code == "AA.J.31.204"
    assert gap.matched_workflow_codes == ["3.1"]
    assert any(kind == "project_task" for kind, _ in events)
    project_task_call = next(payload for kind, payload in events if kind == "project_task")
    assert project_task_call["project_code"] == "AA.J.31"
    assert project_task_call["stage"] == "inbox"
    assert "ocupação do usuário X" in project_task_call["description"]
    assert "Resposta atual entregue pela IA" in project_task_call["notes"]
