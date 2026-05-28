from __future__ import annotations

from app32.tests.e2e.pages.base import BasePage


class IntegrationsPage(BasePage):
    ROUTE = "/api-mcp"
    READY_SELECTOR = "#integrationsWorkspace"
    PRIMARY_LIST_SELECTOR = "#integrationsList"

    def open_page(self) -> None:
        self.open(self.ROUTE)

    def wait_until_ready(self) -> None:
        self.expect_visible(self.READY_SELECTOR)

    def expect_catalog_loaded(self) -> None:
        self.expect_visible(self.PRIMARY_LIST_SELECTOR)
