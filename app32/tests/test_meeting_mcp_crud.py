from __future__ import annotations

import json
from types import SimpleNamespace

from services.meeting_mcp_service import MeetingMCPService
from src.intelligence import tools as tools_module
from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolScope, infer_tool_action
from src.intelligence.mcp_contracts import APP32_CRUD_CONTRACTS_MANIFEST


class _Session:
    def __init__(self):
        self.commits = 0

    def add(self, _obj):
        return None

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None


def _meeting():
    return SimpleNamespace(
        id=9,
        company_id=13,
        project_id=None,
        discussions_json="[]",
        activities_json="[]",
    )


def test_topic_and_decision_crud_keep_stable_ids_and_legacy_decision(monkeypatch):
    meeting = _meeting()
    session = _Session()
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))

    topic_payload, error = MeetingMCPService.create_topic(
        company_id=13, meeting_id=9, title="Meta de vendas", notes="Contexto",
        discussion="Cenário debatido",
    )
    assert error is None
    topic_id = topic_payload["topic"]["id"]
    assert topic_payload["topic"]["discussion"] == "Cenário debatido"

    decision_payload, error = MeetingMCPService.create_decision(
        company_id=13, meeting_id=9, topic_id=topic_id,
        text="Aumentar a meta em 10%", owner="Ana",
    )
    assert error is None
    decision_id = decision_payload["decision"]["id"]
    stored = json.loads(meeting.discussions_json)
    assert stored[0]["decision"] == "Aumentar a meta em 10%"
    assert stored[0]["discussion"] == "Aumentar a meta em 10%"
    assert stored[0]["decisions"][0]["id"] == decision_id

    payload, error = MeetingMCPService.update_decision(
        company_id=13, meeting_id=9, topic_id=topic_id, decision_id=decision_id,
        changes={"text": "Aumentar a meta em 12%"},
    )
    assert error is None
    assert payload["decision"]["text"] == "Aumentar a meta em 12%"
    assert json.loads(meeting.discussions_json)[0]["discussion"] == "Aumentar a meta em 12%"

    payload, error = MeetingMCPService.delete_decision(
        company_id=13, meeting_id=9, topic_id=topic_id, decision_id=decision_id,
    )
    assert error is None
    assert payload["deleted_decision_id"] == decision_id
    assert json.loads(meeting.discussions_json)[0]["decision"] == ""
    assert json.loads(meeting.discussions_json)[0]["discussion"] == ""
    assert session.commits == 4


def test_activity_crud_preserves_deadline_responsible_budget_and_effort(monkeypatch):
    meeting = _meeting()
    session = _Session()
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))

    payload, error = MeetingMCPService.create_activity(
        company_id=13,
        meeting_id=9,
        title="Preparar proposta",
        responsible="Bruno",
        deadline="2026-08-15",
        budget="R$ 8.500",
        estimated_hours=12.5,
        priority="high",
        how="Consolidar escopo e preço",
    )
    assert error is None
    activity = payload["activity"]
    assert activity["deadline"] == "2026-08-15"
    assert activity["responsible"] == "Bruno"
    assert activity["budget"] == "R$ 8.500"
    assert activity["estimated_hours"] == 12.5

    payload, error = MeetingMCPService.update_activity(
        company_id=13,
        meeting_id=9,
        activity_id=activity["id"],
        changes={"responsible": "Carla", "budget": "R$ 9.000"},
    )
    assert error is None
    assert payload["activity"]["responsible"] == "Carla"
    assert payload["activity"]["budget"] == "R$ 9.000"

    payload, error = MeetingMCPService.delete_activity(
        company_id=13, meeting_id=9, activity_id=activity["id"]
    )
    assert error is None
    assert json.loads(meeting.activities_json) == []


def test_activity_crud_rejects_priority_outside_project_contract(monkeypatch):
    meeting = _meeting()
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))

    payload, error = MeetingMCPService.create_activity(
        company_id=13, meeting_id=9, title="Atividade", priority="critical",
    )

    assert payload is None
    assert "low, normal, high ou urgent" in error


