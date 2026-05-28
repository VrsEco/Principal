from __future__ import annotations

from typing import Any


FAILURE_CLASSIFICATION_RULES = {
    "TimeoutError": "timeout",
    "AssertionError": "assertion",
    "HTTPError": "http",
    "RuntimeError": "runtime",
}


def classify_failure_type(raw_type: str | None) -> str:
    normalized = str(raw_type or "").strip()
    return FAILURE_CLASSIFICATION_RULES.get(normalized, normalized.lower() or "unknown")


def build_backlog_candidates(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for journey in manifest.get("journeys") or []:
        if journey.get("status") != "failed":
            continue
        candidates.append(
            {
                "title": f"Falha E2E: {journey.get('journey')}",
                "failure_type": classify_failure_type(journey.get("failure_type")),
                "failed_step": journey.get("failed_step"),
                "run_id": manifest.get("run_id"),
                "company_id": journey.get("company_id"),
            }
        )
    return candidates
