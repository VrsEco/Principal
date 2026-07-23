from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_key_result_resources_do_not_inject_unknown_company_field():
    source = (ROOT / "api" / "resources" / "okr.py").read_text(encoding="utf-8")

    assert "data.pop('company_id', None)" in source
    assert "data['company_id'] = company_id\n            kr = key_result_schema.load(data)" not in source
    assert "data['company_id'] = company_id\n            kr = key_result_area_schema.load(data)" not in source


def test_key_result_access_is_scoped_through_tenant_parent():
    source = (ROOT / "api" / "resources" / "okr.py").read_text(encoding="utf-8")

    assert "KeyResult.query.join(OKRGlobal" in source
    assert "OKRGlobal.company_id == company_id" in source
    assert "KeyResultArea.query.join(OKRArea" in source
    assert "OKRArea.company_id == company_id" in source
    assert "KeyResult.query.filter_by(id=kr_id, company_id=company_id)" not in source
    assert "KeyResultArea.query.filter_by(id=kr_id, company_id=company_id)" not in source


def test_growth_okr_templates_send_tenant_in_query_not_child_payload():
    global_template = (
        ROOT / "templates" / "modules" / "plans" / "growth_okrs_global.html"
    ).read_text(encoding="utf-8")
    area_template = (
        ROOT / "templates" / "modules" / "plans" / "growth_okrs_area.html"
    ).read_text(encoding="utf-8")

    assert "`/api/key-results?company_id=${window.companyId}`" in global_template
    assert "`/api/key-results-area?company_id=${window.companyId}`" in area_template
    assert "company_id: window.companyId" not in global_template
    assert "company_id: window.companyId" not in area_template
