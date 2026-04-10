from datetime import date

from src.core.mcp_work_journey_tools import (
    _build_work_journey_board_envelope,
    _error_envelope,
    _normalize_board_item,
    _success_envelope,
)
from src.intelligence.mcp_contracts import WorkJourneyBoardQuery


def test_normalize_board_item_maps_service_shape_to_contract_shape():
    item = _normalize_board_item(
        {
            "id": 44,
            "item_type": "project_task",
            "display_title": "AA.J.31.44 - Revisar backlog",
            "status": "in_progress",
            "block_id": 7,
            "due_date": date(2026, 4, 10),
            "estimated_minutes": 90,
            "worked_minutes": 30,
        }
    )

    assert item.item_id == 44
    assert item.source_type == "project_task"
    assert item.title == "AA.J.31.44 - Revisar backlog"
    assert item.status == "in_progress"


def test_build_work_journey_board_envelope_returns_success_contract():
    query = WorkJourneyBoardQuery(
        company_id=31,
        employee_id=8,
        anchor_date=date(2026, 4, 9),
        scope="week",
    )
    payload = _build_work_journey_board_envelope(
        {
            "summary": {"pending_count": 1, "worked_minutes": 30},
            "period_items": [
                {
                    "id": 44,
                    "item_type": "project_task",
                    "title": "Revisar backlog",
                    "status": "pending",
                    "block_id": 7,
                    "due_date": date(2026, 4, 10),
                    "estimated_minutes": 90,
                    "worked_minutes": 30,
                }
            ],
        },
        query,
    )

    assert payload["success"] is True
    assert payload["meta"]["operation"] == "board.read"
    assert payload["data"]["company_id"] == 31
    assert payload["data"]["items"][0]["source_type"] == "project_task"


def test_generic_envelopes_return_expected_shape():
    success = _success_envelope(operation="contract.describe", data={"ok": True})
    error = _error_envelope(operation="board.read", message="falhou", code="work_journey_error")

    assert success["success"] is True
    assert success["meta"]["domain"] == "work_journey"
    assert error["success"] is False
    assert error["error"]["code"] == "work_journey_error"
