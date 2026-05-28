from __future__ import annotations

from app32.tests.e2e.data.work_journey_builders import (
    build_work_journey_manual_task_payload,
    build_work_journey_manual_task_update_payload,
)
from app32.tests.e2e.tasks.work_journey_tasks import WorkJourneyTasks


def test_work_journey_route_map_contract():
    tasks = WorkJourneyTasks(work_journey_page=None, company_id=9)
    routes = tasks.route_map(item_id=77)

    assert routes.board == "/api/companies/9/work-journey/board"
    assert routes.manual_tasks == "/api/companies/9/work-journey/items/manual"
    assert routes.item_detail == "/api/companies/9/work-journey/items/77"


def test_work_journey_payload_contract():
    create_payload = build_work_journey_manual_task_payload(employee_id=11, run_marker="AUTOE2E::contract")
    update_payload = build_work_journey_manual_task_update_payload(run_marker="AUTOE2E::contract")
    tasks = WorkJourneyTasks(work_journey_page=None, company_id=9)

    create_request = tasks.build_create_request(create_payload)
    update_request = tasks.build_update_request(update_payload)

    assert create_request["employee_id"] == 11
    assert create_request["title"].startswith("AUTOE2E::contract")
    assert update_request["status"] == "completed"
    assert update_request["worked_minutes"] == 60
