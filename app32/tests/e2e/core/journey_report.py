from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app32.tests.e2e.core.evidence import EvidenceCollector


@dataclass
class JourneyReport:
    journey: str
    run_id: str
    company_id: int | None
    user_label: str | None
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str | None = None
    failed_step: str | None = None
    failure_type: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, *, status: str, failed_step: str | None = None, failure_type: str | None = None) -> None:
        self.status = status
        self.finished_at = datetime.now().isoformat()
        self.failed_step = failed_step
        self.failure_type = failure_type


class JourneyReporter:
    def __init__(self, collector: EvidenceCollector, journey: JourneyReport):
        self.collector = collector
        self.journey = journey
        self._flush()

    def step(self, name: str, *, status: str, details: dict[str, Any] | None = None) -> None:
        self.journey.steps.append(
            {
                "name": name,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "details": details or {},
            }
        )
        self._flush()

    def attach_artifact(self, *, artifact_type: str, path: Path, label: str, metadata: dict[str, Any] | None = None) -> None:
        payload = {
            "type": artifact_type,
            "label": label,
            "path": str(path),
            "metadata": metadata or {},
        }
        self.journey.artifacts.append(payload)
        self.collector.register_artifact(
            artifact_type=artifact_type,
            path=path,
            label=label,
            metadata=metadata or {},
        )
        self._flush()

    def fail(self, *, step: str, failure_type: str, details: dict[str, Any] | None = None) -> None:
        self.step(step, status="failed", details=details or {})
        self.journey.finish(status="failed", failed_step=step, failure_type=failure_type)
        self._flush()

    def succeed(self) -> None:
        self.journey.finish(status="passed")
        self._flush()

    def _flush(self) -> None:
        self.collector.add_or_replace_journey(
            {
                "journey": self.journey.journey,
                "run_id": self.journey.run_id,
                "company_id": self.journey.company_id,
                "user_label": self.journey.user_label,
                "status": self.journey.status,
                "started_at": self.journey.started_at,
                "finished_at": self.journey.finished_at,
                "failed_step": self.journey.failed_step,
                "failure_type": self.journey.failure_type,
                "artifacts": self.journey.artifacts,
                "steps": self.journey.steps,
                "metadata": self.journey.metadata,
            }
        )
