import os
import sys
from types import SimpleNamespace

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


def _build_my_work_open_option() -> AgentMenuOption:
    option = AgentMenuOption(
        code="3.1",
        title="Atividades em Aberto",
        action_key="my_work.open",
        required_fields=[],
    )
    option.id = 31
    return option


def _build_routine_consult_option() -> AgentMenuOption:
    option = AgentMenuOption(
        code="3.0",
        title="Consulta de Rotina",
        action_key="routine.consult",
        required_fields=[
            {"key": "empresa", "label": "Empresa", "required": True, "category": "required"},
            {"key": "periodo", "label": "Periodo", "required": False, "category": "optional"},
            {"key": "status_consulta", "label": "Status", "required": False, "category": "optional"},
            {"key": "entidade", "label": "Tipo de Item", "required": False, "category": "complementary"},
        ],
    )
    option.id = 30
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
    monkeypatch.setattr(menu_engine, "_resolve_user_first_name", lambda user_id: "Fabiano")
    monkeypatch.setattr(menu_engine, "_resolve_company_session_label", lambda company_id: "AA - Versus" if company_id else None)
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)
    monkeypatch.setattr(menu_engine, "_format_root_menu", lambda company_id: "ROOT MENU")


def test_handle_menu_message_project_task_create_full_cycle(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(
        menu_engine,
        "_try_execute_direct_option_result",
        lambda option, payload, company_id, user_id, channel="web": menu_engine.DirectExecutionResult(
            executed=bool(str(option.action_key or "").strip().lower() == "project_task.create" and payload.get("nome_atividade")),
            response_text=f"atividade criada: {payload.get('codigo_projeto')} - {payload.get('nome_atividade')}",
            metadata={},
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
    assert "Fluxo/Tool sugerido: 1.4 - Cadastrar Atividade de Projeto" in result.response_text
    assert "Fabiano" in result.response_text
    assert session.status == "awaiting_confirmation"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="sim",
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
    assert "Para executar, faltam os seguintes dados obrigatorios:" in result.response_text
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
    assert result.response_text == "atividade criada: AA.J.17 - Implementar Workflow V3"
    assert session.status == "idle"
    assert session.collected_data == {}
    assert session.selected_option_id is None


def test_handle_menu_message_back_navigation_restores_previous_steps(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(
        menu_engine,
        "_try_execute_direct_option_result",
        lambda **kwargs: menu_engine.DirectExecutionResult(executed=False, response_text="", metadata={}),
    )

    for message in ("1.4", "sim", "1", "1"):
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
    assert "1.4 - Cadastrar Atividade de Projeto" in result.response_text
    assert session.status == "awaiting_confirmation"


def test_handle_menu_message_operation_company_selection_executes_my_work_with_selected_company(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    captured = {}

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
                "company_name": "Gandu Investimentos e Participações",
                "company_code": "AU",
                "label": "AU - Gandu Investimentos e Participações",
            },
            {
                "index": 2,
                "company_id": 2,
                "company_name": "Gas Evolution",
                "company_code": "AB",
                "label": "AB - Gas Evolution",
            },
        ],
    )
    monkeypatch.setattr(
        menu_engine,
        "_resolve_explicit_company_id_from_payload",
        lambda payload, user_id: payload.get("_selected_company_id") or payload.get("_summary_company_id"),
    )
    monkeypatch.setattr(menu_engine, "_user_can_access_company", lambda user_id, company_id: company_id in {9, 2})
    monkeypatch.setattr(menu_engine, "_resolve_user_first_name", lambda user_id: "Fabiano")
    monkeypatch.setattr(menu_engine, "_resolve_company_session_label", lambda company_id: "ZZ - Sessao" if company_id else None)
    monkeypatch.setattr(
        menu_engine,
        "_try_execute_direct_option_result",
        lambda option, payload, company_id, user_id, channel="web": (
            captured.update({"payload": dict(payload), "company_id": company_id})
            or menu_engine.DirectExecutionResult(executed=True, response_text=f"OK empresa {company_id}", metadata={})
        ),
    )
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)
    monkeypatch.setattr(menu_engine, "_format_root_menu", lambda company_id: "ROOT MENU")

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-my-work",
        message="3.1",
    )

    assert result.handled is True
    assert "Fluxo/Tool sugerido: 3.1 - Atividades em Aberto" in result.response_text
    assert session.status == "awaiting_confirmation"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-my-work",
        message="sim",
    )

    assert result.handled is True
    assert "Escolha a empresa para continuar:" in result.response_text
    assert session.status == menu_engine.COMPANY_SELECTION_STATUS

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-my-work",
        message="1",
    )

    assert result.handled is True
    assert result.response_text == "OK empresa 9"
    assert captured["company_id"] == 9
    assert captured["payload"]["_selected_company_id"] == 9
    assert session.status == "idle"


