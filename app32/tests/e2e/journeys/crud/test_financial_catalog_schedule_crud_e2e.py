from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


def _q(path: str, company_id: int) -> str:
    return f"{path}?company_id={company_id}"


def _suffix(run_id: str) -> str:
    return "".join(ch for ch in run_id if ch.isdigit())[-10:] or "0000000000"


def _catalog_create(http: AuthenticatedHTTPSession, company_id: int, catalog_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return http.request_json(
        "POST",
        _q(f"/api/financial/catalogs/{catalog_type}", company_id),
        json_payload=payload,
        operation=f"financial.catalog.{catalog_type}.create",
    )


def _catalog_update(
    http: AuthenticatedHTTPSession,
    company_id: int,
    catalog_type: str,
    item_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return http.request_json(
        "PUT",
        _q(f"/api/financial/catalogs/{catalog_type}/{item_id}", company_id),
        json_payload=payload,
        operation=f"financial.catalog.{catalog_type}.update",
    )


def _catalog_delete(http: AuthenticatedHTTPSession, company_id: int, catalog_type: str, item_id: int) -> dict[str, Any]:
    return http.request_json(
        "DELETE",
        _q(f"/api/financial/catalogs/{catalog_type}/{item_id}", company_id),
        operation=f"financial.catalog.{catalog_type}.delete",
    )


@pytest.mark.e2e
@pytest.mark.dev_full
def test_financial_catalog_schedule_transactional_e2e(
    e2e_settings: E2EEnvironmentSettings,
    e2e_run_context,
):
    if e2e_settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("CRUD financeiro destrutivo só deve rodar em DEV_FULL.")
    if e2e_settings.missing_requirements:
        pytest.skip(
            "Configuração E2E incompleta. Defina: "
            + ", ".join(e2e_settings.missing_requirements)
        )
    if not e2e_settings.company_id:
        pytest.skip("E2E_COMPANY_ID obrigatório para jornada financeira.")

    company_id = int(e2e_settings.company_id)
    run_suffix = _suffix(e2e_run_context.evidence.run_id)
    # Deliberadamente não gravamos AUTOE2E::<run_id> em tabelas financeiras,
    # porque parte do domínio usa soft delete e a auditoria varre também linhas
    # excluídas logicamente. Os IDs retornados pela API são a trilha de cleanup.
    neutral_prefix = f"E2E{run_suffix}"

    journey = e2e_run_context.reporter.start_journey(
        journey="financial_catalog_schedule_transactional_e2e",
        run_id=e2e_run_context.evidence.run_id,
        company_id=company_id,
        user_label=e2e_settings.username,
        metadata={"domain": "financial", "mode": e2e_settings.environment_name},
    )

    http = AuthenticatedHTTPSession.create(e2e_settings)
    journey.step("http_login", status="running")
    login_payload = http.login()
    http.select_company()
    journey.step("http_login", status="passed", details={"redirect": login_payload.get("redirect")})

    created: dict[str, int] = {}
    schedule_id: int | None = None
    today = date.today()
    due_date = today + timedelta(days=7)

    try:
        journey.step("create_financial_catalogs", status="running")
        bank_account = _catalog_create(
            http,
            company_id,
            "bank_accounts",
            {
                "code": f"BA{run_suffix[-8:]}",
                "name": f"Conta QA {neutral_prefix}",
                "bank_code": "001",
                "bank_name": "Banco QA",
                "branch_number": "0001",
                "account_number": f"9{run_suffix[-7:]}",
                "account_digit": "0",
                "holder_name": "M1 Testes Versus",
                "holder_document": "00000000000191",
                "currency_code": "BRL",
                "metadata_json": {"e2e": True, "scope": "financial_transactional"},
            },
        )
        created["bank_accounts"] = int(bank_account["id"])

        chart_account = _catalog_create(
            http,
            company_id,
            "chart_accounts",
            {
                "code": f"91{run_suffix[-6:]}",
                "name": f"Despesa QA {neutral_prefix}",
                "movement_nature": "debit",
                "accepts_posting": True,
                "account_level_type": "analytic",
                "metadata_json": {"e2e": True},
            },
        )
        created["chart_accounts"] = int(chart_account["id"])

        cost_center = _catalog_create(
            http,
            company_id,
            "cost_centers",
            {
                "code": f"92{run_suffix[-6:]}",
                "name": f"Centro QA {neutral_prefix}",
                "description": "Centro temporário de validação financeira",
                "accepts_posting": True,
                "account_level_type": "analytic",
                "metadata_json": {"e2e": True},
            },
        )
        created["cost_centers"] = int(cost_center["id"])

        counterparty = _catalog_create(
            http,
            company_id,
            "counterparties",
            {
                "code": f"CP{run_suffix[-8:]}",
                "name": f"Favorecido QA {neutral_prefix}",
                "legal_name": f"Favorecido QA Ltda {neutral_prefix}",
                "document_number": "00000000000191",
                "email": "qa-financeiro@example.invalid",
                "is_supplier": True,
                "is_customer": False,
                "default_chart_account_id": created["chart_accounts"],
                "default_cost_center_id": created["cost_centers"],
                "metadata_json": {"e2e": True},
            },
        )
        created["counterparties"] = int(counterparty["id"])

        payment_method = _catalog_create(
            http,
            company_id,
            "payment_methods",
            {
                "code": f"PM{run_suffix[-8:]}",
                "name": f"Forma QA {neutral_prefix}",
                "operation_type": "payable",
                "settlement_days": 0,
                "description": "Forma temporária de validação financeira",
                "metadata_json": {"e2e": True},
            },
        )
        created["payment_methods"] = int(payment_method["id"])
        journey.step("create_financial_catalogs", status="passed", details=created)

        journey.step("update_catalogs", status="running")
        updated_bank = _catalog_update(
            http,
            company_id,
            "bank_accounts",
            created["bank_accounts"],
            {"name": f"Conta QA Editada {neutral_prefix}", "pix_key": f"qa-{run_suffix}@example.invalid"},
        )
        assert updated_bank["name"].startswith("Conta QA Editada")
        updated_counterparty = _catalog_update(
            http,
            company_id,
            "counterparties",
            created["counterparties"],
            {"notes": "Favorecido validado e pronto para título financeiro"},
        )
        assert updated_counterparty["id"] == created["counterparties"]
        journey.step("update_catalogs", status="passed")

        journey.step("create_schedule", status="running")
        schedule_payload = {
            "schedule_code": f"SC{run_suffix[-8:]}",
            "name": f"Título QA {neutral_prefix}",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "draft",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": today.isoformat(),
            "competence_date": today.isoformat(),
            "first_due_date": due_date.isoformat(),
            "next_due_date": due_date.isoformat(),
            "description": "Título financeiro temporário para validação transacional",
            "memo": "Criado, editado, cancelado e excluído pelo harness transacional",
            "document_number_prefix": f"DOC{run_suffix[-8:]}",
            "template_amount": "123.45",
            "currency_code": "BRL",
            "auto_post": False,
            "generate_advance_days": 0,
            "bank_account_id": created["bank_accounts"],
            "counterparty_id": created["counterparties"],
            "chart_account_id": created["chart_accounts"],
            "cost_center_id": created["cost_centers"],
            "notes": "Título temporário de QA financeiro",
            "metadata_json": {"e2e": True, "cleanup": "delete_after_cancel"},
        }
        schedule = http.request_json(
            "POST",
            _q("/api/financial/schedules", company_id),
            json_payload=schedule_payload,
            operation="financial.schedule.create",
        )
        schedule_id = int(schedule["id"])
        assert schedule["company_id"] == company_id
        journey.step("create_schedule", status="passed", details={"schedule_id": schedule_id})

        journey.step("validate_schedule_detail", status="running")
        detail = http.request_json(
            "GET",
            _q(f"/api/financial/schedules/{schedule_id}", company_id),
            operation="financial.schedule.detail",
        )
        assert detail["id"] == schedule_id
        assert detail["counterparty_id"] == created["counterparties"]
        assert detail["chart_account_id"] == created["chart_accounts"]
        assert detail["cost_center_id"] == created["cost_centers"]
        journey.step("validate_schedule_detail", status="passed")

        journey.step("update_and_cancel_schedule", status="running")
        updated_schedule = http.request_json(
            "PUT",
            _q(f"/api/financial/schedules/{schedule_id}", company_id),
            json_payload={
                "name": f"Título QA Editado {neutral_prefix}",
                "template_amount": "234.56",
                "description": "Título financeiro temporário editado para validação",
                "notes": "Atualizado antes do cancelamento",
            },
            operation="financial.schedule.update",
        )
        assert str(updated_schedule["name"]).startswith("Título QA Editado")
        cancelled = http.request_json(
            "POST",
            _q(f"/api/financial/schedules/{schedule_id}/toggle", company_id),
            json_payload={"status": "cancelled"},
            operation="financial.schedule.cancel",
        )
        assert cancelled["status"] == "cancelled"
        journey.step("update_and_cancel_schedule", status="passed")

    except Exception as exc:
        journey.fail(
            step="financial_transactional_runtime",
            failure_type="http_runtime_error",
            details={"error": str(exc), "created": created, "schedule_id": schedule_id},
        )
        raise
    finally:
        if schedule_id is not None:
            journey.step("delete_schedule", status="running", details={"schedule_id": schedule_id})
            delete_schedule = http.request(
                "DELETE",
                _q(f"/api/financial/schedules/{schedule_id}", company_id),
            )
            delete_schedule.raise_for_status()
            journey.step("delete_schedule", status="passed")

        for catalog_type in ("payment_methods", "counterparties", "cost_centers", "chart_accounts", "bank_accounts"):
            item_id = created.get(catalog_type)
            if not item_id:
                continue
            journey.step(f"delete_{catalog_type}", status="running", details={"item_id": item_id})
            _catalog_delete(http, company_id, catalog_type, item_id)
            journey.step(f"delete_{catalog_type}", status="passed")

    journey.succeed()
