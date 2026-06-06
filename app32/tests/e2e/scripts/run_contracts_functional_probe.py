from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import load_environment_settings
from app32.tests.e2e.load.contracts_functional_harness import execute_contracts_functional_probe


def main() -> int:
    settings = load_environment_settings()
    validate_execution_contract(settings)
    results = execute_contracts_functional_probe(settings=settings)
    print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
