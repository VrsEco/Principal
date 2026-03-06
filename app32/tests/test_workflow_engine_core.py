from datetime import date

from models.agent_menu import AgentMenuOption
from src.intelligence.workflows.contracts import WorkflowDiscoveryRequest, WorkflowMatch
from src.intelligence.workflows.matcher import (
    HybridWorkflowMatcher,
    LexicalWorkflowMatcher,
    SemanticWorkflowMatcher,
)
from src.intelligence.workflows.evaluation import (
    WorkflowEvaluationCase,
    evaluate_workflow_discovery,
)
from src.intelligence.workflows.registry import WorkflowRegistry
from src.intelligence.workflows.reranker import HeuristicWorkflowReranker
from src.intelligence.workflows.runtime import WorkflowRuntime
from src.intelligence.workflows.semantic_index import WorkflowSemanticIndex
from src.intelligence.workflows.session import WorkflowSessionState
from src.intelligence.workflows.summary import (
    SUMMARY_ROUTE_PROMPT_COLLABORATOR,
    SUMMARY_ROUTE_PROMPT_COMPANY,
    SUMMARY_ROUTE_PROMPT_DATES,
    SUMMARY_STATUS_AWAITING_DATES,
    SummaryWorkflowCoordinator,
)


def _option(
    *,
    option_id: int,
    code: str,
    title: str,
    action_key: str | None = None,
    keywords: list[str] | None = None,
    company_id: int | None = None,
    sort_order: int = 0,
    description: str | None = None,
):
    return AgentMenuOption(
        id=option_id,
        company_id=company_id,
        code=code,
        title=title,
        action_key=action_key,
        description=description,
        keywords=keywords or [],
        required_fields=[],
        sort_order=sort_order,
        is_active=True,
    )


