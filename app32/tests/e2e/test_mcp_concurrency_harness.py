from __future__ import annotations

from app32.tests.e2e.load.concurrency_profiles import MCP_CONCURRENCY_PROFILES
from app32.tests.e2e.load.mcp_concurrency_harness import _ensure_company_scope, execute_mcp_concurrency
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan
from app32.tests.e2e.test_http_session_contract import _settings


def test_ensure_company_scope_appends_company_id():
    assert _ensure_company_scope("https://app.gestaoversus.com.br/mcp/user/", 9) == (
        "https://app.gestaoversus.com.br/mcp/user/?company_id=9"
    )


def test_mcp_concurrency_harness_collects_results(monkeypatch):
    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

    monkeypatch.setattr(
        "app32.tests.e2e.load.mcp_concurrency_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    monkeypatch.setattr(
        "app32.tests.e2e.load.mcp_concurrency_harness._generate_mcp_token",
        lambda *_args, **kwargs: {
            "token": "mcpu_test",
            "url": "https://app.gestaoversus.com.br/mcp/user/?company_id=9",
            "surface": kwargs["surface"],
        },
    )
    monkeypatch.setattr(
        "app32.tests.e2e.load.mcp_concurrency_harness._run_mcp_session_sync",
        lambda **kwargs: {
            "available_tools": ["bootstrap_session_context"],
            "executed_tools": ["bootstrap_session_context"] * kwargs["commands_per_session"],
            "commands": [],
        },
    )

    plan = build_mcp_session_plan(MCP_CONCURRENCY_PROFILES["baseline"])
    results = execute_mcp_concurrency(settings=_settings(), plan=plan)

    assert len(results) == MCP_CONCURRENCY_PROFILES["baseline"].concurrent_sessions
    assert all(result.success for result in results)
    assert all(result.commands_completed == MCP_CONCURRENCY_PROFILES["baseline"].commands_per_session for result in results)
