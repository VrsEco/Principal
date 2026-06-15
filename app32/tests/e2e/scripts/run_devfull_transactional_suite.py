from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.core.transactional_residue import scan_marker_residue


TRANSACTIONAL_COMMANDS: list[dict[str, Any]] = [
    {
        "suite_id": "meetings_crud_devfull",
        "domain": "meetings",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_meetings_crud_e2e.py",
            "-q",
        ],
    },
    {
        "suite_id": "work_journey_manual_task_crud_devfull",
        "domain": "work_journey",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_work_journey_crud_e2e.py",
            "-q",
        ],
    },
    {
        "suite_id": "admin_performance_settings_transactional_devfull",
        "domain": "admin",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_admin_settings_crud_e2e.py",
            "-q",
        ],
    },
    {
        "suite_id": "processes_bpmn_diagram_transactional_devfull",
        "domain": "processes",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_processes_bpmn_crud_e2e.py",
            "-q",
        ],
    },
]


def _load_manifests(outputs_dir: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(outputs_dir.glob("run_*/reports/manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        payload["_manifest_path"] = str(path)
        manifests.append(payload)
    return manifests


def _build_manifest(summary: dict[str, Any]) -> dict[str, Any]:
    journeys: list[dict[str, Any]] = []
    for result in summary["results"]:
        status = "passed" if result["returncode"] == 0 else "failed"
        journeys.append(
            {
                "journey": f"{result['domain']}::{result['suite_id']}",
                "suite_id": result["suite_id"],
                "domain": result["domain"],
                "status": status,
                "failed_step": None if status == "passed" else "suite_command",
                "failure_type": None if status == "passed" else "runtime",
                "company_id": summary.get("company_id"),
            }
        )
    if summary["residue_total"]:
        journeys.append(
            {
                "journey": "cleanup::residue_audit",
                "suite_id": "devfull_transactional_validation",
                "domain": "cleanup",
                "status": "failed",
                "failed_step": "residue_audit",
                "failure_type": "cleanup",
                "company_id": summary.get("company_id"),
            }
        )
    return {
        "run_id": summary["run_id"],
        "environment": "DEV_FULL",
        "generated_at": summary["generated_at"],
        "suite_id": "devfull_transactional_validation",
        "journeys": journeys,
        "events": [
            {
                "event": "devfull_transactional_suite_completed",
                "total_suites": summary["total_suites"],
                "passed_suites": summary["passed_suites"],
                "failed_suites": summary["failed_suites"],
                "residue_total": summary["residue_total"],
            }
        ],
        "artifacts": [{"kind": "summary", "path": "summary.json"}],
    }


def main() -> int:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        raise SystemExit("A suíte transacional só pode rodar em DEV_FULL.")
    if not settings.destructive_actions_allowed:
        raise SystemExit("Defina E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true para rodar a suíte transacional.")
    if settings.company_id is None:
        raise SystemExit("E2E_COMPANY_ID obrigatório para suíte transacional.")

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_root = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs" / "devfull_transactional" / run_id
    child_outputs = target_root / "child_runs"
    reports_dir = target_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["E2E_ENV_NAME"] = "DEV_FULL"
    env["E2E_DESTRUCTIVE_ACTIONS_ALLOWED"] = "true"
    env["E2E_OUTPUTS_DIR"] = str(child_outputs)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    results: list[dict[str, Any]] = []
    for item in TRANSACTIONAL_COMMANDS:
        completed = subprocess.run(
            item["command"],
            cwd=str(ROOT_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(
            {
                "suite_id": item["suite_id"],
                "domain": item["domain"],
                "command": item["command"],
                "returncode": int(completed.returncode),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )

    manifests = _load_manifests(child_outputs)
    markers = [f"AUTOE2E::{manifest['run_id']}" for manifest in manifests if manifest.get("run_id")]
    residue_hits = scan_marker_residue(company_id=int(settings.company_id), markers=markers)
    residue_total = sum(hit.count for hit in residue_hits)
    failed_suites = sum(1 for item in results if item["returncode"] != 0)
    summary = {
        "run_id": run_id,
        "environment": "DEV_FULL",
        "generated_at": datetime.now().isoformat(),
        "company_id": settings.company_id,
        "total_suites": len(results),
        "passed_suites": sum(1 for item in results if item["returncode"] == 0),
        "failed_suites": failed_suites,
        "failed_suite_ids": [item["suite_id"] for item in results if item["returncode"] != 0],
        "residue_total": residue_total,
        "residue_hits": [hit.to_dict() for hit in residue_hits],
        "markers": markers,
        "child_manifests": manifests,
        "results": results,
    }
    (reports_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports_dir / "manifest.json").write_text(json.dumps(_build_manifest(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failed_suites == 0 and residue_total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
