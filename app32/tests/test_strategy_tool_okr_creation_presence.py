from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_strategy_ops_exposes_okr_creation_tools():
    text = _read("src", "intelligence", "tools_domains", "strategy_ops.py")

    assert "def create_global_okr(" in text
    assert "def create_area_okr(" in text
    assert "def create_global_key_result(" in text
    assert "def create_area_key_result(" in text
    assert 'required_permissions=("okrs.global.create",)' in text
    assert 'required_permissions=("okrs.area.create",)' in text
    assert 'required_permissions=("okrs.key_results.create",)' in text
    assert "record_mutation_success(" in text


def test_tools_and_tools_prod_publish_okr_creation_tools():
    canonical = _read("src", "intelligence", "tools.py")
    prod = _read("tools_PROD.py")

    assert "def create_global_okr(" in canonical
    assert "def create_area_okr(" in canonical
    assert "def create_global_key_result(" in canonical
    assert "def create_area_key_result(" in canonical
    assert "def create_global_okr(" in prod
    assert "def create_area_okr(" in prod
    assert "def create_global_key_result(" in prod
    assert "def create_area_key_result(" in prod
