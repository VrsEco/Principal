from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class AdminFunctionalProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def _status_allows_permission_validation(status_code: int) -> bool:
    return status_code in {200, 403}


def execute_admin_functional_probe(*, settings: E2EEnvironmentSettings) -> list[AdminFunctionalProbeResult]:
    if settings.company_id is None:
        raise RuntimeError("E2E_COMPANY_ID é obrigatório para probe administrativo.")

    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    performance_response = http.request("GET", f"/api/companies/{settings.company_id}/performance-settings")
    performance_response.raise_for_status()
    http.assert_not_login_redirect(performance_response, operation="admin.performance_settings_get")
    performance_payload = http._json_or_raise(performance_response, operation="admin.performance_settings_get")

    e2e_center_response = http.request("GET", "/api/configs/qa/e2e/frontend-state")
    http.assert_not_login_redirect(e2e_center_response, operation="admin.e2e_center_frontend_state")
    frontend_state_payload = None
    if e2e_center_response.status_code == 200:
        frontend_state_payload = http._json_or_raise(e2e_center_response, operation="admin.e2e_center_frontend_state")

    results = [
        AdminFunctionalProbeResult(
            check_name="admin.performance_settings_get",
            route=f"/api/companies/{settings.company_id}/performance-settings",
            success=isinstance(performance_payload, dict),
            status_code=performance_response.status_code,
            details={"keys": sorted(performance_payload.keys())[:8]},
        ),
        AdminFunctionalProbeResult(
            check_name="admin.e2e_center_frontend_state",
            route="/api/configs/qa/e2e/frontend-state",
            success=_status_allows_permission_validation(e2e_center_response.status_code)
            and (
                e2e_center_response.status_code == 403
                or isinstance(frontend_state_payload, dict)
            ),
            status_code=e2e_center_response.status_code,
            details={"permission_validated": e2e_center_response.status_code == 403, "has_payload": isinstance(frontend_state_payload, dict)},
        ),
    ]

    if settings.execution_mode is E2EExecutionMode.DEV_FULL and settings.destructive_actions_allowed:
        update_response = http.request(
            "PUT",
            f"/api/companies/{settings.company_id}/performance-settings",
            json_payload=performance_payload,
        )
        update_response.raise_for_status()
        http.assert_not_login_redirect(update_response, operation="admin.performance_settings_put")
        update_payload = http._json_or_raise(update_response, operation="admin.performance_settings_put")
        results.append(
            AdminFunctionalProbeResult(
                check_name="admin.performance_settings_put",
                route=f"/api/companies/{settings.company_id}/performance-settings",
                success=isinstance(update_payload, dict),
                status_code=update_response.status_code,
                details={"keys": sorted(update_payload.keys())[:8]},
            )
        )

    return results
