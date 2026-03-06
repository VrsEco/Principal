import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows import WorkflowSessionState
from src.intelligence.workflows.field_collection import (
    FIELD_COLLECTION_ROUTE_PROMPT_MISSING,
    FIELD_COLLECTION_ROUTE_READY,
    FieldCollectionCoordinator,
    adjust_required_fields_for_context,
    extract_numbered_fields_from_text,
)
from src.intelligence.workflows.presenters import (
    WorkflowDisplayOption,
    build_missing_fields_prompt,
)
from src.intelligence.workflows.schemas import WorkflowRequiredField


def _build_coordinator() -> FieldCollectionCoordinator:
    return FieldCollectionCoordinator(
        extract_fields_from_text=lambda text: (
            {"nome_atividade": "Implementar V3"}
            if "nome_atividade:" in text
            else {"dados": "status: concluido"}
            if "dados:" in text
            else {}
        ),
        public_payload=lambda payload: {
            key: value for key, value in (payload or {}).items() if not str(key).startswith("_")
        },
    )


def test_extract_numbered_fields_from_text_maps_reply_to_pending_keys():
    data = extract_numbered_fields_from_text(
        "1: AA.J.17\n2: Implementar runtime",
        [
            {"key": "codigo_projeto", "label": "Codigo do Projeto"},
            {"key": "nome_atividade", "label": "Nome da Atividade"},
        ],
    )

    assert data == {
        "codigo_projeto": "AA.J.17",
        "nome_atividade": "Implementar runtime",
    }


def test_workflow_required_field_normalizes_mixed_input():
    fields = WorkflowRequiredField.normalize_many(
        [
            {"key": "Código do Projeto", "label": "Código do Projeto"},
            "Nome da Atividade",
        ]
    )

    assert [field.key for field in fields] == ["codigo_do_projeto", "nome_da_atividade"]


def test_field_collection_coordinator_merge_reply_payload_combines_sources():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"empresa": "Versus", "_nav_stack": [{"status": "awaiting_fields"}]},
        missing_fields=[
            {"key": "codigo_projeto", "label": "Codigo do Projeto"},
            {"key": "nome_atividade", "label": "Nome da Atividade"},
        ],
    )

    merged = coordinator.merge_reply_payload(
        state,
        text="1: AA.J.17\nnome_atividade: Implementar V3",
    )

    assert merged == {
        "empresa": "Versus",
        "codigo_projeto": "AA.J.17",
        "nome_atividade": "Implementar V3",
    }


def test_field_collection_coordinator_prompts_when_required_fields_are_missing():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={"nome_atividade": "Implementar V3"},
    )

    decision = coordinator.evaluate_payload(
        workflow_state=state,
        raw_required_fields=[
            {"key": "codigo_projeto", "label": "Codigo do Projeto"},
            {"key": "nome_atividade", "label": "Nome da Atividade"},
        ],
        payload=state.payload,
    )

    assert decision.route == FIELD_COLLECTION_ROUTE_PROMPT_MISSING
    assert [field.key for field in decision.missing_fields] == ["codigo_projeto"]


def test_adjust_required_fields_for_context_ignores_empresa_for_my_work():
    adjusted = adjust_required_fields_for_context(
        "my_work.open",
        WorkflowRequiredField.normalize_many(
            [
                {"key": "empresa", "label": "Empresa"},
                {"key": "periodo", "label": "Periodo"},
            ]
        ),
    )

    assert [field.key for field in adjusted] == ["periodo"]


def test_field_collection_coordinator_marks_ready_when_contextual_fields_are_optional():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="3.1",
        workflow_action_key="my_work.open",
        payload={},
    )

    decision = coordinator.evaluate_payload(
        workflow_state=state,
        raw_required_fields=[{"key": "empresa", "label": "Empresa"}],
        payload=state.payload,
    )

    assert decision.route == FIELD_COLLECTION_ROUTE_READY
    assert decision.missing_fields == []


def test_build_missing_fields_prompt_renders_existing_data_and_examples():
    option = WorkflowDisplayOption(
        code="5.1",
        title="Iniciar Onboarding",
        action_key="onboarding.start",
    )

    text = build_missing_fields_prompt(
        option,
        [{"key": "tipo_implantacao", "label": "Tipo de Implantacao"}],
        {"empresa": "Versus"},
    )

    assert "Voce quer fazer 5.1 - Iniciar Onboarding." in text
    assert "1 - Tipo de Implantacao (tipo_implantacao)" in text
    assert "- empresa: Versus" in text
    assert "1: real" in text
