from __future__ import annotations

import pytest

from app32.tests.e2e.config.environments import E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@pytest.mark.e2e
@pytest.mark.dev_full
def test_admin_performance_settings_transactional_dev_full(e2e_run_context):
    settings = e2e_run_context.settings
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("CRUD administrativo transacional só roda em DEV_FULL.")
    if settings.missing_requirements:
        pytest.skip(f"Configuração E2E incompleta: {', '.join(settings.missing_requirements)}")
    if not settings.destructive_actions_allowed:
        pytest.skip("CRUD administrativo exige E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true.")

    company_id = settings.company_id
    journey = e2e_run_context.reporter.start_journey(
        journey="admin_performance_settings_transactional_e2e",
        run_id=e2e_run_context.evidence.run_id,
        company_id=company_id,
        user_label=settings.username,
        metadata={"domain": "admin", "mode": settings.execution_mode.value},
    )
    http = AuthenticatedHTTPSession.create(settings)
    original_payload: dict | None = None

    try:
        journey.step("http_login", status="running")
        http.login()
        http.select_company()
        journey.step("http_login", status="passed")

        route = f"/api/companies/{company_id}/performance-settings"
        journey.step("read_original_settings", status="running")
        original_response = http.request("GET", route)
        original_response.raise_for_status()
        original_payload = original_response.json()
        assert isinstance(original_payload, dict)
        original_value = bool(original_payload.get("allow_postpone_after_due_date"))
        journey.step(
            "read_original_settings",
            status="passed",
            details={"allow_postpone_after_due_date": original_value},
        )

        journey.step("update_settings", status="running")
        updated_payload = dict(original_payload)
        updated_payload["allow_postpone_after_due_date"] = not original_value
        update_response = http.request("PUT", route, json_payload=updated_payload)
        update_response.raise_for_status()
        update_payload = update_response.json()
        assert bool(update_payload.get("allow_postpone_after_due_date")) is (not original_value)
        journey.step("update_settings", status="passed")

        journey.step("validate_persisted_settings", status="running")
        persisted_response = http.request("GET", route)
        persisted_response.raise_for_status()
        persisted_payload = persisted_response.json()
        assert bool(persisted_payload.get("allow_postpone_after_due_date")) is (not original_value)
        journey.step("validate_persisted_settings", status="passed")

    except Exception as exc:
        journey.fail(
            step="admin_performance_settings_transactional_e2e",
            failure_type=exc.__class__.__name__,
            details={"error": str(exc)},
        )
        raise
    finally:
        if original_payload is not None:
            journey.step("restore_original_settings", status="running")
            restore_response = http.request(
                "PUT",
                f"/api/companies/{company_id}/performance-settings",
                json_payload=original_payload,
            )
            restore_response.raise_for_status()
            restored_payload = restore_response.json()
            assert bool(restored_payload.get("allow_postpone_after_due_date")) is bool(
                original_payload.get("allow_postpone_after_due_date")
            )
            journey.step("restore_original_settings", status="passed")

    journey.succeed()