def test_handle_menu_message_operation_company_selection_executes_routine_consult_with_selected_company(monkeypatch):
    option = _build_routine_consult_option()
    session = _DummySession(option)
    captured = {}

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
                "company_name": "Versus Gestao Corporativa",
                "company_code": "AA",
                "label": "AA - Versus Gestao Corporativa",
            },
            {
                "index": 2,
                "company_id": 12,
                "company_name": "Save Water",
                "company_code": "AL",
                "label": "AL - Save Water",
            },
        ],
    )
    monkeypatch.setattr(
        menu_engine,
        "_resolve_explicit_company_id_from_payload",
        lambda payload, user_id: payload.get("_selected_company_id") or payload.get("_summary_company_id"),
    )
    monkeypatch.setattr(menu_engine, "_user_can_access_company", lambda user_id, company_id: company_id in {9, 12})
    monkeypatch.setattr(menu_engine, "_resolve_user_first_name", lambda user_id: "Fabiano")
    monkeypatch.setattr(menu_engine, "_resolve_company_session_label", lambda company_id: "AA - Versus Gestao Corporativa" if company_id else None)
    monkeypatch.setattr(
        menu_engine,
        "_try_execute_direct_option_result",
        lambda option, payload, company_id, user_id, channel="web": (
            captured.update({"payload": dict(payload), "company_id": company_id, "channel": channel})
            or menu_engine.DirectExecutionResult(
                executed=True,
                response_text=f"consulta executada na empresa {company_id}",
                metadata={},
            )
        ),
    )
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)
    monkeypatch.setattr(menu_engine, "_format_root_menu", lambda company_id: "ROOT MENU")

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-routine",
        message="3.0",
    )

    assert result.handled is True
    assert "Fluxo/Tool sugerido: 3.0 - Consulta de Rotina" in result.response_text
    assert session.status == "awaiting_confirmation"

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-routine",
        message="sim",
    )

    assert result.handled is True
    assert "Escolha a empresa para continuar:" in result.response_text
    assert session.status == menu_engine.COMPANY_SELECTION_STATUS

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="thread-routine",
        message="1",
    )

    assert result.handled is True
    assert "Campos adicionais disponiveis antes da execucao." in result.response_text
    assert session.status == menu_engine.ADDITIONAL_FIELDS_STATUS
    assert session.collected_data["_selected_company_id"] == 9
    assert session.collected_data["empresa"] == "Versus Gestao Corporativa"
    assert "periodo" in {field.get("key") for field in (session.missing_fields or [])}
    assert captured == {}


