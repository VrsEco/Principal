from __future__ import annotations

import json

from app32.tests.e2e.core.evidence import EvidenceCollector, create_evidence_paths


def test_evidence_manifest_registers_artifacts(tmp_path):
    paths = create_evidence_paths(tmp_path)
    collector = EvidenceCollector(paths)
    artifact = paths.screenshots_dir / "screen.png"
    artifact.write_text("fake", encoding="utf-8")

    collector.register_artifact(
        artifact_type="screenshot",
        path=artifact,
        label="fake-screen",
        metadata={"scenario": "unit"},
    )
    collector.add_event("unit_event", ok=True)

    manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == paths.run_id
    assert manifest["artifacts"][0]["label"] == "fake-screen"
    assert manifest["events"][0]["name"] == "unit_event"
