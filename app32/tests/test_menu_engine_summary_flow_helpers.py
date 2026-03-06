import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence import menu_engine
from services.project_task_service import ProjectTaskService
from models.agent_menu import AgentMenuOption


def test_summary_status_choices_contract():
    options = menu_engine._summary_status_choices()

    assert [item["index"] for item in options] == [1, 2, 3]
    assert [item["key"] for item in options] == ["open", "completed", "all"]
    assert [item["label"] for item in options] == ["Abertas", "Concluidas", "Todas"]


def test_extract_selection_index_only_accepts_plain_number():
    assert menu_engine._extract_selection_index("1") == 1
    assert menu_engine._extract_selection_index(" 2 ") == 2
    assert menu_engine._extract_selection_index("1: hoje") is None
    assert menu_engine._extract_selection_index("empresa 1") is None


def test_extract_selection_indexes_accepts_multi_and_all():
    assert menu_engine._extract_selection_indexes("1", allow_zero=True) == [1]
    assert menu_engine._extract_selection_indexes("1,3,4", allow_zero=True) == [1, 3, 4]
    assert menu_engine._extract_selection_indexes("1 3 4", allow_zero=True) == [1, 3, 4]
    assert menu_engine._extract_selection_indexes("0", allow_zero=True) == [0]
    assert menu_engine._extract_selection_indexes("0", allow_zero=False) is None
    assert menu_engine._extract_selection_indexes("1: hoje", allow_zero=True) is None


def test_format_summary_period_prompt_has_guidance():
    option = AgentMenuOption(code="3.5.4", title="Personalizado")
    text = menu_engine._format_summary_period_prompt(option)

    assert "3.5.4 - Personalizado" in text
    assert "DD/MM/AAAA a DD/MM/AAAA" in text
    assert "Exemplo: 01/03/2026 a 31/03/2026" in text


def test_apply_single_summary_company_selection():
    payload = {"periodo": "hoje"}
    choices = [
        {
            "index": 1,
            "company_id": 77,
            "company_name": "Empresa X",
            "label": "EX - Empresa X",
        }
    ]

    updated = menu_engine._apply_single_summary_company_selection(payload, choices)

    assert updated is not None
    assert updated["_summary_company_id"] == 77
    assert updated["_summary_company_label"] == "EX - Empresa X"
    assert updated["empresa"] == "Empresa X"


def test_apply_single_summary_company_selection_returns_none_for_multiple():
    payload = {"periodo": "hoje"}
    choices = [
        {"index": 1, "company_id": 1, "company_name": "A", "label": "A"},
        {"index": 2, "company_id": 2, "company_name": "B", "label": "B"},
    ]

    assert menu_engine._apply_single_summary_company_selection(payload, choices) is None


def test_is_affirmative_confirmation_text():
    assert menu_engine._is_affirmative_confirmation_text("sim")
    assert menu_engine._is_affirmative_confirmation_text("pode enviar por email")
    assert not menu_engine._is_affirmative_confirmation_text("nao")
    assert not menu_engine._is_affirmative_confirmation_text("")


def test_build_summary_email_subject_from_payload():
    payload = {
        "_summary_employee_name": "Fulano",
        "_summary_company_label": "AA - Empresa X",
        "periodo": "01/03/2026 a 31/03/2026",
        "status": "Todas",
    }
    subject = menu_engine._build_summary_email_subject_from_payload(payload)

    assert "Fulano" in subject
    assert "Empresa X" in subject
    assert "01/03/2026 a 31/03/2026" in subject


def test_summary_email_offer_has_two_options():
    offer = menu_engine.SUMMARY_EMAIL_OFFER_SUFFIX

    assert "1 - Enviar para meu e-mail cadastrado" in offer
    assert "2 - Informar outro e-mail" in offer


def test_whatsapp_summary_status_keeps_email_confirmation_flow(monkeypatch):
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)
    monkeypatch.setattr(
        menu_engine,
        "_execute_summary_menu_report",
        lambda **kwargs: "RELATORIO TESTE",
    )

    option = AgentMenuOption(code="3.5.2", title="Esta Semana")

    class DummySession:
        selected_option = option
        company_id = 1
        user_id = 10
        channel = "whatsapp"
        status = "awaiting_summary_status"
        missing_fields = []
        collected_data = {
            "_summary_status_choices": menu_engine._summary_status_choices(),
            "periodo": "Esta Semana",
            "colaborador": "Fabiano",
        }

    session = DummySession()

    result = menu_engine._handle_summary_status_state(session, "1", "1")

    assert result.handled is True
    assert "RELATORIO TESTE" in result.response_text
    assert "Enviar para meu e-mail cadastrado" in result.response_text
    assert session.status == menu_engine.SUMMARY_EMAIL_CONFIRM_STATUS
    assert session.collected_data["_summary_report_text"] == "RELATORIO TESTE"


