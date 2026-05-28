from __future__ import annotations

from dataclasses import dataclass

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.evidence import EvidenceCollector, EvidencePaths
from app32.tests.e2e.core.reporter import ExecutionReporter


@dataclass(frozen=True)
class RunContext:
    settings: E2EEnvironmentSettings
    evidence: EvidencePaths
    collector: EvidenceCollector
    reporter: ExecutionReporter

    @property
    def run_marker(self) -> str:
        return f"AUTOE2E::{self.evidence.run_id}"
