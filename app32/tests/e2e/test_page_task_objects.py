from __future__ import annotations

from app32.tests.e2e.pages.channels_page import ChannelsPage
from app32.tests.e2e.pages.integrations_page import IntegrationsPage
from app32.tests.e2e.pages.meetings_page import MeetingsPage
from app32.tests.e2e.pages.workspace_page import WorkspacePage


def test_page_object_contracts():
    assert WorkspacePage.ROUTE == "/my-work"
    assert WorkspacePage.READY_SELECTOR == ".my-work-container"

    assert MeetingsPage.ROUTE == "/meetings/"
    assert MeetingsPage.READY_SELECTOR == ".meeting-management"

    assert IntegrationsPage.ROUTE == "/api-mcp"
    assert IntegrationsPage.READY_SELECTOR == "#integrationsWorkspace"

    assert ChannelsPage.ROUTE == "/channels"
    assert ChannelsPage.READY_SELECTOR == "#integrationsContainer"
