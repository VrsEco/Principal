from __future__ import annotations

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from requests.cookies import create_cookie


def _settings() -> E2EEnvironmentSettings:
    from pathlib import Path

    return E2EEnvironmentSettings(
        environment_name="DEV_FULL",
        execution_mode=E2EExecutionMode.DEV_FULL,
        base_url="http://localhost:5002",
        login_path="/login",
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


def test_http_session_json_guard_gives_clear_error():
    session = AuthenticatedHTTPSession.create(_settings())

    class _Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        text = "<html>login</html>"

        def json(self):
            raise ValueError("not json")

    try:
        session._json_or_raise(_Response(), operation="select_company")
    except RuntimeError as exc:
        assert "esperado JSON" in str(exc)
        assert "text/html" in str(exc)
    else:
        raise AssertionError("Era esperado erro claro para resposta não JSON.")


def test_http_session_rejects_login_redirect():
    session = AuthenticatedHTTPSession.create(_settings())

    class _Response:
        url = "http://localhost:5002/login?next=/my-work"

    try:
        session.assert_not_login_redirect(_Response(), operation="workspace.activities")
    except RuntimeError as exc:
        assert "redirecionou para login" in str(exc)
    else:
        raise AssertionError("Era esperado erro claro para redirect de login.")


def test_http_session_falls_back_to_browser_bootstrap(monkeypatch):
    session = AuthenticatedHTTPSession.create(_settings())

    class _FailingSession:
        headers = {"Content-Type": "application/json"}
        cookies = session.session.cookies

        def post(self, *_args, **_kwargs):
            raise RuntimeError("timeout")

    monkeypatch.setattr(session, "session", _FailingSession())
    monkeypatch.setattr(
        session,
        "_bootstrap_via_browser_login",
        lambda: {"success": True, "redirect": "/my-work", "auth_source": "browser_bootstrap"},
    )

    payload = session.login()
    assert payload["auth_source"] == "browser_bootstrap"


def test_http_session_rejects_stale_storage_cookie(monkeypatch):
    session = AuthenticatedHTTPSession.create(_settings())
    session.session.cookies.set_cookie(create_cookie(name="gv_session", value="stale", domain="localhost", path="/"))
    monkeypatch.setattr(session, "_session_is_authenticated", lambda: False)
    monkeypatch.setattr(
        session,
        "_bootstrap_via_browser_login",
        lambda: {"success": True, "redirect": "/my-work", "auth_source": "browser_bootstrap"},
    )

    payload = session.login()
    assert payload["auth_source"] == "browser_bootstrap"


def test_http_session_uses_remote_internal_bootstrap_before_browser(monkeypatch):
    session = AuthenticatedHTTPSession.create(_settings())

    class _FailingSession:
        headers = {"Content-Type": "application/json"}
        cookies = session.session.cookies

        def post(self, *_args, **_kwargs):
            raise RuntimeError("timeout")

    monkeypatch.setattr(session, "session", _FailingSession())
    monkeypatch.setattr(
        session,
        "_bootstrap_via_remote_internal_session",
        lambda: {"success": True, "redirect": "/my-work", "auth_source": "remote_internal_bootstrap"},
    )
    monkeypatch.setattr(session, "_bootstrap_via_browser_login", lambda: (_ for _ in ()).throw(AssertionError("não deveria cair no browser")))

    payload = session.login()
    assert payload["auth_source"] == "remote_internal_bootstrap"
