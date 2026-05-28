from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataVolumeProfile:
    name: str
    record_count: int
    report_row_count: int
    description: str


SMALL_DATASET = DataVolumeProfile(
    name="small",
    record_count=25,
    report_row_count=100,
    description="massa reduzida para validação rápida local",
)

LARGE_DATASET = DataVolumeProfile(
    name="large",
    record_count=2_000,
    report_row_count=25_000,
    description="massa alta para stress funcional de listagens, filtros e relatórios",
)

HUGE_DATASET = DataVolumeProfile(
    name="huge",
    record_count=10_000,
    report_row_count=150_000,
    description="massa extrema para homologação controlada e soak tests",
)


DATA_VOLUME_PROFILES = {
    profile.name: profile
    for profile in (SMALL_DATASET, LARGE_DATASET, HUGE_DATASET)
}