def test_sync_reuses_ui_activity_by_project_and_title_and_preserves_link(monkeypatch):
    meeting = _meeting()
    meeting.project_id = 22
    meeting.activities_json = json.dumps([
        {
            "id": "activity-ui-1",
            "title": "Preparar proposta",
            "project_id": 22,
            "priority": "valor-legado-invalido",
        }
    ])
    existing_task = SimpleNamespace(id=81, project_id=22, what="Preparar proposta", is_deleted=False)

    class _TaskQuery:
        def filter_by(self, **kwargs):
            assert kwargs == {"project_id": 22, "what": "Preparar proposta", "is_deleted": False}
            return self

        def first(self):
            return existing_task

    session = _Session()
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))
    monkeypatch.setattr(
        MeetingMCPService,
        "_validate_project",
        staticmethod(lambda **kwargs: (SimpleNamespace(id=22), None)),
    )
    monkeypatch.setattr(
        "services.meeting_mcp_service.ProjectTask",
        SimpleNamespace(query=_TaskQuery()),
    )
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))

    payload, error = MeetingMCPService.sync_activities(company_id=13, meeting_id=9)

    assert error is None
    assert payload["created_tasks"] == 0
    assert payload["updated_tasks"] == 1
    assert existing_task.priority == "normal"
    assert json.loads(meeting.activities_json)[0]["project_task_id"] == 81


def test_meeting_crud_tools_are_in_sapiens_and_mcp_catalogs():
    expected = {
        "create_meeting",
        "get_meeting",
        "update_meeting",
        "create_meeting_topic",
        "update_meeting_topic",
        "delete_meeting_topic",
        "create_meeting_decision",
        "update_meeting_decision",
        "delete_meeting_decision",
        "create_meeting_activity",
        "update_meeting_activity",
        "delete_meeting_activity",
        "sync_meeting_activities_to_project",
    }
    exported = {tool.name for tool in tools_module.tools}
    assert expected <= exported
    for tool_name in expected:
        capability = catalog.get_tool_capability(tool_name)
        assert capability is not None
        assert capability.domain == "meetings"
        assert ToolScope.SAPIENS.value in capability.scopes
        assert ToolScope.MCP_USER.value in capability.scopes

    scheduling = catalog.get_tool_capability("schedule_meeting")
    assert scheduling is not None
    assert ToolScope.SAPIENS.value in scheduling.scopes
    assert ToolScope.MCP_USER.value in scheduling.scopes
    assert ToolScope.MCP_ADMIN.value in scheduling.scopes
    assert "deprecated" not in scheduling.tags
    assert "tenant_safe" in scheduling.tags


def test_nested_meeting_removal_is_governed_as_meeting_update():
    assert infer_tool_action("delete_meeting_topic", "meetings") == "update"
    assert infer_tool_action("delete_meeting_decision", "meetings") == "update"
    assert infer_tool_action("delete_meeting_activity", "meetings") == "update"


def test_project_and_task_crud_are_discoverable_by_sapiens():
    for tool_name in (
        "create_project", "list_projects", "update_project", "delete_project",
        "list_project_tasks_secure", "create_project_task_secure",
        "update_project_task_secure", "delete_project_task_secure",
    ):
        capability = catalog.get_tool_capability(tool_name)
        assert capability is not None
        assert ToolScope.SAPIENS.value in capability.scopes


def test_meeting_crud_contract_is_implemented_and_mentions_project_sync():
    contract = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("meetings")
    assert contract is not None
    assert "sincronização" in contract.description.lower()
    assert {item.entity for item in contract.operations} >= {
        "meeting", "meeting_topic", "meeting_decision", "meeting_activity"
    }
    assert all(item.implementation_status == "implemented" for item in contract.operations)