def test_summary_collaborator_prompt_has_all_and_multi_hint():
    option = AgentMenuOption(code="3.5.1", title="Hoje")
    text = menu_engine._format_summary_collaborator_prompt(
        option,
        [
            {"index": 1, "label": "Fulano"},
            {"index": 2, "label": "Beltrano"},
        ],
    )

    assert "0 - Todos os colaboradores" in text
    assert "1,3,4" in text


def test_format_summary_collaborator_selection_label():
    assert menu_engine._format_summary_collaborator_selection_label([], all_selected=True) == "Todos os colaboradores"
    assert menu_engine._format_summary_collaborator_selection_label(["Fulano"]) == "Fulano"
    assert (
        menu_engine._format_summary_collaborator_selection_label(["Fulano", "Beltrano"])
        == "Fulano e Beltrano"
    )
    assert "e mais 1" in menu_engine._format_summary_collaborator_selection_label(
        ["A", "B", "C", "D"]
    )


def test_resolve_my_work_collaborator_label_handles_all_and_multi():
    assert (
        menu_engine._resolve_my_work_collaborator_label(
            payload={"colaborador": "Todos os colaboradores"},
            tasks=[],
            processes=[],
            fallback_name="Gestor",
        )
        == "de todos os colaboradores"
    )
    assert (
        menu_engine._resolve_my_work_collaborator_label(
            payload={"colaborador": "Fulano e Beltrano"},
            tasks=[],
            processes=[],
            fallback_name="Gestor",
        )
        == "dos colaboradores Fulano e Beltrano"
    )


def test_email_integration_record_detection_and_apply():
    record = {
        "id": "email_integration",
        "type": "email",
        "provider": "smtp",
        "config": {
            "provider": "smtp",
            "server": "smtp.empresa.com",
            "port": "465",
            "username": "bot@empresa.com",
            "password": "secret",
        },
    }

    assert menu_engine._is_email_integration_record(record)

    class DummyService:
        provider = "smtp"
        smtp_server = None
        smtp_port = 587
        smtp_username = None
        smtp_secret = None
        default_sender = None
        from_name = "Sapiens"
        webhook_url = None
        inbound_protocol = ""
        inbound_host = None
        inbound_port = 0
        inbound_username = None
        inbound_password = None
        inbound_use_ssl = True

    service = DummyService()
    menu_engine._apply_email_integration_to_service(service, record)

    assert service.provider == "smtp"
    assert service.smtp_server == "smtp.empresa.com"
    assert service.smtp_port == 465
    assert service.smtp_username == "bot@empresa.com"
    assert service.smtp_secret == "secret"


def test_email_validation_helpers():
    assert menu_engine._is_valid_email_address("user@example.com")
    assert not menu_engine._is_valid_email_address("user@example")
    assert menu_engine._extract_email_from_text("manda para abc.teste+1@empresa.com.br") == "abc.teste+1@empresa.com.br"
    assert menu_engine._extract_email_from_text("sem email") is None


def test_format_item_selection_prompt_for_project_picker_has_number_guidance():
    option = AgentMenuOption(code="1.4", title="Cadastrar Atividade de Projeto", action_key="project_task.create")

    text = menu_engine._format_item_selection_prompt(
        option,
        {
            "selection_kind": "project_picker",
            "scope_label": "empresa Save Water",
            "choices": [
                {
                    "index": 1,
                    "code": "SW.J.12",
                    "title": "Implantacao ERP",
                    "status": "in_progress",
                    "progress": 65,
                    "due_date": "2026-03-20",
                }
            ],
        },
    )

    assert "Escolha o projeto ativo para a empresa Save Water" in text
    assert "1 - SW.J.12 - Implantacao ERP" in text
    assert "Status: Em andamento" in text
    assert "Informe apenas o numero do projeto." in text
    assert "codigo_projeto: AA.J.12" in text


