from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backfill_versus_commercial_offer_catalog import CATALOG_BLUEPRINT


def test_versus_offer_catalog_blueprint_is_parent_first_and_unique():
    seen = set()
    for item in CATALOG_BLUEPRINT:
        assert item["code"] not in seen
        if item["parent_code"]:
            assert item["parent_code"] in seen
        seen.add(item["code"])


def test_versus_offer_catalog_preserves_performance_hub_identity():
    by_code = {item["code"]: item for item in CATALOG_BLUEPRINT}

    assert by_code["1.01.001"]["name"] == "Performance Hub"
    assert by_code["1.01.001"]["active"] is True
    assert by_code["1.01.001"]["legacy_compatible"] is True


def test_new_offers_start_inactive_until_operational_contract_is_approved():
    by_code = {item["code"]: item for item in CATALOG_BLUEPRINT}

    for code in ("1.02.001", "1.03.001", "1.03.002"):
        assert by_code[code]["selectable"] is True
        assert by_code[code]["active"] is False
        assert by_code[code]["enforce_contract"] is True
