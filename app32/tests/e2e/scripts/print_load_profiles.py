from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.data.profiles import DATA_VOLUME_PROFILES
from app32.tests.e2e.load.concurrency_profiles import (
    MCP_CONCURRENCY_PROFILES,
    USER_CONCURRENCY_PROFILES,
)
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan


def main() -> None:
    payload = {
        "data_volume_profiles": {
            key: profile.__dict__ for key, profile in DATA_VOLUME_PROFILES.items()
        },
        "user_concurrency_profiles": {
            key: profile.__dict__ for key, profile in USER_CONCURRENCY_PROFILES.items()
        },
        "mcp_concurrency_profiles": {
            key: {
                **profile.__dict__,
                "session_plan": build_mcp_session_plan(profile).__dict__,
            }
            for key, profile in MCP_CONCURRENCY_PROFILES.items()
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