def test_handle_item_selection_state_for_project_picker_advances_to_remaining_fields(monkeypatch):
    monkeypatch.setattr(menu_engine.db.session, "commit", lambda: None)

    option = AgentMenuOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
        required_fields=[
            {"key": "codigo_projeto", "label": "Codigo do Projeto"},
            {"key": "nome_atividade", "label": "Nome da Atividade"},
        ],
    )

    class DummySession:
        selected_option = option
        status = "awaiting_item_selection"
        collected_data = {
            "_selection_action": "project_task.create",
            "_selection_kind": "project_picker",
            "_selection_field_key": "codigo_projeto",
            "_selection_value_key": "code",
            "_choices": [
                {"index": 1, "code": "SW.J.11", "title": "Projeto A"},
                {"index": 2, "code": "SW.J.22", "title": "Projeto B"},
            ],
        }
        missing_fields = []
        company_id = 1
        user_id = 99
        channel = "web"

    session = DummySession()
    result = menu_engine._handle_item_selection_state(session, "2", "2")

    assert result.handled is True
    assert result.response_text is not None
    assert "Nome da Atividade" in result.response_text
    assert "Codigo do Projeto" not in result.response_text
    assert session.status == "awaiting_fields"
    assert session.collected_data == {"codigo_projeto": "SW.J.22"}
    assert session.missing_fields == [{"key": "nome_atividade", "label": "Nome da Atividade"}]


def test_build_confirmation_display_items_formats_selected_project(monkeypatch):
    option = AgentMenuOption(code="1.4", title="Cadastrar Atividade de Projeto", action_key="project_task.create")
    monkeypatch.setattr(
        menu_engine,
        "_format_project_choice_line",
        lambda value: "SW.J.12 - Implantacao ERP | Status: Em andamento | Progresso: 65% | Prazo: 20/03/2026",
    )

    items = menu_engine._build_confirmation_display_items(
        option,
        {"codigo_projeto": "SW.J.12", "nome_atividade": "Configurar dashboards"},
    )

    assert items[0].startswith("SW.J.12 - Implantacao ERP")
    assert "nome_atividade: Configurar dashboards" in items


def test_handle_menu_message_keeps_awaiting_fields_on_numbered_reply_with_fluxo(monkeypatch):
    class DummySession:
        def __init__(self):
            self.status = "awaiting_fields"
            self.missing_fields = [{"key": "nome_atividade", "label": "Nome da Atividade"}]
            self.company_id = 1
            self.user_id = 10
            self.channel = "web"
            self.thread_id = "abc"
            self.was_reset = False

    session = DummySession()

    monkeypatch.setattr(menu_engine, "_ensure_default_menu_seed", lambda: None)
    monkeypatch.setattr(menu_engine, "_get_or_create_session", lambda **kwargs: session)
    monkeypatch.setattr(
        menu_engine,
        "_handle_missing_fields_state",
        lambda current_session, text, lower: menu_engine.MenuInterceptResult(
            handled=True,
            response_text=f"capturado:{text}",
        ),
    )
    monkeypatch.setattr(
        menu_engine,
        "_reset_session",
        lambda current_session: setattr(current_session, "was_reset", True),
    )

    result = menu_engine.handle_menu_message(
        user_id=10,
        company_id=1,
        channel="web",
        thread_id="abc",
        message="1: Teste Fabiano Fluxo",
    )

    assert result.handled is True
    assert result.response_text == "capturado:1: Teste Fabiano Fluxo"
    assert session.was_reset is False


def test_try_execute_direct_option_creates_project_task_with_canonical_code(monkeypatch):
    option = AgentMenuOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )

    class DummyTask:
        id = 31
        what = "Teste fabiano whatssapp"
        code = "AB.J.17.31"

    class DummyProject:
        id = 17
        name = "Lucro Real Gas Evolution"
        code = "AB.J.17"

    class DummyCompany:
        client_code = "AB"
        name = "Gas Evolution"

    captured = {}

    def fake_create_project_task(**kwargs):
        captured.update(kwargs)
        return (
            {
                "task": DummyTask(),
                "project": DummyProject(),
                "company": DummyCompany(),
                "responsible_name": "Fabiano Ferreira",
            },
            None,
        )

    monkeypatch.setattr(
        menu_engine,
        "_resolve_company_ids_for_payload",
        lambda payload, active_company_id, user_id: ([1], "empresa AB - Gas Evolution"),
    )
    monkeypatch.setattr(
        ProjectTaskService,
        "create_project_task",
        staticmethod(fake_create_project_task),
    )

    text = menu_engine._try_execute_direct_option(
        option=option,
        payload={
            "codigo_projeto": "AB.J.17",
            "nome_atividade": "Teste fabiano whatssapp",
        },
        company_id=1,
        user_id=10,
    )

    assert captured["project_code"] == "AB.J.17"
    assert captured["task_name"] == "Teste fabiano whatssapp"
    assert captured["allowed_company_ids"] == [1]
    assert text is not None
    assert "AB.J.17.31" in text
    assert "AB.C.1.3.1" not in text
    assert "Fabiano Ferreira" in text
