from __future__ import annotations

from app32.tests.e2e.scripts.run_devfull_transactional_suite import _summarize_mutation_steps


def test_summarize_mutation_steps_counts_create_cancel_delete_and_rollback():
    summary = _summarize_mutation_steps(
        [
            {
                "journeys": [
                    {
                        "metadata": {"domain": "financial"},
                        "steps": [
                            {"name": "create_schedule", "status": "passed"},
                            {"name": "update_and_cancel_schedule", "status": "passed"},
                            {"name": "delete_schedule", "status": "passed"},
                            {"name": "http_login", "status": "passed"},
                            {"name": "financial_transactional_runtime", "status": "failed"},
                        ],
                    }
                ]
            }
        ]
    )

    assert summary["mutation_step_counts"]["create"] == 1
    assert summary["mutation_step_counts"]["update"] == 1
    assert summary["mutation_step_counts"]["cancel"] == 1
    assert summary["mutation_step_counts"]["delete"] == 1
    assert summary["mutation_step_counts"]["rollback"] == 1
    assert summary["mutating_steps_total"] == 4
    assert summary["rollback_steps_total"] == 1
    assert summary["failed_steps_total"] == 1

