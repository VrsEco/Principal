from pathlib import Path
import sys
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app32"))

from services.contracts_service import ContractService


def test_calculate_total_price_handles_brazilian_number_formats():
    total = ContractService.calculate_total_price("2,5", "1.200,40")
    assert total == Decimal("3001.00")


def test_normalize_bool_accepts_expected_truthy_values():
    assert ContractService._normalize_bool("sim") is True
    assert ContractService._normalize_bool("on") is True
    assert ContractService._normalize_bool("0") is False


def test_normalize_int_returns_none_for_invalid_values():
    assert ContractService._normalize_int("") is None
    assert ContractService._normalize_int("abc") is None
    assert ContractService._normalize_int("12") == 12


def test_normalize_date_parses_iso_pattern():
    value = ContractService._normalize_date("2026-05-01")
    assert value.isoformat() == "2026-05-01"
