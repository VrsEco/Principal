import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.agent_menu import AgentMenuOption
from src.intelligence import menu_engine


class _DummySession:
    def __init__(self, option: AgentMenuOption):
        self.user_id = 10
        self.company_id = None
        self.channel = "whatsapp"
        self.thread_id = "thread-1"
        self.status = "idle"
        self.selected_option_id = None
        self.collected_data = {}
        self.missing_fields = []
        self.last_user_message = None
        self._options = {option.id: option}

    @property
    def selected_option(self):
        return self._options.get(self.selected_option_id)


def _build_project_task_option() -> AgentMenuOption:
    option = AgentMenuOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
        required_fields=[
            {"key": "codigo_projeto", "label": "Codigo do Projeto"},
            {"key": "nome_atividade", "label": "Nome da Atividade"},
        ],
    )
    option.id = 14
    return option


def _install_common_patches(monkeypatch, session, option):
    monkeypatch.setattr(menu_engine, "_ensure_default_menu_seed", lambda: None)
    monkeypatch.setattr(menu_engine, "_get_or_create_session", lambda **kwargs: session)
    monkeypatch.setattr(
        menu_engine,
        "_find_option_by_code",
        lambda company_id, code, include_inactive=False: option if code == option.code else None,
    )
    monkeypatch.setattr(menu_engine, "_list_children", lambda company_id, parent_id: [])
    monkeypatch.setattr(
        menu_engine,
        "_load_summary_company_choices",
        lambda user_id: [
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
        ],
    )
    monkeypatch.setattr(
        menu_engine,
        "_resolve_explicit_company_id_from_payload",
        lambda payload, user_id: payload.get("_selected_company_id") or payload.get("_summary_company_id"),
    )
    monkeypatch.setattr(
        menu_engine,
        "_user_can_access_company",
        lambda user_id, company_id: company_id in {9, 12},
    )
    monkeypatch.setattr(
        menu_engine,
        "_load_assisted_field_selection",
        lambda action, field_key, company_id, user_id: {
            "selection_kind": "project_picker",
            "field_key": "codigo_projeto",
            "value_key": "code",
            "scope_label": "empresa AA - Versus",
            "item_label_plural": "projetos",
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
    )
    monkeypatch.setattr(menu_engine, "_format_project_choice_line", lambda project_code: f"{project_code} - Projeto V3")
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)
    monkeypatch.setattr(menu_engine, "_format_root_menu", lambda company_id: "ROOT MENU")


def test_handle_menu_message_project_task_create_full_cycle(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(
        menu_engine,
        "_try_execute_direct_option",
        lambda option, payload, company_id, user_id, channel="web": (
            f"atividade criada: {payload.get('codigo_projeto')} - {payload.get('nome_atividade')}"
            if str(option.action_key or "").strip().lower() == "project_task.create" and payload.get("nome_atividade")
            else None
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="1.4",
    )

    assert result.handled is True
    assert "Escolha a empresa para continuar:" in result.response_text
    assert session.status == menu_engine.COMPANY_SELECTION_STATUS

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="1",
    )

    assert result.handled is True
    assert "Escolha o projeto ativo para a empresa AA - Versus" in result.response_text
    assert session.status == "awaiting_item_selection"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="1",
    )

    assert result.handled is True
    assert "Para executar, faltam os seguintes dados:" in result.response_text
    assert "Nome da Atividade" in result.response_text
    assert session.status == "awaiting_fields"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="1: Implementar Workflow V3",
    )

    assert result.handled is True
    assert "Confirme que voce quer:" in result.response_text
    assert "Implementar Workflow V3" in result.response_text
    assert session.status == "awaiting_confirmation"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="sim",
    )

    assert result.handled is True
    assert result.response_text == "atividade criada: AA.J.17 - Implementar Workflow V3"
    assert session.status == "idle"
    assert session.collected_data == {}
    assert session.selected_option_id is None


def test_handle_menu_message_back_navigation_restores_previous_steps(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_try_execute_direct_option", lambda **kwargs: None)

    for message in ("1.4", "1", "1"):
        result = menu_engine.handle_menu_message(
            user_id=10,
            company_id=None,
            channel="whatsapp",
            thread_id="thread-1",
            message=message,
        )
        assert result.handled is True

    assert session.status == "awaiting_fields"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="voltar",
    )

    assert result.handled is True
    assert "Escolha o projeto ativo para a empresa AA - Versus" in result.response_text
    assert session.status == "awaiting_item_selection"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="voltar",
    )

    assert result.handled is True
    assert "Escolha a empresa para continuar:" in result.response_text
    assert session.status == menu_engine.COMPANY_SELECTION_STATUS

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="voltar",
    )

    assert result.handled is True
    assert result.response_text == "ROOT MENU"
    assert session.status == "idle"
