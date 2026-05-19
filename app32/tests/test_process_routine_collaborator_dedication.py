import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes.processes import _validate_routine_collaborator_payload


def _validate(hours_used):
    return _validate_routine_collaborator_payload(
        {
            "employee_id": 123,
            "hours_used": hours_used,
            "notes": "Operação",
        }
    )


def test_routine_collaborator_dedication_accepts_clock_format():
    payload, error = _validate("04:00")

    assert error is None
    assert payload["hours_used"] == 4.0


def test_routine_collaborator_dedication_accepts_decimal_formats():
    for raw in ("4", "4.5", "4,5"):
        payload, error = _validate(raw)
        expected = 4.5 if raw in {"4.5", "4,5"} else 4.0
        assert error is None
        assert payload["hours_used"] == expected


def test_routine_collaborator_dedication_rejects_zero_after_parsing():
    payload, error = _validate("00:00")

    assert payload is None
    assert error == "A dedicação deve ser maior que zero."
