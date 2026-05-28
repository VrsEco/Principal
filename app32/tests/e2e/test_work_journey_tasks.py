from __future__ import annotations

from app32.tests.e2e.data.work_journey_builders import (
    build_work_journey_manual_task_payload,
    build_work_journey_manual_task_update_payload,
)
from app32.tests.e2e.tasks.work_journey_tasks import WorkJourneyTasks


def test_work_journey_tasks_payloads():
    tasks = WorkJourneyTasks(work_journey_page=None, company_id=9)
    create_payload = tasks.build_create_request(
        build_work_journey_manual_task_payload(employee_id=7, run_marker="AUTOE2E::wj")
    )
    update_payload = tasks.build_update_request(
        build_work_journey_manual_task_update_payload(run_marker="AUTOE2E::wj")
    )

    assert create_payload["employee_id"] == 7
    assert create_payload["status"] == "pending"
    assert update_payload["status"] == "completed"
    assert update_payload["priority"] == "high"
