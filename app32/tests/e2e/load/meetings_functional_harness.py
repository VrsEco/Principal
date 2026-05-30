from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class MeetingsFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


PUBLIC_ERROR_PATTERNS = (
    "Erro interno do servidor",
    "Erro interno",
    "Tente novamente ou contate o suporte",
)


def _contains_public_error(text: str) -> bool:
    normalized = str(text or "").lower()
    return any(pattern.lower() in normalized for pattern in PUBLIC_ERROR_PATTERNS)


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
            and not _contains_public_error(root_html),
            status_code=root_response.status_code,
            details={
                "final_url": str(getattr(root_response, "url", "") or ""),
                "has_public_error": _contains_public_error(root_html),
            },
        ),
        MeetingsFunctionalProbeResult(
            check_name="meetings.company_manage",
            route=company_route,
            success="meeting-management" in company_html
            and "novaReuniao" in company_html
            and not _contains_public_error(company_html),
            status_code=company_response.status_code,
            details={
                "has_management_marker": "meeting-management" in company_html,
                "has_primary_action": "novaReuniao" in company_html,
                "has_public_error": _contains_public_error(company_html),
            },
        ),
    ]
