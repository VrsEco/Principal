from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from app32.tests.e2e.core.evidence import EvidenceCollector, EvidencePaths
from app32.tests.e2e.data.builders import SeedBatchPlan
from app32.tests.e2e.load.mcp_concurrency_harness import MCPConcurrencyResult
from app32.tests.e2e.load.report_filter_volume_harness import ReportFilterProbeResult
from app32.tests.e2e.load.mcp_session_plan import MCPSessionPlan
from app32.tests.e2e.load.user_concurrency_harness import UserConcurrencyResult


def build_volume_summary(plan: SeedBatchPlan) -> dict[str, Any]:
    return {
        "kind": "data_volume",
        "run_marker": plan.run_marker,
        "company_id": plan.company_id,
        "volume_profile": plan.volume_profile,
        "record_count": plan.record_count,
        "report_row_count": plan.report_row_count,
    }


def build_user_concurrency_summary(
    *,
    profile_name: str,
    results: list[UserConcurrencyResult],
) -> dict[str, Any]:
    total = len(results)
    success_count = sum(1 for result in results if result.success)
    failed = [result for result in results if not result.success]
    return {
        "kind": "user_concurrency",
        "profile_name": profile_name,
        "total_workers": total,
        "successful_workers": success_count,
        "failed_workers": total - success_count,
        "success_rate": round((success_count / total) if total else 0.0, 4),
        "iterations_completed": sum(result.iterations_completed for result in results),
        "failures": [asdict(result) for result in failed],
        "results": [asdict(result) for result in results],
    }


def build_mcp_concurrency_summary(
    *,
    plan: MCPSessionPlan,
    results: list[MCPConcurrencyResult],
) -> dict[str, Any]:
    total = len(results)
    success_count = sum(1 for result in results if result.success)
    surfaces: dict[str, int] = {}
    for result in results:
        surfaces[result.resolved_surface] = surfaces.get(result.resolved_surface, 0) + 1
    failed = [result for result in results if not result.success]
    return {
        "kind": "mcp_concurrency",
        "profile_name": plan.profile_name,
        "requested_surfaces": list(plan.surfaces),
        "total_sessions": total,
        "successful_sessions": success_count,
        "failed_sessions": total - success_count,
        "success_rate": round((success_count / total) if total else 0.0, 4),
        "commands_requested": plan.commands_per_session * plan.concurrent_sessions,
        "commands_completed": sum(result.commands_completed for result in results),
        "resolved_surface_distribution": surfaces,
        "failures": [asdict(result) for result in failed],
        "results": [asdict(result) for result in results],
    }


def build_report_filter_volume_summary(
    *,
    profile_name: str,
    results: list[ReportFilterProbeResult],
) -> dict[str, Any]:
    total = len(results)
    success_count = sum(1 for result in results if result.success)
    by_endpoint: dict[str, int] = {}
    for result in results:
        by_endpoint[result.endpoint] = by_endpoint.get(result.endpoint, 0) + 1
    failed = [result.__dict__ for result in results if not result.success]
    return {
        "kind": "report_filter_volume",
        "profile_name": profile_name,
        "total_requests": total,
        "successful_requests": success_count,
        "failed_requests": total - success_count,
        "success_rate": round((success_count / total) if total else 0.0, 4),
        "endpoint_distribution": by_endpoint,
        "failures": failed,
        "results": [result.__dict__ for result in results],
    }


def write_operational_report(
    *,
    collector: EvidenceCollector,
    report_name: str,
    payload: dict[str, Any],
) -> Path:
    path = collector.paths.reports_dir / report_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    collector.register_artifact(
        artifact_type="report",
        path=path,
        label=report_name,
        metadata={"kind": payload.get("kind")},
    )
    collector.add_event("operational_report_written", report_name=report_name, kind=payload.get("kind"))
    return path


def create_operational_report_paths(base_dir: Path) -> EvidencePaths:
    from app32.tests.e2e.core.evidence import create_evidence_paths

    return create_evidence_paths(base_dir)
