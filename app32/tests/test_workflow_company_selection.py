import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows import WorkflowSessionState
from src.intelligence.workflows.company_selection import (
    COMPANY_SELECTION_ROUTE_ADVANCE,
    COMPANY_SELECTION_ROUTE_ERROR,
    COMPANY_SELECTION_ROUTE_PROMPT,
    COMPANY_SELECTION_ROUTE_SKIP,
    OperationCompanySelectionCoordinator,
)
from src.intelligence.workflows.presenters import (
    WorkflowDisplayOption,
    build_operation_company_prompt,
)
from src.intelligence.workflows.schemas import OperationCompanySelectionContext


def _choices():
    return [
        {
            "index": 1,
            "company_id": 9,
            "company_name": "Versus",
            "company_code": "AA",
            "label": "AA - Versus",
        },
        {
            "index": 2,
            "company_id": 12,
            "company_name": "Save Water",
            "company_code": "SW",
            "label": "SW - Save Water",
        },
    ]


def _build_coordinator() -> OperationCompanySelectionCoordinator:
    return OperationCompanySelectionCoordinator(
        public_payload=lambda payload: {
            key: value for key, value in (payload or {}).items() if not str(key).startswith("_")
        },
        summary_action_keys={"summary.today", "summary.week", "summary.month", "summary.custom"},
    )


def test_company_selection_context_builds_choices_from_hidden_payload():
    context = OperationCompanySelectionContext.build_from_payload(
        {"_operation_company_choices": _choices()}
    )

    assert len(context.choices) == 2
    assert context.choices[0].company_id == 9
    assert context.choices[1].label == "SW - Save Water"


def test_company_selection_prepare_prompts_for_non_web_without_explicit_company():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        channel="whatsapp",
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"nome_atividade": "Implementar V3"},
    )

    decision = coordinator.prepare_initial_selection(
        state,
        normalized_channel="whatsapp",
        explicit_company_id=None,
        choices=_choices(),
    )

    assert decision.route == COMPANY_SELECTION_ROUTE_PROMPT
    assert len(decision.choices) == 2
    assert "_operation_company_choices" in decision.payload


def test_company_selection_prepare_skips_for_web_channel():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        channel="web",
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={},
    )

    decision = coordinator.prepare_initial_selection(
        state,
        normalized_channel="web",
        explicit_company_id=None,
        choices=_choices(),
    )

    assert decision.route == COMPANY_SELECTION_ROUTE_SKIP


def test_company_selection_select_company_returns_error_for_invalid_index():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"_operation_company_choices": _choices()},
    )

    decision = coordinator.select_company(
        state,
        selected_index=3,
        user_can_access_company=lambda user_id, company_id: True,
    )

    assert decision.route == COMPANY_SELECTION_ROUTE_ERROR
    assert "Indice de empresa invalido" in (decision.response_text or "")


def test_company_selection_select_company_adds_summary_context_when_needed():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="3.5.2",
        workflow_action_key="summary.week",
        payload={"periodo": "esta semana", "_operation_company_choices": _choices()},
    )

    decision = coordinator.select_company(
        state,
        selected_index=2,
        user_can_access_company=lambda user_id, company_id: True,
    )

    assert decision.route == COMPANY_SELECTION_ROUTE_ADVANCE
    assert decision.payload["empresa"] == "Save Water"
    assert decision.payload["_selected_company_id"] == 12
    assert decision.payload["_summary_company_id"] == 12
    assert "_operation_company_choices" not in decision.payload


def test_company_selection_select_company_denies_access_and_requires_reset():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"_operation_company_choices": _choices()},
    )

    decision = coordinator.select_company(
        state,
        selected_index=1,
        user_can_access_company=lambda user_id, company_id: False,
    )

    assert decision.route == COMPANY_SELECTION_ROUTE_ERROR
    assert decision.should_reset_session is True
    assert "nao possui acesso" in (decision.response_text or "").lower()


def test_operation_company_presenter_builds_prompt():
    option = WorkflowDisplayOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )

    text = build_operation_company_prompt(option, _choices())

    assert "Escolha a empresa para continuar:" in text
    assert "1 - AA - Versus" in text
    assert "2 - SW - Save Water" in text
