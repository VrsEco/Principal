from __future__ import annotations

import pytest

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.data.meeting_builders import (
    build_meeting_draft_payload,
    build_meeting_execution_payload,
)
from app32.tests.e2e.tasks.meetings_tasks import MeetingsTasks


@pytest.mark.e2e
@pytest.mark.dev_full
def test_meetings_crud_e2e_contract(
    e2e_settings: E2EEnvironmentSettings,
    e2e_run_context,
):
    if e2e_settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("CRUD inicial de meetings só deve rodar em DEV_FULL.")
    if e2e_settings.missing_requirements:
        pytest.skip(
            "Configuração E2E incompleta. Defina: "
            + ", ".join(e2e_settings.missing_requirements)
        )

    tasks = MeetingsTasks(None, company_id=e2e_settings.company_id or 0)
    journey = e2e_run_context.reporter.start_journey(
        journey="meetings_crud_e2e",
        run_id=e2e_run_context.evidence.run_id,
        company_id=e2e_settings.company_id,
        user_label=e2e_settings.username,
        metadata={"domain": "meetings", "mode": e2e_settings.environment_name},
    )
    journey.step("build_payloads", status="running")
    create_payload = tasks.build_create_request(
        build_meeting_draft_payload(run_marker=e2e_run_context.run_marker)
    )
    execution_payload = tasks.build_execution_request(
        build_meeting_execution_payload(run_marker=e2e_run_context.run_marker)
    )

    assert create_payload["title"]
    assert execution_payload["activities"]
    journey.step(
        "build_payloads",
        status="passed",
        details={
            "create_title": create_payload["title"],
            "activity_count": len(execution_payload["activities"]),
        },
    )
    http = AuthenticatedHTTPSession.create(e2e_settings)
    journey.step("http_login", status="running")
    login_payload = http.login()
    http.select_company()
    journey.step("http_login", status="passed", details={"redirect": login_payload.get("redirect")})

    journey.step("create_meeting", status="running")
    create_response = http.request("POST", f"/meetings/api/company/{e2e_settings.company_id}/meeting", json_payload=create_payload)
    create_response.raise_for_status()
    create_payload_response = create_response.json()
    meeting_id = int(create_payload_response["meeting_id"])
    project_id: int | None = None
    journey.step("create_meeting", status="passed", details={"meeting_id": meeting_id})

    routes = tasks.route_map(meeting_id)
    try:
        journey.step("update_preliminares", status="running")
        update_response = http.request("PUT", routes.preliminares, json_payload=create_payload)
        update_response.raise_for_status()
        journey.step("update_preliminares", status="passed")

        journey.step("start_meeting", status="running")
        start_response = http.request("POST", routes.start, json_payload={"project_type": "new"})
        start_response.raise_for_status()
        start_payload = start_response.json()
        if start_payload.get("project_id"):
            project_id = int(start_payload["project_id"])
        journey.step("start_meeting", status="passed", details=start_payload)

        journey.step("save_execution", status="running")
        execution_response = http.request("PUT", routes.execution, json_payload=execution_payload)
        execution_response.raise_for_status()
        journey.step("save_execution", status="passed")

        journey.step("finish_meeting", status="running")
        finish_response = http.request("POST", routes.finish, json_payload={})
        finish_response.raise_for_status()
        journey.step("finish_meeting", status="passed")
    except Exception as exc:
        journey.fail(
            step="crud_runtime",
            failure_type="http_runtime_error",
            details={"error": str(exc), "meeting_id": meeting_id},
        )
        raise
    finally:
        journey.step("delete_meeting", status="running", details={"meeting_id": meeting_id})
        delete_response = http.request("DELETE", routes.delete)
        delete_response.raise_for_status()
        journey.step("delete_meeting", status="passed")
        if project_id is not None:
            journey.step("delete_generated_project", status="running", details={"project_id": project_id})
            project_delete_response = http.request(
                "DELETE",
                f"/api/projects/{project_id}?company_id={e2e_settings.company_id}",
            )
            project_delete_response.raise_for_status()
            journey.step("delete_generated_project", status="passed")

    journey.succeed()