def test_create_meeting_persists_scheduled_date_and_time(monkeypatch):
    added = []
    session = _Session()
    session.add = added.append
    monkeypatch.setattr(MeetingMCPService, "_validate_project", staticmethod(lambda **kwargs: (None, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))
    monkeypatch.setattr("services.meeting_mcp_service.Meeting", lambda **kwargs: SimpleNamespace(id=5, to_dict=lambda: kwargs, **kwargs))
    monkeypatch.setattr(MeetingMCPService, "_sync_work_journey", staticmethod(lambda _meeting: None))

    payload, error = MeetingMCPService.create_meeting(
        company_id=13, title="Tia Sonia x Versus", scheduled_date="05/10/2026",
        scheduled_time="9:00", planned_duration_minutes=120,
    )

    assert error is None
    meeting = payload["meeting"]
    assert meeting["scheduled_date"].isoformat() == "2026-10-05"
    assert meeting["scheduled_time"] == "09:00"
    assert meeting["planned_duration_minutes"] == 120

    _, error = MeetingMCPService.create_meeting(company_id=13, title="x", scheduled_time="25:99")
    assert error == "Horário inválido. Use HH:MM."


def test_update_meeting_accepts_scheduled_fields_and_rejects_invalid_values(monkeypatch):
    meeting = SimpleNamespace(
        id=109, company_id=13, project_id=None, scheduled_date=None, scheduled_time=None,
        planned_duration_minutes=None, to_dict=lambda: {},
    )
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=_Session()))

    _, error = MeetingMCPService.update_meeting(
        company_id=13, meeting_id=109,
        changes={"scheduled_date": "2026-10-05", "scheduled_time": "09:00", "planned_duration_minutes": "120"},
    )
    assert error is None
    assert meeting.scheduled_date.isoformat() == "2026-10-05"
    assert meeting.scheduled_time == "09:00"
    assert meeting.planned_duration_minutes == 120

    _, error = MeetingMCPService.update_meeting(company_id=13, meeting_id=109, changes={"scheduled_date": "amanhã"})
    assert error and "inválida" in error


def test_meeting_mcp_create_and_update_sync_work_journey(monkeypatch):
    calls = []
    session = _Session()
    monkeypatch.setattr(MeetingMCPService, "_validate_project", staticmethod(lambda **kwargs: (None, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))
    monkeypatch.setattr(
        "services.meeting_mcp_service.Meeting",
        lambda **kwargs: SimpleNamespace(id=7, to_dict=lambda: {}, **kwargs),
    )
    monkeypatch.setattr(
        "services.work_journey_sync.sync_meeting_item",
        lambda company_id, meeting_id, preferred_employee_id=None: calls.append((company_id, meeting_id)),
    )

    MeetingMCPService.create_meeting(company_id=13, title="Reunião")
    meeting = SimpleNamespace(id=7, company_id=13, project_id=None, to_dict=lambda: {})
    monkeypatch.setattr(MeetingMCPService, "get_meeting", staticmethod(lambda **kwargs: (meeting, None)))
    MeetingMCPService.update_meeting(company_id=13, meeting_id=7, changes={"title": "Novo"})

    assert calls == [(13, 7), (13, 7)]


def test_meeting_mcp_sync_failure_does_not_break_the_write(monkeypatch):
    session = _Session()
    monkeypatch.setattr(MeetingMCPService, "_validate_project", staticmethod(lambda **kwargs: (None, None)))
    monkeypatch.setattr("services.meeting_mcp_service.db", SimpleNamespace(session=session))
    monkeypatch.setattr(
        "services.meeting_mcp_service.Meeting",
        lambda **kwargs: SimpleNamespace(id=7, to_dict=lambda: {"id": 7}, **kwargs),
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("falha")

    monkeypatch.setattr("services.work_journey_sync.sync_meeting_item", _boom)

    payload, error = MeetingMCPService.create_meeting(company_id=13, title="Reunião")

    assert error is None
    assert payload["meeting"] == {"id": 7}
