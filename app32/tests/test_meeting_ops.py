from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

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

    def _lookup(_meeting_id, company_id=None):
        called["lookup"] = True
        return None, "should not be called"

    monkeypatch.setattr(meeting_ops, "_get_meeting_in_company_scope", _lookup)

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

    allowed = SimpleNamespace(allowed=True, resolved_company_id=12)
    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, allowed),
    )
    monkeypatch.setattr(
        meeting_ops,
        "evaluate_mutation_limit",
        lambda **kwargs: SimpleNamespace(allowed=True, reason="ok"),
    )
    monkeypatch.setattr(
        meeting_ops,
        "_get_meeting_in_company_scope",
        lambda meeting_id, company_id=None: (meeting, None),
    )
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

    def _fake_start_meeting(*, meeting_id, company_id=None):
        called["meeting_id"] = meeting_id
        called["company_id"] = company_id
        return "ok"

    monkeypatch.setattr(tools_module.meeting_ops_domain, "start_meeting", _fake_start_meeting)

    assert tools_module.start_meeting.func(meeting_id=42, company_id=10) == "ok"
    assert called == {"meeting_id": 42, "company_id": 10}


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


def test_schedule_meeting_denies_company_out_of_scope(monkeypatch) -> None:
    denied = SimpleNamespace(allowed=False, reason="company_id solicitado não pertence ao escopo do principal")
    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, denied),
    )

    result = meeting_ops.schedule_meeting(
        title="Planejamento",
        date="2026-05-20",
        time="09:00",
        guests="ana@empresa.com",
        company_id=10,
    )

    assert "não pertence ao escopo do principal" in result


def test_schedule_meeting_uses_explicit_company_id(monkeypatch) -> None:
    created = {}
    persisted = []

    class _FakeMeeting:
        id = 33
        query = _FakeQuery()

        def __init__(self, **kwargs):
            created.update(kwargs)
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.id = 33

    _FakeMeeting.query.value = _FakeMeeting(company_id=10, title="persisted")
    created.clear()

    class _FakeSession:
        def add(self, obj):
            persisted.append(obj)

        def commit(self):
            return None

        def rollback(self):
            return None

    allowed = SimpleNamespace(allowed=True, resolved_company_id=10)
    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, allowed),
    )
    monkeypatch.setattr(
        meeting_ops,
        "evaluate_mutation_limit",
        lambda **kwargs: SimpleNamespace(allowed=True, reason="ok"),
    )
    monkeypatch.setattr(
        meeting_ops,
        "record_mutation_success",
        lambda **kwargs: {"ok": True, **kwargs},
    )
    monkeypatch.setattr(meeting_ops, "db", SimpleNamespace(session=_FakeSession()))

    with patch("models.meeting.Meeting", _FakeMeeting), patch(
        "services.email_service.email_service",
        SimpleNamespace(send_email=lambda **kwargs: True),
    ):
        result = meeting_ops.schedule_meeting(
            title="Planejamento",
            date="2026-05-20",
            time="09:00",
            guests="ana@empresa.com",
            company_id=10,
        )

    assert created["company_id"] == 10
    assert _FakeMeeting.query.last_filter_kwargs == {"id": 33, "company_id": 10}
    assert "criada com sucesso" in result


def test_start_meeting_uses_explicit_company_id(monkeypatch) -> None:
    meeting = SimpleNamespace(
        id=42,
        title="Comitê",
        company_id=10,
        project_id=77,
        actual_date=None,
        actual_time=None,
        status="draft",
    )
    captured = {}
    allowed = SimpleNamespace(allowed=True, resolved_company_id=10)

    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, allowed),
    )
    monkeypatch.setattr(
        meeting_ops,
        "evaluate_mutation_limit",
        lambda **kwargs: SimpleNamespace(allowed=True, reason="ok"),
    )
    monkeypatch.setattr(
        meeting_ops,
        "record_mutation_success",
        lambda **kwargs: {"ok": True, **kwargs},
    )
    monkeypatch.setattr(
        meeting_ops,
        "_get_meeting_in_company_scope",
        lambda meeting_id, company_id=None: (
            captured.update({"meeting_id": meeting_id, "company_id": company_id}) or (meeting, None)
        ),
    )
    monkeypatch.setattr(
        meeting_ops,
        "db",
        SimpleNamespace(session=SimpleNamespace(add=lambda obj: None, flush=lambda: None, commit=lambda: None, rollback=lambda: None)),
    )

    result = meeting_ops.start_meeting(meeting_id=42, company_id=10)

    assert captured == {"meeting_id": 42, "company_id": 10}
    assert "INICIADA" in result


def test_delete_meeting_secure_requires_confirmation(monkeypatch) -> None:
    denied = SimpleNamespace(
        allowed=False,
        reason="mutação destrutiva exige confirmação explícita",
        to_audit_event=lambda: {"allowed": False},
    )
    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, denied),
    )

    result = meeting_ops.delete_meeting_secure(
        meeting_id=33,
        reason="limpeza de teste",
        confirm=False,
        company_id=1,
    )

    assert result["success"] is False
    assert "confirmação explícita" in result["error"]


def test_delete_meeting_secure_deletes_meeting_and_work_journey(monkeypatch) -> None:
    deleted = []
    meeting = SimpleNamespace(id=33, title="Teste", company_id=1, project_id=88)
    work_item_1 = SimpleNamespace(id=1)
    work_item_2 = SimpleNamespace(id=2)
    allowed = SimpleNamespace(
        allowed=True,
        resolved_company_id=1,
        to_audit_event=lambda: {"allowed": True},
    )

    class _FakeWJQuery:
        def filter_by(self, **kwargs):
            self.last_filter_kwargs = kwargs
            return self

        def all(self):
            return [work_item_1, work_item_2]

    fake_wj_model = SimpleNamespace(query=_FakeWJQuery())

    monkeypatch.setattr(
        meeting_ops,
        "_authorize_meeting_mcp",
        lambda **kwargs: ({"user_id": 3}, allowed),
    )
    monkeypatch.setattr(
        meeting_ops,
        "evaluate_mutation_limit",
        lambda **kwargs: SimpleNamespace(allowed=True, reason="ok"),
    )
    monkeypatch.setattr(
        meeting_ops,
        "_get_meeting_in_company_scope",
        lambda meeting_id, company_id=None: (meeting, None),
    )
    monkeypatch.setattr(
        meeting_ops,
        "record_mutation_success",
        lambda **kwargs: {"ok": True, **kwargs},
    )
    monkeypatch.setattr(
        meeting_ops,
        "db",
        SimpleNamespace(
            session=SimpleNamespace(
                delete=lambda obj: deleted.append(obj),
                commit=lambda: None,
                rollback=lambda: None,
            )
        ),
    )

    with patch("models.WorkJourneyItem", fake_wj_model):
        result = meeting_ops.delete_meeting_secure(
            meeting_id=33,
            reason="limpeza de teste",
            confirm=True,
            company_id=1,
        )

    assert result["success"] is True
    assert result["removed_work_journey_items"] == 2
    assert deleted == [work_item_1, work_item_2, meeting]
