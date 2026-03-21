import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.agent_action_backlog_service as backlog_service


def _build_action(**overrides):
    payload = {
        "approval_key": "project_task.complete|10|9|AA.J.31.205",
        "action_key": "project_task.complete",
        "channel": "whatsapp",
        "object_code": "AA.J.31.205",
        "approval_status": "pending",
    }
    data = {
        "id": 91,
        "type": "workflow_approval_request",
        "status": "pending",
        "title": "Aprovação necessária: a conclusão da atividade AA.J.31.205",
        "description": "Ação sensível solicitada via WhatsApp.",
        "payload": payload,
        "company_id": 9,
        "user_id": 10,
        "requesting_agent": "sapiens",
        "handling_agent": "operations",
        "created_at": datetime(2026, 3, 20, 22, 0, 0),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_ensure_backlog_task_for_action_creates_link_and_updates_payload(monkeypatch):
    captured = {"added": []}
    fake_task = SimpleNamespace(
        id=301,
        code="AA.J.31.301",
        notes="",
        logs=[],
        status="planned",
        stage="inbox",
        completion_date=None,
    )

    class _FakeLink:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setattr(backlog_service, "AgentActionBacklogLink", _FakeLink)
    monkeypatch.setattr(backlog_service, "find_backlog_link_by_action_id", lambda action_id: None)
    monkeypatch.setattr(backlog_service, "_recover_orphan_backlog_task_for_action", lambda action: None)
    monkeypatch.setattr(
        backlog_service,
        "create_backlog_task",
        lambda **kwargs: (fake_task, None),
    )
    monkeypatch.setattr(backlog_service.db.session, "add", lambda item: captured["added"].append(item))
    monkeypatch.setattr(backlog_service.db.session, "commit", lambda: captured.setdefault("committed", True))

    action = _build_action()
    link, task = backlog_service.ensure_backlog_task_for_action(action, autocommit=True)

    assert link is not None
    assert task is fake_task
    assert captured["committed"] is True
    assert action.payload["backlog_card"]["task_id"] == 301
    assert action.payload["backlog_card"]["task_code"] == "AA.J.31.301"
    assert fake_task.stage == "waiting"
    assert fake_task.status == "planned"
    assert "AgentAction vinculado: #91" in fake_task.notes
    assert any(log.get("type") == "agent_action_sync" for log in fake_task.logs)


def test_sync_backlog_task_for_action_marks_completed_without_duplicate_logs(monkeypatch):
    fake_task = SimpleNamespace(
        id=302,
        code="AA.J.31.302",
        notes="",
        logs=[],
        status="planned",
        stage="waiting",
        completion_date=None,
    )
    fake_link = SimpleNamespace(
        task=fake_task,
        backlog_project_code="AA.J.31",
        link_type="workflow_approval_request",
    )

    monkeypatch.setattr(backlog_service, "find_backlog_link_by_action_id", lambda action_id: fake_link)
    monkeypatch.setattr(backlog_service.db.session, "flush", lambda: None)

    action = _build_action(status="executed", payload={**_build_action().payload, "approval_status": "approved"})

    backlog_service.sync_backlog_task_for_action(action, autocommit=False)
    backlog_service.sync_backlog_task_for_action(action, autocommit=False)

    assert fake_task.status == "completed"
    assert fake_task.stage == "completed"
    assert fake_task.completion_date is not None
    assert action.payload["backlog_card"]["task_code"] == "AA.J.31.302"
    sync_logs = [log for log in fake_task.logs if log.get("type") == "agent_action_sync"]
    assert len(sync_logs) == 1
