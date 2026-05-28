from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class ReportDownloadResult:
    route: str
    success: bool
    status_code: int
    content_type: str
    content_length: int
    details: dict[str, Any]


def execute_report_download_probe(*, settings: E2EEnvironmentSettings) -> list[ReportDownloadResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    route = f"/my-work/export-pdf?scope=me&active_company_id={settings.company_id or ''}"
    response = http.request("GET", route)
    content_type = str(response.headers.get("Content-Type") or "")
    return [
        ReportDownloadResult(
            route=route,
            success=response.ok and "html" in content_type.lower(),
            status_code=response.status_code,
            content_type=content_type,
            content_length=len(response.text or ""),
            details={"expects": "html print view"},
        )
    ]
