from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.core.full_coverage_autocorrect import write_full_coverage_audit_report


def main() -> int:
    company_id_raw = str(os.environ.get("E2E_COMPANY_ID") or "").strip()
    company_id = int(company_id_raw) if company_id_raw.isdigit() else None
    outputs_root = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs"
    sync_aa_j1 = str(os.environ.get("E2E_AUTOCORRECT_CREATE_AAJ1") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "sim",
    }
    summary_path = write_full_coverage_audit_report(
        outputs_root,
        company_id=company_id,
        sync_aa_j1=sync_aa_j1,
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    strict = str(os.environ.get("E2E_COVERAGE_STRICT") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "sim",
    }
    if strict and int(payload.get("coverage_gaps_total") or 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
