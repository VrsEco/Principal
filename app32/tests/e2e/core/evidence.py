from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidencePaths:
    run_id: str
    root_dir: Path
    traces_dir: Path
    screenshots_dir: Path
    videos_dir: Path
    reports_dir: Path
    manifest_path: Path
    junit_path: Path


class EvidenceCollector:
    def __init__(self, paths: EvidencePaths):
        self.paths = paths
        self._manifest: dict[str, Any] = {
            "run_id": paths.run_id,
            "generated_at": datetime.now().isoformat(),
            "artifacts": [],
            "events": [],
            "journeys": [],
        }
        self.flush()

    def register_artifact(
        self,
        *,
        artifact_type: str,
        path: Path,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._manifest["artifacts"].append(
            {
                "type": artifact_type,
                "label": label,
                "path": str(path),
                "metadata": metadata or {},
            }
        )
        self.flush()

    def add_event(self, name: str, **payload: Any) -> None:
        self._manifest["events"].append(
            {
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
            }
        )
        self.flush()

    def add_or_replace_journey(self, payload: dict[str, Any]) -> None:
        journeys = self._manifest.setdefault("journeys", [])
        journey_name = payload.get("journey")
        replaced = False
        for index, item in enumerate(journeys):
            if item.get("journey") == journey_name:
                journeys[index] = payload
                replaced = True
                break
        if not replaced:
            journeys.append(payload)
        self.flush()

    def flush(self) -> None:
        self.paths.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.manifest_path.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def create_evidence_paths(base_dir: Path) -> EvidencePaths:
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    root_dir = base_dir / run_id
    traces_dir = root_dir / "traces"
    screenshots_dir = root_dir / "screenshots"
    videos_dir = root_dir / "videos"
    reports_dir = root_dir / "reports"
    manifest_path = reports_dir / "manifest.json"
    junit_path = reports_dir / "junit.xml"

    for path in (root_dir, traces_dir, screenshots_dir, videos_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    return EvidencePaths(
        run_id=run_id,
        root_dir=root_dir,
        traces_dir=traces_dir,
        screenshots_dir=screenshots_dir,
        videos_dir=videos_dir,
        reports_dir=reports_dir,
        manifest_path=manifest_path,
        junit_path=junit_path,
    )
