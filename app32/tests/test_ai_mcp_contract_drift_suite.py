from __future__ import annotations

from dataclasses import dataclass

from src.core.mcp_surface_registry import get_surface_manifest
from src.intelligence.mcp_contracts import (
    APP32_PERMISSION_MATRIX_MANIFEST,
    APP32_PROFILE_CONTRACTS_MANIFEST,
    APP32_SURFACE_PLAYBOOKS_MANIFEST,
)
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolScope
from services.tool_first_catalog_service import ToolFirstCatalogService


@dataclass(frozen=True)
class DriftScenario:
    tool_name: str
    domain: str
    surface: str
    role: str
    action: str
    should_allow: bool
    requested_company_id: int = 7


def _tool_names_for_surface(surface: str) -> set[str]:
    manifest = get_surface_manifest(surface, include_tools=True)
    return {tool["name"] for tool in manifest.get("tools", [])}


def test_contract_drift_surface_playbooks_match_profile_contract_roles():
    for playbook in APP32_SURFACE_PLAYBOOKS_MANIFEST.playbooks:
        allowed_roles = {
            contract.profile
            for contract in APP32_PROFILE_CONTRACTS_MANIFEST.profiles
            if playbook.surface in contract.allowed_surfaces
        }
        assert set(playbook.actor_roles) == allowed_roles


def test_contract_drift_permission_matrix_domains_remain_inside_profile_and_surface_contracts():
    for matrix in APP32_PERMISSION_MATRIX_MANIFEST.matrices:
        profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(matrix.profile)
        surface_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(matrix.surface)

        assert profile_contract is not None
        assert surface_playbook is not None

        matrix_domains = {rule.domain for rule in matrix.domains}
        assert matrix_domains <= set(profile_contract.allowed_domains)
        assert matrix_domains <= set(surface_playbook.allowed_domains)


def test_contract_drift_canonical_capabilities_match_expected_scopes_and_domains():
    expected = {
        "list_my_companies": ("identity_self_service", {ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value}),
        "list_system_users": ("identity_admin", {ToolScope.MCP_ADMIN.value}),
        "register_system_user": ("identity_admin", {ToolScope.MCP_ADMIN.value}),
        "get_team_workload_read_model": ("workload", {ToolScope.MCP_ANALYTICS.value}),
        "list_team_workload": ("workload", {ToolScope.MCP_ANALYTICS.value, ToolScope.MCP_OPS.value}),
        "query_database": ("analytics", {ToolScope.MCP_ANALYTICS.value}),
        "escalate_technical_issue": ("operations", {ToolScope.MCP_OPS.value}),
    }

    for tool_name, (expected_domain, expected_scopes) in expected.items():
        capability = catalog.get_tool_capability(tool_name)
        assert capability is not None
        assert capability.domain == expected_domain
        assert expected_scopes <= set(capability.scopes)


def test_contract_drift_surface_manifests_expose_only_expected_canonical_tools():
    user_tools = _tool_names_for_surface("user")
    admin_tools = _tool_names_for_surface("admin")
    analytics_tools = _tool_names_for_surface("analytics")
    ops_tools = _tool_names_for_surface("ops")

    assert "list_my_companies" in user_tools
    assert "list_my_companies" in admin_tools
    assert "list_system_users" not in user_tools
    assert "list_system_users" in admin_tools
    assert "register_system_user" not in user_tools
    assert "register_system_user" in admin_tools
    assert "get_team_workload_read_model" in analytics_tools
    assert "get_team_workload_read_model" not in ops_tools
    assert "list_team_workload" in analytics_tools
    assert "list_team_workload" in ops_tools
    assert "query_database" in analytics_tools
    assert "query_database" not in user_tools
    assert "query_database" not in admin_tools


def test_contract_drift_policy_matches_canonical_allow_and_deny_scenarios():
    scenarios = [
        DriftScenario(
            tool_name="list_my_companies",
            domain="identity_self_service",
            surface="user",
            role="cliente",
            action="read",
            should_allow=True,
        ),
        DriftScenario(
            tool_name="list_system_users",
            domain="identity_admin",
            surface="user",
            role="administrador",
            action="read",
            should_allow=False,
        ),
        DriftScenario(
            tool_name="get_team_workload_read_model",
            domain="workload",
            surface="analytics",
            role="administrador",
            action="analyze",
            should_allow=True,
        ),
        DriftScenario(
            tool_name="list_team_workload",
            domain="workload",
            surface="ops",
            role="admin_tecnico",
            action="analyze",
            should_allow=True,
        ),
        DriftScenario(
            tool_name="list_team_workload",
            domain="workload",
            surface="analytics",
            role="cliente",
            action="read",
            should_allow=False,
        ),
        DriftScenario(
            tool_name="query_database",
            domain="analytics",
            surface="analytics",
            role="colaborador",
            action="read",
            should_allow=False,
        ),
    ]

    for scenario in scenarios:
        decision = evaluate_tool_policy(
            {"user_id": 10, "company_id": scenario.requested_company_id, "role": scenario.role},
            ToolPolicyRequest(
                tool_name=scenario.tool_name,
                surface=scenario.surface,
                domain=scenario.domain,
                action=scenario.action,
                requested_company_id=scenario.requested_company_id,
            ),
        )
        assert decision.allowed is scenario.should_allow, scenario


def test_contract_drift_workload_and_identity_have_matrix_coverage_on_expected_surfaces():
    admin_analytics = [m for m in APP32_PERMISSION_MATRIX_MANIFEST.get_profile("administrador") if m.surface == "analytics"][0]
    tech_analytics = [m for m in APP32_PERMISSION_MATRIX_MANIFEST.get_profile("admin_tecnico") if m.surface == "analytics"][0]
    tech_ops = [m for m in APP32_PERMISSION_MATRIX_MANIFEST.get_profile("admin_tecnico") if m.surface == "ops"][0]

    assert any(rule.domain == "workload" for rule in admin_analytics.domains)
    assert any(rule.domain == "workload" for rule in tech_analytics.domains)
    assert any(rule.domain == "workload" for rule in tech_ops.domains)
    assert all(rule.domain != "identity_admin" for matrix in APP32_PERMISSION_MATRIX_MANIFEST.matrices for rule in matrix.domains)


def test_contract_drift_tool_first_catalog_references_only_published_capabilities_or_planned_backlog():
    payload = ToolFirstCatalogService.build_catalog(None)
    published_capability_names = {tool["name"] for tool in catalog.get_capability_manifest(include_tools=True).get("tools", [])}

    for domain in payload["domains"]:
        for tool in domain["published_tools"]:
            assert tool["name"] in published_capability_names
        for planned in domain["planned_tools"]:
            assert planned["name"] not in {tool["name"] for tool in domain["published_tools"]}
