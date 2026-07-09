from __future__ import annotations

import pytest

from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy, require_tool_policy
from src.intelligence.tooling.capabilities import infer_tool_action


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
    with pytest.raises(PermissionError, match="surface ops não permitida para o perfil administrador"):
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


def test_tool_policy_blocks_cliente_from_admin_surface() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 3, "company_id": 7, "role": "cliente"},
        ToolPolicyRequest(
            tool_name="list_system_users",
            surface="admin",
            domain="admin",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is False
    assert "surface admin não permitida" in decision.reason
    assert "surface_not_allowed_for_profile" in decision.checks


def test_tool_policy_allows_admin_tecnico_on_ops_surface() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 4, "company_id": 7, "role": "admin_tecnico"},
        ToolPolicyRequest(
            tool_name="escalate_technical_issue",
            surface="ops",
            domain="diagnostics",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is True


def test_tool_policy_allows_identity_self_service_on_user_surface() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 5, "company_id": 7, "role": "cliente"},
        ToolPolicyRequest(
            tool_name="list_my_companies",
            surface="user",
            domain="identity_self_service",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is True


def test_tool_policy_blocks_identity_admin_on_user_surface() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 6, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="list_system_users",
            surface="user",
            domain="identity_admin",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is False
    assert "surface user não expõe domínio administrativo" in decision.reason
    assert "surface_user_blocks_admin_domain" in decision.checks


def test_tool_policy_allows_workload_for_admin_on_analytics() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 7, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_team_workload_read_model",
            surface="analytics",
            domain="workload",
            action="analyze",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is True


def test_tool_policy_allows_routine_queries_for_supported_user_profiles() -> None:
    for role in ("colaborador", "cliente", "administrador"):
        decision = evaluate_tool_policy(
            {"user_id": 8, "company_id": 7, "role": role},
            ToolPolicyRequest(
                tool_name="get_my_work",
                surface="user",
                domain="routine",
                action="read",
                requested_company_id=7,
            ),
        )
        assert decision.allowed is True, role


def test_tool_policy_normalizes_legacy_work_alias_into_routine() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 9, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_my_work",
            surface="user",
            domain="work",
            action="read",
            requested_company_id=7,
        ),
    )

    assert decision.allowed is True


def test_tool_policy_allows_user_only_feature_without_company_context() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 12, "company_id": None, "role": "colaborador"},
        ToolPolicyRequest(
            tool_name="get_my_work",
            surface="user",
            domain="routine",
            action="read",
            required_context=("user",),
        ),
    )

    assert decision.allowed is True
    assert decision.resolved_company_id is None
    assert "tenant_scope_not_required" in decision.checks


def test_tool_policy_blocks_company_required_feature_without_company_context() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 12, "company_id": None, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="list_process_hierarchy",
            surface="user",
            domain="processes",
            action="read",
            required_context=("company",),
        ),
    )

    assert decision.allowed is False
    assert "feature exige company_id" in decision.reason
    assert "missing_required_company_context" in decision.checks


def test_tool_policy_allows_company_only_feature_without_user_context() -> None:
    decision = evaluate_tool_policy(
        {"user_id": None, "company_id": 7, "role": "administrador"},
        ToolPolicyRequest(
            tool_name="get_financial_results",
            surface="admin",
            domain="finance",
            action="read",
            requested_company_id=7,
            required_context=("company",),
        ),
    )

    assert decision.allowed is True
    assert decision.resolved_company_id == 7


def test_tool_policy_blocks_domain_outside_squad_cliente_overlay() -> None:
    decision = evaluate_tool_policy(
        {
            "user_id": 20,
            "company_id": 7,
            "role": "colaborador",
            "metadata": {"harness_key": "harness_comercial_cliente_v1"},
        },
        ToolPolicyRequest(
            tool_name="list_process_hierarchy",
            surface="user",
            domain="processes",
            action="read",
            requested_company_id=7,
            metadata={"harness_key": "harness_comercial_cliente_v1"},
        ),
    )

    assert decision.allowed is False
    assert "overlay comercial_cliente não permite o domínio processes" == decision.reason
    assert "runtime_overlay_domain_blocked" in decision.checks


