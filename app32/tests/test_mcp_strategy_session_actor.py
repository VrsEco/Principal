"""Estratégia no mcp-versus: autor e revisor vêm da sessão autenticada, nunca do cliente (M2)."""
from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_strategy_alignment_tools as alignment
import src.core.mcp_plan_driver_tools as plan_driver
import src.core.mcp_plan_global_okr_correction_tools as okr_correction
import src.core.mcp_plan_global_okr_tools as okr_create
import src.core.mcp_plan_participant_tools as participants
import src.core.mcp_sector_strategy_tools as sector
from src.core.mcp_session_actor import require_session_user_id, session_user_id

TWELVE = [
    "upsert_strategy_identity_tool",
    "upsert_organizational_identity_tool",
    "upsert_process_strategy_profile_tool",
    "upsert_process_strategic_profile_tool",
    "upsert_process_strategy_alignment_link_tool",
    "upsert_indicator_line_of_sight_tool",
    "review_strategy_maturation_item_tool",
    "create_single_plan_driver_tool",
    "correct_plan_global_okrs_tool",
    "create_and_link_plan_global_okrs_tool",
    "sync_plan_participants_tool",
    "create_sector_okr_structure_tool",
]
IDENTITY_PARAMS = {"user_id", "reviewer_user_id", "approver_user_id", "actor_user_id", "request_id", "trace_id"}


@pytest.fixture(scope="module")
def manager():
    server = FastMCP("probe")
    alignment.register_strategy_alignment_tools(server)
    plan_driver.register_plan_driver_tools(server)
    okr_correction.register_plan_global_okr_correction_tools(server)
    okr_create.register_plan_global_okr_tools(server)
    participants.register_plan_participant_tools(server)
    sector.register_sector_strategy_tools(server)
    return server._tool_manager


@pytest.mark.parametrize("name", TWELVE)
def test_no_strategy_mutation_accepts_identity_from_the_client(manager, name):
    props = set(manager.get_tool(name).parameters["properties"])
    assert props.isdisjoint(IDENTITY_PARAMS), f"{name}: {props & IDENTITY_PARAMS}"
    assert "company_id" in props


def test_session_user_helpers(monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": "42"})
    assert session_user_id() == 42 and require_session_user_id() == 42
    for raw in (None, "", "abc", 0, -3):
        monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda raw=raw: {"user_id": raw})
        assert session_user_id() is None
    with pytest.raises(PermissionError):
        require_session_user_id()


def test_identity_upsert_is_attributed_to_the_session_user(manager, monkeypatch):
    seen = {}
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": 77})
    monkeypatch.setattr(
        alignment.StrategyAlignmentN1Service,
        "upsert_identity",
        staticmethod(lambda company_id, payload, user_id=None: seen.update(user_id=user_id) or {"ok": True}),
    )
    out = manager.get_tool("upsert_strategy_identity_tool").fn(company_id=9, payload={"mission": "x"})
    assert out["success"] is True and seen["user_id"] == 77


def test_maturation_review_uses_the_session_user_as_reviewer(manager, monkeypatch):
    seen = {}
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": 78})
    monkeypatch.setattr(
        alignment.StrategyAlignmentN1Service,
        "review_maturation_item",
        staticmethod(lambda **kw: seen.update(kw) or {"decision": kw["decision"]}),
    )
    manager.get_tool("review_strategy_maturation_item_tool").fn(company_id=9, item_id=1, decision="hold")
    assert seen["reviewer_user_id"] == 78


def test_write_without_a_session_user_is_refused_with_an_error_envelope(manager, monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {})
    called = []
    monkeypatch.setattr(alignment.StrategyAlignmentN1Service, "upsert_identity", staticmethod(lambda **kw: called.append(kw)))
    out = manager.get_tool("upsert_strategy_identity_tool").fn(company_id=9, payload={"mission": "x"})
    assert out["success"] is False and out["error"]["code"] == "strategy_alignment_n1_forbidden" and not called


def test_plan_tool_without_a_session_user_is_refused_before_the_service(manager, monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {})
    called = []
    monkeypatch.setattr(plan_driver.PlanDriverMCPService, "create_single_driver", staticmethod(lambda **kw: called.append(kw)))
    out = manager.get_tool("create_single_plan_driver_tool").fn(company_id=9, plan_id=1, description="d")
    assert out["success"] is False and out["error"]["code"] == "plan_driver_forbidden" and not called
