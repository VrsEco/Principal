from __future__ import annotations

from playwright.sync_api import Page, expect


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def open(self, route: str) -> None:
        self.page.goto(route, wait_until="domcontentloaded")
        self.page.wait_for_load_state("networkidle")

    def expect_visible(self, selector: str) -> None:
        expect(self.page.locator(selector)).to_be_visible()

    def current_url(self) -> str:
        return self.page.url
