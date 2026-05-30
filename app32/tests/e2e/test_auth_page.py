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
    def wait_for(self):
        return None

    def count(self):
        return 0


class _DummyPage:
    def __init__(self):
        self.context = _DummyContext()
        self.calls: list[tuple[str, str, int | None]] = []

    def goto(self, url: str, wait_until: str, timeout: int | None = None):
        self.calls.append((url, wait_until, timeout))
        if len(self.calls) == 1:
            raise PlaywrightError("timeout")
        return None

    def locator(self, _selector: str):
        return _DummyLocator()


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
