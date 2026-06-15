from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.catalog.ui_safe_contract_executor import write_ui_safe_execution_report


def main() -> int:
    outputs_root = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs"
    summary_path = write_ui_safe_execution_report(outputs_root)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if int(payload.get("failed_contracts_total") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
