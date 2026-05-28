from __future__ import annotations

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


def _settings() -> E2EEnvironmentSettings:
    from pathlib import Path

    return E2EEnvironmentSettings(
        environment_name="DEV_FULL",
        execution_mode=E2EExecutionMode.DEV_FULL,
        base_url="http://localhost:5002",
        login_path="/auth/login",
        post_login_path="/my-work",
        username="tester@example.com",
        password="secret",
        company_id=9,
        headless=False,
        browser_name="chromium",
        storage_state_path=Path("dummy.json"),
        outputs_dir=Path("."),
        traces_dir=Path("."),
        screenshots_dir=Path("."),
        videos_dir=Path("."),
        reports_dir=Path("."),
        destructive_actions_allowed=True,
        requires_isolated_tenant=True,
        require_explicit_company=True,
    )


def test_http_session_factory():
    session = AuthenticatedHTTPSession.create(_settings())
    assert session.settings.base_url == "http://localhost:5002"
    assert session.session.headers["Content-Type"] == "application/json"
