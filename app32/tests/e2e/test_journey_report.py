from __future__ import annotations

import json
from pathlib import Path

from app32.tests.e2e.core.evidence import EvidenceCollector, create_evidence_paths
from app32.tests.e2e.core.reporter import ExecutionReporter


def test_journey_report_writes_manifest(tmp_path):
    paths = create_evidence_paths(tmp_path)
    collector = EvidenceCollector(paths)
    reporter = ExecutionReporter(collector)

    journey = reporter.start_journey(
        journey="unit_journey",
        run_id=paths.run_id,
        company_id=9,
        user_label="tester@example.com",
        metadata={"kind": "unit"},
    )
    journey.step("prepare", status="passed")
    artifact = paths.screenshots_dir / "unit.png"
    artifact.write_text("x", encoding="utf-8")
    journey.attach_artifact(
        artifact_type="screenshot",
        path=artifact,
        label="unit-shot",
        metadata={"step": "prepare"},
    )
    journey.succeed()

    manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    assert manifest["journeys"][0]["journey"] == "unit_journey"
    assert manifest["journeys"][0]["status"] == "passed"
    assert manifest["journeys"][0]["artifacts"][0]["label"] == "unit-shot"
