from __future__ import annotations

import inspect
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.mcp_strategic_tree_tools import register_strategic_tree_tools


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


class _FakeService:
    def __init__(self):
        self.calls = []

    def list_trees(self, actor):
        self.calls.append(("list", actor))
        return {"trees": [], "company_id": actor.company_id}

    def get_tree(self, actor, tree_id):
        self.calls.append(("get", actor, tree_id))
        return {"tree": {"id": tree_id, "company_id": actor.company_id}}

    def get_branch(self, actor, **kwargs):
        self.calls.append(("branch", actor, kwargs))
        return {"node": {"id": kwargs["node_id"]}}

    def add_contribution(self, actor, **kwargs):
        self.calls.append(("add", actor, kwargs))
        return {"created": True, "contribution": {"id": 77, "company_id": actor.company_id}}


def _context(company_id=9):
    return SimpleNamespace(
        user_id=3,
        company_id=company_id,
        role="cliente",
        accessible_company_ids=(9,),
    )


def test_strategic_tree_mcp_reads_and_writes_use_runtime_actor(monkeypatch):
    import src.core.mcp_strategic_tree_tools as module

    service = _FakeService()
    monkeypatch.setattr(module, "StrategicTreeService", lambda: service)
    monkeypatch.setattr(module, "resolve_mcp_execution_context", lambda payload: _context(payload["company_id"]))
    mcp = _FakeMCP()
    register_strategic_tree_tools(mcp)

    listed = mcp.registered["strategic_tree_list"](9)
    created = mcp.registered["strategic_tree_add_contribution"](
        9,
        5,
        "Conhecimento confirmado pelo gestor.",
        idempotency_key="qa-1",
        human_gate_confirmed=True,
    )

    assert listed["meta"]["company_id"] == 9
    assert created["data"]["created"] is True
    assert service.calls[0][1].user_id == 3
    assert service.calls[1][2]["source_type"] == "mcp"
    assert service.calls[1][2]["surface"] == "mcp"


def test_strategic_tree_mcp_write_requires_explicit_human_gate(monkeypatch):
    import src.core.mcp_strategic_tree_tools as module

    monkeypatch.setattr(module, "StrategicTreeService", _FakeService)
    monkeypatch.setattr(module, "resolve_mcp_execution_context", lambda payload: _context())
    mcp = _FakeMCP()
    register_strategic_tree_tools(mcp)

    with pytest.raises(PermissionError, match="Confirmação humana"):
        mcp.registered["strategic_tree_add_contribution"](9, 5, "Tentativa sem gate")


def test_strategic_tree_capabilities_are_published_and_governed():
    from src.intelligence.tool_catalog import catalog
    from src.intelligence.tooling.capabilities import infer_tool_action

    read = catalog.get_tool_capability("strategic_tree_get_branch")
    write = catalog.get_tool_capability("strategic_tree_add_contribution")

    assert read.domain == "knowledge"
    assert read.required_context == ("user", "company")
    assert infer_tool_action(read.name, read.domain) == "read"
    assert write.human_gate is True
    assert write.permissions == ("knowledge.create",)
    assert infer_tool_action(write.name, write.domain) == "create"
    assert "mcp_user" in write.scopes


def test_mcp_write_contract_exposes_company_and_human_gate(monkeypatch):
    import src.core.mcp_strategic_tree_tools as module

    monkeypatch.setattr(module, "StrategicTreeService", _FakeService)
    mcp = _FakeMCP()
    register_strategic_tree_tools(mcp)
    signature = inspect.signature(mcp.registered["strategic_tree_add_contribution"])

    assert "company_id" in signature.parameters
    assert "human_gate_confirmed" in signature.parameters
    assert signature.parameters["human_gate_confirmed"].default is False
