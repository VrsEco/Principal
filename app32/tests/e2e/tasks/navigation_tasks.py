from __future__ import annotations

from dataclasses import dataclass

from app32.tests.e2e.pages.channels_page import ChannelsPage
from app32.tests.e2e.pages.integrations_page import IntegrationsPage
from app32.tests.e2e.pages.meetings_page import MeetingsPage
from app32.tests.e2e.pages.workspace_page import WorkspacePage


@dataclass
class NavigationTasks:
    workspace: WorkspacePage
    meetings: MeetingsPage
    integrations: IntegrationsPage
    channels: ChannelsPage

    def open_workspace(self) -> None:
        self.workspace.open_page()
        self.workspace.wait_until_ready()

    def open_meetings(self) -> None:
        self.meetings.open_page()
        self.meetings.wait_until_ready()
        self.meetings.expect_primary_action()

    def open_integrations(self) -> None:
        self.integrations.open_page()
        self.integrations.wait_until_ready()
        self.integrations.expect_catalog_loaded()

    def open_channels(self) -> None:
        self.channels.open_page()
        self.channels.wait_until_ready()
        self.channels.expect_channel_selector()
