from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.tenant_context import TenantContextResolver


class AuthPage:
    def __init__(self, page: Page, settings: E2EEnvironmentSettings):
        self.page = page
        self.settings = settings

    def open(self) -> None:
        preferred_url = self.settings.login_url
        if self.settings.post_login_path:
            separator = "&" if "?" in preferred_url else "?"
            preferred_url = f"{preferred_url}{separator}next={self.settings.post_login_path}"
        self.page.goto(preferred_url, wait_until="domcontentloaded")
        self.page.locator("body").wait_for()
        if self._is_login_screen():
            expect(self.page).to_have_title("Login | Versus Gestão")

    def login(self) -> None:
        if not self._is_login_screen():
            return
        self._email_input().fill(self.settings.username)
        self._password_input().fill(self.settings.password)
        self.page.locator("#submitBtn").click()
        self.page.locator("body").wait_for()

    def ensure_authenticated_workspace(self) -> None:
        TenantContextResolver(self.page, self.settings).ensure_company_selected()
        self._assert_not_on_login_screen()

    def _email_input(self) -> Locator:
        return self.page.locator("#email")

    def _password_input(self) -> Locator:
        return self.page.locator("#password")

    def _is_login_screen(self) -> bool:
        return self._email_input().count() > 0 and self._password_input().count() > 0

    def _assert_not_on_login_screen(self) -> None:
        if self._is_login_screen() or "/login" in self.page.url:
            raise AssertionError(
                "Autenticação E2E não foi concluída: a página permaneceu no login "
                f"(url atual={self.page.url})."
            )