def test_handle_menu_message_attaches_discovery_metadata_for_implicit_selection(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: True)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower_text, channel="web": (
            [option],
            {
                "strategy": "hybrid",
                "candidate_count": 1,
                "selected_code": option.code,
                "selected_action_key": option.action_key,
                "top_matches": [
                    {
                        "code": option.code,
                        "action_key": option.action_key,
                        "score": 96,
                        "reasons": ["semantic:atividade", "lexical:projeto"],
                    }
                ],
            },
        ),
    )
    monkeypatch.setattr(
        menu_engine,
        "_prepare_option_flow",
        lambda session, option, text, lower: menu_engine.MenuInterceptResult(
            handled=True,
            response_text="FLOW READY",
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="criar atividade do projeto",
    )

    assert result.handled is True
    assert result.response_text == "FLOW READY"
    assert result.metadata["menu_engine"]["intercept_stage"] == "implicit_discovery_selected"
    assert result.metadata["menu_engine"]["selected_option_code"] == option.code
    assert result.metadata["workflow_discovery"]["selected_action_key"] == option.action_key
    assert result.metadata["workflow_discovery"]["confidence"]["route"] == "select"


def test_get_or_create_session_reuses_external_thread_when_company_context_changes(monkeypatch):
    stored_session = SimpleNamespace(
        id=77,
        user_id=10,
        company_id=1,
        channel="whatsapp",
        thread_id="wa_5511999999999",
        status=menu_engine.COMPANY_SELECTION_STATUS,
        updated_at=1,
    )

    class _QueryStub:
        def __init__(self, exact_match, fallback_match):
            self._exact_match = exact_match
            self._fallback_match = fallback_match
            self._last_filters = ()

        def filter(self, *args):
            self._last_filters = args
            return self

        def order_by(self, *args):
            return self

        def first(self):
            if len(self._last_filters) >= 4:
                return self._exact_match
            return self._fallback_match

    class _AgentMenuSessionStub:
        class _Field:
            def __init__(self, name):
                self.name = name

            def __eq__(self, other):
                return (self.name, other)

            def desc(self):
                return self

        query = _QueryStub(exact_match=None, fallback_match=stored_session)
        user_id = _Field("user_id")
        company_id = _Field("company_id")
        channel = _Field("channel")
        thread_id = _Field("thread_id")
        updated_at = _Field("updated_at")
        id = _Field("id")

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    added = []

    monkeypatch.setattr(menu_engine, "AgentMenuSession", _AgentMenuSessionStub)
    monkeypatch.setattr(menu_engine.db.session, "add", lambda session: added.append(session))
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)

    session = menu_engine._get_or_create_session(
        user_id=10,
        company_id=9,
        channel="whatsapp",
        thread_id="wa_5511999999999",
    )

    assert session is stored_session
    assert added == []


