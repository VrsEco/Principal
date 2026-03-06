from datetime import date

from models.agent_menu import AgentMenuOption
from src.intelligence.workflows.matcher import LexicalWorkflowMatcher
from src.intelligence.workflows.registry import WorkflowRegistry
from src.intelligence.workflows.runtime import WorkflowRuntime
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
):
    return AgentMenuOption(
        id=option_id,
        company_id=company_id,
        code=code,
        title=title,
        action_key=action_key,
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
