from __future__ import annotations

from services.mcp_runtime_health_service import McpRuntimeCommandResult, McpRuntimeHealthService


def test_mcp_runtime_command_result_parses_status_output():
    result = McpRuntimeCommandResult(
        action="status",
        exit_code=0,
        stdout="port=8101\nlocal_health=ok\npublic_health=fail\n",
        stderr="",
    )

    payload = result.to_payload()

    assert payload["ok"] is True
    assert payload["status"]["port"] == "8101"
    assert payload["status"]["local_health"] == "ok"
    assert payload["status"]["public_health"] == "fail"


def test_mcp_runtime_repair_skips_restart_when_already_healthy(monkeypatch):
    monkeypatch.setattr(McpRuntimeHealthService, "status", classmethod(lambda cls: {"healthy": True}))

    payload = McpRuntimeHealthService.repair()

    assert payload["success"] is True
    assert payload["repaired"] is False
    assert "já estava saudável" in payload["message"]


def test_mcp_runtime_repair_restarts_when_unhealthy(monkeypatch):
    statuses = [{"healthy": False}, {"healthy": True}]
    calls = []

    monkeypatch.setattr(McpRuntimeHealthService, "status", classmethod(lambda cls: statuses.pop(0)))
    monkeypatch.setattr(
        McpRuntimeHealthService,
        "run_manager",
        classmethod(
            lambda cls, action, timeout_seconds=90: calls.append(action)
            or McpRuntimeCommandResult(action=action, exit_code=0, stdout="local_health=ok\npublic_health=ok\n", stderr="")
        ),
    )

    payload = McpRuntimeHealthService.repair()

    assert calls == ["restart"]
    assert payload["success"] is True
    assert payload["repaired"] is True
