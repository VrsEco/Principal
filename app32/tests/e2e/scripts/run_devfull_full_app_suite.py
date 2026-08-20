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

from app32.tests.e2e.catalog.inventory import load_inventory
from app32.tests.e2e.catalog.suite_catalog import get_suite_definition
from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings


FULL_APP_SUITE_IDS = [
    "inventory_system_scan",
    "ui_inventory_contract_scan",
    "ui_human_like_contract_generation",
    "ui_safe_contract_execution",
    "ui_mutation_contract_execution",
    "smoke_real_navigation",
    "workspace_functional_probe",
    "integrations_functional_probe",
    "meetings_functional_probe",
    "work_journey_functional_probe",
    "processes_functional_probe",
    "financial_functional_probe",
    "contracts_functional_probe",
    "contracts_tenant_contract_probe",
    "workspace_tenant_contract_probe",
    "consultive_tenant_contract_probe",
    "reports_functional_probe",
    "admin_functional_probe",
    "mcp_http_health_probe",
    "full_coverage_autocorrect_audit",
    "user_concurrency_probe",
    "mcp_concurrency_probe",
    "devfull_transactional_validation",
    "drift_detection",
]

TRANSACTIONAL_DOMAINS_IMPLEMENTED = {"admin", "financial", "integrations", "meetings", "processes", "work_journey"}


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


def _print_json_utf8(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _run_suite(suite_id: str, env: dict[str, str]) -> dict[str, Any]:
    suite = get_suite_definition(suite_id)
    if "DEV_FULL" not in suite.environments:
        return {
            "suite_id": suite_id,
            "label": suite.label,
            "domain": suite.domain,
            "returncode": 0,
            "skipped": True,
            "skip_reason": "Suíte não aplicável em DEV_FULL.",
        }

    child_env = env.copy()
    if suite.command_kind == "pytest":
        child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        command = [sys.executable, "-m", "pytest", *suite.command_args]
    elif suite.command_kind == "python":
        command = [sys.executable, *suite.command_args]
    else:
        raise RuntimeError(f"command_kind não suportado: {suite.command_kind}")

    completed = _run_command_with_timeout(command, env=child_env)
    return {
        "suite_id": suite.suite_id,
        "label": suite.label,
        "domain": suite.domain,
        "destructive": suite.destructive,
        "command": command,
        "returncode": int(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _coverage_matrix() -> list[dict[str, Any]]:
    inventory = load_inventory()
    modules = inventory.get("modules") or []
    rows: list[dict[str, Any]] = []
    for module in modules:
        name = str(module.get("name") or "")
        items = module.get("items") or []
        implemented_items = [item for item in items if str(item.get("scenario") or "").strip().lower() not in {"", "backlog"}]
        trans_items = [
            item for item in implemented_items
            if "DEV_FULL" in (item.get("environment_modes") or [])
            and any(action in {"criar", "alterar", "excluir", "salvar_parametrizacao", "salvar_rascunho"} for action in (item.get("actions") or []))
        ]
        rows.append(
            {
                "module": name,
                "criticality": module.get("criticality"),
                "inventory_items": len(items),
                "functional_covered_items": len(implemented_items),
                "transactional_candidate_items": len(trans_items),
                "transactional_status": "implemented" if name in TRANSACTIONAL_DOMAINS_IMPLEMENTED else "pending",
            }
        )
    return rows


def _build_manifest(summary: dict[str, Any]) -> dict[str, Any]:
    journeys: list[dict[str, Any]] = []
    for result in summary.get("results") or []:
        failed = int(result.get("returncode") or 0) != 0
        journeys.append(
            {
                "journey": f"{result.get('domain')}::{result.get('suite_id')}",
                "suite_id": result.get("suite_id"),
                "domain": result.get("domain"),
                "status": "failed" if failed else "passed",
                "failed_step": "suite_command" if failed else None,
                "failure_type": "runtime" if failed else None,
                "company_id": summary.get("company_id"),
            }
        )
    return {
        "run_id": summary["run_id"],
        "environment": "DEV_FULL",
        "generated_at": summary["generated_at"],
        "suite_id": "devfull_full_app_validation",
        "journeys": journeys,
        "events": [
            {
                "event": "devfull_full_app_suite_completed",
                "total_suites": summary["total_suites"],
                "passed_suites": summary["passed_suites"],
                "failed_suites": summary["failed_suites"],
                "transactional_domains_implemented": sorted(TRANSACTIONAL_DOMAINS_IMPLEMENTED),
            }
        ],
        "artifacts": [{"kind": "summary", "path": "summary.json"}],
    }


def main() -> int:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        raise SystemExit("A suíte full-app destrutiva/controlada só pode rodar em DEV_FULL.")
    if settings.company_id is None:
        raise SystemExit("E2E_COMPANY_ID obrigatório para suíte full-app.")

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_root = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs" / "devfull_full_app" / run_id
    reports_dir = target_root / "reports"
    child_outputs = target_root / "child_runs"
    reports_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["E2E_ENV_NAME"] = "DEV_FULL"
    env["E2E_DESTRUCTIVE_ACTIONS_ALLOWED"] = "true"
    env["E2E_OUTPUTS_DIR"] = str(child_outputs)

    results = [_run_suite(suite_id, env) for suite_id in FULL_APP_SUITE_IDS]
    failed = [item for item in results if int(item.get("returncode") or 0) != 0]
    coverage = _coverage_matrix()
    summary = {
        "run_id": run_id,
        "environment": "DEV_FULL",
        "generated_at": datetime.now().isoformat(),
        "company_id": settings.company_id,
        "total_suites": len(results),
        "passed_suites": len(results) - len(failed),
        "failed_suites": len(failed),
        "failed_suite_ids": [item["suite_id"] for item in failed],
        "coverage_matrix": coverage,
        "transactional_domains_implemented": sorted(TRANSACTIONAL_DOMAINS_IMPLEMENTED),
        "transactional_domains_pending": [
            row["module"] for row in coverage
            if row["transactional_candidate_items"] and row["transactional_status"] != "implemented"
        ],
        "results": results,
    }
    (reports_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports_dir / "manifest.json").write_text(json.dumps(_build_manifest(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    _print_json_utf8(summary)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
