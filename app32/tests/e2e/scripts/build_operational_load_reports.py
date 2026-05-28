from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.core.evidence import EvidenceCollector
from app32.tests.e2e.core.operational_report import (
    build_mcp_concurrency_summary,
    build_report_filter_volume_summary,
    build_user_concurrency_summary,
    build_volume_summary,
    create_operational_report_paths,
    write_operational_report,
)
from app32.tests.e2e.data.builders import build_seed_batch_plan
from app32.tests.e2e.data.profiles import DATA_VOLUME_PROFILES
from app32.tests.e2e.load.concurrency_profiles import MCP_CONCURRENCY_PROFILES, USER_CONCURRENCY_PROFILES
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan
from app32.tests.e2e.load.mcp_concurrency_harness import MCPConcurrencyResult
from app32.tests.e2e.load.report_filter_volume_harness import ReportFilterProbeResult
from app32.tests.e2e.load.user_concurrency_harness import UserConcurrencyResult


def main() -> int:
    paths = create_operational_report_paths(ROOT_DIR / "app32" / "tests" / "e2e" / "outputs" / "operational_reports")
    collector = EvidenceCollector(paths)

    volume_summary = build_volume_summary(
        build_seed_batch_plan(
            run_marker=f"AUTOE2E::{paths.run_id}",
            company_id=9,
            profile=DATA_VOLUME_PROFILES["large"],
        )
    )
    user_summary = build_user_concurrency_summary(
        profile_name=USER_CONCURRENCY_PROFILES["baseline"].name,
        results=[
            UserConcurrencyResult(
                user_label="tester#1",
                success=True,
                iterations_completed=USER_CONCURRENCY_PROFILES["baseline"].iterations_per_user,
                details={"status_code": 200},
            )
        ],
    )
    mcp_summary = build_mcp_concurrency_summary(
        plan=build_mcp_session_plan(MCP_CONCURRENCY_PROFILES["baseline"]),
        results=[
            MCPConcurrencyResult(
                session_label="mcp-session-1",
                requested_surface="user",
                resolved_surface="user",
                success=True,
                commands_completed=MCP_CONCURRENCY_PROFILES["baseline"].commands_per_session,
                details={"executed_tools": ["bootstrap_session_context"]},
            )
        ],
    )
    report_filter_summary = build_report_filter_volume_summary(
        profile_name=DATA_VOLUME_PROFILES["large"].name,
        results=[
            ReportFilterProbeResult(
                endpoint="/my-work/api/filter-options",
                success=True,
                status_code=200,
                iteration=0,
                details={"profile": "large"},
            )
        ],
    )

    write_operational_report(collector=collector, report_name="volume_summary.json", payload=volume_summary)
    write_operational_report(collector=collector, report_name="user_concurrency_summary.json", payload=user_summary)
    write_operational_report(collector=collector, report_name="mcp_concurrency_summary.json", payload=mcp_summary)
    write_operational_report(collector=collector, report_name="report_filter_volume_summary.json", payload=report_filter_summary)

    print(
        json.dumps(
            {
                "run_id": paths.run_id,
                "reports_dir": str(paths.reports_dir),
                "reports": [volume_summary, user_summary, mcp_summary, report_filter_summary],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
