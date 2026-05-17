from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import src.core.mcp_http_server as http_server


def _load_connections_module():
    module_path = Path(
        r"C:\GestaoVersus\app32\app32\.agent\vendor-skills\skills\mcp-builder\scripts\connections.py"
    )
    spec = importlib.util.spec_from_file_location("mcp_builder_connections", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar módulo de conexões MCP.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_http_server_flag_supports_stateless_mode(monkeypatch):
    monkeypatch.setenv("APP32_MCP_HTTP_STATELESS", "true")
    assert http_server._env_flag("APP32_MCP_HTTP_STATELESS", False) is True


def test_http_connection_reinitializes_and_replays_on_invalid_session():
    module = _load_connections_module()
    conn = module.MCPConnectionHTTP("https://example.com/mcp/user", reconnect_attempts=2, reconnect_backoff_seconds=0)

    reconnect_calls: list[str] = []
    attempts = {"count": 0}

    async def fake_reconnect():
        reconnect_calls.append("reconnected")

    async def fake_list_tools():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("Bad Request: No valid session ID provided")
        return [{"name": "ok"}]

    conn._reconnect = fake_reconnect  # type: ignore[method-assign]

    result = asyncio.run(conn._call_with_reconnect("list_tools", fake_list_tools))

    assert result == [{"name": "ok"}]
    assert attempts["count"] == 2
    assert reconnect_calls == ["reconnected"]


def test_http_connection_does_not_retry_for_non_session_error():
    module = _load_connections_module()
    conn = module.MCPConnectionHTTP("https://example.com/mcp/user", reconnect_attempts=2, reconnect_backoff_seconds=0)

    async def fake_callback():
        raise RuntimeError("Erro de validação de payload")

    try:
        asyncio.run(conn._call_with_reconnect("call_tool:test", fake_callback))
    except RuntimeError as exc:
        assert "payload" in str(exc)
    else:
        raise AssertionError("Era esperado RuntimeError para erro não relacionado à sessão.")
