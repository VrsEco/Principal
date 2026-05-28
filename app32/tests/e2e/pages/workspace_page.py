from __future__ import annotations

from app32.tests.e2e.pages.base import BasePage


class WorkspacePage(BasePage):
    ROUTE = "/my-work"
    READY_SELECTOR = ".my-work-container"

    def open_page(self) -> None:
        self.open(self.ROUTE)

    def wait_until_ready(self) -> None:
        self.expect_visible(self.READY_SELECTOR)
