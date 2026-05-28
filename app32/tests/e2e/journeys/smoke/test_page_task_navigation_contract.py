from __future__ import annotations

from types import SimpleNamespace

from app32.tests.e2e.pages.channels_page import ChannelsPage
from app32.tests.e2e.pages.integrations_page import IntegrationsPage
from app32.tests.e2e.pages.meetings_page import MeetingsPage
from app32.tests.e2e.pages.workspace_page import WorkspacePage
from app32.tests.e2e.tasks.navigation_tasks import NavigationTasks


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


def test_navigation_tasks_open_routes(monkeypatch):
    monkeypatch.setattr(
        "app32.tests.e2e.pages.base.expect",
        lambda _locator: SimpleNamespace(to_be_visible=lambda: None),
    )
    page = _DummyPage()
    tasks = NavigationTasks(
        workspace=WorkspacePage(page),
        meetings=MeetingsPage(page),
        integrations=IntegrationsPage(page),
        channels=ChannelsPage(page),
    )

    tasks.open_workspace()
    tasks.open_meetings()
    tasks.open_integrations()
    tasks.open_channels()

    assert page.visited == ["/my-work", "/meetings/", "/api-mcp", "/channels"]
