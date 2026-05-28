from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.load.concurrency_profiles import USER_CONCURRENCY_PROFILES
from app32.tests.e2e.load.user_concurrency_harness import execute_user_concurrency


def main() -> None:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        raise SystemExit("Este harness multiusuário só pode rodar em DEV_FULL.")

    profile = USER_CONCURRENCY_PROFILES["baseline"]

    def operation(http, _iteration: int):
        response = http.request("GET", "/my-work")
        return {"status_code": response.status_code, "ok": response.ok}

    results = execute_user_concurrency(
        settings=settings,
        profile=profile,
        operation=operation,
    )
    print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
