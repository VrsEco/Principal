from decimal import Decimal
from types import SimpleNamespace

from services.routine_execution_rule_service import build_event_instance_code, build_execution_groups


def _assignment(role_id, assignment_type="executor", distribution_mode="collective", title="Vendedor"):
    return SimpleNamespace(
        role_id=role_id,
        assignment_type=assignment_type,
        distribution_mode=distribution_mode,
        hours_used=Decimal("2.0"),
        notes=None,
        role=SimpleNamespace(title=title),
    )


def test_individual_distribution_creates_one_group_per_occupant():
    assignments = [
        _assignment(1, "responsible", title="Gerente Comercial"),
        _assignment(2, distribution_mode="individual"),
    ]
    occupants = {
        1: [{"id": 7, "name": "Gerente", "email": "gerente@example.com"}],
        2: [
            {"id": 8, "name": "Vendedor A", "email": "a@example.com"},
            {"id": 9, "name": "Vendedor B", "email": "b@example.com"},
        ],
    }

    groups, responsible = build_execution_groups(assignments, occupants)

    assert [item["target_employee_id"] for item in groups] == [8, 9]
    assert [item["executor_id"] for item in groups] == [8, 9]
    assert responsible[0]["id"] == 7
    assert responsible[0]["role_title"] == "Gerente Comercial"


def test_pool_distribution_does_not_freeze_one_occupant_as_executor():
    groups, _ = build_execution_groups(
        [_assignment(2, distribution_mode="pool")],
        {2: [{"id": 8, "name": "Vendedor A", "email": None}]},
    )

    assert groups[0]["distribution_mode"] == "pool"
    assert groups[0]["executor_id"] is None
    assert groups[0]["collaborators"][0]["id"] == 8


def test_event_instance_code_is_idempotent_and_target_sensitive():
    first = build_event_instance_code("BA.C.2", 40, "novo_pedido", "pedido:123", "8")
    repeated = build_event_instance_code("BA.C.2", 40, "novo_pedido", "pedido:123", "8")
    other_target = build_event_instance_code("BA.C.2", 40, "novo_pedido", "pedido:123", "9")

    assert first == repeated
    assert first != other_target
    assert len(first) <= 100

