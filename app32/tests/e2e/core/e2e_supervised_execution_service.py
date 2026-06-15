from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from app32.tests.e2e.catalog.suite_catalog import get_suite_definition, list_suite_catalog, repo_root
except ModuleNotFoundError:  # pragma: no cover - compatibilidade de import local
    from tests.e2e.catalog.suite_catalog import get_suite_definition, list_suite_catalog, repo_root


@dataclass
class SupervisedExecutionRecord:
    execution_id: str
    suite_id: str
    environment: str
    status: str
    started_at: str
    finished_at: str | None
    command: list[str]
    workdir: str
    stdout_path: str
    stderr_path: str
    exit_code: int | None
    pid: int | None = None
    worker_pid: int | None = None
    child_pid: int | None = None
    summary_path: str | None = None
    manifest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class E2ESupervisedExecutionService:
    _process_registry: dict[str, subprocess.Popen] = {}

    @classmethod
    def supervised_root(cls) -> Path:
        return repo_root() / "app32" / "tests" / "e2e" / "outputs" / "supervised_runs"

    @classmethod
    def _execution_dir(cls, execution_id: str) -> Path:
        return cls.supervised_root() / execution_id

    @classmethod
    def _meta_path(cls, execution_id: str) -> Path:
        return cls._execution_dir(execution_id) / "meta.json"

    @classmethod
    def list_suites(cls) -> list[dict[str, Any]]:
        return [item.to_dict() for item in list_suite_catalog()]

    @classmethod
    def start_execution(
        cls,
        *,
        suite_id: str,
        environment: str,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        suite = get_suite_definition(suite_id)
        if environment not in suite.environments:
            raise ValueError(f"Suíte {suite_id} não suporta ambiente {environment}.")

        execution_id = f"{suite_id}-{uuid.uuid4().hex[:10]}"
        execution_dir = cls._execution_dir(execution_id)
        execution_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = execution_dir / "stdout.log"
        stderr_path = execution_dir / "stderr.log"

        command = cls._build_command(suite.command_kind, suite.command_args)
        env = os.environ.copy()
        env["E2E_ENV_NAME"] = environment
        env.setdefault("E2E_BASE_URL", env.get("EXTERNAL_URL") or "https://app.gestaoversus.com.br")
        if company_id is not None:
            env["E2E_COMPANY_ID"] = str(company_id)
        if user_id is not None:
            env["E2E_USER_ID"] = str(user_id)
        if suite.command_kind == "pytest":
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        cls._inject_browser_native_library_path(env)

        record = SupervisedExecutionRecord(
            execution_id=execution_id,
            suite_id=suite_id,
            environment=environment,
            status="running",
            started_at=datetime.now().isoformat(),
            finished_at=None,
            command=command,
            workdir=str(repo_root()),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            exit_code=None,
        )
        cls._write_record(record)
        worker_command = cls._build_worker_command(
            execution_id=execution_id,
            command=command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        with open(os.devnull, "rb") as devnull_in, open(os.devnull, "wb") as devnull_out:
            process = subprocess.Popen(
                worker_command,
                cwd=str(repo_root()),
                env=env,
                stdin=devnull_in,
                stdout=devnull_out,
                stderr=devnull_out,
                close_fds=True,
                start_new_session=(os.name != "nt"),
            )
        cls._process_registry[execution_id] = process
        payload = record.to_dict()
        payload["pid"] = process.pid
        payload["worker_pid"] = process.pid
        cls._write_payload(execution_id, payload)
        return payload

    @classmethod
    def list_executions(cls) -> list[dict[str, Any]]:
        root = cls.supervised_root()
        if not root.exists():
            return []
        items: list[dict[str, Any]] = []
        for meta_path in sorted(root.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            items.append(cls._refresh_record(payload))
        return items

    @classmethod
    def get_execution(cls, execution_id: str) -> dict[str, Any]:
        meta_path = cls._meta_path(execution_id)
        if not meta_path.exists():
            raise FileNotFoundError(execution_id)
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return cls._refresh_record(payload)

    @classmethod
    def _refresh_record(cls, payload: dict[str, Any]) -> dict[str, Any]:
        execution_id = payload["execution_id"]
        process = cls._process_registry.get(execution_id)
        if process is not None:
            exit_code = process.poll()
            if exit_code is None:
                return payload
            payload["exit_code"] = exit_code
            payload["status"] = "passed" if exit_code == 0 else "failed"
            payload["finished_at"] = payload.get("finished_at") or datetime.now().isoformat()
            cls._process_registry.pop(execution_id, None)
            cls._write_payload(execution_id, payload)
            return payload
        if payload.get("status") == "running" and not cls._pid_is_alive(payload.get("pid")):
            payload["exit_code"] = cls._infer_orphan_exit_code(payload)
            payload["status"] = "passed" if payload["exit_code"] == 0 else "failed"
            payload["finished_at"] = payload.get("finished_at") or datetime.now().isoformat()
            cls._write_payload(execution_id, payload)
        return payload

    @staticmethod
    def _pid_is_alive(raw_pid: Any) -> bool:
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _infer_orphan_exit_code(payload: dict[str, Any]) -> int:
        stderr_path = Path(str(payload.get("stderr_path") or ""))
        stdout_path = Path(str(payload.get("stdout_path") or ""))
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
        if not stdout_text.strip() and not stderr_text.strip():
            return 1
        decoded_stdout = E2ESupervisedExecutionService._decode_stdout_json(stdout_text)
        if E2ESupervisedExecutionService._payload_has_failure(decoded_stdout):
            return 1
        if "Traceback" in stderr_text or "Error:" in stderr_text or "FAILED" in stdout_text:
            return 1
        return 0

    @staticmethod
    def _decode_stdout_json(stdout: str) -> Any:
        text = str(stdout or "").strip()
        if not text:
            return None
        start_positions = [pos for pos in (text.find("["), text.find("{")) if pos >= 0]
        if not start_positions:
            return None
        decoder = json.JSONDecoder()
        try:
            payload, _ = decoder.raw_decode(text[min(start_positions):])
            return payload
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _payload_has_failure(payload: Any) -> bool:
        if isinstance(payload, dict):
            if payload.get("failed_suites") or payload.get("returncode") not in {None, 0}:
                return True
            if payload.get("success") is False:
                return True
            return any(E2ESupervisedExecutionService._payload_has_failure(value) for value in payload.values())
        if isinstance(payload, list):
            return any(E2ESupervisedExecutionService._payload_has_failure(item) for item in payload)
        return False

    @staticmethod
    def _build_command(command_kind: str, command_args: tuple[str, ...]) -> list[str]:
        python_executable = E2ESupervisedExecutionService._resolve_python_executable()
        if command_kind == "pytest":
            return [python_executable, "-m", "pytest", *command_args]
        if command_kind == "python":
            return [python_executable, *command_args]
        raise ValueError(f"command_kind não suportado: {command_kind}")

    @staticmethod
    def _resolve_python_executable() -> str:
        repo_based_candidates = E2ESupervisedExecutionService._discover_repo_python_candidates()
        executable_based_candidates = E2ESupervisedExecutionService._discover_python_near_current_executable()
        candidates = [
            os.environ.get("APP32_E2E_PYTHON"),
            *repo_based_candidates,
            *executable_based_candidates,
            str(Path(os.environ.get("VIRTUAL_ENV", "")).joinpath("bin", "python")) if os.environ.get("VIRTUAL_ENV") else None,
            getattr(sys, "_base_executable", None),
            shutil.which("python3"),
            shutil.which("python"),
            sys.executable,
        ]
        for candidate in candidates:
            if not candidate:
                continue
            executable_name = Path(str(candidate)).name.lower()
            if executable_name in {"uwsgi", "uwsgi.exe"}:
                continue
            return str(candidate)
        return "python3"

    @staticmethod
    def _build_worker_command(
        *,
        execution_id: str,
        command: list[str],
        stdout_path: Path,
        stderr_path: Path,
    ) -> list[str]:
        python_executable = E2ESupervisedExecutionService._resolve_python_executable()
        worker_script = repo_root() / "app32" / "tests" / "e2e" / "scripts" / "supervised_run_worker.py"
        return [
            python_executable,
            str(worker_script.relative_to(repo_root())),
            "--execution-id",
            execution_id,
            "--command-json",
            json.dumps(command, ensure_ascii=False),
            "--workdir",
            str(repo_root()),
            "--stdout-path",
            str(stdout_path),
            "--stderr-path",
            str(stderr_path),
            "--meta-path",
            str(E2ESupervisedExecutionService._meta_path(execution_id)),
        ]

    @staticmethod
    def _inject_browser_native_library_path(env: dict[str, str]) -> None:
        """Permite Playwright em hosts sem pacotes nativos instalados via sudo.

        No Configr o usuário `app` não possui sudo; as bibliotecas do Chromium
        podem ser provisionadas em espaço do usuário e expostas ao subprocesso
        E2E por `LD_LIBRARY_PATH`.
        """
        candidates = [
            Path("/home/app/.local/gv-browser-libs/root/usr/lib/x86_64-linux-gnu"),
            repo_root().parent / ".local" / "gv-browser-libs" / "root" / "usr" / "lib" / "x86_64-linux-gnu",
        ]
        existing = [str(path) for path in candidates if path.exists()]
        if not existing:
            return
        current = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = ":".join([*existing, current] if current else existing)

    @staticmethod
    def _discover_repo_python_candidates() -> list[str]:
        root = repo_root()
        candidates: list[str] = []
        for anchor in (root.parent, root):
            virtualenv_root = anchor / ".virtualenv"
            if virtualenv_root.exists():
                for python_path in virtualenv_root.glob("*/bin/python*"):
                    if python_path.is_file() and "config" not in python_path.name:
                        candidates.append(str(python_path))
        for anchor in (root, root.parent):
            for direct_candidate in ("venv", ".venv"):
                python_path = anchor / direct_candidate / "bin" / "python"
                if python_path.is_file():
                    candidates.append(str(python_path))
        return candidates

    @staticmethod
    def _discover_python_near_current_executable() -> list[str]:
        executable = Path(str(sys.executable or ""))
        if not executable.name.lower().startswith("uwsgi"):
            return []
        search_dir = executable.parent
        candidates: list[str] = []
        for name in ("python", "python3", "python3.12", "python3.11", "python3.10"):
            python_path = search_dir / name
            if python_path.is_file():
                candidates.append(str(python_path))
        return candidates

    @classmethod
    def _write_record(cls, record: SupervisedExecutionRecord) -> None:
        cls._write_payload(record.execution_id, record.to_dict())

    @classmethod
    def _write_payload(cls, execution_id: str, payload: dict[str, Any]) -> None:
        meta_path = cls._meta_path(execution_id)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
