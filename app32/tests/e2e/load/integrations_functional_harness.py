from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class IntegrationsFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def execute_integrations_functional_probe(*, settings: E2EEnvironmentSettings) -> list[IntegrationsFunctionalProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    catalog_payload = http.request_json(
        "GET",
        "/api/integrations/catalog",
        operation="integrations.catalog",
    )
    requests_payload = http.request_json(
        "GET",
        "/api/integrations/requests",
        operation="integrations.requests",
    )
    html_response = http.request("GET", "/api-mcp")
    html_response.raise_for_status()
    http.assert_not_login_redirect(html_response, operation="integrations.page")
    html_body = html_response.text or ""

    return [
        IntegrationsFunctionalProbeResult(
            check_name="integrations.catalog",
            route="/api/integrations/catalog",
            success=bool(catalog_payload.get("success")) and isinstance(catalog_payload.get("catalog"), dict),
            status_code=200,
            details={
                "summary_keys": sorted((catalog_payload.get("catalog") or {}).get("summary", {}).keys()),
            },
        ),
        IntegrationsFunctionalProbeResult(
            check_name="integrations.requests",
            route="/api/integrations/requests",
            success=bool(requests_payload.get("success")) and isinstance(requests_payload.get("requests"), list),
            status_code=200,
            details={
                "request_count": len(requests_payload.get("requests") or []),
            },
        ),
        IntegrationsFunctionalProbeResult(
            check_name="integrations.page",
            route="/api-mcp",
            success="#integrationsWorkspace" in html_body or "API / MCP" in html_body,
            status_code=html_response.status_code,
            details={
                "has_workspace_marker": "#integrationsWorkspace" in html_body,
                "has_title": "API / MCP" in html_body,
            },
        ),
    ]
