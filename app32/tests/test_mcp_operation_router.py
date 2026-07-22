from datetime import date

import src.core.mcp_operation_router_tools as router_tools
import src.core.mcp_surface_registry as surface_registry
from services.mcp_operation_router_service import McpOperationRouterService
from src.core.mcp_runtime import MCPExecutionContext


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


def test_routes_payables_next_week_without_catalog_crawl():
    result = McpOperationRouterService.resolve(
        request_text="Quanto temos de contas a pagar para a próxima semana?",
        company_id=1,
        current_harness_key="harness_coordenador_cliente_v1",
        reference_date=date(2026, 7, 18),
    )
    assert result["route_status"] == "ready"
    assert result["domain"] == "finance"
    assert result["target_harness_key"] == "harness_admfin_cliente_v1"
    assert result["preferred_tool"] == "get_financial_payables_due_summary"
    assert result["arguments"] == {
        "company_id": 1,
        "due_date_from": "2026-07-20",
        "due_date_to": "2026-07-26",
    }
    assert result["execution_sequence"] == [
        "select_app32_session_harness_tool",
        "get_financial_payables_due_summary",
    ]


def test_routes_cross_domain_requests_to_single_preferred_tool():
    cases = (
        ("Mostre a hierarquia de processos", "processes", "list_process_hierarchy", "harness_operacional_cliente_v1"),
        ("Quais projetos estão em andamento?", "projects", "list_projects", "harness_operacional_cliente_v1"),
        ("Mostre o planejamento estratégico", "strategy", "list_plans", "harness_coordenador_cliente_v1"),
        ("Como estão nossas vendas?", "strategy", "get_commercial_dashboard", "harness_comercial_cliente_v1"),
    )
    for request, domain, tool, harness in cases:
        result = McpOperationRouterService.resolve(
            request_text=request,
            company_id=9,
            current_harness_key="harness_coordenador_cliente_v1",
            reference_date=date(2026, 7, 18),
        )
        assert result["route_status"] == "ready"
        assert result["domain"] == domain
        expected_business_area = "commercial" if tool == "get_commercial_dashboard" else domain
        assert result["business_area"] == expected_business_area
        assert result["preferred_tool"] == tool
        assert result["target_harness_key"] == harness


def test_unknown_request_returns_fast_fallback_without_discovery():
    result = McpOperationRouterService.resolve(
        request_text="Quero discutir uma hipótese completamente nova",
        company_id=9,
        current_harness_key="harness_coordenador_cliente_v1",
    )
    assert result["route_status"] == "unsupported_fast_fallback"
    assert result["preferred_tool"] is None
    assert "Não varrer catálogos" in result["discovery_policy"]


def test_router_tool_uses_active_tenant_and_rejects_cross_tenant(monkeypatch):
    monkeypatch.setattr(
        router_tools,
        "get_http_request_context",
        lambda: {
            "user_id": 7,
            "company_id": 1,
            "accessible_company_ids": [1, 9],
            "harness_key": "harness_coordenador_cliente_v1",
        },
    )
    mcp = _FakeMCP()
    router_tools.register_operation_router_tools(mcp)
    ok = mcp.registered["resolve_app32_operation_tool"](
        request_text="Quais projetos estão em andamento?",
        company_id=1,
        reference_date="2026-07-18",
    )
    assert ok["success"] is True
    assert ok["data"]["company_id"] == 1
    denied = mcp.registered["resolve_app32_operation_tool"](
        request_text="Quais projetos estão em andamento?",
        company_id=6,
    )
    assert denied["success"] is False
    assert denied["error"]["code"] == "mcp_operation_company_forbidden"


