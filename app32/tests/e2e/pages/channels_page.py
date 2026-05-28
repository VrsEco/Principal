from __future__ import annotations

from app32.tests.e2e.pages.base import BasePage


class ChannelsPage(BasePage):
    ROUTE = "/channels"
    READY_SELECTOR = "#integrationsContainer"
    PRIMARY_LABEL_SELECTOR = ".form-label"

    def open_page(self) -> None:
        self.open(self.ROUTE)

    def wait_until_ready(self) -> None:
        self.expect_visible(self.READY_SELECTOR)

    def expect_channel_selector(self) -> None:
        self.expect_visible(self.PRIMARY_LABEL_SELECTOR)
