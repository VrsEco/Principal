from __future__ import annotations

from src.core.mcp_http_auth import App32McpHttpIdentity, reset_http_request_context, set_http_request_context
from src.core.mcp_runtime import resolve_mcp_execution_context


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
    assert context.metadata["surface"] == "user"
    assert context.metadata["transport"] == "streamable_http"

