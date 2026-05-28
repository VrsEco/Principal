from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import load_environment_settings
from app32.tests.e2e.core.auth import AuthPage
from app32.tests.e2e.core.browser_session import managed_page
from app32.tests.e2e.core.evidence import create_evidence_paths


def main() -> None:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    evidence = create_evidence_paths(settings.outputs_dir)
    with managed_page(settings, evidence) as (_, _, _, page):
        auth_page = AuthPage(page, settings)
        auth_page.open()
        auth_page.login()
        auth_page.ensure_authenticated_workspace()
    print(settings.storage_state_path)


if __name__ == "__main__":
    main()
