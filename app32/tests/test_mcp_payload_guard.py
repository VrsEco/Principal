"""Limitador de tamanho das respostas do mcp-versus (coorte de routine)."""
from __future__ import annotations

import asyncio
import datetime as dt
import inspect
import json

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_payload_guard as guard
import src.core.mcp_surface_registry as registry
from src.core.mcp_payload_guard import guard_tool_callable, limit_mcp_payload

LIMIT = 8_000


def _big(n=400):
    return {
        "summary": {"total": n},
        "employees": [{"id": 1, "items": [{"i": i, "title": f"tarefa {i}" * 5} for i in range(n)]}],
        "small": [1, 2, 3],
    }


def test_small_payload_is_returned_untouched_and_identical():
    data = {"a": [1, 2, 3], "b": "x"}
    assert limit_mcp_payload(data, max_chars=LIMIT) is data


def test_non_container_results_pass_through():
    assert limit_mcp_payload("texto", max_chars=LIMIT) == "texto"
    assert limit_mcp_payload(None, max_chars=LIMIT) is None


def test_oversized_dict_is_reduced_under_limit_and_marked():
    data = _big()
    assert len(json.dumps(data)) > LIMIT
    out = limit_mcp_payload(data, max_chars=LIMIT)
    assert len(json.dumps(out, ensure_ascii=False)) <= LIMIT
    meta = out["_truncation"]
    assert meta["truncated"] is True and meta["max_chars"] == LIMIT and meta["original_chars"] > LIMIT
    cut = {item["path"]: item for item in meta["lists"]}
    items = cut["employees[0].items"]
    assert items["total"] == 400 and 1 <= items["kept"] < 400
    assert len(out["employees"][0]["items"]) == items["kept"]


def test_unrelated_fields_and_small_lists_are_preserved():
    out = limit_mcp_payload(_big(), max_chars=LIMIT)
    assert out["summary"] == {"total": 400}
    assert out["small"] == [1, 2, 3]
    assert out["employees"][0]["id"] == 1


def test_original_object_is_not_mutated():
    data = _big()
    before = json.dumps(data, sort_keys=True)
    limit_mcp_payload(data, max_chars=LIMIT)
    assert json.dumps(data, sort_keys=True) == before


def test_top_level_list_is_wrapped_and_marked():
    out = limit_mcp_payload([{"i": i, "t": "x" * 50} for i in range(500)], max_chars=LIMIT)
    assert set(out) == {"items", "_truncation"}
    assert len(json.dumps(out)) <= LIMIT


def test_non_serializable_values_do_not_break_it():
    data = {"d": dt.date(2026, 10, 8), "rows": [{"day": dt.datetime(2026, 10, 8), "t": "x" * 200} for _ in range(200)]}
    out = limit_mcp_payload(data, max_chars=LIMIT)
    assert out["_truncation"]["truncated"] is True
    json.dumps(out)


def test_irreducible_long_strings_are_shortened():
    out = limit_mcp_payload({"texto": "x" * 50_000}, max_chars=LIMIT)
    assert len(out["texto"]) < 3_000
    assert out["_truncation"]["truncated"] is True


def test_guard_never_raises_on_hostile_input():
    class Boom:
        def __repr__(self):
            raise RuntimeError("boom")

    value = {"x": [Boom() for _ in range(3)]}
    assert limit_mcp_payload(value, max_chars=LIMIT) is value


def test_env_override_and_invalid_values(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_MAX_RESPONSE_CHARS", "12000")
    assert guard.max_response_chars() == 12_000
    for bad in ("abc", "100", "-5", ""):
        monkeypatch.setenv("MCP_VERSUS_MAX_RESPONSE_CHARS", bad)
        assert guard.max_response_chars() == guard.DEFAULT_MAX_CHARS


def test_guard_preserves_signature_for_schema_generation():
    def tool(company_id: int, employee_id: int | None = None) -> dict:
        """Doc."""
        return _big()

    wrapped = guard_tool_callable(tool, lambda r: limit_mcp_payload(r, max_chars=LIMIT))
    assert inspect.signature(wrapped) == inspect.signature(tool)
    assert wrapped.__doc__ == "Doc."
    assert wrapped.__app32_result_guarded__ is True
    assert "_truncation" in wrapped(9)


def test_guard_supports_async_tools():
    async def tool(company_id: int) -> dict:
        return _big()

    wrapped = guard_tool_callable(tool, lambda r: limit_mcp_payload(r, max_chars=LIMIT))
    assert inspect.iscoroutinefunction(wrapped)
    assert "_truncation" in asyncio.run(wrapped(9))


def test_errors_from_the_tool_still_propagate():
    def tool() -> dict:
        raise PermissionError("grant negado")

    with pytest.raises(PermissionError):
        guard_tool_callable(tool)()


def test_every_routine_tool_is_registered_with_the_guard(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv("MCP_VERSUS_ROUTINE_READ_ENABLED", "1")
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user")))
    server = registry.build_oauth_unified_mcp_server()
    registered = {tool.name: tool for tool in asyncio.run(FastMCP.list_tools(server))}
    manager = server._tool_manager
    for name in registry.UNIFIED_ROUTINE_READ_TOOL_NAMES:
        assert name in registered, name
        fn = manager.get_tool(name).fn
        assert getattr(fn, "__app32_result_guarded__", False) is True, f"{name} sem limitador de tamanho"
