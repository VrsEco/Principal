"""Variantes seguras de conhecimento: company_id explícito, grant validado, somente leitura."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_knowledge_tools as knowledge

TOOLS = knowledge.SECURE_COMPANY_SELECTION_TOOLS
ORIGINALS = ("answer_product_help", "search_organizational_knowledge", "answer_organizational_question")


class _Service:
    def __init__(self):
        self.calls = []

    def search(self, question, **kwargs):
        self.calls.append(("search", question, kwargs))
        return {"results": []}

    def answer(self, question, **kwargs):
        self.calls.append(("answer", question, kwargs))
        return {"claims": []}


@pytest.fixture
def server(monkeypatch):
    service = _Service()
    monkeypatch.setattr(knowledge, "KnowledgeQueryService", lambda: service)
    payloads = []

    def fake_context(payload=None, **_):
        payloads.append(dict(payload or {}))
        return SimpleNamespace(company_id=(payload or {}).get("company_id"), user_id=3, employee_id=23)

    monkeypatch.setattr(knowledge, "resolve_mcp_execution_context", fake_context)
    mcp = FastMCP("probe")
    knowledge.register_knowledge_tools(mcp)
    return SimpleNamespace(mcp=mcp, service=service, payloads=payloads, fn=lambda n: mcp._tool_manager.get_tool(n).fn)


def test_the_closed_list_has_exactly_two_tools():
    assert set(TOOLS) == {"search_organizational_knowledge_secure", "answer_organizational_question_secure"}


@pytest.mark.parametrize("name", TOOLS)
def test_schema_requires_company_id_and_never_accepts_user_or_tenant_overrides(server, name):
    props = server.mcp._tool_manager.get_tool(name).parameters["properties"]
    assert "company_id" in props and "question" in props
    assert not {"user_id", "employee_id", "tenant_id", "role", "surface"} & set(props)


@pytest.mark.parametrize("name", ORIGINALS)
def test_original_tools_still_do_not_accept_company_id(server, name):
    assert "company_id" not in server.mcp._tool_manager.get_tool(name).parameters["properties"]


@pytest.mark.parametrize("name,method", [(TOOLS[0], "search"), (TOOLS[1], "answer")])
def test_requests_the_company_explicitly_and_uses_the_authenticated_identity(server, name, method):
    server.fn(name)(company_id=9, question="Qual é a missão?", limit=3)
    assert server.payloads == [{"company_id": 9}]
    call, question, kwargs = server.service.calls[0]
    assert call == method and question == "Qual é a missão?"
    assert kwargs["company_id"] == 9 and kwargs["limit"] == 3 and kwargs["require_company"] is True
    assert kwargs["user_id"] == 3 and kwargs["employee_id"] == 23


@pytest.mark.parametrize("name", TOOLS)
def test_one_company_per_call_never_mixes_tenants(server, name):
    server.fn(name)(company_id=9, question="x")
    server.fn(name)(company_id=1, question="x")
    assert [c[2]["company_id"] for c in server.service.calls] == [9, 1]
    assert server.payloads == [{"company_id": 9}, {"company_id": 1}]


@pytest.mark.parametrize("name", TOOLS)
def test_grant_denial_propagates_and_nothing_is_read(server, monkeypatch, name):
    def deny(payload=None, **_):
        raise PermissionError("principal grant negado: grant do principal para a empresa não encontrado")

    monkeypatch.setattr(knowledge, "resolve_mcp_execution_context", deny)
    with pytest.raises(PermissionError):
        server.fn(name)(company_id=999999, question="x")
    assert server.service.calls == []


@pytest.mark.parametrize("name", TOOLS)
def test_resolved_company_must_match_the_requested_one(server, monkeypatch, name):
    monkeypatch.setattr(
        knowledge,
        "resolve_mcp_execution_context",
        lambda payload=None, **_: SimpleNamespace(company_id=1, user_id=3, employee_id=23),
    )
    with pytest.raises(PermissionError):
        server.fn(name)(company_id=9, question="x")
    assert server.service.calls == []


@pytest.mark.parametrize("name", TOOLS)
@pytest.mark.parametrize("limit", [0, -1, 21, True, "5", None])
def test_invalid_limit_is_rejected_before_any_read(server, name, limit):
    with pytest.raises(ValueError):
        server.fn(name)(company_id=9, question="x", limit=limit)
    assert server.service.calls == [] and server.payloads == []


@pytest.mark.parametrize("name", TOOLS)
@pytest.mark.parametrize("question", ["", "   ", "x" * 2001, None])
def test_invalid_question_is_rejected_before_any_read(server, name, question):
    with pytest.raises(ValueError):
        server.fn(name)(company_id=9, question=question)
    assert server.service.calls == []


@pytest.mark.parametrize("name", TOOLS)
@pytest.mark.parametrize("company_id", [0, -5, True, "9", None])
def test_invalid_company_is_rejected_before_any_read(server, name, company_id):
    with pytest.raises(ValueError):
        server.fn(name)(company_id=company_id, question="x")
    assert server.service.calls == []
