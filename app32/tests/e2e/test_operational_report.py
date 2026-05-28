from __future__ import annotations

import json

from app32.tests.e2e.core.evidence import EvidenceCollector, create_evidence_paths
from app32.tests.e2e.core.operational_report import (
    build_mcp_concurrency_summary,
    build_report_filter_volume_summary,
    build_user_concurrency_summary,
    build_volume_summary,
    write_operational_report,
)
from app32.tests.e2e.data.builders import build_seed_batch_plan
from app32.tests.e2e.data.profiles import DATA_VOLUME_PROFILES
from app32.tests.e2e.load.concurrency_profiles import MCP_CONCURRENCY_PROFILES
from app32.tests.e2e.load.mcp_concurrency_harness import MCPConcurrencyResult
from app32.tests.e2e.load.report_filter_volume_harness import ReportFilterProbeResult
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan
from app32.tests.e2e.load.user_concurrency_harness import UserConcurrencyResult


def test_operational_report_writes_volume_summary(tmp_path):
    paths = create_evidence_paths(tmp_path)
    collector = EvidenceCollector(paths)
    summary = build_volume_summary(
        build_seed_batch_plan(
            run_marker="AUTOE2E::run_1",
            company_id=9,
            profile=DATA_VOLUME_PROFILES["large"],
        )
    )

    report_path = write_operational_report(
        collector=collector,
        report_name="volume_summary.json",
        payload=summary,
    )

    manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    assert report_path.exists()
    assert manifest["artifacts"][0]["type"] == "report"
    assert manifest["artifacts"][0]["label"] == "volume_summary.json"


def test_user_concurrency_summary_exposes_failures():
    summary = build_user_concurrency_summary(
        profile_name="baseline",
        results=[
            UserConcurrencyResult(user_label="u1", success=True, iterations_completed=3, details={}),
            UserConcurrencyResult(user_label="u2", success=False, iterations_completed=1, details={"error": "timeout"}),
        ],
    )

    assert summary["successful_workers"] == 1
    assert summary["failed_workers"] == 1
    assert summary["failures"][0]["user_label"] == "u2"


def test_mcp_concurrency_summary_exposes_surface_distribution():
    summary = build_mcp_concurrency_summary(
        plan=build_mcp_session_plan(MCP_CONCURRENCY_PROFILES["baseline"]),
        results=[
            MCPConcurrencyResult(
                session_label="m1",
                requested_surface="user",
                resolved_surface="user",
                success=True,
                commands_completed=5,
                details={},
            ),
            MCPConcurrencyResult(
                session_label="m2",
                requested_surface="admin",
                resolved_surface="user",
                success=False,
                commands_completed=0,
                details={"error": "unauthorized"},
            ),
        ],
    )

    assert summary["resolved_surface_distribution"]["user"] == 2
    assert summary["failed_sessions"] == 1
    assert summary["failures"][0]["session_label"] == "m2"


def test_report_filter_volume_summary_exposes_endpoint_distribution():
    summary = build_report_filter_volume_summary(
        profile_name="large",
        results=[
            ReportFilterProbeResult(
                endpoint="/my-work/api/filter-options",
                success=True,
                status_code=200,
                iteration=0,
                details={},
            ),
            ReportFilterProbeResult(
                endpoint="/my-work/api/activities",
                success=False,
                status_code=500,
                iteration=0,
                details={"error": "timeout"},
            ),
        ],
    )

    assert summary["endpoint_distribution"]["/my-work/api/filter-options"] == 1
    assert summary["failed_requests"] == 1
    assert summary["failures"][0]["endpoint"] == "/my-work/api/activities"
