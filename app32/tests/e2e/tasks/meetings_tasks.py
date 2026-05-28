from __future__ import annotations

from dataclasses import asdict, dataclass

from app32.tests.e2e.data.meeting_builders import (
    MeetingDraftPayload,
    MeetingExecutionPayload,
)
from app32.tests.e2e.pages.meetings_page import MeetingsPage


@dataclass(frozen=True)
class MeetingRouteMap:
    create: str
    detail: str
    preliminares: str
    start: str
    execution: str
    finish: str
    delete: str


class MeetingsTasks:
    def __init__(self, meetings_page: MeetingsPage | None, company_id: int):
        self.meetings_page = meetings_page
        self.company_id = int(company_id)

    def open_workspace(self) -> None:
        if self.meetings_page is None:
            raise RuntimeError("meetings_page é obrigatório para navegação visual.")
        self.meetings_page.open_page()
        self.meetings_page.wait_until_ready()
        self.meetings_page.expect_primary_action()

    def route_map(self, meeting_id: int) -> MeetingRouteMap:
        return MeetingRouteMap(
            create=f"/meetings/api/company/{self.company_id}/meeting",
            detail=f"/meetings/api/meeting/{meeting_id}?company_id={self.company_id}",
            preliminares=f"/meetings/api/meeting/{meeting_id}/preliminares?company_id={self.company_id}",
            start=f"/meetings/api/meeting/{meeting_id}/iniciar?company_id={self.company_id}",
            execution=f"/meetings/api/meeting/{meeting_id}/execucao?company_id={self.company_id}",
            finish=f"/meetings/api/meeting/{meeting_id}/finalizar?company_id={self.company_id}",
            delete=f"/meetings/api/meeting/{meeting_id}?company_id={self.company_id}",
        )

    def build_create_request(self, payload: MeetingDraftPayload) -> dict:
        return asdict(payload)

    def build_execution_request(self, payload: MeetingExecutionPayload) -> dict:
        return asdict(payload)
