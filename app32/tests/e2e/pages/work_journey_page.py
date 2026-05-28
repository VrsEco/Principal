from __future__ import annotations

from app32.tests.e2e.pages.base import BasePage


class WorkJourneyPage(BasePage):
    route = "/work-journey"
    readiness_selector = "[data-work-journey-root], #workJourneyRoot, .work-journey-board"

    def expect_primary_region(self) -> None:
        self.page.locator(self.readiness_selector).first.wait_for(state="visible")