def test_handle_menu_message_auto_selects_clear_winner_even_with_multiple_candidates(monkeypatch):
    option = _build_project_task_option()
    other = AgentMenuOption(
        code="1.5",
        title="Finalizar Atividade de Projeto",
        action_key="project_task.complete",
        required_fields=[{"key": "codigo_atividade", "label": "Codigo da Atividade"}],
    )
    other.id = 15
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: True)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower_text, channel="web": (
            [option, other],
            {
                "strategy": "hybrid",
                "candidate_count": 2,
                "selected_code": option.code,
                "selected_action_key": option.action_key,
                "top_matches": [
                    {
                        "code": option.code,
                        "action_key": option.action_key,
                        "score": 42,
                        "reasons": ["semantic:atividade", "lexical:cadastro"],
                    },
                    {
                        "code": other.code,
                        "action_key": other.action_key,
                        "score": 24,
                        "reasons": ["semantic:concluir"],
                    },
                ],
            },
        ),
    )
    monkeypatch.setattr(
        menu_engine,
        "_prepare_option_flow",
        lambda session, option, text, lower: menu_engine.MenuInterceptResult(
            handled=True,
            response_text=f"FLOW:{option.code}",
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="quero cadastrar atividade",
    )

    assert result.handled is True
    assert result.response_text == "FLOW:1.4"
    assert result.metadata["workflow_discovery"]["confidence"]["route"] == "select"
    assert result.metadata["workflow_discovery"]["confidence"]["reason"] == "clear_winner"


def test_handle_menu_message_attaches_discovery_metadata_for_ambiguous_selection(monkeypatch):
    option = _build_project_task_option()
    other = AgentMenuOption(
        code="1.5",
        title="Finalizar Atividade de Projeto",
        action_key="project_task.complete",
        required_fields=[{"key": "codigo_atividade", "label": "Codigo da Atividade"}],
    )
    other.id = 15
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: True)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower_text, channel="web": (
            [option, other],
            {
                "strategy": "hybrid",
                "candidate_count": 2,
                "selected_code": option.code,
                "selected_action_key": option.action_key,
                "top_matches": [
                    {
                        "code": option.code,
                        "action_key": option.action_key,
                        "score": 72,
                        "reasons": ["semantic:atividade"],
                    },
                    {
                        "code": other.code,
                        "action_key": other.action_key,
                        "score": 71,
                        "reasons": ["semantic:concluir"],
                    },
                ],
            },
        ),
    )
    monkeypatch.setattr(menu_engine, "_format_ambiguous_options", lambda candidates: "AMBIGUO")

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="atividade do projeto",
    )

    assert result.handled is True
    assert result.response_text == "AMBIGUO"
    assert result.metadata["menu_engine"]["intercept_stage"] == "implicit_discovery_ambiguous"
    assert result.metadata["workflow_discovery"]["candidate_count"] == 2
    assert len(result.metadata["workflow_discovery"]["top_matches"]) == 2
    assert result.metadata["workflow_discovery"]["confidence"]["route"] == "ambiguous"



def test_handle_menu_message_attaches_discovery_metadata_for_no_match(monkeypatch):
    option = _build_project_task_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: True)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower_text, channel="web": (
            [],
            {
                "strategy": "hybrid",
                "candidate_count": 0,
                "top_matches": [],
            },
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="quero uma analise de ocupacao do usuario x",
    )

    assert result.handled is False
    assert result.metadata["menu_engine"]["intercept_stage"] == "implicit_discovery_no_match"
    assert result.metadata["menu_engine"]["handled"] is False
    assert result.metadata["workflow_discovery"]["confidence"]["route"] == "no_match"


def test_looks_like_command_accepts_operational_query_in_natural_language():
    assert (
        menu_engine._looks_like_command(
            "quais as atividades abertas da ventana com os responsável márcio simoes"
        )
        is True
    )


def test_looks_like_command_accepts_hitl_approval_short_reply():
    assert menu_engine._looks_like_command("aprovado.") is True


def test_looks_like_command_accepts_deadline_rewrite_short_phrase():
    assert menu_engine._looks_like_command("coloque todas para o dia 31/03/2026") is True


def test_looks_like_command_accepts_batch_task_completion_phrase():
    assert menu_engine._looks_like_command("Pode dar como concluida as atividades de IDs: 24 e 323") is True


def test_looks_like_command_accepts_task_completion_without_ids():
    assert menu_engine._looks_like_command("Pode dar como concluída as atividades") is True


def test_looks_like_command_accepts_my_companies_query():
    assert menu_engine._looks_like_command("Quantas empresas estão vinculadas a mim atualmente?") is True


def test_extract_fields_from_text_infers_company_collaborator_and_period():
    payload = menu_engine._extract_fields_from_text(
        "Quais as instâncias atrasadas para Caroline Marques da empresa Gandu Investimentos esta semana?"
    )

    assert payload["empresa"] == "Gandu Investimentos"
    assert payload["colaborador"] == "Caroline Marques"
    assert payload["periodo"] == "esta semana"
    assert payload["entidade"] == "process_instance"
    assert payload["status_consulta"] == "overdue"


