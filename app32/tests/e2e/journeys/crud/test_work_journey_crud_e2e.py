from __future__ import annotations

import pytest

from app32.tests.e2e.config.environments import E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.data.work_journey_builders import (
    build_work_journey_manual_task_payload,
    build_work_journey_manual_task_update_payload,
)
from app32.tests.e2e.tasks.work_journey_tasks import WorkJourneyTasks


@pytest.mark.e2e
@pytest.mark.dev_full
def test_work_journey_manual_task_crud_dev_full(e2e_run_context):
    settings = e2e_run_context.settings
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        pytest.skip("CRUD de work-journey só roda em DEV_FULL.")
    if settings.missing_requirements:
        pytest.skip(f"Configuração E2E incompleta: {', '.join(settings.missing_requirements)}")

    journey = e2e_run_context.reporter.start_journey(
        journey="work_journey_manual_task_crud_e2e",
        run_id=e2e_run_context.evidence.run_id,
        company_id=settings.company_id,
        user_label=settings.username,
        metadata={"domain": "work_journey", "mode": settings.execution_mode.value},
    )

    http = AuthenticatedHTTPSession.create(settings)
    tasks = WorkJourneyTasks(work_journey_page=None, company_id=settings.company_id or 0)  # type: ignore[arg-type]
    item_id: int | None = None

    try:
        journey.step("http_login", status="running")
        http.login()
        http.select_company()
        journey.step("http_login", status="passed")

        journey.step("resolve_employee", status="running")
        employee_id = tasks.resolve_current_employee_id(http)
        journey.step("resolve_employee", status="passed", details={"employee_id": employee_id})

        journey.step("create_manual_task", status="running")
        create_payload = tasks.build_create_request(
            build_work_journey_manual_task_payload(
                employee_id=employee_id,
                run_marker=e2e_run_context.run_marker,
            )
        )
        create_response = http.request("POST", tasks.route_map().manual_tasks, json_payload=create_payload)
        create_response.raise_for_status()
        created = create_response.json()
        item_id = int((created.get("item") or {}).get("id"))
        journey.step("create_manual_task", status="passed", details={"item_id": item_id})

        journey.step("list_manual_tasks", status="running")
        listed = tasks.list_manual_tasks(http, employee_id)
        listed_ids = [int(item["id"]) for item in ((listed.get("data") or {}).get("items") or [])]
        assert item_id in listed_ids
        journey.step("list_manual_tasks", status="passed", details={"total_items": len(listed_ids)})

        journey.step("update_manual_task", status="running")
        update_payload = tasks.build_update_request(
            build_work_journey_manual_task_update_payload(run_marker=e2e_run_context.run_marker)
        )
        update_response = http.request(
            "PATCH",
            tasks.route_map(item_id).item_detail,
            json_payload=update_payload,
        )
        update_response.raise_for_status()
        updated = update_response.json()
        assert (updated.get("item") or {}).get("status") == "completed"
        journey.step("update_manual_task", status="passed")

    except Exception as exc:
        journey.fail(
            step="work_journey_manual_task_crud_e2e",
            failure_type=exc.__class__.__name__,
            details={"error": str(exc), "item_id": item_id},
        )
        raise
    finally:
        if item_id is not None:
            journey.step("delete_manual_task", status="running", details={"item_id": item_id})
            delete_response = http.request("DELETE", tasks.route_map(item_id).item_detail)
            delete_response.raise_for_status()
            journey.step("delete_manual_task", status="passed")

    journey.succeed()
