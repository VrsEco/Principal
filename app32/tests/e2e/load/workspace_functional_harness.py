from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class WorkspaceFunctionalProbeResult:
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


def execute_workspace_functional_probe(*, settings: E2EEnvironmentSettings) -> list[WorkspaceFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    filter_payload = http.request_json(
        "GET",
        "/my-work/api/filter-options",
        operation="workspace.filter_options",
    )
    activities_payload = http.request_json(
        "GET",
        f"/my-work/api/activities?scope=me&active_company_id={settings.company_id or ''}",
        operation="workspace.activities",
    )

    export_route = f"/my-work/export-pdf?scope=me&active_company_id={settings.company_id or ''}"
    export_response = http.request("GET", export_route)
    export_response.raise_for_status()
    http.assert_not_login_redirect(export_response, operation="workspace.export_pdf")
    export_body = export_response.text or ""
    export_content_type = str(export_response.headers.get("Content-Type") or "")
    export_success = (
        export_response.ok
        and "html" in export_content_type.lower()
        and not _contains_public_error(export_body)
    )

    return [
        WorkspaceFunctionalProbeResult(
            check_name="workspace.filter_options",
            route="/my-work/api/filter-options",
            success=bool(filter_payload.get("success")) and isinstance(filter_payload.get("data"), dict),
            status_code=200,
            details={
                "companies": len((filter_payload.get("data") or {}).get("companies") or []),
                "collaborators": len((filter_payload.get("data") or {}).get("collaborators") or []),
            },
        ),
        WorkspaceFunctionalProbeResult(
            check_name="workspace.activities",
            route="/my-work/api/activities",
            success=bool(activities_payload.get("success")) and isinstance(activities_payload.get("data"), list),
            status_code=200,
            details={
                "activities": len(activities_payload.get("data") or []),
                "has_stats": isinstance(activities_payload.get("stats"), dict),
            },
        ),
        WorkspaceFunctionalProbeResult(
            check_name="workspace.export_pdf",
            route=export_route,
            success=export_success,
            status_code=export_response.status_code,
            details={
                "content_type": export_content_type,
                "content_length": len(export_body),
                "has_public_error": _contains_public_error(export_body),
            },
        ),
    ]
