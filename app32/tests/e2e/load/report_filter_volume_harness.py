from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.data.profiles import DataVolumeProfile


@dataclass(frozen=True)
class ReportFilterProbeResult:
    endpoint: str
    success: bool
    status_code: int
    iteration: int
    details: dict[str, Any]


CRITICAL_FILTER_ENDPOINTS = (
    "/my-work/api/filter-options",
    "/my-work/api/activities",
    "/api/dashboard/filter-options",
)


def execute_report_filter_volume_probe(
    *,
    settings: E2EEnvironmentSettings,
    profile: DataVolumeProfile,
) -> list[ReportFilterProbeResult]:
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    iterations = max(1, min(12, profile.record_count // 200))
    results: list[ReportFilterProbeResult] = []
    for iteration in range(iterations):
        for endpoint in CRITICAL_FILTER_ENDPOINTS:
            response = http.request("GET", endpoint)
            results.append(
                ReportFilterProbeResult(
                    endpoint=endpoint,
                    success=response.ok,
                    status_code=response.status_code,
                    iteration=iteration,
                    details={"profile": profile.name},
                )
            )
    return results
