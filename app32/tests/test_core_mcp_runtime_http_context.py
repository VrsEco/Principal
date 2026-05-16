from __future__ import annotations

import inspect
from typing import Optional

from src.core.mcp_http_auth import App32McpHttpIdentity, reset_http_request_context, set_http_request_context
from src.core.mcp_runtime import resolve_mcp_execution_context, wrap_mcp_callable


def test_runtime_prefers_http_request_context(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-1",
            user_id=3,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "company_id": 9,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [company_id],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.user_id == 3
    assert context.company_id == 9
    assert context.employee_id == 23
    assert context.role == "director"
    assert context.permissions == ("approve",)
    assert context.metadata["surface"] == "user"
    assert context.metadata["transport"] == "streamable_http"



def test_runtime_pins_single_accessible_company_when_request_has_no_company(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-2",
            user_id=3,
            company_id=None,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.company_id == 12
    assert context.metadata["company_resolution_source"] == "runtime_identity.single_accessible_company_id"


def test_runtime_prefers_selected_company_from_payload(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-3",
            user_id=3,
            company_id=None,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12, 15],
        },
    )

    try:
        context = resolve_mcp_execution_context({"_selected_company_id": 15})
    finally:
        reset_http_request_context(tokens)

    assert context.company_id == 15
    assert context.metadata["company_resolution_source"] == "payload._selected_company_id"


def test_runtime_ignores_company_id_from_env_when_request_has_no_company(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USER_ID", "3")
    monkeypatch.setenv("APP32_MCP_COMPANY_ID", "9")
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12, 15],
        },
    )

    context = resolve_mcp_execution_context({})

    assert context.user_id == 3
    assert context.company_id is None
    assert context.metadata["company_resolution_source"] is None


def test_runtime_normalizes_permission_mapping_into_resource_action_tokens(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-4",
            user_id=4,
            company_id=11,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 4,
            "company_id": 11,
            "fallback_role": "colaborador",
            "surface": "user",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 77,
            "role": "colaborador",
            "permissions": {"financial": ["view", "create"]},
            "accessible_company_ids": [company_id],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert "financial" in context.permissions
    assert "financial.view" in context.permissions
    assert "financial.create" in context.permissions


def test_wrap_mcp_callable_materializes_forward_ref_annotations():
    def sample_tool(note: Optional[str] = None) -> dict[str, str]:
        return {"note": note or ""}

    wrapped = wrap_mcp_callable(sample_tool)
    signature = inspect.signature(wrapped)

    assert signature.parameters["note"].annotation == Optional[str]
    assert signature.return_annotation == dict[str, str]
