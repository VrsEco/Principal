from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.catalog.suite_catalog import get_suite_definition


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa uma suíte E2E oficial por suite_id e ambiente.")
    parser.add_argument("--suite-id", required=True)
    parser.add_argument("--environment", required=True)
    args = parser.parse_args()

    suite = get_suite_definition(args.suite_id)
    environment = str(args.environment or "").strip().upper()
    if environment not in suite.environments:
        raise SystemExit(f"Suíte {args.suite_id} não suporta ambiente {environment}.")

    env = os.environ.copy()
    env["E2E_ENV_NAME"] = environment
    if suite.command_kind == "pytest":
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        command = [sys.executable, "-m", "pytest", *suite.command_args]
    elif suite.command_kind == "python":
        command = [sys.executable, *suite.command_args]
    else:
        raise SystemExit(f"command_kind não suportado: {suite.command_kind}")

    completed = subprocess.run(command, cwd=str(ROOT_DIR), env=env, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
