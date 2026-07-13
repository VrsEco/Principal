from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class McpRuntimeCommandResult:
    action: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ok": self.ok,
            "exit_code": self.exit_code,
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
            "status": _parse_status_output(self.stdout),
        }


def _app_dir() -> Path:
    configured = os.environ.get("APP32_APP_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1]


def _manager_script() -> Path:
    return _app_dir() / "scripts" / "manage_mcp_http.sh"


def _parse_status_output(output: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for raw_line in (output or "").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        status[key.strip()] = value.strip()
    return status


class McpRuntimeHealthService:
    """Operações controladas sobre o runtime MCP HTTP.

    A regra de negócio fica centralizada no script idempotente
    `scripts/manage_mcp_http.sh`; este serviço apenas cria uma ponte segura
    para telas administrativas e testes.
    """

    ALLOWED_ACTIONS = {"status", "health", "restart"}

    @classmethod
    def run_manager(cls, action: str, *, timeout_seconds: int = 90) -> McpRuntimeCommandResult:
        normalized = (action or "").strip().lower()
        if normalized not in cls.ALLOWED_ACTIONS:
            raise ValueError("Ação MCP não permitida.")

        script = _manager_script()
        if not script.exists():
            return McpRuntimeCommandResult(
                action=normalized,
                exit_code=127,
                stdout="",
                stderr=f"Script de gerenciamento MCP não encontrado: {script}",
            )

        completed = subprocess.run(
            ["bash", str(script), normalized],
            cwd=str(_app_dir()),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return McpRuntimeCommandResult(
            action=normalized,
            exit_code=int(completed.returncode),
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    @classmethod
    def status(cls) -> dict[str, Any]:
        result = cls.run_manager("status", timeout_seconds=30)
        payload = result.to_payload()
        status = payload.get("status") or {}
        payload["healthy"] = status.get("local_health") == "ok" and status.get("public_health") == "ok"
        return payload

    @classmethod
    def repair(cls) -> dict[str, Any]:
        before = cls.status()
        if before.get("healthy") is True:
            return {
                "success": True,
                "repaired": False,
                "message": "Runtime MCP já estava saudável.",
                "before": before,
                "after": before,
            }

        restart = cls.run_manager("restart", timeout_seconds=120).to_payload()
        after = cls.status()
        success = bool(after.get("healthy"))
        return {
            "success": success,
            "repaired": success,
            "message": "Runtime MCP reiniciado com sucesso." if success else "Falha ao reparar runtime MCP.",
            "before": before,
            "restart": restart,
            "after": after,
        }


__all__ = ["McpRuntimeHealthService", "McpRuntimeCommandResult"]
