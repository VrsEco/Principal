"""Sonda externa de saúde do mcp-versus: decisões de status e leitura do log (sem rede)."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qa" / "mcp_health_probe.py"
spec = importlib.util.spec_from_file_location("mcp_health_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
sys.modules["mcp_health_probe"] = probe  # dataclasses resolve anotações por sys.modules
spec.loader.exec_module(probe)

BASE = "https://mcp.example"
METADATA = json.dumps(
    {
        "resource": f"{BASE}/mcp/pilot",
        "authorization_servers": ["https://id.example/realms/app32"],
        "scopes_supported": ["mcp:access", "mcp:user", "mcp:analytics", "mcp:finance"],
    }
).encode()
OIDC = json.dumps({"token_endpoint": "https://id.example/realms/app32/protocol/openid-connect/token"}).encode()


def _fetcher(overrides=None, seconds=0.2):
    routes = {
        f"{BASE}/mcp/healthz": (200, b"ok"),
        f"{BASE}/.well-known/oauth-protected-resource/mcp/pilot": (200, METADATA),
        "https://id.example/realms/app32/.well-known/openid-configuration": (200, OIDC),
        f"{BASE}/mcp/pilot/": (401, b""),
    }
    routes.update(overrides or {})

    def fetch(url, timeout):
        outcome = routes[url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome[0], outcome[1], seconds

    return fetch


def _report(fetch):
    return probe.Report(base=BASE, checks=probe.run_checks(BASE, fetch))


def test_all_green_is_healthy():
    report = _report(_fetcher())
    assert [c.status for c in report.checks] == ["ok", "ok", "ok", "ok"] and report.exit_code == 0


def test_slow_response_is_degraded_not_failed():
    report = _report(_fetcher(seconds=4.0))
    assert report.exit_code == 1 and {c.status for c in report.checks} == {"slow"}


def test_very_slow_or_unreachable_is_a_failure():
    assert _report(_fetcher(seconds=11.0)).exit_code == 2
    report = _report(_fetcher({f"{BASE}/mcp/healthz": TimeoutError()}))
    assert report.exit_code == 2 and report.checks[0].name == "healthz" and "TimeoutError" in report.checks[0].detail


def test_healthz_not_200_fails():
    assert _report(_fetcher({f"{BASE}/mcp/healthz": (503, b"")})).exit_code == 2


def test_discovery_without_base_scopes_fails():
    metadata = json.dumps({"authorization_servers": ["https://id.example/realms/app32"], "scopes_supported": ["mcp:analytics"]}).encode()
    report = _report(_fetcher({f"{BASE}/.well-known/oauth-protected-resource/mcp/pilot": (200, metadata)}))
    check = next(c for c in report.checks if c.name == "oauth_discovery")
    assert check.status == "fail" and "ausentes" in check.detail and report.exit_code == 2


def test_missing_authorization_server_skips_the_idp_check_and_fails_discovery():
    metadata = json.dumps({"scopes_supported": ["mcp:access", "mcp:user"]}).encode()
    report = _report(_fetcher({f"{BASE}/.well-known/oauth-protected-resource/mcp/pilot": (200, metadata)}))
    assert "idp_discovery" not in {c.name for c in report.checks} and report.exit_code == 2


def test_idp_down_fails():
    report = _report(_fetcher({"https://id.example/realms/app32/.well-known/openid-configuration": (502, b"")}))
    assert next(c for c in report.checks if c.name == "idp_discovery").status == "fail" and report.exit_code == 2


@pytest.mark.parametrize("status", [200, 500, 502])
def test_mcp_endpoint_must_demand_authentication(status):
    report = _report(_fetcher({f"{BASE}/mcp/pilot/": (status, b"")}))
    assert next(c for c in report.checks if c.name == "mcp_requires_auth").status == "fail"


def test_log_scan_counts_symptoms_inside_the_window(tmp_path):
    log = tmp_path / "mcp.log"
    log.write_text(
        "\n".join(
            [
                "2026-10-09T10:00:00 WARNING:src.core.mcp_surface_registry:MCP permission discovery failed (OperationalError)",
                "2026-10-09T12:30:00 WARNING MCP permission discovery failed (OperationalError)",
                "2026-10-09T12:40:00 Traceback (most recent call last):",
                "2026-10-09T12:41:00 INFO tudo bem",
            ]
        ),
        encoding="utf-8",
    )
    counts = probe.scan_log(log, minutes=60, now=datetime(2026, 10, 9, 13, 0, tzinfo=timezone.utc))
    assert counts == {"permission_discovery_failed": 1, "operational_error": 1, "traceback": 1}


def test_log_symptoms_degrade_the_result():
    report = probe.Report(base=BASE, checks=probe.run_checks(BASE, _fetcher()), log_counts={"permission_discovery_failed": 2, "operational_error": 2, "traceback": 0})
    assert report.exit_code == 1


def test_render_mentions_every_check_and_the_verdict():
    text = probe.render(_report(_fetcher()))
    assert "healthz" in text and "idp_discovery" in text and "RESULTADO: saudável" in text
