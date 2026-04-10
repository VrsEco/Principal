from __future__ import annotations

from src.intelligence.mcp_contracts import APP32_ALLOWED_ANALYSIS_CATALOG
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy


def test_allowed_analysis_catalog_never_allows_cross_tenant_or_sql_freeform():
    for analysis in APP32_ALLOWED_ANALYSIS_CATALOG.analyses:
        assert analysis.cross_tenant_allowed is False
        assert analysis.sql_freeform_allowed is False
        assert analysis.requires_explicit_company_id is True
        assert "analytics" in analysis.allowed_surfaces


def test_tool_policy_blocks_cross_tenant_analytics_even_for_admin_profile():
    decision = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_projects_execution_risk_read_model",
            surface="analytics",
            domain="projects",
            action="read",
            risk="medium",
            requested_company_id=8,
            accessible_company_ids=(7,),
        ),
    )

    assert decision.allowed is False
    assert "escopo" in decision.reason
    assert "requested_company_mismatch" in decision.checks


def test_tool_policy_allows_analytics_read_for_admin_when_company_is_accessible():
    decision = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_projects_execution_risk_read_model",
            surface="analytics",
            domain="projects",
            action="read",
            risk="medium",
            requested_company_id=8,
            accessible_company_ids=(8,),
        ),
    )

    assert decision.allowed is True
    assert decision.resolved_surface == "analytics"
    assert decision.resolved_company_id == 8


def test_tool_policy_blocks_analytics_mutation_even_for_admin_profile():
    decision = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_projects_execution_risk_read_model",
            surface="analytics",
            domain="projects",
            action="update",
            risk="medium",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is False
    assert "somente leitura" in decision.reason
    assert "surface_analytics_read_only" in decision.checks


def test_tool_policy_blocks_non_admin_profile_from_analytics_surface_before_read_model():
    decision = evaluate_tool_policy(
        {"user_id": 2, "company_id": 7, "role": "colaborador"},
        ToolPolicyRequest(
            tool_name="get_team_workload_read_model",
            surface="analytics",
            domain="workload",
            action="read",
            risk="low",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is False
    assert "surface analytics não permitida" in decision.reason
    assert "surface_not_allowed_for_profile" in decision.checks
