from pathlib import Path

from flask import Flask

from api.resources.okr import OKR_LIST_MAX_PER_PAGE, _okr_list_pagination_args


def _app():
    return Flask(__name__)


def test_okr_pagination_is_opt_in_for_legacy_clients():
    with _app().test_request_context("/api/okrs-global"):
        assert _okr_list_pagination_args() == (False, 1, OKR_LIST_MAX_PER_PAGE)


def test_okr_pagination_normalizes_page_and_caps_page_size():
    with _app().test_request_context("/api/okrs-area?paginated=true&page=-3&per_page=999"):
        assert _okr_list_pagination_args() == (True, 1, OKR_LIST_MAX_PER_PAGE)


def test_okr_lists_keep_tenant_scope_and_page_at_database_level():
    root = Path(__file__).resolve().parents[1]
    resource = (root / "api" / "resources" / "okr.py").read_text(encoding="utf-8")
    global_model = (root / "models" / "okr_global.py").read_text(encoding="utf-8")
    area_model = (root / "models" / "okr_area.py").read_text(encoding="utf-8")
    migration = (root / "migrations" / "versions" / "20260913_1300_add_okr_list_pagination_indexes.py").read_text(encoding="utf-8")

    assert "OKRGlobal.query.filter_by(company_id=company_id)" in resource
    assert "OKRArea.query.filter_by(company_id=company_id)" in resource
    assert "query.offset((page - 1) * per_page).limit(per_page).all()" in resource
    assert '"pagination": {' in resource
    assert "ix_okrs_global_company_deadline_id" in global_model
    assert "ix_okrs_area_company_deadline_id" in area_model
    assert 'down_revision = "20260913_1200"' in migration


def test_okr_workspace_requests_paginated_contract_and_loads_incrementally():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "modules" / "okrs" / "okrs_v2.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in template
    assert "fetchOKRs({ append: true })" in template
    assert "switchTab(tab)" in template and "fetchOKRs();" in template
    assert "Carregar mais (${okrs.length} de ${okrPagination.total})" in template
