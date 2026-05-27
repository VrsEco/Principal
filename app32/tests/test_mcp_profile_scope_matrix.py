from src.intelligence.mcp_contracts import (
    APP32_CRUD_CONTRACTS_MANIFEST,
    APP32_SURFACE_PLAYBOOKS_MANIFEST,
)
from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolScope


def test_user_playbook_profiles_are_restricted_to_operational_roles():
    playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("user")

    assert playbook is not None
    assert set(playbook.actor_roles) == {"colaborador", "cliente", "administrador"}
    assert "admin_tecnico" not in playbook.actor_roles
    assert "finance" in playbook.allowed_domains
    assert any(item.overlay == "coordenador_cliente" for item in playbook.role_overlays)
    assert any(item.overlay == "admfin_cliente" for item in playbook.role_overlays)


def test_admin_analytics_and_ops_playbooks_are_restricted_to_admin_profiles():
    admin = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("admin")
    analytics = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("analytics")
    ops = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("ops")

    assert admin is not None
    assert analytics is not None
    assert ops is not None

    for playbook in (admin, analytics):
        assert set(playbook.actor_roles) == {"administrador", "admin_tecnico"}
        assert "colaborador" not in playbook.actor_roles
        assert "cliente" not in playbook.actor_roles

    assert set(ops.actor_roles) == {"admin_tecnico"}
    assert "administrador" not in ops.actor_roles
    assert "colaborador" not in ops.actor_roles
    assert "cliente" not in ops.actor_roles


def test_finance_contract_is_permission_aware_on_user_and_admin_gated_on_delete():
    finance = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("finance")
    user = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("user")

    assert finance is not None
    assert user is not None

    create_or_update = [operation for operation in finance.operations if operation.action in {"create", "update"}]
    delete_ops = [operation for operation in finance.operations if operation.action == "delete"]
    assert create_or_update
    assert delete_ops
    for operation in create_or_update:
        assert "colaborador" in operation.allowed_roles
        assert operation.human_gate_required is False
        assert operation.surface == "mcp_user"
    for operation in delete_ops:
        assert set(operation.allowed_roles) == {"administrador", "admin_tecnico"}
        assert operation.human_gate_required is True
        assert operation.surface == "mcp_admin"

    assert "finance" in user.allowed_domains


def test_strategy_contract_and_capability_are_gated_and_surface_aligned():
    strategy = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("strategy")
    assert strategy is not None

    update_ops = [operation for operation in strategy.operations if operation.action == "update"]
    analyze_ops = [operation for operation in strategy.operations if operation.action == "analyze"]
    assert update_ops
    assert analyze_ops
    assert all(operation.human_gate_required is True for operation in update_ops)
    assert all(operation.surface == "mcp_admin" for operation in update_ops)
    assert all(operation.surface == "mcp_analytics" for operation in analyze_ops)

    capability = catalog.get_tool_capability("update_plan_section")
    diagnostics_capability = catalog.get_tool_capability("get_plan_diagnostics")
    assert capability is not None
    assert diagnostics_capability is not None
    assert capability.human_gate is True
    assert diagnostics_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value)


def test_capability_scopes_match_expected_surfaces_by_profile():
    query_capability = catalog.get_tool_capability("query_database")
    escalation_capability = catalog.get_tool_capability("escalate_technical_issue")
    plan_capability = catalog.get_tool_capability("get_plan_diagnostics")
    user_listing_capability = catalog.get_tool_capability("list_system_users")
    workload_capability = catalog.get_tool_capability("get_team_workload_read_model")

    assert query_capability is not None
    assert escalation_capability is not None
    assert plan_capability is not None
    assert user_listing_capability is not None
    assert workload_capability is not None

    assert query_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value)
    assert escalation_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_OPS.value)
    assert plan_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value)
    assert user_listing_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value)
    assert workload_capability.scopes == (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value)


def test_customer_profile_only_appears_in_read_or_operational_non_sensitive_contracts():
    customer_allowed = []
    for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains:
        for operation in contract.operations:
            if "cliente" in operation.allowed_roles:
                customer_allowed.append((contract.domain, operation.action, operation.surface))

    assert customer_allowed
    assert all(surface == "mcp_user" for _, _, surface in customer_allowed)
    assert all(action in {"read", "list", "analyze"} for _, action, _ in customer_allowed)
