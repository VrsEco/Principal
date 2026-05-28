from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import load_environment_settings
from app32.tests.e2e.config.profiles import build_execution_contract


def main() -> None:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    contract = build_execution_contract(settings)
    print(
        json.dumps(
            {
                "environment_name": settings.environment_name,
                "base_url": settings.base_url,
                "login_path": settings.login_path,
                "post_login_path": settings.post_login_path,
                "company_id": settings.company_id,
                "headless": settings.headless,
                "browser_name": settings.browser_name,
                "outputs_dir": str(settings.outputs_dir),
                "contract": {
                    "mode": contract.mode.value,
                    "destructive_actions_allowed": contract.destructive_actions_allowed,
                    "requires_isolated_tenant": contract.requires_isolated_tenant,
                    "require_explicit_company": contract.require_explicit_company,
                    "summary": contract.summary,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
