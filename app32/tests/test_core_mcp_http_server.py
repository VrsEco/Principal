from __future__ import annotations

import asyncio
import json

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse

import src.core.mcp_http_server as http_server


def test_transport_security_allows_public_reverse_proxy_host_and_local_runtime():
    settings = http_server._build_transport_security_settings()
    if settings is None:
        pytest.skip("Pacote MCP local ainda não expõe TransportSecuritySettings.")

    assert settings.enable_dns_rebinding_protection is True
    assert "app.gestaoversus.com.br" in settings.allowed_hosts
    assert "app.gestaoversus.com.br:443" in settings.allowed_hosts
    assert "127.0.0.1:*" in settings.allowed_hosts
    assert "https://app.gestaoversus.com.br" in settings.allowed_origins


def test_create_http_app_mounts_expected_surfaces(monkeypatch):
    def fake_surface_app(surface: str):
        app = Starlette()

        async def endpoint(_):
            return JSONResponse({"surface": surface})

        app.add_route("/", endpoint)
        return app

    monkeypatch.setattr(http_server, "build_surface_http_app", fake_surface_app)

    app = http_server.create_http_app()
    paths = {getattr(route, "path", None) for route in app.routes}

    assert "/" in paths
    assert "/healthz" in paths
    assert "/mcp/user" in paths
    assert "/mcp/admin" in paths
    assert "/mcp/analytics" in paths
    assert "/mcp/ops" in paths



def test_healthz_publishes_safe_transient_recovery_contract():
    response = asyncio.run(http_server._healthz(None))

    assert response.status_code == 200
    recovery = json.loads(response.body)["transient_recovery"]
    assert recovery["retryable_http_statuses"] == [502, 503, 504]
    assert recovery["read_only_max_attempts"] == 3
    assert recovery["backoff_seconds"] == [1, 2, 4]
    assert recovery["restore_company_and_harness"] is True
    assert recovery["auto_retry_mutations"] is False
