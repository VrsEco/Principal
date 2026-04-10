from __future__ import annotations

import pytest

from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy, require_tool_policy


def test_tool_policy_allows_user_surface_read_inside_tenant() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 10, "company_id": 7, "role": "colaborador"},
        ToolPolicyRequest(
            tool_name="list_project_tasks",
            surface="mcp_user",
            domain="routine",
            action="read",
            risk="low",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is True
    assert decision.resolved_surface == "user"
    assert decision.resolved_company_id == 7
    assert decision.to_audit_event()["tool_name"] == "list_project_tasks"


def test_tool_policy_blocks_user_surface_admin_domain() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 10, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="list_users",
            surface="user",
            domain="admin",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is False
    assert "domínio administrativo" in decision.reason
    assert "surface_user_blocks_admin_domain" in decision.checks


def test_tool_policy_blocks_cross_tenant_even_for_mcp_surface() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 10, "company_id": 7, "role": "colaborador"},
        ToolPolicyRequest(
            tool_name="read_finance_summary",
            surface="analytics",
            domain="finance",
            action="read",
            risk="medium",
            requested_company_id=8,
        ),
    )

    assert decision.allowed is False
    assert "escopo" in decision.reason


def test_tool_policy_requires_confirmation_for_destructive_admin_action() -> None:
    request = ToolPolicyRequest(
        tool_name="delete_user",
        surface="admin",
        domain="admin",
        action="delete",
        risk="critical",
        requested_company_id=7,
        confirmed_mutation=False,
    )

    decision = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador"},
        request,
    )

    assert decision.allowed is False
    assert "confirmação explícita" in decision.reason

    allowed = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(**{**request.__dict__, "confirmed_mutation": True}),
    )
    assert allowed.allowed is True


def test_require_tool_policy_raises_permission_error_with_reason() -> None:
    with pytest.raises(PermissionError, match="surface ops exige administrador técnico"):
        require_tool_policy(
            {"user_id": 2, "company_id": 7, "role": "administrador"},
            ToolPolicyRequest(
                tool_name="inspect_runtime",
                surface="ops",
                domain="diagnostics",
                action="read",
                requested_company_id=7,
            ),
        )
