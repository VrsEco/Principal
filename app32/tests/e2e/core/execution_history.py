from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_manifests(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_journeys = {item.get("journey"): item.get("status") for item in previous.get("journeys") or []}
    curr_journeys = {item.get("journey"): item.get("status") for item in current.get("journeys") or []}

    regressions = []
    recovered = []
    new_journeys = []
    for journey, status in curr_journeys.items():
        prev_status = prev_journeys.get(journey)
        if prev_status == "passed" and status == "failed":
            regressions.append(journey)
        elif prev_status == "failed" and status == "passed":
            recovered.append(journey)
        elif prev_status is None:
            new_journeys.append(journey)

    return {
        "previous_run_id": previous.get("run_id"),
        "current_run_id": current.get("run_id"),
        "regressions": regressions,
        "recovered": recovered,
        "new_journeys": new_journeys,
        "status": "regression" if regressions else "stable",
    }


def latest_manifests(outputs_root: Path, limit: int = 2) -> list[Path]:
    manifests = sorted(outputs_root.glob("**/reports/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return manifests[:limit]
