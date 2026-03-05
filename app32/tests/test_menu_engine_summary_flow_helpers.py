import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence import menu_engine
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
