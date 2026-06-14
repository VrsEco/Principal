from __future__ import annotations

import json
from pathlib import Path

from app32.tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService


def test_supervised_execution_service_lists_suites():
    suites = E2ESupervisedExecutionService.list_suites()

    assert any(item["suite_id"] == "smoke_real_navigation" for item in suites)


def test_supervised_execution_service_reads_execution_meta(tmp_path, monkeypatch):
    execution_root = tmp_path / "supervised_runs"
    execution_dir = execution_root / "exec-1"
    execution_dir.mkdir(parents=True)
    meta = execution_dir / "meta.json"
    meta.write_text(
        json.dumps(
            {
                "execution_id": "exec-1",
                "suite_id": "smoke_real_navigation",
                "environment": "DEV_FULL",
                "status": "passed",
                "started_at": "2026-05-27T20:00:00",
                "finished_at": "2026-05-27T20:01:00",
                "command": ["python"],
                "workdir": "C:/GestaoVersus/app32",
                "stdout_path": "stdout.log",
                "stderr_path": "stderr.log",
                "exit_code": 0,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(E2ESupervisedExecutionService, "supervised_root", classmethod(lambda cls: execution_root))
    items = E2ESupervisedExecutionService.list_executions()

    assert items[0]["execution_id"] == "exec-1"
    assert items[0]["status"] == "passed"


def test_supervised_execution_service_refreshes_orphan_running_execution(tmp_path, monkeypatch):
    execution_root = tmp_path / "supervised_runs"
    execution_dir = execution_root / "exec-orphan"
    execution_dir.mkdir(parents=True)
    stdout_path = execution_dir / "stdout.log"
    stderr_path = execution_dir / "stderr.log"
    stdout_path.write_text("[{\"success\": true}]", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    (execution_dir / "meta.json").write_text(
        json.dumps(
            {
                "execution_id": "exec-orphan",
                "suite_id": "workspace_functional_probe",
                "environment": "PROD_SAFE",
                "status": "running",
                "started_at": "2026-06-14T19:35:00",
                "finished_at": None,
                "command": ["python"],
                "workdir": "C:/GestaoVersus/app32",
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "exit_code": None,
                "pid": 99999999,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(E2ESupervisedExecutionService, "supervised_root", classmethod(lambda cls: execution_root))
    items = E2ESupervisedExecutionService.list_executions()

    assert items[0]["status"] == "passed"
    assert items[0]["exit_code"] == 0


def test_supervised_execution_service_marks_orphan_summary_with_failed_suites_as_failed(tmp_path, monkeypatch):
    execution_root = tmp_path / "supervised_runs"
    execution_dir = execution_root / "exec-full"
    execution_dir.mkdir(parents=True)
    stdout_path = execution_dir / "stdout.log"
    stderr_path = execution_dir / "stderr.log"
    stdout_path.write_text(json.dumps({"failed_suites": 2, "results": []}), encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    (execution_dir / "meta.json").write_text(
        json.dumps(
            {
                "execution_id": "exec-full",
                "suite_id": "full_system_validation",
                "environment": "PROD_SAFE",
                "status": "running",
                "started_at": "2026-06-14T19:35:00",
                "finished_at": None,
                "command": ["python"],
                "workdir": "C:/GestaoVersus/app32",
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "exit_code": None,
                "pid": 99999999,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(E2ESupervisedExecutionService, "supervised_root", classmethod(lambda cls: execution_root))
    items = E2ESupervisedExecutionService.list_executions()

    assert items[0]["status"] == "failed"
    assert items[0]["exit_code"] == 1


def test_supervised_execution_service_resolves_python_without_uwsgi(monkeypatch):
    monkeypatch.setenv("APP32_E2E_PYTHON", "")
    monkeypatch.setenv("VIRTUAL_ENV", "")
    monkeypatch.setattr("app32.tests.e2e.core.e2e_supervised_execution_service.sys.executable", "/var/www/.pyenv/versions/3.12.12/bin/uwsgi")
    monkeypatch.setattr("app32.tests.e2e.core.e2e_supervised_execution_service.sys._base_executable", "/usr/bin/python3", raising=False)

    command = E2ESupervisedExecutionService._build_command("python", ("app32/tests/e2e/scripts/build_inventory_candidates.py",))

    assert Path(command[0]).name.lower().startswith("python")
    assert "uwsgi" not in command[0].lower()
