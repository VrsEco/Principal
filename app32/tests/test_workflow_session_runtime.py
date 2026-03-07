import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.session_runtime import (
    SessionNavigationRuntime,
    SessionPromptRenderer,
    build_session_snapshot,
    extract_navigation_stack,
    payload_without_navigation,
)


def _build_renderer() -> SessionPromptRenderer:
    return SessionPromptRenderer(
        render_root_menu=lambda company_id: f"root:{company_id}",
        public_payload=lambda payload: {
            key: value for key, value in (payload or {}).items() if not str(key).startswith("_")
        },
        render_confirmation=lambda option, payload, channel: (
            f"confirm:{option.code}:{payload.get('nome')}:{channel}"
        ),
        render_missing_fields=lambda option, missing_fields, payload, channel: (
            f"fields:{option.code}:{payload}:{len(missing_fields)}:{channel}"
        ),
        render_item_selection=lambda option, selection, channel: (
            f"select:{option.code}:{selection.get('selection_kind')}:{len(selection.get('choices') or [])}:{channel}"
        ),
        render_operation_company=lambda option, choices, channel: f"company:{option.code}:{len(choices)}:{channel}",
        render_summary_period=lambda option, channel: f"period:{option.code}:{channel}",
        render_summary_company=lambda option, choices, channel: f"summary-company:{option.code}:{len(choices)}:{channel}",
        render_summary_collaborator=lambda option, choices, channel: f"summary-collab:{option.code}:{len(choices)}:{channel}",
        render_summary_status=lambda option, choices, channel: f"summary-status:{option.code}:{len(choices)}:{channel}",
        summary_status_choices=lambda: [{"index": 1, "label": "Abertas"}],
        company_selection_status="awaiting_operation_company",
        summary_email_confirm_status="awaiting_summary_email_confirmation",
        summary_email_custom_status="awaiting_summary_email_custom",
        summary_email_offer_suffix="email-offer",
    )


def _build_session(**overrides):
    option = overrides.pop("selected_option", SimpleNamespace(code="3.5.1", title="Hoje"))
    payload = {
        "company_id": 9,
        "status": "awaiting_fields",
        "selected_option_id": 17,
        "selected_option": option,
        "collected_data": {"nome": "Ana"},
        "missing_fields": [{"key": "prazo"}],
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_payload_without_navigation_removes_only_hidden_stack():
    payload = payload_without_navigation({"nome": "Ana", "_nav_stack": [{"status": "awaiting_fields"}]})

    assert payload == {"nome": "Ana"}


def test_extract_navigation_stack_filters_invalid_items():
    history = extract_navigation_stack(
        {
            "_nav_stack": [
                {"status": "awaiting_fields"},
                "invalido",
                2,
                {"status": "awaiting_confirmation"},
            ]
        }
    )

    assert history == [
        {"status": "awaiting_fields"},
        {"status": "awaiting_confirmation"},
    ]


def test_build_session_snapshot_ignores_idle_state():
    session = _build_session(status="idle")

    assert build_session_snapshot(session) is None


def test_session_prompt_renderer_passes_session_channel():
    renderer = _build_renderer()
    session = _build_session(channel="whatsapp")

    text = renderer.render(session)

    assert text == "fields:3.5.1:{'nome': 'Ana'}:1:whatsapp"


def test_prompt_renderer_sanitizes_hidden_payload_on_missing_fields():
    renderer = _build_renderer()
    session = _build_session(
        collected_data={
            "nome": "Ana",
            "_secret": "nao-deve-aparecer",
            "_nav_stack": [{"status": "awaiting_confirmation"}],
        }
    )

    text = renderer.render(session)

    assert text == "fields:3.5.1:{'nome': 'Ana'}:1:web"


def test_navigation_runtime_transition_pushes_previous_snapshot():
    commits = []
    runtime = SessionNavigationRuntime(
        commit_session=lambda: commits.append("commit"),
        reset_session=lambda session: None,
        prompt_renderer=_build_renderer(),
    )
    session = _build_session(
        status="awaiting_fields",
        selected_option_id=17,
        collected_data={"nome": "Ana"},
        missing_fields=[{"key": "prazo"}],
    )

    runtime.transition_state(
        session,
        status="awaiting_confirmation",
        payload={"nome": "Ana", "prazo": "10/03/2026"},
        missing_fields=[],
    )

    assert commits == ["commit"]
    assert session.status == "awaiting_confirmation"
    assert session.collected_data["nome"] == "Ana"
    assert session.collected_data["prazo"] == "10/03/2026"
    assert len(session.collected_data["_nav_stack"]) == 1
    assert session.collected_data["_nav_stack"][0]["status"] == "awaiting_fields"
    assert session.collected_data["_nav_stack"][0]["collected_data"] == {"nome": "Ana"}


def test_navigation_runtime_handle_back_navigation_restores_previous_snapshot():
    commits = []
    runtime = SessionNavigationRuntime(
        commit_session=lambda: commits.append("commit"),
        reset_session=lambda session: None,
        prompt_renderer=_build_renderer(),
    )
    session = _build_session(
        status="awaiting_confirmation",
        collected_data={
            "nome": "Ana",
            "_nav_stack": [
                {
                    "status": "awaiting_fields",
                    "selected_option_id": 17,
                    "collected_data": {"nome": "Ana"},
                    "missing_fields": [{"key": "prazo"}],
                }
            ],
        },
        missing_fields=[],
    )

    result = runtime.handle_back_navigation(session)

    assert commits == ["commit"]
    assert session.status == "awaiting_fields"
    assert session.collected_data == {"nome": "Ana"}
    assert session.missing_fields == [{"key": "prazo"}]
    assert result.response_text == "fields:3.5.1:{'nome': 'Ana'}:1:web"


def test_navigation_runtime_handle_back_navigation_resets_when_history_missing():
    resets = []
    runtime = SessionNavigationRuntime(
        commit_session=lambda: None,
        reset_session=lambda session: (
            setattr(session, "status", "idle"),
            setattr(session, "selected_option_id", None),
            setattr(session, "collected_data", {}),
            setattr(session, "missing_fields", []),
            resets.append("reset"),
        ),
        prompt_renderer=_build_renderer(),
    )
    session = _build_session(status="awaiting_confirmation", collected_data={"nome": "Ana"})

    result = runtime.handle_back_navigation(session)

    assert resets == ["reset"]
    assert session.status == "idle"
    assert result.response_text == "root:9"
