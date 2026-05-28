from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.catalog.drift_detector import detect_inventory_drift


def main() -> int:
    payload = detect_inventory_drift()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "aligned" else 1


if __name__ == "__main__":
    raise SystemExit(main())