def test_extract_fields_from_text_infers_project_task_scope_and_open_status():
    payload = menu_engine._extract_fields_from_text(
        "Quais são as atividades em aberto para Joaquim Guga na empresa Gandu Investimentos?"
    )

    assert payload["empresa"] == "Gandu Investimentos"
    assert payload["colaborador"] == "Joaquim Guga"
    assert payload["entidade"] == "project_task"
    assert payload["status_consulta"] == "open"


def test_extract_fields_from_text_strips_company_suffix_from_collaborator_with_accents():
    payload = menu_engine._extract_fields_from_text(
        "Quais as atividades em aberto para Márcio Simões da empresa Ventana?"
    )

    assert payload["empresa"] == "Ventana"
    assert payload["colaborador"] == "Márcio Simões"
    assert payload["entidade"] == "project_task"
    assert payload["status_consulta"] == "open"


def test_extract_fields_from_text_infers_implicit_company_alias_without_keyword_empresa():
    payload = menu_engine._extract_fields_from_text(
        "Quero as atividades abertas da Ventana com os Responsável Márcio Simoes"
    )

    assert payload["empresa"] == "Ventana"
    assert payload["colaborador"] == "Márcio Simoes"
    assert payload["entidade"] == "project_task"
    assert payload["status_consulta"] == "open"


def test_extract_fields_from_text_infers_due_range_period_for_today_queue_language():
    payload = menu_engine._extract_fields_from_text(
        "Me diga o que temos para fazer hoje?"
    )

    assert payload["periodo"] == "hoje"
    assert "colaborador" not in payload


def test_extract_fields_from_text_infers_month_period_for_pending_company_queue():
    payload = menu_engine._extract_fields_from_text(
        "Preciso saber o que tenho de atividades pendentes para este mês na empresa Gás Evolution"
    )

    assert payload["empresa"] == "Gás Evolution"
    assert payload["entidade"] == "project_task"
    assert payload["status_consulta"] == "open"
    assert payload["periodo"] == "este mes"
    assert "colaborador" not in payload


def test_extract_fields_from_text_avoids_false_positive_collaborator_for_week_period():
    payload = menu_engine._extract_fields_from_text(
        "Qual atividades eu tenho pendente para esta semana na empresa versus gestão corporativa"
    )

    assert payload["empresa"] == "versus gestão corporativa"
    assert payload["periodo"] == "esta semana"
    assert "colaborador" not in payload


def test_handle_menu_message_greeting_only_offers_menu_or_free_question(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: False)

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="oi",
    )

    assert result.handled is True
    assert "Olá Fabiano! Espero que esteja bem." in result.response_text
    assert "digitar menu" in result.response_text
    assert "pergunta diretamente" in result.response_text
    assert result.metadata["menu_engine"]["intercept_stage"] == "greeting_only"


