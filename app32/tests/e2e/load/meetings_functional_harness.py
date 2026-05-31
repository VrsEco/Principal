from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.functional_guards import contains_public_error, is_html_success
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class MeetingsFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def execute_meetings_functional_probe(*, settings: E2EEnvironmentSettings) -> list[MeetingsFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    root_response = http.request("GET", "/meetings/")
    root_response.raise_for_status()
    http.assert_not_login_redirect(root_response, operation="meetings.root")
    root_html = root_response.text or ""

    company_route = f"/meetings/company/{settings.company_id or ''}"
    company_response = http.request("GET", company_route)
    company_response.raise_for_status()
    http.assert_not_login_redirect(company_response, operation="meetings.company_manage")
    company_html = company_response.text or ""

    return [
        MeetingsFunctionalProbeResult(
            check_name="meetings.root",
            route="/meetings/",
            success="/meetings/company/" in str(getattr(root_response, "url", "") or "")
            and not contains_public_error(root_html),
            status_code=root_response.status_code,
            details={
                "final_url": str(getattr(root_response, "url", "") or ""),
                "has_public_error": contains_public_error(root_html),
            },
        ),
        MeetingsFunctionalProbeResult(
            check_name="meetings.company_manage",
            route=company_route,
            success=is_html_success(company_html, all_markers=("meeting-management", "novaReuniao")),
            status_code=company_response.status_code,
            details={
                "has_management_marker": "meeting-management" in company_html,
                "has_primary_action": "novaReuniao" in company_html,
                "has_public_error": contains_public_error(company_html),
            },
        ),
    ]
