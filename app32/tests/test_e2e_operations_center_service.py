import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.e2e_operations_center_service import E2EOperationsCenterService


class _Task:
    def __init__(self, task_id=11, task_code="AA.J.31.11"):
        self.id = task_id
        self.task_code = task_code


def test_e2e_operations_center_service_collects_latest_runs(tmp_path, monkeypatch):
    repo_root = tmp_path
    reports_dir = repo_root / "app32" / "tests" / "e2e" / "outputs" / "dev_full" / "run_1" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_1",
                "generated_at": "2026-05-27T19:00:00",
                "artifacts": [{"label": "shot", "path": str(reports_dir / "shot.png")}],
                "events": [{"name": "boot"}],
                "journeys": [{"journey": "smoke", "status": "failed", "failure_type": "AssertionError", "failed_step": "authenticate", "company_id": 9}],
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "shot.png").write_text("x", encoding="utf-8")

    reports_dir2 = repo_root / "app32" / "tests" / "e2e" / "outputs" / "prod_safe" / "run_2" / "reports"
    reports_dir2.mkdir(parents=True)
    (reports_dir2 / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_2",
                "generated_at": "2026-05-27T20:00:00",
                "artifacts": [],
                "events": [{"name": "boot"}],
                "journeys": [{"journey": "smoke", "status": "passed"}],
            }
        ),
        encoding="utf-8",
    )

    runbooks = repo_root / "app32" / "docs" / "runbooks"
    runbooks.mkdir(parents=True)
    (runbooks / "robot_e2e_aa_j18_sprint1_runbook.md").write_text("# Sprint 1", encoding="utf-8")
    (runbooks / "robot_e2e_aa_j18_sprint5_runbook.md").write_text("# Sprint 5", encoding="utf-8")

    monkeypatch.setattr(E2EOperationsCenterService, "get_repo_root", classmethod(lambda cls: repo_root))
    monkeypatch.setattr(E2EOperationsCenterService, "get_outputs_root", classmethod(lambda cls: repo_root / "app32" / "tests" / "e2e" / "outputs"))
    monkeypatch.setattr(E2EOperationsCenterService, "get_runbooks_root", classmethod(lambda cls: repo_root / "app32" / "docs" / "runbooks"))

    state = E2EOperationsCenterService.build_frontend_state(SimpleNamespace(id=9, name="Versus", client_code="VRS"))

    assert state["summary"]["total_runs"] >= 2
    assert state["summary"]["backlog_candidates"] == 1
    assert state["system_actions"]["inventory_scan"]["suite_id"] == "inventory_system_scan"
    assert state["system_actions"]["full_validation"]["suite_id"] == "full_system_validation"
    assert all(item["suite_id"] not in {"inventory_system_scan", "full_system_validation"} for item in state["partial_suite_catalog"])
    assert {item["environment"] for item in state["latest_runs"][:2]} == {"DEV_FULL", "PROD_SAFE"}
    assert state["latest_diff"]["status"] in {"stable", "regression"}
    assert state["operational_view"]["coverage"]["matrix"][0]["item"] == "Telas e páginas"
    assert state["operational_view"]["execution"]["matrix"][0]["item"] == "Rodadas executadas"
    assert state["operational_view"]["issues"]["matrix"][0]["item"]
    assert state["operational_view"]["issues"]["items"][0]["severity"] in {"alta", "média"}
    assert state["runbooks"][-1]["label"] in {"Sprint 5", "Sprint 6"}


def test_e2e_operations_center_service_resolves_run_detail_and_backlog_sync(tmp_path, monkeypatch):
    repo_root = tmp_path
    reports_dir = repo_root / "app32" / "tests" / "e2e" / "outputs" / "dev_full" / "run_x" / "reports"
    reports_dir.mkdir(parents=True)
    artifact_path = reports_dir / "trace.zip"
    artifact_path.write_text("trace", encoding="utf-8")
    (reports_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "generated_at": "2026-05-27T19:00:00",
                "artifacts": [{"label": "trace", "path": str(artifact_path)}],
                "events": [],
                "journeys": [{"journey": "smoke", "status": "failed", "failure_type": "TimeoutError", "failed_step": "open_workspace", "company_id": 9}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(E2EOperationsCenterService, "get_repo_root", classmethod(lambda cls: repo_root))
    monkeypatch.setattr(E2EOperationsCenterService, "get_outputs_root", classmethod(lambda cls: repo_root / "app32" / "tests" / "e2e" / "outputs"))

    detail = E2EOperationsCenterService.get_run_detail("run_x")
    assert detail["artifacts_total"] == 1
    assert detail["backlog_candidates"][0]["failure_type"] == "timeout"
    assert E2EOperationsCenterService._build_operational_view([], [detail], detail["backlog_candidates"])["issues"]["items"][0]["suggestion"]
    assert E2EOperationsCenterService.resolve_run_file("run_x", "artifact", artifact_index=0).name == "trace.zip"

    result = E2EOperationsCenterService.sync_backlog_candidates(
        "run_x",
        user_id=5,
        company_id=9,
        create_task_fn=lambda **kwargs: (_Task(), None),
    )
    assert result["created"][0]["task_code"] == "AA.J.31.11"