def test_handle_menu_message_clear_operational_request_does_not_fall_into_greeting(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    _install_common_patches(monkeypatch, session, option)
    monkeypatch.setattr(menu_engine, "_looks_like_command", lambda lower: True)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower, channel="web": (
            [option],
            {"strategy": "implicit", "top_matches": [{"code": option.code, "score": 0.93}]},
        ),
    )

    class _Decision:
        route = menu_engine.DISCOVERY_CONFIDENCE_ROUTE_SELECT
        selected_code = option.code
        candidate_codes = [option.code]
        reason = "clear_winner"

    monkeypatch.setattr(
        menu_engine,
        "_build_workflow_discovery_confidence_policy",
        lambda: SimpleNamespace(decide=lambda matches: _Decision()),
    )
    monkeypatch.setattr(menu_engine, "attach_confidence_decision_to_trace", lambda trace, decision: trace)
    monkeypatch.setattr(
        menu_engine,
        "_prepare_option_flow",
        lambda session, option, text, lower: menu_engine.MenuInterceptResult(
            handled=True,
            response_text="WORKFLOW OK",
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=None,
        channel="whatsapp",
        thread_id="thread-1",
        message="Quais atividades tenho para hoje?",
    )

    assert result.handled is True
    assert result.response_text == "WORKFLOW OK"
    assert result.metadata["menu_engine"]["intercept_stage"] == "implicit_discovery_selected"


def test_extract_fields_from_text_strips_trailing_preposition_from_collaborator():
    payload = menu_engine._extract_fields_from_text(
        "gostaria de saber as atividade vencidas de Caroline Marques na empresa Gandu Motor"
    )

    assert payload["empresa"] == "Gandu Motor"
    assert payload["colaborador"] == "Caroline Marques"
    assert payload["status_consulta"] == "overdue"


def test_extract_fields_from_text_infers_batch_ids_for_completion():
    payload = menu_engine._extract_fields_from_text(
        "Pode dar como concluida as atividades de IDs: 24 e 323"
    )

    assert payload["ids"] == "24,323"
    assert payload["codigo_atividade"] == "24,323"


def test_extract_fields_from_text_accepts_company_alias_shortcut():
    payload = menu_engine._extract_fields_from_text("AU - Gandu Investimentos e Participações")

    assert payload["empresa"] == "AU - Gandu Investimentos e Participações"


def test_extract_fields_from_text_detects_agent_action_approval_command():
    payload = menu_engine._extract_fields_from_text("aprovar 331")

    assert payload["agent_action_operation"] == "approve"
    assert payload["agent_action_id"] == "331"


def test_extract_fields_from_text_detects_deadline_update_command():
    payload = menu_engine._extract_fields_from_text("coloque todas para o dia 31/03/2026")

    assert payload["due_date"] == "31/03/2026"
    assert payload["prazo"] == "31/03/2026"


def test_handle_menu_message_prompts_context_disambiguation_for_new_command_during_pending_summary(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    session.status = menu_engine.SUMMARY_EMAIL_CONFIRM_STATUS
    session.selected_option_id = option.id
    session.collected_data = {"_summary_report_text": "RELATORIO TESTE"}

    monkeypatch.setattr(menu_engine, "_ensure_default_menu_seed", lambda: None)
    monkeypatch.setattr(menu_engine, "_get_or_create_session", lambda **kwargs: session)
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=9,
        channel="whatsapp",
        thread_id="thread-ctx",
        message="Quais as atividades eu tenho para hoje?",
    )

    assert result.handled is True
    assert "1 - Nova conversa" in result.response_text
    assert session.status == menu_engine.CONTEXT_DISAMBIGUATION_STATUS
    assert session.collected_data["_context_disambiguation_pending_message"] == "Quais as atividades eu tenho para hoje?"


def test_handle_menu_message_context_disambiguation_new_conversation_replays_pending_message(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    session.status = menu_engine.CONTEXT_DISAMBIGUATION_STATUS
    session.selected_option_id = option.id
    session.collected_data = {
        "_summary_report_text": "RELATORIO TESTE",
        "_context_disambiguation_previous_status": menu_engine.SUMMARY_EMAIL_CONFIRM_STATUS,
        "_context_disambiguation_pending_message": "Quais as atividades eu tenho para hoje?",
    }

    monkeypatch.setattr(menu_engine, "_ensure_default_menu_seed", lambda: None)
    monkeypatch.setattr(menu_engine, "_get_or_create_session", lambda **kwargs: session)
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)
    monkeypatch.setattr(
        menu_engine,
        "_discover_options_by_keywords",
        lambda company_id, lower_text, channel="web": ([option], {"top_matches": [{"code": option.code}]}),
    )

    class _Decision:
        route = menu_engine.DISCOVERY_CONFIDENCE_ROUTE_SELECT
        selected_code = option.code
        candidate_codes = [option.code]

    monkeypatch.setattr(
        menu_engine,
        "_build_workflow_discovery_confidence_policy",
        lambda: type("P", (), {"decide": lambda self, matches: _Decision()})(),
    )
    monkeypatch.setattr(menu_engine, "attach_confidence_decision_to_trace", lambda trace, decision: trace)

    captured = {}
    monkeypatch.setattr(
        menu_engine,
        "_prepare_option_flow",
        lambda current_session, selected_option, text, lower: (
            captured.update({"message": text}) or menu_engine.MenuInterceptResult(handled=True, response_text="ATIVIDADES DE HOJE")
        ),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=9,
        channel="whatsapp",
        thread_id="thread-ctx",
        message="1",
    )

    assert result.handled is True
    assert result.response_text == "ATIVIDADES DE HOJE"
    assert captured["message"] == "Quais as atividades eu tenho para hoje?"
    assert session.status == "idle"


def test_handle_menu_message_context_disambiguation_continue_restores_previous_flow(monkeypatch):
    option = _build_my_work_open_option()
    session = _DummySession(option)
    session.status = menu_engine.CONTEXT_DISAMBIGUATION_STATUS
    session.selected_option_id = option.id
    session.missing_fields = []
    session.collected_data = {
        "_summary_report_text": "RELATORIO TESTE",
        "_context_disambiguation_previous_status": menu_engine.SUMMARY_EMAIL_CONFIRM_STATUS,
        "_context_disambiguation_pending_message": "Quais as atividades eu tenho para hoje?",
    }

    monkeypatch.setattr(menu_engine, "_ensure_default_menu_seed", lambda: None)
    monkeypatch.setattr(menu_engine, "_get_or_create_session", lambda **kwargs: session)
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(menu_engine.db.session, "rollback", lambda: None)

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=9,
        channel="whatsapp",
        thread_id="thread-ctx",
        message="2",
    )

    assert result.handled is True
    assert "continue a solicitacao atual com mais detalhes" in result.response_text
    assert session.status == menu_engine.SUMMARY_EMAIL_CONFIRM_STATUS


