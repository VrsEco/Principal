from __future__ import annotations

from types import SimpleNamespace

from app32.tests.e2e.config.environments import E2EExecutionMode, E2EEnvironmentSettings
from app32.tests.e2e.core.tenant_context import TenantContextResolver


class _DummyLocator:
    def __init__(self, page=None):
        self.page = page

    @property
    def first(self):
        return self

    def click(self):
        if self.page is not None:
            self.page.url = "http://127.0.0.1:5002/my-work"
        return None


class _DummyPage:
    def __init__(self, url: str):
        self.url = url

    def locator(self, _selector: str):
        return _DummyLocator(self)

    def wait_for_load_state(self, _state: str):
        return None


def _settings(company_id: int | None = 9) -> E2EEnvironmentSettings:
    return E2EEnvironmentSettings(
        environment_name="DEV_FULL",
        execution_mode=E2EExecutionMode.DEV_FULL,
        base_url="http://127.0.0.1:5002",
        login_path="/auth/login",
        post_login_path="/my-work",
        username="dev@example.com",
        password="secret",
        company_id=company_id,
        headless=False,
        browser_name="chromium",
        storage_state_path=SimpleNamespace(exists=lambda: False, parent=SimpleNamespace(mkdir=lambda **kwargs: None)),
        outputs_dir=SimpleNamespace(),
        traces_dir=SimpleNamespace(),
        screenshots_dir=SimpleNamespace(),
        videos_dir=SimpleNamespace(),
        reports_dir=SimpleNamespace(),
        destructive_actions_allowed=True,
        requires_isolated_tenant=True,
        require_explicit_company=True,
    )


def test_tenant_context_noop_without_company():
    resolver = TenantContextResolver(_DummyPage("http://127.0.0.1:5002/my-work"), _settings(company_id=None))
    resolver.ensure_company_selected()


def test_tenant_context_portal_path(monkeypatch):
    monkeypatch.setattr("app32.tests.e2e.core.tenant_context.expect", lambda _locator: SimpleNamespace(to_be_visible=lambda: None))
    resolver = TenantContextResolver(_DummyPage("http://127.0.0.1:5002/portal"), _settings())
    resolver.ensure_company_selected()


def test_tenant_context_rejects_login_redirect():
    resolver = TenantContextResolver(_DummyPage("http://127.0.0.1:5002/login?next=/my-work"), _settings())
    try:
        resolver.ensure_company_selected()
    except AssertionError as exc:
        assert "/login" in str(exc)
    else:
        raise AssertionError("Era esperado falhar quando o contexto volta para /login.")