def test_known_capability_gap_does_not_guess_or_refresh_catalog():
    result = McpOperationRouterService.resolve(
        request_text="Qual é o saldo bancário consolidado?",
        company_id=1,
        current_harness_key="harness_coordenador_cliente_v1",
        reference_date=date(2026, 7, 18),
    )
    assert result["route_status"] == "capability_not_available"
    assert result["domain"] == "finance"
    assert result["business_area"] == "finance"
    assert result["target_harness_key"] == "harness_admfin_cliente_v1"
    assert result["preferred_tool"] is None
    assert result["execution_sequence"] == []
    assert "Não atualizar tools/list" in result["discovery_policy"]


def test_routes_known_domain_to_safe_specialist_discovery():
    result = McpOperationRouterService.resolve(
        request_text="Qual é a margem financeira por unidade?",
        company_id=1,
        current_harness_key="harness_coordenador_cliente_v1",
    )
    assert result["route_status"] == "specialist_discovery"
    assert result["domain"] == "finance"
    assert result["target_harness_key"] == "harness_admfin_cliente_v1"
    assert result["execution_sequence"] == ["select_app32_session_harness_tool"]
    assert result["candidate_execution_policy"] == "exact_semantic_match_required"
    assert result["on_no_exact_match"] == "capability_not_available"


def test_payables_without_period_requests_only_missing_input():
    result = McpOperationRouterService.resolve(
        request_text="Quanto temos de contas a pagar?",
        company_id=1,
        current_harness_key="harness_admfin_cliente_v1",
        reference_date=date(2026, 7, 18),
    )
    assert result["route_status"] == "needs_input"
    assert result["missing_arguments"] == ["due_date_from", "due_date_to"]
    assert result["execution_sequence"] == []
    assert "período" in result["user_message"]


def test_process_runtime_route_uses_company_scope_contract():
    result = McpOperationRouterService.resolve(
        request_text="Quais processos estão em andamento?",
        company_id=9,
        current_harness_key="harness_operacional_cliente_v1",
    )
    assert result["preferred_tool"] == "get_my_work"
    assert result["arguments"] == {"scope": "company", "company_ids": "9"}


def test_routes_mission_maturity_to_next_action_engine():
    result = McpOperationRouterService.resolve(
        request_text="Qual é o próximo passo da missão?",
        company_id=9,
        current_harness_key="harness_coordenador_cliente_v1",
    )

    assert result["route_status"] == "ready"
    assert result["domain"] == "consultive"
    assert result["preferred_tool"] == "consultive_get_next_action"
    assert result["arguments"] == {
        "company_id": 9,
        "front_key": "identity",
        "subphase_key": "mission",
    }


def _squad_cliente_context(*, permissions=("strategy.alignment.read",)):
    return MCPExecutionContext(
        user_id=44,
        company_id=13,
        employee_id=None,
        role="cliente",
        channel="claude_code",
        thread_id="thread-squad-cliente",
        accessible_company_ids=(13,),
        permissions=permissions,
        metadata={
            "surface": "user",
            "runtime_profile": "squad_cliente",
            "actor_type": "client_agent",
            "harness_key": "harness_coordenador_cliente_v1",
            "mcp_enabled": True,
            "training_completed": True,
        },
    )


def test_strategy_metrics_route_is_ready_published_and_overlay_executable(monkeypatch):
    context = _squad_cliente_context()
    monkeypatch.setattr(
        router_tools,
        "get_http_request_context",
        lambda: {
            "user_id": 44,
            "company_id": 13,
            "accessible_company_ids": [13],
            "surface": "user",
            "harness_key": "harness_coordenador_cliente_v1",
        },
    )
    monkeypatch.setattr(router_tools, "resolve_mcp_execution_context", lambda payload: context)
    monkeypatch.setattr(surface_registry, "resolve_mcp_execution_context", lambda payload: context)
    mcp = _FakeMCP()
    router_tools.register_operation_router_tools(mcp)

    routed = mcp.registered["resolve_app32_operation_tool"](
        request_text="Consultar conexões e métricas estratégicas de objetivos e indicadores",
        company_id=13,
    )
    manifest = surface_registry.get_surface_manifest("user", include_tools=True)
    capability = next(
        item for item in manifest["tools"] if item["name"] == "get_strategic_connection_metrics"
    )

    assert routed["success"] is True
    assert routed["data"]["route_status"] == "ready"
    assert routed["data"]["preferred_tool"] == "get_strategic_connection_metrics"
    assert routed["data"]["target_harness_key"] == "harness_coordenador_cliente_v1"
    assert routed["data"]["harness_switch_required"] is False
    assert routed["data"]["execution_sequence"] == ["get_strategic_connection_metrics"]
    assert routed["data"]["capability_state"] == "executable_in_effective_catalog"
    assert capability["domain"] == "strategy"
    assert capability["permissions"] == ["strategy.alignment.read"]
    assert capability["risk"] == "low"
    assert capability["human_gate"] is False


