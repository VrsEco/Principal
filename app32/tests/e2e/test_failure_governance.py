from __future__ import annotations

from app32.tests.e2e.core.failure_governance import build_backlog_candidates, classify_failure_type


def test_failure_governance_classifies_timeout():
    assert classify_failure_type("TimeoutError") == "timeout"


def test_failure_governance_builds_backlog_candidates():
    manifest = {
        "run_id": "run_x",
        "journeys": [
            {
                "journey": "smoke",
                "status": "failed",
                "failure_type": "AssertionError",
                "failed_step": "authenticate",
                "company_id": 9,
            }
        ],
    }
    candidates = build_backlog_candidates(manifest)

    assert candidates[0]["title"] == "Falha E2E: smoke"
    assert candidates[0]["failure_type"] == "assertion"
