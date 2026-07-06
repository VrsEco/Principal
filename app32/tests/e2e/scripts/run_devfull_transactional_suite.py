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


MUTATION_STEP_HINTS: dict[str, tuple[str, ...]] = {
    "create": ("create", "criar"),
    "update": ("update", "edit", "alterar", "salvar", "save"),
    "process": ("process", "gerar", "execute", "run"),
    "cancel": ("cancel", "cancelar"),
    "delete": ("delete", "excluir", "remove", "cleanup"),
    "rollback": ("rollback", "restore", "restaura", "delete_", "cleanup"),
}

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
    {
        "suite_id": "financial_catalog_schedule_transactional_devfull",
        "domain": "financial",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_financial_catalog_schedule_crud_e2e.py",
            "-q",
        ],
    },
    {
        "suite_id": "integrations_request_transactional_devfull",
        "domain": "integrations",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/crud/test_integrations_request_crud_e2e.py",
            "-q",
        ],
    },
]


def _suite_timeout_seconds() -> int:
    return int(os.environ.get("E2E_SUITE_TIMEOUT_SECONDS") or 300)


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        return
    process.kill()


def _run_command_with_timeout(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    timeout_seconds = _suite_timeout_seconds()
    process = subprocess.Popen(
        command,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return subprocess.CompletedProcess(
            args=command,
            returncode=int(process.returncode or 0),
            stdout=stdout or "",
            stderr=stderr or "",
        )
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=(exc.stdout or stdout or ""),
            stderr=(exc.stderr or stderr or "") + f"\nTimeoutExpired: suíte excedeu {timeout_seconds}s.\n",
        )


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
                "mutating_steps_total": (summary.get("controlled_mutation") or {}).get("mutating_steps_total"),
                "rollback_steps_total": (summary.get("controlled_mutation") or {}).get("rollback_steps_total"),
            }
        ],
        "artifacts": [{"kind": "summary", "path": "summary.json"}],
    }


def _classify_step(name: str) -> set[str]:
    normalized = str(name or "").lower()
    return {
        bucket
        for bucket, hints in MUTATION_STEP_HINTS.items()
        if any(hint in normalized for hint in hints)
    }


def _summarize_mutation_steps(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {bucket: 0 for bucket in MUTATION_STEP_HINTS}
    domains: dict[str, dict[str, int]] = {}
    total_passed_steps = 0
    total_failed_steps = 0

    for manifest in manifests:
        for journey in manifest.get("journeys") or []:
            domain = str((journey.get("metadata") or {}).get("domain") or "unknown")
            domain_counts = domains.setdefault(domain, {bucket: 0 for bucket in MUTATION_STEP_HINTS})
            for step in journey.get("steps") or []:
                status = str(step.get("status") or "")
                if status == "passed":
                    total_passed_steps += 1
                if status == "failed":
                    total_failed_steps += 1
                if status != "passed":
                    continue
                for bucket in _classify_step(str(step.get("name") or "")):
                    counts[bucket] += 1
                    domain_counts[bucket] += 1

    return {
        "mutation_step_counts": counts,
        "mutation_steps_by_domain": domains,
        "mutating_steps_total": sum(counts[bucket] for bucket in ("create", "update", "process", "cancel", "delete")),
        "rollback_steps_total": counts["rollback"],
        "passed_steps_total": total_passed_steps,
        "failed_steps_total": total_failed_steps,
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
        completed = _run_command_with_timeout(item["command"], env=env)
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
    mutation_summary = _summarize_mutation_steps(manifests)
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
        "controlled_mutation": {
            "company_id": settings.company_id,
            "destructive_actions_allowed": settings.destructive_actions_allowed,
            "requires_explicit_company": True,
            "cleanup_policy": "rollback_or_delete_and_residue_zero",
            "residue_zero": residue_total == 0,
            **mutation_summary,
        },
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
