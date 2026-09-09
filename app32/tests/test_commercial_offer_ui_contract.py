from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


def test_product_service_screen_exposes_operational_contract_readiness():
    template = (
        APP_ROOT / "templates" / "modules" / "contracts" / "contracts_items_catalog_items.html"
    ).read_text(encoding="utf-8")

    assert 'data-section="oferta"' in template
    assert "Contrato operacional" in template
    assert "Pronta para ativação" in template
    assert 'name="commercial_contract_enforced"' in template
    assert 'name="commercial_contract_json"' in template
    assert "Prefira a atualização assistida via MCP" in template


def test_catalog_route_preserves_commercial_metadata_during_general_edits():
    route_source = (APP_ROOT / "api" / "routes" / "contracts.py").read_text(encoding="utf-8")

    assert '"commercial_contract_v1"' in route_source
    assert '"commercial_contract_enforced"' in route_source
    assert '"commercial_contract_legacy"' in route_source
    assert "existing_metadata = dict(item.metadata_json or {})" in route_source
    assert "json.loads(raw_contract)" in route_source


def test_product_service_readiness_layout_is_responsive():
    template = (
        APP_ROOT / "templates" / "modules" / "contracts" / "contracts_items_catalog_items.html"
    ).read_text(encoding="utf-8")

    assert "@media (max-width: 760px)" in template
    assert ".cw-form-grid,.cw-readiness-grid { grid-template-columns:1fr; }" in template
