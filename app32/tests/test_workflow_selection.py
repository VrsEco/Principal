from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows import WorkflowSessionState
from src.intelligence.workflows.presenters import (
    WorkflowDisplayOption,
    build_item_selection_prompt,
)
from src.intelligence.workflows.schemas import AssistedSelectionContext
from src.intelligence.workflows.selection import (
    SELECTION_ROUTE_ADVANCE,
    SELECTION_ROUTE_CONFIRM,
    AssistedSelectionCoordinator,
    build_assisted_selection_payload,
)


def _build_coordinator():
    return AssistedSelectionCoordinator(
        extract_fields_from_text=lambda text: (
            {"codigo_projeto": "AA.J.17"}
            if "codigo_projeto:" in text
            else {"id_reuniao": "55"}
            if "id_reuniao:" in text
            else {}
        ),
        parse_selection_number_date=lambda text: (
            (2, None) if text == "2" else (1, "20/03/2026") if text == "1: 20/03/2026" else None
        ),
        parse_completion_date=lambda raw: date(2026, 3, 20) if raw == "20/03/2026" else None,
        public_payload=lambda payload: {
            key: value for key, value in (payload or {}).items() if not str(key).startswith("_")
        },
    )


def test_assisted_selection_context_builds_from_hidden_payload():
    context = AssistedSelectionContext.build_from_payload(
        {
            "_selection_action": "meeting.start",
            "_selection_kind": "project_picker",
            "_selection_field_key": "codigo_projeto",
            "_selection_value_key": "code",
            "_choices": [{"index": 1, "code": "AA.J.17"}],
            "_scope_label": "empresa AA - Versus",
            "_item_label_plural": "projetos",
        }
    )

    assert context.selection_action == "meeting.start"
    assert context.selection_kind == "project_picker"
    assert context.selection_field_key == "codigo_projeto"
    assert context.selection_value_key == "code"
    assert context.scope_label == "empresa AA - Versus"


def test_build_assisted_selection_payload_for_project_picker():
    payload = build_assisted_selection_payload(
        {"empresa": "Versus"},
        selection_action="project_task.create",
        selection={
            "selection_kind": "project_picker",
            "field_key": "codigo_projeto",
            "value_key": "code",
            "choices": [{"index": 1, "code": "AA.J.17"}],
            "scope_label": "empresa AA - Versus",
            "item_label_plural": "projetos",
        },
    )

    assert payload["empresa"] == "Versus"
    assert payload["_selection_action"] == "project_task.create"
    assert payload["_selection_kind"] == "project_picker"
    assert payload["_selection_field_key"] == "codigo_projeto"
    assert payload["_selection_value_key"] == "code"


def test_assisted_selection_coordinator_advances_project_picker_by_index():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="1.4",
        workflow_action_key="project_task.create",
        payload={
            "_selection_action": "project_task.create",
            "_selection_kind": "project_picker",
            "_selection_field_key": "codigo_projeto",
            "_selection_value_key": "code",
            "_choices": [
                {"index": 1, "code": "AA.J.11"},
                {"index": 2, "code": "AA.J.22"},
            ],
        },
    )

    decision = coordinator.handle_reply(state, text="2")

    assert decision.route == SELECTION_ROUTE_ADVANCE
    assert decision.payload["codigo_projeto"] == "AA.J.22"


def test_assisted_selection_coordinator_confirms_meeting_direct_field():
    coordinator = _build_coordinator()
    state = WorkflowSessionState(
        user_id=10,
        workflow_code="4.2",
        workflow_action_key="meeting.start",
        payload={
            "_selection_action": "meeting.start",
            "_choices": [{"index": 1, "id": 55, "code": "55"}],
        },
    )

    decision = coordinator.handle_reply(state, text="id_reuniao: 55")

    assert decision.route == SELECTION_ROUTE_CONFIRM
    assert decision.payload["id_reuniao"] == "55"


def test_item_selection_presenter_builds_project_picker_prompt():
    option = WorkflowDisplayOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )

    text = build_item_selection_prompt(
        option,
        {
            "selection_kind": "project_picker",
            "scope_label": "empresa AA - Versus",
            "choices": [
                {
                    "index": 1,
                    "code": "AA.J.17",
                    "title": "Projeto V3",
                    "status": "in_progress",
                    "progress": 65,
                    "due_date": "2026-03-20",
                }
            ],
        },
        format_project_status_label=lambda status: "Em andamento",
        format_date_br=lambda value: "20/03/2026",
    )

    assert "Escolha o projeto ativo para a empresa AA - Versus" in text
    assert "1 - AA.J.17 - Projeto V3" in text
    assert "Informe apenas o numero do projeto." in text
