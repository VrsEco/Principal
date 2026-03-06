import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows import WorkflowSessionState
from src.intelligence.workflows.confirmation import (
    CONFIRMATION_ROUTE_CANCELLED,
    CONFIRMATION_ROUTE_DIRECT_RESPONSE,
    CONFIRMATION_ROUTE_EXECUTION_PROMPT,
    CONFIRMATION_ROUTE_RECONFIRM,
    ConfirmationCoordinator,
)


def _build_coordinator() -> ConfirmationCoordinator:
    return ConfirmationCoordinator(
        confirm_words={"sim", "ok"},
        cancel_words={"nao", "cancelar"},
        extract_fields_from_text=lambda text: (
            {"nome_atividade": "Ajustado"}
            if "nome_atividade:" in text
            else {"dados": "status: concluido"}
            if "dados:" in text
            else {}
        ),
        public_payload=lambda payload: {
            key: value for key, value in (payload or {}).items() if not str(key).startswith("_")
        },
        try_execute_direct_option=lambda **kwargs: (
            "atividade criada"
            if kwargs.get("option") and getattr(kwargs["option"], "action_key", "") == "project_task.create"
            else None
        ),
        build_execution_prompt=lambda option, payload, original_user_text: (
            f"prompt:{option.code}:{payload.get('empresa')}:{original_user_text}"
        ),
    )


def test_confirmation_coordinator_cancels_flow():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        company_id=9,
        status="awaiting_confirmation",
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"empresa": "Versus"},
    )

    decision = coordinator.handle_reply(
        state,
        option=SimpleNamespace(code="1.4", action_key="project_task.create"),
        text="nao",
        lower="nao",
    )

    assert decision.route == CONFIRMATION_ROUTE_CANCELLED
    assert "Acao cancelada" in (decision.response_text or "")


def test_confirmation_coordinator_returns_direct_response_when_available():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        company_id=9,
        channel="web",
        status="awaiting_confirmation",
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"empresa": "Versus", "_nav_stack": [{"status": "awaiting_fields"}]},
    )

    decision = coordinator.handle_reply(
        state,
        option=SimpleNamespace(code="1.4", action_key="project_task.create"),
        text="sim",
        lower="sim",
    )

    assert decision.route == CONFIRMATION_ROUTE_DIRECT_RESPONSE
    assert decision.response_text == "atividade criada"
    assert decision.payload == {"empresa": "Versus"}


def test_confirmation_coordinator_builds_execution_prompt_when_direct_execution_is_not_available():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        company_id=9,
        channel="whatsapp",
        status="awaiting_confirmation",
        workflow_code="2.1",
        workflow_action_key="process_instance.start",
        payload={"empresa": "Versus"},
        last_user_message="iniciar processo da empresa",
    )

    decision = coordinator.handle_reply(
        state,
        option=SimpleNamespace(code="2.1", action_key="process_instance.start"),
        text="sim",
        lower="sim",
    )

    assert decision.route == CONFIRMATION_ROUTE_EXECUTION_PROMPT
    assert decision.override_message == "prompt:2.1:Versus:iniciar processo da empresa"


def test_confirmation_coordinator_reconfirms_with_payload_adjustments():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        company_id=9,
        status="awaiting_confirmation",
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"empresa": "Versus", "nome_atividade": "Original"},
    )

    decision = coordinator.handle_reply(
        state,
        option=SimpleNamespace(code="1.4", action_key="project_task.create"),
        text="nome_atividade: Ajustado",
        lower="nome_atividade: ajustado",
    )

    assert decision.route == CONFIRMATION_ROUTE_RECONFIRM
    assert decision.payload["nome_atividade"] == "Ajustado"
    assert decision.payload["empresa"] == "Versus"
