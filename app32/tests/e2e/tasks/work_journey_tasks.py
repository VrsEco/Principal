from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.data.work_journey_builders import (
    WorkJourneyManualTaskPayload,
    WorkJourneyManualTaskUpdatePayload,
)
from app32.tests.e2e.pages.work_journey_page import WorkJourneyPage


@dataclass(frozen=True)
class WorkJourneyRouteMap:
    board: str
    manual_tasks: str
    item_detail: str


class WorkJourneyTasks:
    def __init__(self, work_journey_page: WorkJourneyPage | None, company_id: int):
        self.work_journey_page = work_journey_page
        self.company_id = int(company_id)

    def open_workspace(self) -> None:
        if self.work_journey_page is None:
            raise RuntimeError("work_journey_page é obrigatório para navegação visual.")
        self.work_journey_page.open_page()
        self.work_journey_page.wait_until_ready()
        self.work_journey_page.expect_primary_region()

    def route_map(self, item_id: int | None = None) -> WorkJourneyRouteMap:
        return WorkJourneyRouteMap(
            board=f"/api/companies/{self.company_id}/work-journey/board",
            manual_tasks=f"/api/companies/{self.company_id}/work-journey/items/manual",
            item_detail=f"/api/companies/{self.company_id}/work-journey/items/{item_id or 0}",
        )

    def resolve_current_employee_id(self, http: AuthenticatedHTTPSession) -> int:
        response = http.request("GET", self.route_map().board)
        response.raise_for_status()
        payload = response.json()
        employee_id = (((payload.get("data") or {}).get("employee") or {}).get("id"))
        if not employee_id:
            raise RuntimeError(f"Não foi possível resolver employee_id na jornada de trabalho: {payload}")
        return int(employee_id)

    def list_manual_tasks(self, http: AuthenticatedHTTPSession, employee_id: int) -> dict[str, Any]:
        response = http.request(
            "GET",
            f"/api/companies/{self.company_id}/work-journey/manual-tasks?employee_id={employee_id}",
        )
        response.raise_for_status()
        return response.json()

    def build_create_request(self, payload: WorkJourneyManualTaskPayload) -> dict[str, Any]:
        return asdict(payload)

    def build_update_request(self, payload: WorkJourneyManualTaskUpdatePayload) -> dict[str, Any]:
        return asdict(payload)
