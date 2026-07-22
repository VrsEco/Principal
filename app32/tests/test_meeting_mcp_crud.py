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
        company_id=13, meeting_id=9, title="Meta de vendas", notes="Contexto"
    )
    assert error is None
    topic_id = topic_payload["topic"]["id"]

    decision_payload, error = MeetingMCPService.create_decision(
        company_id=13, meeting_id=9, topic_id=topic_id,
        text="Aumentar a meta em 10%", owner="Ana",
    )
    assert error is None
    decision_id = decision_payload["decision"]["id"]
    stored = json.loads(meeting.discussions_json)
    assert stored[0]["decision"] == "Aumentar a meta em 10%"
    assert stored[0]["decisions"][0]["id"] == decision_id

    payload, error = MeetingMCPService.update_decision(
        company_id=13, meeting_id=9, topic_id=topic_id, decision_id=decision_id,
        changes={"text": "Aumentar a meta em 12%"},
    )
    assert error is None
    assert payload["decision"]["text"] == "Aumentar a meta em 12%"

    payload, error = MeetingMCPService.delete_decision(
        company_id=13, meeting_id=9, topic_id=topic_id, decision_id=decision_id,
    )
    assert error is None
    assert payload["deleted_decision_id"] == decision_id
    assert json.loads(meeting.discussions_json)[0]["decision"] == ""
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
    assert ToolScope.SAPIENS.value not in scheduling.scopes
    assert ToolScope.MCP_USER.value not in scheduling.scopes


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
