from __future__ import annotations

from dataclasses import dataclass
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

    bordero_create_html = http.request("GET", f"/financial/borderos/new?company_id={settings.company_id}&bordero_type=receivable")
    bordero_create_html.raise_for_status()
    http.assert_not_login_redirect(bordero_create_html, operation="financial.bordero_create_page")

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
