from __future__ import annotations

from src.intelligence.security import mcp_mutation_guard as guard


def test_evaluate_mutation_limit_blocks_when_threshold_reached(monkeypatch):
    monkeypatch.setattr(
        guard,
        "load_mutation_limit_policy",
        lambda: guard.MutationLimitPolicy(
            create_limit=2,
            update_limit=3,
            delete_limit=1,
            restore_limit=1,
            window_hours=24,
        ),
    )
    monkeypatch.setattr(guard, "count_recent_mutations", lambda **kwargs: 2)

    decision = guard.evaluate_mutation_limit(
        action="create",
        company_id=9,
        user_id=7,
    )

    assert decision.allowed is False
    assert decision.limit == 2
    assert "atingido" in decision.reason


def test_evaluate_mutation_limit_requires_user_and_company():
    decision = guard.evaluate_mutation_limit(action="update", company_id=None, user_id=7)

    assert decision.allowed is False
    assert "usuário associado" in decision.reason

