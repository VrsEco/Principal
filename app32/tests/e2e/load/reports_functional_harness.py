from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class ReportsFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def execute_reports_functional_probe(*, settings: E2EEnvironmentSettings) -> list[ReportsFunctionalProbeResult]:
    if settings.company_id is None:
        raise RuntimeError("E2E_COMPANY_ID é obrigatório para probe de relatórios.")

    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    work_journey_report_route = f"/companies/{settings.company_id}/work-journey/report"
    work_journey_report = http.request("GET", work_journey_report_route)
    work_journey_report.raise_for_status()
    http.assert_not_login_redirect(work_journey_report, operation="reports.work_journey_report")

    work_journey_pdf_route = f"/companies/{settings.company_id}/work-journey/export-pdf"
    work_journey_pdf = http.request("GET", work_journey_pdf_route)
    work_journey_pdf.raise_for_status()
    http.assert_not_login_redirect(work_journey_pdf, operation="reports.work_journey_report_pdf")

    workspace_print = http.request("GET", f"/my-work/export-pdf?scope=me&active_company_id={settings.company_id}")
    workspace_print.raise_for_status()
    http.assert_not_login_redirect(workspace_print, operation="reports.workspace_print")

    return [
        ReportsFunctionalProbeResult(
            check_name="reports.work_journey_report",
            route=work_journey_report_route,
            success="jornada" in (work_journey_report.text or "").lower() or "work journey" in (work_journey_report.text or "").lower(),
            status_code=work_journey_report.status_code,
            details={"content_type": str(work_journey_report.headers.get("Content-Type") or "")},
        ),
        ReportsFunctionalProbeResult(
            check_name="reports.work_journey_report_pdf",
            route=work_journey_pdf_route,
            success="html" in str(work_journey_pdf.headers.get("Content-Type") or "").lower(),
            status_code=work_journey_pdf.status_code,
            details={"content_type": str(work_journey_pdf.headers.get("Content-Type") or ""), "content_length": len(work_journey_pdf.text or "")},
        ),
        ReportsFunctionalProbeResult(
            check_name="reports.workspace_print",
            route=f"/my-work/export-pdf?scope=me&active_company_id={settings.company_id}",
            success="html" in str(workspace_print.headers.get("Content-Type") or "").lower(),
            status_code=workspace_print.status_code,
            details={"content_type": str(workspace_print.headers.get("Content-Type") or ""), "content_length": len(workspace_print.text or "")},
        ),
    ]
