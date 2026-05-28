from __future__ import annotations

from app32.tests.e2e.core.execution_history import compare_manifests


def test_execution_history_detects_regression():
    previous = {"run_id": "run_1", "journeys": [{"journey": "smoke", "status": "passed"}]}
    current = {"run_id": "run_2", "journeys": [{"journey": "smoke", "status": "failed"}]}

    diff = compare_manifests(previous, current)

    assert diff["status"] == "regression"
    assert diff["regressions"] == ["smoke"]
