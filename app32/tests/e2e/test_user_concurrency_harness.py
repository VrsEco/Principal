from __future__ import annotations

from app32.tests.e2e.load.concurrency_profiles import USER_CONCURRENCY_PROFILES
from app32.tests.e2e.load.user_concurrency_harness import execute_user_concurrency
from app32.tests.e2e.test_http_session_contract import _settings


def test_user_concurrency_harness_collects_results(monkeypatch):
    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

    monkeypatch.setattr(
        "app32.tests.e2e.load.user_concurrency_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_user_concurrency(
        settings=_settings(),
        profile=USER_CONCURRENCY_PROFILES["baseline"],
        operation=lambda _http, iteration: {"iteration": iteration},
    )

    assert len(results) == USER_CONCURRENCY_PROFILES["baseline"].concurrent_users
    assert all(result.success for result in results)
