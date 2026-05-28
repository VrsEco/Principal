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
