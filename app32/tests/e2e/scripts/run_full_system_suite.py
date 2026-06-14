from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.catalog.suite_catalog import list_suite_catalog

EXCLUDED_FULL_RUN_SUITES = {"inventory_system_scan", "full_system_validation"}


def _decode_stdout_json(stdout: str) -> object | None:
    text = str(stdout or "").strip()
    if not text:
        return None
    start_positions = [pos for pos in (text.find("["), text.find("{")) if pos >= 0]
    if not start_positions:
        return None
    start = min(start_positions)
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(text[start:])
        return payload
    except json.JSONDecodeError:
        return None


def _collect_failed_success_checks(payload: object, *, path: str = "$") -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if payload.get("success") is False:
            failures.append(
                {
                    "path": path,
                    "check_name": payload.get("check_name"),
                    "route": payload.get("route") or payload.get("endpoint"),
                    "status_code": payload.get("status_code"),
                    "details": payload.get("details"),
                }
            )
        for key, value in payload.items():
            failures.extend(_collect_failed_success_checks(value, path=f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            failures.extend(_collect_failed_success_checks(value, path=f"{path}[{index}]"))
    return failures


def _internal_failures_from_stdout(stdout: str) -> list[dict[str, object]]:
    payload = _decode_stdout_json(stdout)
    if payload is None:
        return []
    return _collect_failed_success_checks(payload)


def _build_manifest(summary: dict[str, object]) -> dict[str, object]:
    """Converte o resumo do teste completo para o contrato operacional E2E.

    A Central do Robô lê `manifest.json`; sem este arquivo a execução completa
    terminava rápido, mas não atualizava as áreas funcionais na tela.
    """
    journeys: list[dict[str, object]] = []
    for result in summary.get("results") or []:
        if not isinstance(result, dict):
            continue
        returncode = int(result.get("returncode") or 0)
        failed_step = None
        failure_type = None
        if returncode != 0:
            failure_type = "assertion" if result.get("internal_failures") else "runtime"
            failed_step = "internal_success_check" if result.get("internal_failures") else "suite_command"
        journeys.append(
            {
                "journey": f"{result.get('domain') or 'system'}::{result.get('suite_id')}",
                "status": "passed" if returncode == 0 else "failed",
                "suite_id": result.get("suite_id"),
                "domain": result.get("domain"),
                "failed_step": failed_step,
                "failure_type": failure_type,
                "company_id": os.environ.get("E2E_COMPANY_ID"),
            }
        )
    return {
        "run_id": summary.get("run_id"),
        "environment": summary.get("environment"),
        "generated_at": summary.get("generated_at"),
        "suite_id": "full_system_validation",
        "journeys": journeys,
        "events": [
            {
                "event": "full_system_suite_completed",
                "total_suites": summary.get("total_suites"),
                "passed_suites": summary.get("passed_suites"),
                "failed_suites": summary.get("failed_suites"),
            }
        ],
        "artifacts": [
            {
                "kind": "summary",
                "path": "summary.json",
            }
        ],
    }


def main() -> int:
    environment = str(os.environ.get("E2E_ENV_NAME") or "DEV_FULL").strip().upper()
    suites = [
        suite for suite in list_suite_catalog()
        if environment in suite.environments and suite.suite_id not in EXCLUDED_FULL_RUN_SUITES
    ]

    env = os.environ.copy()
    results: list[dict[str, object]] = []
    for suite in suites:
        if suite.command_kind == "pytest":
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            command = [sys.executable, "-m", "pytest", *suite.command_args]
        elif suite.command_kind == "python":
            command = [sys.executable, *suite.command_args]
        else:
            raise RuntimeError(f"command_kind não suportado: {suite.command_kind}")

        completed = subprocess.run(
            command,
            cwd=str(ROOT_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        internal_failures = _internal_failures_from_stdout(completed.stdout)
        effective_returncode = completed.returncode if completed.returncode != 0 or not internal_failures else 1
        results.append(
            {
                "suite_id": suite.suite_id,
                "label": suite.label,
                "domain": suite.domain,
                "returncode": effective_returncode,
                "process_returncode": completed.returncode,
                "internal_failures": internal_failures,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs" / "full_system" / environment.lower() / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "environment": environment,
        "generated_at": datetime.now().isoformat(),
        "total_suites": len(results),
        "passed_suites": sum(1 for item in results if item["returncode"] == 0),
        "failed_suites": sum(1 for item in results if item["returncode"] != 0),
        "failed_suite_ids": [item["suite_id"] for item in results if item["returncode"] != 0],
        "results": results,
    }
    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(_build_manifest(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed_suites"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
