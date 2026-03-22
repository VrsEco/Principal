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
from src.intelligence.workflows.evaluation_catalog import (
    build_default_workflow_evaluation_cases,
)
from src.intelligence.workflows.confidence import (
    DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS,
    DISCOVERY_CONFIDENCE_ROUTE_SELECT,
    WorkflowDiscoveryConfidencePolicy,
)
from src.intelligence.workflows.registry import WorkflowRegistry
from src.intelligence.workflows.reranker import HeuristicWorkflowReranker
from src.intelligence.workflows.reranker import LLMWorkflowReranker
from src.intelligence.workflows.reranker import WorkflowLLMRerankDecision
from src.intelligence.workflows.reranker import build_default_workflow_reranker
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


def test_heuristic_reranker_prioritizes_deadline_update_for_coloque_para_o_dia():
    options = [
        _option(
            option_id=40,
            code="1.5",
            title="Finalizar Atividade de Projeto",
            action_key="project_task.complete",
            keywords=["concluir atividade"],
            sort_order=15,
        ),
        _option(
            option_id=41,
            code="1.6",
            title="Editar Atividade de Projeto",
            action_key="project_task.update",
            keywords=["editar atividade", "alterar prazo da atividade"],
            sort_order=16,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(text="coloque todas para o dia 31/03/2026", top_k=2),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "project_task.update"


def test_heuristic_reranker_prioritizes_agent_action_approve_for_approval_command():
    options = [
        _option(
            option_id=42,
            code="6.1",
            title="Aprovar Solicitação",
            action_key="agent_action.approve",
            keywords=["aprovar ticket", "aprovado"],
            sort_order=61,
        ),
        _option(
            option_id=43,
            code="1.5",
            title="Finalizar Atividade de Projeto",
            action_key="project_task.complete",
            keywords=["concluir atividade"],
            sort_order=15,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(text="aprovar 331", top_k=2),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "agent_action.approve"


def test_heuristic_reranker_prioritizes_collaborator_occupancy_over_summary_month():
    options = [
        _option(
            option_id=44,
            code="3.5.3",
            title="Este Mes",
            action_key="summary.month",
            keywords=["resumo mes", "este mes"],
            sort_order=38,
        ),
        _option(
            option_id=45,
            code="3.6",
            title="Ocupacao de Colaborador",
            action_key="collaborator.occupancy",
            keywords=["ocupacao do colaborador", "capacidade do colaborador"],
            sort_order=40,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(text="me diga a ocupação de Caroline Marques este mes.", top_k=2),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "collaborator.occupancy"


def test_heuristic_reranker_prioritizes_pending_decisions_listing():
    options = [
        _option(
            option_id=46,
            code="6.4",
            title="Listar Solicitações Pendentes",
            action_key="agent_action.list_pending",
            keywords=["acoes aguardando minha decisao", "listar solicitacoes pendentes"],
            sort_order=64,
        ),
        _option(
            option_id=47,
            code="5.2",
            title="Diagnosticar Onboarding",
            action_key="onboarding.diagnose",
            keywords=["diagnosticar onboarding"],
            sort_order=52,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(text="Liste 20 ações do sistema que estão aguardando minha decisão.", top_k=2),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "agent_action.list_pending"


def test_heuristic_reranker_prioritizes_company_access_listing():
    options = [
        _option(
            option_id=146,
            code="3.7",
            title="Empresas Vinculadas ao Usuario",
            action_key="company.list_accessible",
            keywords=["quantas empresas estão vinculadas a mim", "minhas empresas"],
            sort_order=41,
        ),
        _option(
            option_id=147,
            code="1.1",
            title="Cadastrar Projeto",
            action_key="project.create",
            keywords=["cadastrar projeto", "novo projeto"],
            sort_order=11,
        ),
    ]

    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(text="Quantas empresas estão vinculadas a mim atualmente?", top_k=2),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "company.list_accessible"
    assert any("company=list_accessible" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_prioritizes_project_task_audit_for_missing_responsible():
    options = [
        _option(
            option_id=48,
            code="1.7",
            title="Auditar Atividades de Projeto",
            action_key="project_task.audit",
            keywords=["atividades sem responsável", "auditoria de atividades"],
            sort_order=17,
        ),
        _option(
            option_id=49,
            code="3.1",
            title="Atividades em Aberto",
            action_key="my_work.open",
            keywords=["atividades em aberto"],
            sort_order=31,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=10, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=10, reasons=[]),
    ]

    reranked = HeuristicWorkflowReranker().rerank(
        WorkflowDiscoveryRequest(
            text="Analise as atividades de projetos que estão sem responsável, de todas as empresas.",
            top_k=2,
        ),
        matches,
        registry,
    )

    assert reranked[0].workflow.action_key == "project_task.audit"


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
    assert result.telemetry["reranker_kind"] == "HeuristicWorkflowReranker"


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


def test_workflow_discovery_confidence_policy_selects_clear_winner():
    policy = WorkflowDiscoveryConfidencePolicy()

    decision = policy.decide(
        [
            {"code": "3.5.4", "action_key": "summary.custom", "score": 42},
            {"code": "3.5.2", "action_key": "summary.week", "score": 24},
        ]
    )

    assert decision.route == DISCOVERY_CONFIDENCE_ROUTE_SELECT
    assert decision.selected_code == "3.5.4"
    assert decision.reason == "clear_winner"


def test_workflow_discovery_confidence_policy_requires_disambiguation_for_close_scores():
    policy = WorkflowDiscoveryConfidencePolicy()

    decision = policy.decide(
        [
            {"code": "4.1", "action_key": "meeting.schedule", "score": 27},
            {"code": "4.2", "action_key": "meeting.start", "score": 24},
        ]
    )

    assert decision.route == DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS
    assert decision.reason == "needs_disambiguation"


def test_llm_workflow_reranker_reorders_candidates_from_structured_response():
    matches = [
        WorkflowMatch(
            workflow=WorkflowRegistry.from_menu_options(
                [
                    _option(
                        option_id=51,
                        code="3.5.2",
                        title="Esta Semana",
                        action_key="summary.week",
                        keywords=["resumo semana"],
                    ),
                    _option(
                        option_id=52,
                        code="3.5.4",
                        title="Personalizado",
                        action_key="summary.custom",
                        keywords=["resumo personalizado"],
                    ),
                ]
            ).list()[0],
            score=30,
            reasons=["semantic:semana"],
        ),
        WorkflowMatch(
            workflow=WorkflowRegistry.from_menu_options(
                [
                    _option(
                        option_id=51,
                        code="3.5.2",
                        title="Esta Semana",
                        action_key="summary.week",
                        keywords=["resumo semana"],
                    ),
                    _option(
                        option_id=52,
                        code="3.5.4",
                        title="Personalizado",
                        action_key="summary.custom",
                        keywords=["resumo personalizado"],
                    ),
                ]
            ).list()[1],
            score=28,
            reasons=["semantic:datas"],
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(
        [
            _option(
                option_id=51,
                code="3.5.2",
                title="Esta Semana",
                action_key="summary.week",
                keywords=["resumo semana"],
            ),
            _option(
                option_id=52,
                code="3.5.4",
                title="Personalizado",
                action_key="summary.custom",
                keywords=["resumo personalizado"],
            ),
        ]
    )
    reranker = LLMWorkflowReranker(
        invoke_llm=lambda request, matches, registry: WorkflowLLMRerankDecision(
            ranked=[
                {"workflow_code": "3.5.4", "reason": "datas explicitas"},
                {"workflow_code": "3.5.2", "reason": "periodo semanal como fallback"},
            ]
        )
    )

    reranked = list(
        reranker.rerank(
            WorkflowDiscoveryRequest(text="resumo de 01/03/2026 a 05/03/2026"),
            matches,
            registry,
        )
    )

    assert reranked[0].workflow.code == "3.5.4"
    assert any(reason == "llm_reranker:rank=1" for reason in reranked[0].reasons)
    assert any("datas explicitas" in reason for reason in reranked[0].reasons)


def test_llm_workflow_reranker_ignores_unknown_codes_and_preserves_remaining_order():
    registry = WorkflowRegistry.from_menu_options(
        [
            _option(option_id=61, code="4.1", title="Agendar", action_key="meeting.schedule"),
            _option(option_id=62, code="4.2", title="Iniciar", action_key="meeting.start"),
            _option(option_id=63, code="4.3", title="Resumir", action_key="meeting.summarize"),
        ]
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=20, reasons=["semantic:agenda"]),
        WorkflowMatch(workflow=registry.list()[1], score=19, reasons=["semantic:iniciar"]),
        WorkflowMatch(workflow=registry.list()[2], score=18, reasons=["semantic:ata"]),
    ]
    reranker = LLMWorkflowReranker(
        invoke_llm=lambda request, matches, registry: {
            "ranked": [
                {"workflow_code": "4.9", "reason": "invalido"},
                {"workflow_code": "4.3", "reason": "o usuario quer um resumo"},
            ]
        }
    )

    reranked = list(
        reranker.rerank(
            WorkflowDiscoveryRequest(text="quero resumir a reuniao"),
            matches,
            registry,
        )
    )

    assert reranked[0].workflow.code == "4.3"
    assert reranked[1].workflow.code == "4.1"
    assert reranked[2].workflow.code == "4.2"


def test_build_default_workflow_reranker_falls_back_to_heuristic_when_disabled(monkeypatch):
    monkeypatch.delenv("WORKFLOW_LLM_RERANKER_ENABLED", raising=False)

    reranker = build_default_workflow_reranker()

    assert isinstance(reranker, HeuristicWorkflowReranker)


def test_heuristic_reranker_prioritizes_overdue_for_singular_vencido():
    registry = WorkflowRegistry.from_menu_options(
        [
            _option(option_id=71, code="3.1", title="Atividades em Aberto", action_key="my_work.open"),
            _option(option_id=72, code="3.2", title="Atividades Vencidas", action_key="my_work.overdue"),
        ]
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=20, reasons=["semantic:trabalho"]),
        WorkflowMatch(workflow=registry.list()[1], score=19, reasons=["semantic:vencido"]),
    ]
    reranker = HeuristicWorkflowReranker()

    reranked = list(
        reranker.rerank(
            WorkflowDiscoveryRequest(text="o que esta vencido no meu trabalho"),
            matches,
            registry,
        )
    )

    assert reranked[0].workflow.action_key == "my_work.overdue"


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
    assert report.top_k_success_count == 2
    assert report.top_k_accuracy == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert len(report.domain_breakdown) == 1


def test_evaluate_workflow_discovery_exposes_rank_metrics_and_domains():
    options = [
        _option(
            option_id=47,
            code="4.1",
            title="Agendar Reuniao",
            action_key="meeting.schedule",
            keywords=["agendar reuniao"],
        ),
        _option(
            option_id=48,
            code="4.3",
            title="Resumir Reuniao",
            action_key="meeting.summarize",
            keywords=["resumir reuniao"],
        ),
    ]

    class StubRuntime:
        def discover_from_menu_options(self, **kwargs):
            del kwargs
            registry = WorkflowRegistry.from_menu_options(options)
            return type(
                "Result",
                (),
                {
                    "selected_match": WorkflowMatch(
                        workflow=registry.list()[0],
                        score=20,
                        reasons=[],
                    ),
                    "matches": [
                        WorkflowMatch(workflow=registry.list()[0], score=20, reasons=[]),
                        WorkflowMatch(workflow=registry.list()[1], score=19, reasons=[]),
                    ],
                },
            )()

    report = evaluate_workflow_discovery(
        runtime=StubRuntime(),
        options=options,
        cases=[
            WorkflowEvaluationCase(
                domain="meeting",
                label="meeting_summary_rank_2",
                text="quero um resumo da reuniao",
                expected_action_key="meeting.summarize",
            ),
        ],
        top_k=2,
    )

    assert report.total_cases == 1
    assert report.success_count == 0
    assert report.top_k_success_count == 1
    assert report.top_k_accuracy == 1.0
    assert report.items[0].expected_rank == 2
    assert report.items[0].reciprocal_rank == 0.5
    assert report.domain_breakdown[0].domain == "meeting"


def test_default_workflow_evaluation_catalog_covers_multiple_domains():
    cases = build_default_workflow_evaluation_cases()

    domains = {case.domain for case in cases}
    labels = {case.label for case in cases}

    assert len(cases) >= 12
    assert {"summary", "my_work", "project_task", "meeting", "onboarding"} <= domains
    assert {
        "my_work_overdue_instances_by_collaborator",
        "my_work_open_tasks_by_collaborator",
        "my_work_due_today_queue",
        "my_work_due_week_pending",
        "my_work_due_month_pending",
    } <= labels


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


def test_heuristic_reranker_prioritizes_collaborator_occupancy_for_capacity_query():
    options = [
        _option(
            option_id=60,
            code="3.1",
            title="Atividades em Aberto",
            action_key="my_work.open",
            keywords=["atividades em aberto"],
            sort_order=31,
        ),
        _option(
            option_id=61,
            code="3.6",
            title="Ocupacao de Colaborador",
            action_key="collaborator.occupancy",
            keywords=["ocupacao do colaborador", "capacidade do colaborador"],
            sort_order=36,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Quero saber a capacidade do colaborador Caroline Marques esta semana",
        company_id=9,
        channel="whatsapp",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=12, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=12, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "collaborator.occupancy"
    assert any("collaborator" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_prioritizes_project_task_complete_for_batch_ids():
    options = [
        _option(
            option_id=62,
            code="1.5",
            title="Finalizar Atividade de Projeto",
            action_key="project_task.complete",
            keywords=["concluir atividade"],
            sort_order=15,
        ),
        _option(
            option_id=63,
            code="2.2",
            title="Finalizar Instancia de Processo",
            action_key="process_instance.complete",
            keywords=["encerrar processo"],
            sort_order=22,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Pode dar como concluida as atividades de IDs: 24 e 323",
        company_id=9,
        channel="whatsapp",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=12, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=12, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "project_task.complete"
    assert any("batch_ids" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_preserves_my_work_for_process_instance_queries():
    options = [
        _option(
            option_id=64,
            code="1.5",
            title="Finalizar Atividade de Projeto",
            action_key="project_task.complete",
            keywords=["concluir atividade"],
            sort_order=15,
        ),
        _option(
            option_id=65,
            code="3.2",
            title="Meu Trabalho Atrasado",
            action_key="my_work.overdue",
            keywords=["trabalho atrasado", "instancias atrasadas"],
            sort_order=32,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Quais instancias atrasadas para Caroline Marques da empresa Gandu Investimentos?",
        company_id=9,
        channel="whatsapp",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=12, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=12, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "my_work.overdue"
    assert any("process_instance" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_prioritizes_overdue_when_phrase_also_contains_em_aberto():
    options = [
        _option(
            option_id=81,
            code="3.1",
            title="Atividades em Aberto",
            action_key="my_work.open",
            keywords=["atividades em aberto"],
            sort_order=31,
        ),
        _option(
            option_id=82,
            code="3.2",
            title="Meu Trabalho Atrasado",
            action_key="my_work.overdue",
            keywords=["trabalho atrasado", "instancias atrasadas"],
            sort_order=32,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Quais as atividades e instancias atrasadas que Joaquim Guga da empresa Gandu Investimentos tem em aberto?",
        company_id=7,
        channel="whatsapp",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=22, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=20, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "my_work.overdue"
    assert any("my_work=overdue" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_prioritizes_due_range_for_today_work_queue():
    options = [
        _option(
            option_id=66,
            code="3.1",
            title="Atividades em Aberto",
            action_key="my_work.open",
            keywords=["atividades em aberto"],
            sort_order=31,
        ),
        _option(
            option_id=67,
            code="3.3",
            title="Vencendo no Periodo",
            action_key="my_work.due_range",
            keywords=["o que vence no periodo", "tarefas desta semana"],
            sort_order=33,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Me diga o que temos para fazer hoje?",
        company_id=9,
        channel="web",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=12, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=12, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "my_work.due_range"
    assert any("period_queue" in reason for reason in reranked[0].reasons)


def test_heuristic_reranker_prioritizes_due_range_for_pending_month_queue():
    options = [
        _option(
            option_id=68,
            code="3.1",
            title="Atividades em Aberto",
            action_key="my_work.open",
            keywords=["atividades em aberto"],
            sort_order=31,
        ),
        _option(
            option_id=69,
            code="3.3",
            title="Vencendo no Periodo",
            action_key="my_work.due_range",
            keywords=["o que vence no periodo", "tarefas deste mes"],
            sort_order=33,
        ),
    ]
    registry = WorkflowRegistry.from_menu_options(options)
    reranker = HeuristicWorkflowReranker()
    request = WorkflowDiscoveryRequest(
        text="Preciso saber o que tenho de atividades pendentes para este mês na empresa Gás Evolution",
        company_id=9,
        channel="whatsapp",
    )
    matches = [
        WorkflowMatch(workflow=registry.list()[0], score=12, reasons=[]),
        WorkflowMatch(workflow=registry.list()[1], score=12, reasons=[]),
    ]

    reranked = reranker.rerank(request, matches, registry)

    assert reranked
    assert reranked[0].workflow.action_key == "my_work.due_range"
    assert any("period_queue" in reason for reason in reranked[0].reasons)
