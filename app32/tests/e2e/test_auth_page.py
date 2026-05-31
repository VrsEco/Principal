from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.auth import AuthPage


class _DummyContext:
    def __init__(self):
        self.cookies_cleared = 0

    def clear_cookies(self):
        self.cookies_cleared += 1


class _DummyLocator:
    def __init__(self, page=None, selector: str | None = None):
        self.page = page
        self.selector = selector

    def wait_for(self):
        return None

    def count(self):
        if self.selector in {"#email", "#password"}:
            return 1 if getattr(self.page, "login_inputs_present", False) else 0
        return 0

    def fill(self, _value: str):
        return None

    def click(self):
        if self.page is not None:
            self.page.url = "https://app.example.com/portal"
        return None


class _DummyPage:
    def __init__(self, *, login_inputs_present: bool = False):
        self.context = _DummyContext()
        self.calls: list[tuple[str, str, int | None]] = []
        self.url = "https://app.example.com/login?next=/my-work"
        self.login_inputs_present = login_inputs_present

    def goto(self, url: str, wait_until: str, timeout: int | None = None):
        self.calls.append((url, wait_until, timeout))
        if len(self.calls) == 1:
            raise PlaywrightError("timeout")
        self.url = url
        return None

    def locator(self, _selector: str):
        return _DummyLocator(self, _selector)

    def wait_for_url(self, predicate, timeout: int | None = None):
        self.calls.append(("wait_for_url", str(timeout or ""), timeout))
        if predicate(self.url):
            return None
        raise PlaywrightError("wait_for_url timeout")


def _settings() -> E2EEnvironmentSettings:
    return E2EEnvironmentSettings(
        environment_name="PROD_SAFE",
        execution_mode=E2EExecutionMode.PROD_SAFE,
        base_url="https://app.example.com",
        login_path="/login",
        post_login_path="/my-work",
        username="tester@example.com",
        password="secret",
        company_id=10,
        headless=True,
        browser_name="chromium",
        storage_state_path=Path("dummy.json"),
        outputs_dir=Path("."),
        traces_dir=Path("."),
        screenshots_dir=Path("."),
        videos_dir=Path("."),
        reports_dir=Path("."),
        destructive_actions_allowed=False,
        requires_isolated_tenant=True,
        require_explicit_company=True,
    )


def test_auth_page_open_retries_on_initial_timeout():
    page = _DummyPage()
    auth = AuthPage(page, _settings())
    auth.open()

    assert page.context.cookies_cleared == 1
    assert page.calls[0][0].endswith("/login?next=/my-work")
    assert page.calls[1][0].endswith("/login")


def test_auth_page_login_waits_for_authenticated_transition():
    page = _DummyPage(login_inputs_present=True)
    auth = AuthPage(page, _settings())

    auth.login()

    assert page.url.endswith("/portal")