def test_tool_policy_blocks_action_outside_squad_cliente_overlay() -> None:
    decision = evaluate_tool_policy(
        {
            "user_id": 21,
            "company_id": 7,
            "role": "administrador",
            "metadata": {"harness_key": "harness_admfin_cliente_v1"},
        },
        ToolPolicyRequest(
            tool_name="delete_project_task",
            surface="user",
            domain="projects",
            action="delete",
            requested_company_id=7,
            metadata={"harness_key": "harness_admfin_cliente_v1"},
        ),
    )

    assert decision.allowed is False
    assert "overlay admfin_cliente não permite a ação delete" == decision.reason
    assert "runtime_overlay_action_blocked" in decision.checks


def test_tool_policy_allows_strategy_maturation_review_for_cliente_harness() -> None:
    action = infer_tool_action("review_strategy_maturation_item_tool", "strategy")

    decision = evaluate_tool_policy(
        {
            "user_id": 22,
            "company_id": 1,
            "role": "cliente",
            "metadata": {
                "runtime_profile": "squad_cliente",
                "actor_type": "client_agent",
                "harness_key": "harness_coordenador_cliente_v1",
            },
        },
        ToolPolicyRequest(
            tool_name="review_strategy_maturation_item_tool",
            surface="user",
            domain="strategy",
            action=action,
            risk="medium",
            requested_company_id=1,
            required_permissions=("strategy.maturation.review",),
            required_context=("user", "company"),
            metadata={"harness_key": "harness_coordenador_cliente_v1"},
        ),
    )

    assert action == "review"
    assert decision.allowed is True
    assert decision.resolved_surface == "user"
    assert decision.resolved_company_id == 1


def test_tool_policy_allows_strategy_maturation_review_for_estrategico_cliente_overlay() -> None:
    decision = evaluate_tool_policy(
        {
            "user_id": 23,
            "company_id": 1,
            "role": "cliente",
            "metadata": {
                "runtime_profile": "squad_cliente",
                "actor_type": "client_agent",
                "harness_key": "harness_estrategico_cliente_v1",
            },
        },
        ToolPolicyRequest(
            tool_name="review_strategy_maturation_item_tool",
            surface="user",
            domain="strategy",
            action=infer_tool_action("review_strategy_maturation_item_tool", "strategy"),
            risk="medium",
            requested_company_id=1,
            required_permissions=("strategy.maturation.review",),
            required_context=("user", "company"),
            metadata={"harness_key": "harness_estrategico_cliente_v1"},
        ),
    )

    assert decision.allowed is True


def test_tool_policy_allows_identity_self_service_without_selected_company_even_with_accessible_companies() -> None:
    decision = evaluate_tool_policy(
        {"user_id": 5, "company_id": None, "role": "cliente"},
        ToolPolicyRequest(
            tool_name="list_my_companies",
            surface="user",
            domain="identity_self_service",
            action="read",
            accessible_company_ids=(7, 8),
            required_context=("user",),
        ),
    )

    assert decision.allowed is True
    assert decision.resolved_company_id is None
    assert "tenant_scope_not_required" in decision.checks


def test_tool_policy_blocks_strategy_maturation_review_without_selected_company() -> None:
    decision = evaluate_tool_policy(
        {
            "user_id": 24,
            "company_id": None,
            "role": "cliente",
            "metadata": {
                "runtime_profile": "squad_cliente",
                "actor_type": "client_agent",
                "harness_key": "harness_coordenador_cliente_v1",
                "multi_company": True,
            },
        },
        ToolPolicyRequest(
            tool_name="review_strategy_maturation_item_tool",
            surface="user",
            domain="strategy",
            action=infer_tool_action("review_strategy_maturation_item_tool", "strategy"),
            risk="medium",
            required_permissions=("strategy.maturation.review",),
            required_context=("user", "company"),
            metadata={
                "harness_key": "harness_coordenador_cliente_v1",
                "multi_company": True,
            },
        ),
    )

    assert decision.allowed is False
    assert "empresa não selecionada" in decision.reason
    assert "missing_required_company_context" in decision.checks
