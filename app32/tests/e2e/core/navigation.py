from __future__ import annotations

from playwright.sync_api import Page, expect

from app32.tests.e2e.config.smoke_targets import SmokeTarget


class NavigationSmoke:
    def __init__(self, page: Page):
        self.page = page

    def open_target(self, target: SmokeTarget) -> None:
        timeout_ms = 30000
        settings = getattr(self.page, "_e2e_settings", None)
        if settings is not None:
            timeout_ms = getattr(settings, "navigation_timeout_ms", timeout_ms)
        self.page.goto(target.route, wait_until="domcontentloaded", timeout=timeout_ms)
        self.page.locator("body").wait_for()
        expect(self.page.locator(target.readiness_selector)).to_be_visible()
        assert target.expected_url_fragment in self.page.url, (
            f"Destino {target.key} não chegou ao fragmento esperado. "
            f"Atual={self.page.url} esperado conter={target.expected_url_fragment}"
        )