def test_extract_choice_index_from_text_matches_company_alias_or_label():
    choices = [
        {
            "index": 1,
            "company_id": 7,
            "company_name": "Gandu Investimentos e Participações",
            "company_code": "AU",
            "label": "AU - Gandu Investimentos e Participações",
        }
    ]

    assert menu_engine._extract_choice_index_from_text("AU", choices) == 1
    assert menu_engine._extract_choice_index_from_text(
        "AU - Gandu Investimentos e Participações",
        choices,
    ) == 1


def test_extract_choice_index_from_text_matches_collaborator_name():
    choices = [{"index": 2, "employee_id": 55, "name": "Fabiano"}]

    assert menu_engine._extract_choice_index_from_text("Fabiano", choices) == 2


def test_extract_fields_from_text_parses_occupancy_without_false_collaborator_suffix():
    payload = menu_engine._extract_fields_from_text(
        "me diga a ocupação de Caroline Marques este mes."
    )

    assert payload["colaborador"] == "Caroline Marques"
    assert payload["periodo"] == "este mes"


def test_extract_fields_from_text_does_not_infer_collaborator_for_cross_company_analytics():
    payload = menu_engine._extract_fields_from_text(
        "Analise as atividades de projetos que estão sem responsável, de todas as empresas."
    )

    assert payload["entidade"] == "project_task"
    assert "colaborador" not in payload


def test_extract_fields_from_text_captures_pending_action_limit_without_false_company():
    payload = menu_engine._extract_fields_from_text(
        "Liste 20 ações do sistema que estão aguardando minha decisão."
    )

    assert payload["limite"] == "20"
    assert "empresa" not in payload


def test_extract_fields_from_text_detects_project_task_audit_missing_responsible():
    payload = menu_engine._extract_fields_from_text(
        "Analise as atividades de projetos que estão sem responsável, de todas as empresas."
    )

    assert payload["entidade"] == "project_task"
    assert payload["tipo_auditoria"] == "missing_responsible"


