from __future__ import annotations

from playwright.sync_api import Page, expect

from app32.tests.e2e.config.environments import E2EEnvironmentSettings


class TenantContextResolver:
    def __init__(self, page: Page, settings: E2EEnvironmentSettings):
        self.page = page
        self.settings = settings

    def ensure_company_selected(self) -> None:
        if self.settings.company_id is None:
            return
        if "/portal" in self.page.url:
            self._select_company_on_portal()
            return
        self._assert_company_context_loaded()

    def _select_company_on_portal(self) -> None:
        selector = f'[data-portal-company-id="{self.settings.company_id}"]'
        card = self.page.locator(selector).first
        expect(card).to_be_visible()
        card.click()
        self.page.locator("body").wait_for()
        self._assert_company_context_loaded()

    def _assert_company_context_loaded(self) -> None:
        current_url = self.page.url
        if "/login" in current_url:
            raise AssertionError(
                "Contexto autenticado inválido: a navegação retornou para /login "
                f"após tentativa de autenticação/seleção de empresa. URL atual={current_url}"
            )
        if "/portal" in current_url:
            raise AssertionError(
                "Seleção de empresa não foi concluída: a sessão permaneceu em /portal "
                f"após a tentativa de resolver o tenant. URL atual={current_url}"
            )
        if self.settings.post_login_path not in current_url:
            raise AssertionError(
                "Contexto autenticado não chegou ao destino pós-login esperado. "
                f"Esperado conter={self.settings.post_login_path} atual={current_url}"
            )
        expect(self.page.locator("body")).to_be_visible()
