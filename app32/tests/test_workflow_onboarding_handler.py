import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    OnboardingDiagnoseExecutionHandler,
    OnboardingDiagnoseRequest,
    OnboardingGoLiveCheckExecutionHandler,
    OnboardingGoLiveCheckRequest,
    OnboardingStartExecutionHandler,
    OnboardingStartRequest,
    OnboardingStatusExecutionHandler,
    OnboardingStatusRequest,
)


def _company(**overrides):
    payload = {
        "id": 9,
        "client_code": "AA",
        "name": "Versus",
        "segment": "Consultoria",
        "city": "Salvador",
        "state": "BA",
        "mission": "Missao",
        "vision": "Visao",
        "values": "Valores",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_onboarding_status_handler_reports_incomplete_fields():
    handler = OnboardingStatusExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(segment=None, mission=None),
    )

    result = handler.execute(
        OnboardingStatusRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "INCOMPLETO" in result.response_text
    assert "Segmento" in result.response_text
    assert "Missao" in result.response_text


def test_onboarding_status_handler_reports_complete():
    handler = OnboardingStatusExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(),
    )

    result = handler.execute(
        OnboardingStatusRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "COMPLETO" in result.response_text
    assert "100%" in result.response_text


def test_onboarding_go_live_check_handler_reports_blockers():
    handler = OnboardingGoLiveCheckExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(client_code=None, segment=None),
        load_operational_metrics=lambda company_id: {
            "active_employees": 0,
            "employees_with_any_contact": 0,
            "projects_count": 0,
            "open_tasks_count": 0,
            "processes_count": 0,
            "open_instances_count": 0,
            "meetings_count": 0,
        },
    )

    result = handler.execute(
        OnboardingGoLiveCheckRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "NAO PRONTO" in result.response_text
    assert "Bloqueadores:" in result.response_text
    assert "Campos cadastrais essenciais pendentes" in result.response_text


def test_onboarding_go_live_check_handler_reports_ready_with_alerts():
    handler = OnboardingGoLiveCheckExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(),
        load_operational_metrics=lambda company_id: {
            "active_employees": 10,
            "employees_with_any_contact": 3,
            "projects_count": 2,
            "open_tasks_count": 0,
            "processes_count": 1,
            "open_instances_count": 0,
            "meetings_count": 0,
        },
    )

    result = handler.execute(
        OnboardingGoLiveCheckRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "PRONTO COM ALERTAS" in result.response_text
    assert "Alertas:" in result.response_text


def test_onboarding_start_handler_validates_type_and_creates_real_session():
    created = {}
    handler = OnboardingStartExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        create_session=lambda user_id, onboarding_type, company_id: (
            created.update(
                {
                    "user_id": user_id,
                    "onboarding_type": onboarding_type,
                    "company_id": company_id,
                }
            )
            or SimpleNamespace(id=55)
        ),
    )

    invalid = handler.execute(
        OnboardingStartRequest(
            payload={"tipo": "desconhecido"},
            active_company_id=9,
            user_id=10,
        )
    )
    valid = handler.execute(
        OnboardingStartRequest(
            payload={"tipo": "real"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert invalid.response_text == "Tipo de cadastro invalido. Use: real ou modelo."
    assert created == {"user_id": 10, "onboarding_type": "real", "company_id": 9}
    assert "Sessao de onboarding iniciada com sucesso (ID 55)." in valid.response_text
    assert "informe o CNPJ" in valid.response_text


def test_onboarding_diagnose_handler_reports_pending_and_suggestions():
    handler = OnboardingDiagnoseExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(mission=None, vision=None),
        normalize_objective=lambda raw: "reunioes",
        format_objective_label=lambda raw: "Reunioes",
        load_diagnostic_metrics=lambda company_id: {
            "active_employees": 5,
            "roles_count": 1,
            "projects_count": 1,
            "open_tasks_count": 1,
            "processes_count": 1,
            "open_instances_count": 1,
            "meetings_count": 0,
            "employees_with_telegram": 0,
            "employees_with_whatsapp": 0,
            "employees_with_email": 0,
            "employees_with_any_contact": 0,
        },
    )

    result = handler.execute(
        OnboardingDiagnoseRequest(
            payload={"objetivo": "reunioes"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "Diagnostico de funcionamento (Reunioes) - AA - Versus" in result.response_text
    assert "Pendencias para funcionar melhor:" in result.response_text
    assert "Nao ha reunioes cadastradas." in result.response_text
    assert "Proximos passos sugeridos:" in result.response_text


def test_onboarding_diagnose_handler_reports_ready_status_when_no_pending():
    handler = OnboardingDiagnoseExecutionHandler(
        resolve_single_company_for_operation=lambda payload, active_company_id, user_id, allow_none_company: (9, None),
        load_company_by_id=lambda company_id: _company(),
        normalize_objective=lambda raw: "geral",
        format_objective_label=lambda raw: "Geral",
        load_diagnostic_metrics=lambda company_id: {
            "active_employees": 5,
            "roles_count": 2,
            "projects_count": 3,
            "open_tasks_count": 2,
            "processes_count": 2,
            "open_instances_count": 1,
            "meetings_count": 2,
            "employees_with_telegram": 2,
            "employees_with_whatsapp": 3,
            "employees_with_email": 5,
            "employees_with_any_contact": 5,
        },
    )

    result = handler.execute(
        OnboardingDiagnoseRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "Status: pronto para operacao no objetivo informado." in result.response_text
