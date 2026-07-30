from __future__ import annotations

import inspect
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.mcp_knowledge_tools import register_knowledge_tools


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

    def answer(self, question, **kwargs):
        self.calls.append(("answer", question, kwargs))
        return {"mode": "answer", "company_id": kwargs["company_id"]}

    def search(self, question, **kwargs):
        self.calls.append(("search", question, kwargs))
        return {"mode": "search", "company_id": kwargs["company_id"]}


def test_knowledge_mcp_tools_take_company_only_from_runtime_context(monkeypatch):
    import src.core.mcp_knowledge_tools as module

    service = _FakeService()
    monkeypatch.setattr(module, "KnowledgeQueryService", lambda: service)
    monkeypatch.setattr(
        module,
        "resolve_mcp_execution_context",
        lambda payload: SimpleNamespace(company_id=9, user_id=7, employee_id=21),
    )
    mcp = _FakeMCP()
    register_knowledge_tools(mcp)

    product = mcp.registered["answer_product_help"]("Como publicar?")
    corporate = mcp.registered["search_organizational_knowledge"]("Última decisão")

    assert product == {"mode": "answer", "company_id": 9}
    assert corporate == {"mode": "search", "company_id": 9}
    assert "company_id" not in inspect.signature(
        mcp.registered["search_organizational_knowledge"]
    ).parameters
    assert service.calls[0][2]["source_types"] == ("product_help",)
    assert service.calls[0][2]["require_company"] is False
    assert service.calls[0][2]["user_id"] == 7
    assert service.calls[0][2]["employee_id"] == 21
    assert service.calls[1][2]["require_company"] is True
    assert service.calls[1][2]["user_id"] == 7
    assert service.calls[1][2]["employee_id"] == 21


def test_knowledge_capabilities_are_canonical_and_read_only():
    from src.intelligence.tool_catalog import catalog
    from src.intelligence.security.tenant_rbac import PrincipalContext, validate_permission

    product = catalog.get_tool_capability("answer_product_help")
    corporate = catalog.get_tool_capability("answer_organizational_question")

    assert product.domain == "knowledge"
    assert product.risk.value == "low"
    assert "mcp_user" in product.scopes
    assert corporate.required_context == ("company",)
    assert corporate.permissions == ("knowledge.read",)
    decision = validate_permission(
        PrincipalContext(role="colaborador"),
        domain="knowledge",
        action="read",
    )
    assert decision.allowed is True


def test_rbac_catalog_contains_knowledge_read_surface():
    from services.rbac_permission_catalog_service import RbacPermissionCatalogService
    from src.intelligence.mcp_contracts import (
        APP32_PERMISSION_MATRIX_MANIFEST,
        APP32_PROFILE_CONTRACTS_MANIFEST,
    )

    keys = RbacPermissionCatalogService.node_map()
    overlay = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay("coordenador_cliente")
    matrix = APP32_PERMISSION_MATRIX_MANIFEST.get_overlay("coordenador_cliente")[0]

    assert "knowledge.search" in keys
    assert "knowledge.mcp.answers" in keys
    assert "knowledge" in overlay.allowed_domains
    assert "knowledge" in {rule.domain for rule in matrix.domains}
