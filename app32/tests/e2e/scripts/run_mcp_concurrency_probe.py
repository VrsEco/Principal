from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.load.concurrency_profiles import MCP_CONCURRENCY_PROFILES
from app32.tests.e2e.load.mcp_concurrency_harness import execute_mcp_concurrency
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan


def main() -> int:
    settings = load_environment_settings()
    if settings.execution_mode is not E2EExecutionMode.DEV_FULL:
        raise SystemExit("O probe MCP concorrente só pode rodar em DEV_FULL.")
    settings.validate_or_raise()

    plan = build_mcp_session_plan(MCP_CONCURRENCY_PROFILES["baseline"])
    results = execute_mcp_concurrency(settings=settings, plan=plan)

    print(
        json.dumps(
            {
                "profile": plan.profile_name,
                "concurrent_sessions": plan.concurrent_sessions,
                "commands_per_session": plan.commands_per_session,
                "results": [
                    {
                        "session_label": result.session_label,
                        "requested_surface": result.requested_surface,
                        "resolved_surface": result.resolved_surface,
                        "success": result.success,
                        "commands_completed": result.commands_completed,
                        "details": result.details,
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
