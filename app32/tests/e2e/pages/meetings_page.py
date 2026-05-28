from __future__ import annotations

from app32.tests.e2e.pages.base import BasePage


class MeetingsPage(BasePage):
    ROUTE = "/meetings/"
    READY_SELECTOR = ".meeting-management"
    PRIMARY_ACTION_SELECTOR = "button[onclick*='novaReuniao']"

    def open_page(self) -> None:
        self.open(self.ROUTE)

    def wait_until_ready(self) -> None:
        self.expect_visible(self.READY_SELECTOR)

    def expect_primary_action(self) -> None:
        self.expect_visible(self.PRIMARY_ACTION_SELECTOR)
