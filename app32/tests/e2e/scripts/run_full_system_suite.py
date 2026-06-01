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
        results.append(
            {
                "suite_id": suite.suite_id,
                "label": suite.label,
                "domain": suite.domain,
                "returncode": completed.returncode,
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
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed_suites"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
