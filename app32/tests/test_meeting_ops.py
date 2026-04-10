from __future__ import annotations

import json
from types import SimpleNamespace

from src.intelligence.tools_domains import meeting_ops
from src.intelligence import tools as tools_module


class _FakeQuery:
    def __init__(self, value=None):
        self.value = value
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.value


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
