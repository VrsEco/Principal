"""Integração de contexto autenticado com gates simulados; sem bootstrap."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core import mcp_runtime as runtime
from services import mcp_company_reference_service as references
from services import principal_authorization_service as authorization


@pytest.fixture
def authenticated(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(runtime, "get_http_request_context", lambda: {
        "transport": "streamable_http", "principal_id": 71, "user_id": 32,
        "company_id": None, "surface": "user", "auth_method": "oauth_oidc_bearer",
    })
    resolver = Mock(return_value=8)
    gate = Mock(return_value=SimpleNamespace(allowed=True, company_id=8,
        principal=SimpleNamespace(user_id=32), role="client", mcp_permissions=()))
    monkeypatch.setattr(references, "resolve_company_reference", resolver)
    monkeypatch.setattr(authorization.principal_authorization_service, "resolve_for_company", gate)
    monkeypatch.setattr(runtime, "resolve_runtime_identity", lambda **kw: {
        "company_id": 8, "employee_id": 73, "role": "client", "permissions": {},
        "accessible_company_ids": [8],
    })
    return resolver, gate


def test_reference_uses_authenticated_principal_and_rechecks_grant(authenticated):
    resolver, gate = authenticated
    context = runtime.resolve_mcp_execution_context({"company_ref": "AW", "user_id": 999, "principal_id": 999})
    resolver.assert_called_once_with("AW", principal_id=71, user_id=32,
                                    explicit_id=None, accessible_company_ids=None)
    gate.assert_called_once_with(principal_id=71, company_id=8)
    assert (context.company_id, context.user_id, context.employee_id) == (8, 32, 73)


def test_reference_cannot_bypass_revoked_grant(authenticated):
    resolver, gate = authenticated
    gate.return_value = SimpleNamespace(allowed=False, reason="revoked")
    with pytest.raises(PermissionError, match="principal grant negado"):
        runtime.resolve_mcp_execution_context({"company_ref": "AW"})


def test_ambiguity_does_not_reach_company_gate(authenticated):
    resolver, gate = authenticated
    resolver.side_effect = ValueError("Empresa ambígua")
    with pytest.raises(ValueError, match="ambígua"):
        runtime.resolve_mcp_execution_context({"company_ref": "Meu Chapa"})
    gate.assert_not_called()


def test_existing_numeric_id_does_not_invoke_reference_resolver(authenticated):
    resolver, gate = authenticated
    context = runtime.resolve_mcp_execution_context({"company_id": 8})
    resolver.assert_not_called()
    assert context.company_id == 8


def test_task_tool_schema_exposes_reference_and_personal_filters():
    from mcp.server.fastmcp import FastMCP
    path = Path(__file__).parents[1] / "src/intelligence/tools.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    tool = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "list_project_tasks_secure")
    tool.decorator_list = []
    namespace = {}
    exec(compile(ast.Module(body=[tool], type_ignores=[]), str(path), "exec"), namespace)
    mcp = FastMCP("isolated-schema")
    mcp.tool()(runtime.wrap_mcp_callable(namespace[tool.name]))
    import asyncio
    schema = asyncio.run(mcp.list_tools())[0].inputSchema
    assert {"company_ref", "company_id", "mine_only", "open_only"} <= schema["properties"].keys()