def test_extract_fields_from_text_detects_project_task_audit_missing_due_date():
    payload = menu_engine._extract_fields_from_text(
        "analise as atividades de todas as empresas que estão sem data."
    )

    assert payload["entidade"] == "project_task"
    assert payload["tipo_auditoria"] == "missing_due_date"


def test_extract_fields_from_text_preserves_mixed_entity_when_tasks_and_instances_are_requested():
    payload = menu_engine._extract_fields_from_text(
        "Me dê as atividades e instâncias de Joaquim Guga da empresa Gandu Investimentos"
    )

    assert payload["empresa"] == "Gandu Investimentos"
    assert payload["colaborador"] == "Joaquim Guga"
    assert payload["entidade"] == "mixed"


def test_extract_fields_from_text_handles_mixed_entity_question_with_que_and_open_suffix():
    payload = menu_engine._extract_fields_from_text(
        "Quais as atividades e instâncias que Joaquim Guga da empresa Gandu Investimentos tem em aberto?"
    )

    assert payload["empresa"] == "Gandu Investimentos"
    assert payload["colaborador"] == "Joaquim Guga"
    assert payload["entidade"] == "mixed"
    assert payload["status_consulta"] == "open"


def test_extract_fields_from_text_does_not_capture_full_question_as_collaborator():
    payload = menu_engine._extract_fields_from_text(
        "Quais as atividades eu tenho vencidas na empresa Versus Gestão Corporativa?"
    )

    assert payload["empresa"] == "Versus Gestão Corporativa"
    assert "colaborador" not in payload


def test_extract_fields_from_text_detects_explicit_usuario_collaborator():
    payload = menu_engine._extract_fields_from_text(
        "Quais as atividades o usuário Caroline Marques tem vencidas?"
    )

    assert payload["colaborador"] == "Caroline Marques"
    assert payload["status_consulta"] == "overdue"


def test_extract_numbered_fields_from_text_accepts_whatsapp_hyphen_format():
    parsed = menu_engine.extract_workflow_numbered_fields_from_text(
        "1 - Caroline Marques",
        [{"key": "colaborador", "label": "Colaborador", "required": False, "category": "optional"}],
    )

    assert parsed["colaborador"] == "Caroline Marques"


def test_extract_numbered_fields_from_text_ignores_bare_numeric_reply_for_single_optional_field():
    parsed = menu_engine.extract_workflow_numbered_fields_from_text(
        "1",
        [{"key": "colaborador", "label": "Colaborador", "required": False, "category": "optional"}],
    )

    assert parsed == {}


def test_build_auto_filled_session_lines_prefers_explicit_company_over_active_company():
    lines = menu_engine._build_auto_filled_session_lines(
        {
            "_session_user_name": "Fabiano",
            "_session_company_label": "AL - Save Water",
            "_resolved_company_label": "AA - Versus Gestao Corporativa",
        }
    )

    assert "Usuario: Fabiano" in lines
    assert "Empresa da consulta: AA - Versus Gestao Corporativa" in lines
    assert all("Save Water" not in line for line in lines)


def test_adjust_required_fields_for_context_normalizes_my_work_collaborator_as_optional():
    fields = menu_engine.adjust_workflow_required_fields_for_context(
        "my_work.overdue",
        [
            menu_engine.WorkflowRequiredField(key="empresa", label="Empresa", required=True, category="required"),
            menu_engine.WorkflowRequiredField(key="colaborador", label="Colaborador", required=True, category="required"),
            menu_engine.WorkflowRequiredField(key="colaborador", label="Colaborador", required=False, category="optional"),
            menu_engine.WorkflowRequiredField(key="entidade", label="Tipo de Item", required=True, category="required"),
        ],
    )

    normalized = {field.key: field for field in fields}
    assert "empresa" not in normalized
    assert normalized["colaborador"].required is False
    assert normalized["colaborador"].category == "optional"
    assert normalized["entidade"].required is False
    assert normalized["entidade"].category == "complementary"