def test_registry_prefers_company_specific_workflow_and_ignores_navigation_nodes():
    options = [
        _option(option_id=1, code="3.5", title="Resumos", action_key=None, sort_order=10),
        _option(
            option_id=2,
            company_id=None,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo semana"],
            sort_order=11,
        ),
        _option(
            option_id=3,
            company_id=9,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo da semana"],
            sort_order=11,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options, preferred_company_id=9)

    workflows = registry.list()
    assert len(workflows) == 1
    assert workflows[0].code == "3.5.2"
    assert workflows[0].company_id == 9
    assert workflows[0].source_option_id == 3


def test_lexical_matcher_prioritizes_summary_week_for_resumo_da_semana():
    options = [
        _option(
            option_id=10,
            code="3.5.1",
            title="Hoje",
            action_key="summary.today",
            keywords=["resumo hoje", "resumo do dia"],
            sort_order=10,
        ),
        _option(
            option_id=11,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo semana", "resumo da semana"],
            sort_order=11,
        ),
        _option(
            option_id=12,
            code="3.5.3",
            title="Este Mes",
            action_key="summary.month",
            keywords=["resumo mes", "resumo do mes"],
            sort_order=12,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matcher = LexicalWorkflowMatcher()

    matches = matcher.match_menu_options(
        text="quero um resumo da semana da equipe",
        registry=registry,
        top_k=3,
    )

    assert matches
    assert matches[0].workflow.action_key == "summary.week"
    assert matches[0].score > 0


def test_lexical_matcher_prioritizes_project_task_create_for_cadastro():
    options = [
        _option(
            option_id=20,
            code="1.4",
            title="Cadastrar Atividade de Projeto",
            action_key="project_task.create",
            keywords=["cadastrar atividade", "nova atividade de projeto"],
            sort_order=14,
        ),
        _option(
            option_id=21,
            code="1.6",
            title="Editar Atividade de Projeto",
            action_key="project_task.update",
            keywords=["editar atividade", "alterar atividade de projeto"],
            sort_order=16,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matcher = LexicalWorkflowMatcher()

    matches = matcher.match_menu_options(
        text="preciso cadastrar uma nova atividade de projeto",
        registry=registry,
        top_k=2,
    )

    assert matches[0].workflow.action_key == "project_task.create"


def test_workflow_runtime_supports_explicit_code_discovery():
    options = [
        _option(
            option_id=30,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo semana"],
            sort_order=37,
        ),
        _option(
            option_id=31,
            code="3.5.4",
            title="Personalizado",
            action_key="summary.custom",
            keywords=["resumo personalizado"],
            sort_order=39,
        ),
    ]

    runtime = WorkflowRuntime()
    result = runtime.discover_from_menu_options(
        text="executar 3.5.2",
        options=options,
        preferred_company_id=None,
        top_k=2,
    )

    assert result.selected is not None
    assert result.selected.code == "3.5.2"


def test_semantic_matcher_recovers_operational_readiness_intent_from_description():
    options = [
        _option(
            option_id=32,
            code="4.3",
            title="Go Live Check",
            action_key="onboarding.go_live_check",
            keywords=["go live", "check operacional"],
            description="Verificar se a empresa esta pronta para operar e entrar em producao.",
            sort_order=43,
        ),
        _option(
            option_id=33,
            code="4.1",
            title="Status do Onboarding",
            action_key="onboarding.status",
            keywords=["status onboarding"],
            description="Mostrar o status do cadastro da empresa.",
            sort_order=41,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matcher = SemanticWorkflowMatcher()

    result = matcher.discover(
        request=WorkflowDiscoveryRequest(
            text="quero saber se a empresa esta pronta para operar",
            top_k=2,
        ),
        registry=registry,
    )

    assert result.selected is not None
    assert result.selected.action_key == "onboarding.go_live_check"
    assert any(
        reason.startswith("semantic_roots:")
        for reason in result.matches[0].reasons
    )


class _PromoteCustomSummaryReranker:
    def rerank(self, request, matches, registry):
        ordered = list(matches)
        if len(ordered) < 2:
            return ordered

        promoted = []
        deferred = []
        for match in ordered:
            if match.workflow.action_key == "summary.custom":
                promoted.append(
                    WorkflowMatch(
                        workflow=match.workflow,
                        score=match.score + 25,
                        reasons=[*match.reasons, "reranker:promoted_for_custom_period"],
                    )
                )
            else:
                deferred.append(match)
        return promoted + deferred


def test_hybrid_matcher_supports_optional_reranker_on_top_candidates():
    options = [
        _option(
            option_id=34,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo da semana", "semana"],
            description="Gerar resumo semanal das atividades.",
            sort_order=35,
        ),
        _option(
            option_id=35,
            code="3.5.4",
            title="Personalizado",
            action_key="summary.custom",
            keywords=["resumo personalizado", "periodo customizado"],
            description="Gerar resumo para um periodo customizado informado pelo usuario.",
            sort_order=37,
        ),
    ]

    runtime = WorkflowRuntime(
        matcher=HybridWorkflowMatcher(reranker=_PromoteCustomSummaryReranker())
    )
    result = runtime.discover_from_menu_options(
        text="quero um resumo da semana mas com periodo personalizado",
        options=options,
        top_k=2,
    )

    assert result.selected is not None
    assert result.selected.action_key == "summary.custom"
    assert any(
        reason == "reranker:promoted_for_custom_period"
        for reason in result.matches[0].reasons
    )


def test_registry_builds_semantic_index_once_and_reuses_instance():
    options = [
        _option(
            option_id=36,
            code="4.4",
            title="Diagnostico do Onboarding",
            action_key="onboarding.diagnose",
            keywords=["diagnostico onboarding"],
            description="Diagnosticar gargalos e pendencias para a operacao.",
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    index_a = registry.semantic_index()
    index_b = registry.semantic_index()

    assert isinstance(index_a, WorkflowSemanticIndex)
    assert index_a is index_b
    profile = index_a.get("4.4")
    assert profile is not None
    assert any(
        "gargalos e pendencias para a operacao" in fragment.lower()
        for fragment in profile.fragments
    )


def test_runtime_reuses_cached_registry_for_same_catalog_snapshot():
    options = [
        _option(
            option_id=37,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo da semana"],
        ),
        _option(
            option_id=38,
            code="3.5.4",
            title="Personalizado",
            action_key="summary.custom",
            keywords=["resumo personalizado"],
        ),
    ]

    runtime = WorkflowRuntime()

    registry_a = runtime.resolve_registry_from_menu_options(options)
    registry_b = runtime.resolve_registry_from_menu_options(options)

    assert registry_a is registry_b


def test_heuristic_reranker_prioritizes_custom_summary_when_dates_are_explicit():
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="quero resumo de 01/03/2026 a 07/03/2026",
        top_k=2,
    )
    registry = WorkflowRegistry.from_menu_options(
        [
            _option(
                option_id=39,
                code="3.5.2",
                title="Esta Semana",
                action_key="summary.week",
            ),
            _option(
                option_id=40,
                code="3.5.4",
                title="Personalizado",
                action_key="summary.custom",
            ),
        ]
    )
    summary_week = registry.get_by_code("3.5.2")
    summary_custom = registry.get_by_code("3.5.4")
    assert summary_week is not None
    assert summary_custom is not None
    matches = [
        WorkflowMatch(
            workflow=summary_week,
            score=20,
            reasons=["lexical:title_phrase:esta semana"],
        ),
        WorkflowMatch(
            workflow=summary_custom,
            score=18,
            reasons=["semantic:semantic_similarity_medium:personalizado"],
        ),
    ]

    reranked = list(
        reranker.rerank(
            request=request,
            matches=matches,
            registry=registry,
        )
    )

    assert reranked[0].workflow.action_key == "summary.custom"
    assert any(reason == "reranker:summary_period=custom" for reason in reranked[0].reasons)


def test_workflow_runtime_exposes_discovery_telemetry():
    options = [
        _option(
            option_id=41,
            code="4.3",
            title="Go Live Check",
            action_key="onboarding.go_live_check",
            keywords=["go live", "pronto para operar"],
            description="Verificar se a empresa esta pronta para operar.",
        ),
        _option(
            option_id=42,
            code="4.4",
            title="Diagnostico do Onboarding",
            action_key="onboarding.diagnose",
            keywords=["diagnostico onboarding"],
            description="Diagnosticar gargalos e pendencias da operacao.",
        ),
    ]

    runtime = WorkflowRuntime()
    result = runtime.discover_from_menu_options(
        text="quero saber se a empresa esta pronta para operar",
        options=options,
        top_k=2,
    )

    assert result.telemetry["strategy"] == "hybrid"
    assert result.telemetry["semantic_match_count"] >= 1
    assert len(result.telemetry["final_top_matches"]) >= 1
    assert result.telemetry["selected_action_key"] == "onboarding.go_live_check"
    assert isinstance(result.telemetry["reranker_deltas"], list)


def test_workflow_runtime_accepts_callable_reranker_adapter():
    options = [
        _option(
            option_id=43,
            code="3.5.2",
            title="Esta Semana",
            action_key="summary.week",
            keywords=["resumo semana"],
        ),
        _option(
            option_id=44,
            code="3.5.4",
            title="Personalizado",
            action_key="summary.custom",
            keywords=["resumo personalizado"],
        ),
    ]

    def _callable_reranker(request, matches, registry):
        del request, registry
        ordered = list(matches)
        return sorted(
            ordered,
            key=lambda match: 0 if match.workflow.action_key == "summary.custom" else 1,
        )

    runtime = WorkflowRuntime(rerank_callable=_callable_reranker)
    result = runtime.discover_from_menu_options(
        text="resumo personalizado da equipe",
        options=options,
        top_k=2,
    )

    assert result.selected is not None
    assert result.selected.action_key == "summary.custom"


def test_evaluate_workflow_discovery_reports_accuracy():
    options = [
        _option(
            option_id=45,
            code="1.4",
            title="Cadastrar Atividade de Projeto",
            action_key="project_task.create",
            keywords=["cadastrar atividade", "nova atividade de projeto"],
        ),
        _option(
            option_id=46,
            code="4.3",
            title="Go Live Check",
            action_key="onboarding.go_live_check",
            keywords=["go live", "pronto para operar"],
        ),
    ]
    runtime = WorkflowRuntime()

    report = evaluate_workflow_discovery(
        runtime=runtime,
        options=options,
        cases=[
            WorkflowEvaluationCase(
                text="preciso cadastrar nova atividade de projeto",
                expected_action_key="project_task.create",
            ),
            WorkflowEvaluationCase(
                text="quero saber se a empresa esta pronta para operar",
                expected_action_key="onboarding.go_live_check",
            ),
        ],
        top_k=2,
    )

    assert report.total_cases == 2
    assert report.success_count == 2
    assert report.accuracy == 1.0


def test_workflow_session_state_reads_agent_menu_session_context():
    option = _option(
        option_id=40,
        code="3.5.2",
        title="Esta Semana",
        action_key="summary.week",
    )

    class DummySession:
        user_id = 10
        company_id = 9
        channel = "whatsapp"
        thread_id = "abc"
        status = "awaiting_summary_company"
        selected_option_id = 40
        selected_option = option
        collected_data = {"periodo": "esta semana"}
        missing_fields = []
        last_user_message = "quero um resumo"

    state = WorkflowSessionState.from_agent_menu_session(DummySession())

    assert state.user_id == 10
    assert state.company_id == 9
    assert state.workflow_code == "3.5.2"
    assert state.workflow_action_key == "summary.week"
    assert state.payload["periodo"] == "esta semana"


def test_summary_workflow_coordinator_routes_custom_without_period_to_dates():
    coordinator = SummaryWorkflowCoordinator(
        resolve_period_from_payload=lambda payload: (None, None),
        apply_preselected_summary_company_selection=lambda **kwargs: None,
    )
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="3.5.4",
        workflow_action_key="summary.custom",
        payload={},
    )

    decision = coordinator.prepare_initial_step(state)

    assert decision.handled is True
    assert decision.route == SUMMARY_ROUTE_PROMPT_DATES
    assert decision.status == SUMMARY_STATUS_AWAITING_DATES


def test_summary_workflow_coordinator_routes_week_with_preselected_company_to_collaborator():
    coordinator = SummaryWorkflowCoordinator(
        resolve_period_from_payload=lambda payload: (None, None),
        apply_preselected_summary_company_selection=lambda **kwargs: {
            "periodo": "esta semana",
            "_summary_company_id": 9,
            "_summary_company_label": "AA - Versus Gestao Corporativa",
            "empresa": "Versus Gestao Corporativa",
        },
    )
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="3.5.2",
        workflow_action_key="summary.week",
        payload={},
    )

    decision = coordinator.prepare_initial_step(state)

    assert decision.handled is True
    assert decision.route == SUMMARY_ROUTE_PROMPT_COLLABORATOR
    assert decision.payload["_summary_company_id"] == 9
    assert decision.payload["periodo"] == "esta semana"


def test_summary_workflow_coordinator_advance_custom_period_to_company_when_valid():
    coordinator = SummaryWorkflowCoordinator(
        resolve_period_from_payload=lambda payload: (date(2026, 3, 1), date(2026, 3, 31)),
        apply_preselected_summary_company_selection=lambda **kwargs: None,
    )
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="3.5.4",
        workflow_action_key="summary.custom",
        payload={},
    )

    decision = coordinator.advance_custom_period(
        state,
        payload={"periodo": "01/03/2026 a 31/03/2026"},
    )

    assert decision.handled is True
    assert decision.route == SUMMARY_ROUTE_PROMPT_COMPANY
    assert decision.payload["data_inicial"] == "2026-03-01"
    assert decision.payload["data_final"] == "2026-03-31"
