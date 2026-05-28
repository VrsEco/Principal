from __future__ import annotations

from dataclasses import dataclass

from app32.tests.e2e.data.profiles import DataVolumeProfile


@dataclass(frozen=True)
class SeedBatchPlan:
    run_marker: str
    company_id: int
    volume_profile: str
    record_count: int
    report_row_count: int


def build_seed_batch_plan(
    *,
    run_marker: str,
    company_id: int,
    profile: DataVolumeProfile,
) -> SeedBatchPlan:
    return SeedBatchPlan(
        run_marker=run_marker,
        company_id=company_id,
        volume_profile=profile.name,
        record_count=profile.record_count,
        report_row_count=profile.report_row_count,
    )
