from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from app32.tests.e2e.core.evidence import EvidenceCollector
from app32.tests.e2e.core.journey_report import JourneyReport, JourneyReporter


class ExecutionReporter:
    def __init__(self, collector: EvidenceCollector):
        self.collector = collector

    def capture_screenshot(self, page: Page, *, label: str, file_name: str) -> Path:
        path = self.collector.paths.screenshots_dir / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        self.collector.register_artifact(
            artifact_type="screenshot",
            path=path,
            label=label,
        )
        return path

    def register_trace(self, path: Path) -> None:
        self.collector.register_artifact(
            artifact_type="trace",
            path=path,
            label="playwright-trace",
        )

    def add_event(self, name: str, **payload) -> None:
        self.collector.add_event(name, **payload)

    def start_journey(
        self,
        *,
        journey: str,
        run_id: str,
        company_id: int | None,
        user_label: str | None,
        metadata: dict | None = None,
    ) -> JourneyReporter:
        return JourneyReporter(
            self.collector,
            JourneyReport(
                journey=journey,
                run_id=run_id,
                company_id=company_id,
                user_label=user_label,
                metadata=metadata or {},
            ),
        )
