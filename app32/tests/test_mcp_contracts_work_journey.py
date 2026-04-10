from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.intelligence.mcp_contracts import (
    WORK_JOURNEY_PILOT_MANIFEST,
    MCPResponseMeta,
    WorkJourneyBoardItem,
    WorkJourneyBoardPayload,
    WorkJourneyBoardQuery,
    WorkJourneyBoardResponseEnvelope,
)


def test_work_journey_pilot_manifest_has_expected_operations():
    actions = [rule.action for rule in WORK_JOURNEY_PILOT_MANIFEST.operations]

    assert WORK_JOURNEY_PILOT_MANIFEST.domain == "work_journey"
    assert "board.read" in actions
    assert "agenda.generate" in actions
    assert any(rule.human_gate_required for rule in WORK_JOURNEY_PILOT_MANIFEST.operations)


def test_work_journey_board_contract_builds_success_envelope():
    query = WorkJourneyBoardQuery(
        company_id=31,
        employee_id=8,
        anchor_date=date(2026, 4, 9),
        scope="week",
    )
    payload = WorkJourneyBoardPayload(
        company_id=query.company_id,
        employee_id=query.employee_id,
        anchor_date=query.anchor_date,
        scope=query.scope,
        items=[
            WorkJourneyBoardItem(
                item_id=101,
                source_type="project_task",
                title="Revisar backlog da sprint",
                status="pending",
                block_id=5,
                due_date=date(2026, 4, 10),
                estimated_minutes=90,
                worked_minutes=0,
            )
        ],
        summary={"total_items": 1, "total_minutes": 90},
    )
    meta = MCPResponseMeta(
        domain="work_journey",
        operation="board.read",
        scope="mcp_user",
        company_id=query.company_id,
        user_id=7,
        actor_role="colaborador",
        capability="work_journey.board.read",
        permissions=["work_journey.read"],
        generated_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )

    envelope = WorkJourneyBoardResponseEnvelope(data=payload, meta=meta)

    assert envelope.success is True
    assert envelope.data.summary["total_items"] == 1
    assert envelope.data.items[0].source_type == "project_task"
    assert envelope.meta.operation == "board.read"


def test_work_journey_board_contract_forbids_extra_fields():
    with pytest.raises(ValidationError):
        WorkJourneyBoardQuery(
            company_id=31,
            employee_id=8,
            anchor_date=date(2026, 4, 9),
            scope="week",
            extra_field="forbidden",  # type: ignore[arg-type]
        )
