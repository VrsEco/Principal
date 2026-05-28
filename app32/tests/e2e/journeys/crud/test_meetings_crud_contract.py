from __future__ import annotations

from types import SimpleNamespace

from app32.tests.e2e.data.meeting_builders import (
    build_meeting_draft_payload,
    build_meeting_execution_payload,
)
from app32.tests.e2e.pages.meetings_page import MeetingsPage
from app32.tests.e2e.tasks.meetings_tasks import MeetingsTasks


class _DummyPage:
    def __init__(self):
        self.url = ""
        self.visited: list[str] = []

    def goto(self, route: str, wait_until: str = "domcontentloaded"):
        self.url = route
        self.visited.append(route)

    def wait_for_load_state(self, _state: str):
        return None

    def locator(self, _selector: str):
        return SimpleNamespace()


def test_meetings_task_routes_and_payloads(monkeypatch):
    monkeypatch.setattr(
        "app32.tests.e2e.pages.base.expect",
        lambda _locator: SimpleNamespace(to_be_visible=lambda: None),
    )
    page = _DummyPage()
    tasks = MeetingsTasks(MeetingsPage(page), company_id=9)

    tasks.open_workspace()
    route_map = tasks.route_map(meeting_id=77)
    create_payload = tasks.build_create_request(build_meeting_draft_payload(run_marker="AUTOE2E::demo"))
    execution_payload = tasks.build_execution_request(build_meeting_execution_payload(run_marker="AUTOE2E::demo"))

    assert page.visited == ["/meetings/"]
    assert route_map.create == "/meetings/api/company/9/meeting"
    assert route_map.preliminares == "/meetings/api/meeting/77/preliminares?company_id=9"
    assert route_map.execution == "/meetings/api/meeting/77/execucao?company_id=9"
    assert route_map.finish == "/meetings/api/meeting/77/finalizar?company_id=9"
    assert create_payload["title"].startswith("AUTOE2E::demo")
    assert execution_payload["meeting_notes"].startswith("Conclusões da reunião")