def test_sector_structure_mutation_routes_to_published_human_gated_tool(monkeypatch):
    context = _squad_cliente_context(
        permissions=("okrs.area.create", "okrs.key_results.create", "project.create")
    )
    monkeypatch.setattr(
        router_tools,
        "get_http_request_context",
        lambda: {
            "user_id": 44,
            "company_id": 13,
            "accessible_company_ids": [13],
            "surface": "user",
            "harness_key": "harness_operacional_cliente_v1",
        },
    )
    monkeypatch.setattr(router_tools, "resolve_mcp_execution_context", lambda payload: context)
    monkeypatch.setattr(surface_registry, "resolve_mcp_execution_context", lambda payload: context)
    mcp = _FakeMCP()
    router_tools.register_operation_router_tools(mcp)

    routed = mcp.registered["resolve_app32_operation_tool"](
        request_text="Cadastrar a estrutura setorial com dois OKRs setoriais, resultados-chave propostos e projetos",
        company_id=13,
    )
    manifest = surface_registry.get_surface_manifest("user", include_tools=True)
    capability = next(item for item in manifest["tools"] if item["name"] == "create_sector_okr_structure_tool")

    assert routed["data"]["route_status"] == "ready"
    assert routed["data"]["preferred_tool"] == "create_sector_okr_structure_tool"
    assert routed["data"]["action"] == "create"
    assert routed["data"]["risk"] == "medium"
    assert routed["data"]["human_gate_required"] is True
    assert routed["data"]["target_harness_key"] == "harness_coordenador_cliente_v1"
    assert routed["data"]["harness_switch_required"] is True
    assert routed["data"]["execution_sequence"] == [
        "select_app32_session_harness_tool",
        "create_sector_okr_structure_tool",
    ]
    assert capability["domain"] == "strategy"
    assert capability["permissions"] == ["okrs.area.create", "okrs.key_results.create", "project.create"]
    assert capability["human_gate"] is True


def test_router_never_returns_ready_when_capability_is_not_effectively_available(monkeypatch):
    context = _squad_cliente_context()
    monkeypatch.setattr(
        router_tools,
        "get_http_request_context",
        lambda: {
            "user_id": 44,
            "company_id": 13,
            "accessible_company_ids": [13],
            "surface": "user",
            "harness_key": "harness_coordenador_cliente_v1",
        },
    )
    monkeypatch.setattr(router_tools, "resolve_mcp_execution_context", lambda payload: context)
    monkeypatch.setattr(
        surface_registry,
        "get_surface_capability_status",
        lambda *args, **kwargs: {
            "executable": False,
            "reason": "tool ausente ou bloqueada no runtime efetivo",
        },
    )
    mcp = _FakeMCP()
    router_tools.register_operation_router_tools(mcp)

    routed = mcp.registered["resolve_app32_operation_tool"](
        request_text="Consultar métricas estratégicas dos indicadores",
        company_id=13,
    )

    assert routed["data"]["route_status"] == "capability_not_available"
    assert routed["data"]["preferred_tool"] is None
    assert routed["data"]["execution_sequence"] == []
    assert routed["data"]["blocked_preferred_tool"] == "get_strategic_connection_metrics"
