import pytest
from pydantic import ValidationError

from schemas.routine_execution_rule import RoutineExecutionRuleInput


def test_triggered_rule_requires_a_trigger():
    with pytest.raises(ValidationError, match="pelo menos um gatilho"):
        RoutineExecutionRuleInput.model_validate({"execution_mode": "triggered"})


def test_scheduled_rule_rejects_trigger_and_recommends_hybrid():
    with pytest.raises(ValidationError, match="modo híbrido"):
        RoutineExecutionRuleInput.model_validate(
            {
                "execution_mode": "scheduled",
                "triggers": [{"trigger_code": "pedido_recebido", "name": "Pedido recebido"}],
            }
        )


def test_rule_accepts_one_responsible_and_normalizes_trigger_code():
    rule = RoutineExecutionRuleInput.model_validate(
        {
            "execution_mode": "hybrid",
            "role_assignments": [
                {"role_id": 10, "assignment_type": "responsible"},
                {"role_id": 20, "assignment_type": "executor", "distribution_mode": "individual"},
            ],
            "triggers": [{"trigger_code": " Novo Pedido ", "name": "Novo pedido"}],
        }
    )

    assert rule.triggers[0].trigger_code == "novo_pedido"


def test_rule_rejects_more_than_one_responsible():
    with pytest.raises(ValidationError, match="no máximo uma função responsável"):
        RoutineExecutionRuleInput.model_validate(
            {
                "role_assignments": [
                    {"role_id": 10, "assignment_type": "responsible"},
                    {"role_id": 11, "assignment_type": "responsible"},
                ]
            }
        )

