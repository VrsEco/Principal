from pathlib import Path

from src.intelligence.simulated_agent_harness import (
    SimulatedAgentScenario,
    evaluate_simulated_agent_scenario,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_simulated_agent_harness.md"


def test_simulated_agent_allows_user_surface_for_colaborador_same_tenant():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="user-colab-strategy-read",
            user_id=10,
            role="colaborador",
            surface="user",
            tool_name="list_plans",
            domain="strategy",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    assert result.allowed is True
    assert result.reason == "ok"
    assert result.resolved_surface == "user"
    assert result.resolved_company_id == 21
    assert result.tool_in_surface_manifest is True
    assert "simulated_scope_allowed" in result.checks


def test_simulated_agent_blocks_admin_surface_for_colaborador():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="admin-colab-block",
            user_id=11,
            role="colaborador",
            surface="admin",
            tool_name="update_company_status",
            domain="governance",
            action="update",
            requested_company_id=21,
            accessible_company_ids=(21,),
            risk="high",
            confirmed_mutation=True,
        )
    )

    assert result.allowed is False
    assert "não previsto no playbook" in result.reason or "surface admin não permitida" in result.reason or "surface admin exige" in result.reason
    assert result.resolved_surface == "admin"


def test_simulated_agent_blocks_analytics_mutation():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="analytics-mutation-block",
            user_id=12,
            role="administrador",
            surface="analytics",
            tool_name="get_plan_diagnostics_read_model",
            domain="strategy",
            action="update",
            requested_company_id=21,
            accessible_company_ids=(21, 22),
            confirmed_mutation=True,
        )
    )

    assert result.allowed is False
    assert result.reason == "surface analytics é somente leitura/análise"
    assert "surface_analytics_read_only" in result.checks


def test_simulated_agent_requires_explicit_company_for_admin_multiempresa():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="admin-explicit-company-required",
            user_id=13,
            role="administrador",
            surface="admin",
            tool_name="update_company_status",
            domain="governance",
            action="read",
            requested_company_id=None,
            accessible_company_ids=(21, 22),
        )
    )

    assert result.allowed is False
    assert "company_id" in result.reason
    assert result.runtime_security.tenant_allowed is False or result.policy_decision.allowed is False


def test_simulated_agent_requires_confirmation_for_high_risk_mutation():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="admin-high-risk-confirmation",
            user_id=14,
            role="administrador",
            surface="admin",
            tool_name="update_company_status",
            domain="governance",
            action="update",
            requested_company_id=21,
            accessible_company_ids=(21, 22),
            risk="high",
            confirmed_mutation=False,
        )
    )

    assert result.allowed is False
    assert result.reason == "mutação de alto risco exige confirmação explícita"
    assert "high_risk_mutation_requires_confirmation" in result.checks


def test_simulated_agent_tool_must_exist_in_surface_manifest():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="user-tool-out-of-surface",
            user_id=15,
            role="administrador",
            surface="user",
            tool_name="query_database",
            domain="analytics",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    assert result.allowed is False
    assert result.reason == "domínio analytics não permitido na surface user" or "não pertence ao manifest da surface user" in result.reason


def test_simulated_agent_doc_contains_harness_and_smoke_reference():
    text = DOC.read_text(encoding="utf-8")

    assert "Harness Simulado de Agente para Validação de Escopo" in text
    assert "src.intelligence.simulated_agent_harness" in text
    assert "evaluate_simulated_agent_scenario" in text
    assert "AI_MCP_SIMULATED_HARNESS_OK 6" in text


def test_simulated_agent_summary_contains_policy_and_runtime_metadata():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="summary-shape",
            user_id=16,
            role="administrador",
            surface="analytics",
            tool_name="get_plan_diagnostics_read_model",
            domain="strategy",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    summary = result.to_summary()

    assert summary["scenario_id"] == "summary-shape"
    assert summary["policy"]["tool_name"] == "get_plan_diagnostics_read_model"
    assert summary["runtime_security"]["tenant_allowed"] is True
    assert summary["resolved_company_id"] == 21


def test_simulated_agent_allows_identity_self_service_on_user_surface():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="user-identity-self-service",
            user_id=17,
            role="cliente",
            surface="user",
            tool_name="list_my_companies",
            domain="identity_self_service",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    assert result.allowed is True
    assert result.reason == "ok"


def test_simulated_agent_blocks_runtime_profile_surface_mismatch():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="runtime-profile-surface-mismatch",
            user_id=20,
            role="administrador",
            surface="user",
            tool_name="list_plans",
            domain="strategy",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
            runtime_profile="squad_versus",
        )
    )

    assert result.allowed is False
    assert result.reason == "runtime_profile squad_versus exige surface admin"
    assert "runtime_profile_surface_mismatch" in result.checks


def test_simulated_agent_blocks_when_training_not_completed():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="runtime-profile-training-required",
            user_id=21,
            role="cliente",
            surface="user",
            tool_name="list_my_companies",
            domain="identity_self_service",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
            runtime_profile="squad_cliente",
            mcp_enabled=True,
            training_completed=False,
        )
    )

    assert result.allowed is False
    assert result.reason == "usuário MCP ainda não concluiu habilitação/treinamento obrigatório"
    assert "runtime_profile_training_required" in result.checks


def test_simulated_agent_blocks_identity_admin_on_user_surface():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="user-identity-admin-block",
            user_id=18,
            role="administrador",
            surface="user",
            tool_name="list_system_users",
            domain="identity_admin",
            action="read",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    assert result.allowed is False
    assert "domínio identity_admin não permitido na surface user" in result.reason or "domínio administrativo" in result.reason


def test_simulated_agent_allows_workload_on_ops_for_admin_tecnico():
    result = evaluate_simulated_agent_scenario(
        SimulatedAgentScenario(
            scenario_id="ops-workload-admin-tecnico",
            user_id=19,
            role="admin_tecnico",
            surface="ops",
            tool_name="list_team_workload",
            domain="workload",
            action="analyze",
            requested_company_id=21,
            accessible_company_ids=(21,),
        )
    )

    assert result.allowed is True
    assert result.reason == "ok"
