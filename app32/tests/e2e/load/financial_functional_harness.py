from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.functional_guards import contains_public_error, is_html_success
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class FinancialFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def _path_with_query(path: str, **params: Any) -> str:
    query = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }
    if not query:
        return path
    return f"{path}?{urlencode(query)}"


def _extract_schedules(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "schedules", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _counterparty_contract_ok(schedules: list[dict[str, Any]]) -> bool:
    for item in schedules:
        summary = item.get("summary")
        if not isinstance(summary, dict) or "counterparty_name" not in summary:
            return False
    return True


def execute_financial_functional_probe(*, settings: E2EEnvironmentSettings) -> list[FinancialFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    schedule_html = http.request("GET", "/financial/reports/agendamento")
    schedule_html.raise_for_status()
    http.assert_not_login_redirect(schedule_html, operation="financial.schedule_report_page")

    bank_statement_html = http.request("GET", "/financial/reports/extrato-bancario")
    bank_statement_html.raise_for_status()
    http.assert_not_login_redirect(bank_statement_html, operation="financial.bank_statement_page")

    transfers_html = http.request("GET", _path_with_query("/financial/transfers", company_id=settings.company_id))
    transfers_html.raise_for_status()
    http.assert_not_login_redirect(transfers_html, operation="financial.transfers_page")

    bank_accounts_payload = http.request_json(
        "GET",
        _path_with_query("/api/financial/catalogs/bank_accounts", company_id=settings.company_id),
        operation="financial.bank_accounts_catalog_for_transfer",
    )
    bank_accounts = (
        [item for item in bank_accounts_payload if isinstance(item, dict)]
        if isinstance(bank_accounts_payload, list)
        else []
    )

    bordero_create_html = http.request("GET", f"/financial/borderos/new?company_id={settings.company_id}&bordero_type=receivable")
    bordero_create_html.raise_for_status()
    http.assert_not_login_redirect(bordero_create_html, operation="financial.bordero_create_page")

    schedules_list_html = http.request("GET", _path_with_query("/financial/schedules", company_id=settings.company_id))
    schedules_list_html.raise_for_status()
    http.assert_not_login_redirect(schedules_list_html, operation="financial.schedules_list_page")

    schedules_payload = http.request_json(
        "GET",
        _path_with_query("/api/financial/schedules", company_id=settings.company_id),
        operation="financial.schedules_api_counterparty_contract",
    )
    schedules = _extract_schedules(schedules_payload)
    selected_schedule_id = next((item.get("id") for item in schedules if item.get("id")), None)

    if selected_schedule_id:
        schedule_automation_html = http.request(
            "GET",
            _path_with_query(
                f"/financial/schedules/{selected_schedule_id}",
                company_id=settings.company_id,
                open_tab="automacoes",
            ),
        )
        schedule_automation_html.raise_for_status()
        http.assert_not_login_redirect(schedule_automation_html, operation="financial.schedule_local_automations_tab")
        schedule_automation_success = is_html_success(
            schedule_automation_html.text,
            all_markers=(
                'data-tab="automacoes"',
                'data-panel="automacoes"',
                "Automações do título financeiro",
            ),
        )
        schedule_automation_status_code = schedule_automation_html.status_code
        schedule_automation_details: dict[str, Any] = {
            "schedule_id": selected_schedule_id,
            "content_type": str(schedule_automation_html.headers.get("Content-Type") or ""),
            "has_public_error": contains_public_error(schedule_automation_html.text),
        }
    else:
        schedule_automation_success = True
        schedule_automation_status_code = 204
        schedule_automation_details = {
            "skipped": True,
            "reason": "Sem título financeiro disponível para validar a aba local de automações.",
        }

    pdf_response = http.request("GET", "/financial/reports/agendamento/export-pdf")
    pdf_response.raise_for_status()
    http.assert_not_login_redirect(pdf_response, operation="financial.schedule_report_pdf")

    xlsx_response = http.request("GET", "/financial/reports/agendamento/export-xlsx")
    xlsx_response.raise_for_status()
    http.assert_not_login_redirect(xlsx_response, operation="financial.schedule_report_xlsx")

    return [
        FinancialFunctionalProbeResult(
            check_name="financial.schedule_report_page",
            route="/financial/reports/agendamento",
            success=is_html_success(
                schedule_html.text,
                any_markers=("relat", "financeiro"),
            ),
            status_code=schedule_html.status_code,
            details={
                "content_type": str(schedule_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(schedule_html.text),
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.bank_statement_page",
            route="/financial/reports/extrato-bancario",
            success=is_html_success(
                bank_statement_html.text,
                any_markers=("Extrato", "banc"),
            ),
            status_code=bank_statement_html.status_code,
            details={
                "content_type": str(bank_statement_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(bank_statement_html.text),
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.transfers_page",
            route=_path_with_query("/financial/transfers", company_id=settings.company_id),
            success=is_html_success(
                transfers_html.text,
                all_markers=("Transferência Bancária", "Nova transferência", "data-company-id"),
            ),
            status_code=transfers_html.status_code,
            details={
                "content_type": str(transfers_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(transfers_html.text),
                "company_id": settings.company_id,
                "mutation_guard": "PROD_SAFE cobre apenas renderização; POST /api/financial/transfers permanece fora do probe.",
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.bank_accounts_catalog_for_transfer",
            route=_path_with_query("/api/financial/catalogs/bank_accounts", company_id=settings.company_id),
            success=isinstance(bank_accounts_payload, list),
            status_code=200,
            details={
                "total_bank_accounts": len(bank_accounts),
                "contract": "lista de contas bancárias deve ser tenant-safe via company_id para alimentar a workspace de transferência.",
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.bordero_create_page",
            route=f"/financial/borderos/new?company_id={settings.company_id}&bordero_type=receivable",
            success=is_html_success(
                bordero_create_html.text,
                any_markers=("borderô", "bordero", "financeiro"),
            ),
            status_code=bordero_create_html.status_code,
            details={
                "content_type": str(bordero_create_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(bordero_create_html.text),
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.schedules_list_page",
            route=_path_with_query("/financial/schedules", company_id=settings.company_id),
            success=is_html_success(
                schedules_list_html.text,
                all_markers=("Títulos Financeiros", "Favorecido"),
            ),
            status_code=schedules_list_html.status_code,
            details={
                "content_type": str(schedules_list_html.headers.get("Content-Type") or ""),
                "has_public_error": contains_public_error(schedules_list_html.text),
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.schedules_api_counterparty_contract",
            route=_path_with_query("/api/financial/schedules", company_id=settings.company_id),
            success=_counterparty_contract_ok(schedules),
            status_code=200,
            details={
                "total_schedules": len(schedules),
                "with_counterparty_id": sum(1 for item in schedules if item.get("counterparty_id") not in (None, "")),
                "contract": "summary.counterparty_name obrigatório para evitar regressão de favorecido/JSON safety.",
            },
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.schedule_local_automations_tab",
            route=(
                _path_with_query(
                    f"/financial/schedules/{selected_schedule_id}",
                    company_id=settings.company_id,
                    open_tab="automacoes",
                )
                if selected_schedule_id
                else "/financial/schedules/<id>?open_tab=automacoes"
            ),
            success=schedule_automation_success,
            status_code=schedule_automation_status_code,
            details=schedule_automation_details,
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.schedule_report_pdf",
            route="/financial/reports/agendamento/export-pdf",
            success="pdf" in str(pdf_response.headers.get("Content-Type") or "").lower(),
            status_code=pdf_response.status_code,
            details={"content_type": str(pdf_response.headers.get("Content-Type") or ""), "content_length": len(pdf_response.content or b"")},
        ),
        FinancialFunctionalProbeResult(
            check_name="financial.schedule_report_xlsx",
            route="/financial/reports/agendamento/export-xlsx",
            success="spreadsheetml" in str(xlsx_response.headers.get("Content-Type") or "").lower(),
            status_code=xlsx_response.status_code,
            details={"content_type": str(xlsx_response.headers.get("Content-Type") or ""), "content_length": len(xlsx_response.content or b"")},
        ),
    ]
