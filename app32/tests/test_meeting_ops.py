from __future__ import annotations

import json
from types import SimpleNamespace

from src.intelligence.tools_domains import meeting_ops
from src.intelligence import tools as tools_module


class _FakeQuery:
    def __init__(self, value=None):
        self.value = value
        self.last_filter_kwargs = None
        self.filter_history = []
        self.limit_value = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        self.filter_history.append(kwargs)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def first(self):
        return self.value

    def all(self):
        if isinstance(self.value, list):
            return self.value
        return [self.value] if self.value is not None else []


def test_send_meeting_minutes_rejects_invalid_channel_before_lookup(monkeypatch) -> None:
    called = {"lookup": False}

    def _lookup(_meeting_id):
        called["lookup"] = True
        return None, "should not be called"

    monkeypatch.setattr(meeting_ops, "get_meeting_in_active_company", _lookup)

    result = meeting_ops.send_meeting_minutes(10, channel="sms")

    assert "canal inválido" in result
    assert called["lookup"] is False


def test_log_meeting_discussion_blocks_linked_project_from_other_company(monkeypatch) -> None:
    meeting = SimpleNamespace(
        id=7,
        title="Comitê",
        company_id=12,
        project_id=99,
        discussions_json="[]",
        activities_json="[]",
    )
    project_query = _FakeQuery(None)
    fake_project_model = SimpleNamespace(query=project_query)

    monkeypatch.setattr(meeting_ops, "get_meeting_in_active_company", lambda _meeting_id: (meeting, None))
    monkeypatch.setattr("models.project.Project", fake_project_model)

    result = meeting_ops.log_meeting_discussion(
        meeting_id=7,
        topic="Plano",
        decision="Criar ação",
        responsible="Ana",
        deadline="2026-04-30",
    )

    assert "não pertence à empresa ativa" in result
    assert project_query.last_filter_kwargs == {"id": 99, "company_id": 12}


def test_tools_meeting_wrappers_delegate_to_domain(monkeypatch) -> None:
    called = {}

    def _fake_start_meeting(*, meeting_id):
        called["meeting_id"] = meeting_id
        return "ok"

    monkeypatch.setattr(tools_module.meeting_ops_domain, "start_meeting", _fake_start_meeting)

    assert tools_module.start_meeting.func(meeting_id=42) == "ok"
    assert called == {"meeting_id": 42}


def test_list_meetings_honors_explicit_company_and_limit(monkeypatch) -> None:
    meeting = SimpleNamespace(
        id=5,
        title="Ritual Semanal",
        status="draft",
        scheduled_date=SimpleNamespace(isoformat=lambda: "2026-05-16"),
        scheduled_time="09:00",
        project=None,
    )
    fake_query = _FakeQuery([meeting])
    fake_meeting_model = SimpleNamespace(
        query=fake_query,
        scheduled_date=SimpleNamespace(desc=lambda: SimpleNamespace(nullslast=lambda: None)),
        scheduled_time=SimpleNamespace(desc=lambda: SimpleNamespace(nullslast=lambda: None)),
        created_at=SimpleNamespace(desc=lambda: None),
    )

    monkeypatch.setattr(meeting_ops, "get_active_company_id", lambda: 31)
    monkeypatch.setattr("models.meeting.Meeting", fake_meeting_model)

    result = meeting_ops.list_meetings(company_id=10, status="draft", limit=7)

    assert fake_query.filter_history[0] == {"company_id": 10}
    assert fake_query.filter_history[1] == {"status": "draft"}
    assert fake_query.limit_value == 7
    assert "Ritual Semanal" in result


def test_tools_list_meetings_wrapper_delegates_to_domain(monkeypatch) -> None:
    called = {}

    def _fake_list_meetings(*, company_id=None, status=None, limit=20):
        called["company_id"] = company_id
        called["status"] = status
        called["limit"] = limit
        return "meetings-ok"

    monkeypatch.setattr(tools_module.meeting_ops_domain, "list_meetings", _fake_list_meetings)

    assert tools_module.list_meetings.func(10, "draft", 5) == "meetings-ok"
    assert called == {"company_id": 10, "status": "draft", "limit": 5}
