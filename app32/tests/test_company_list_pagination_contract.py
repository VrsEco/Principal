import inspect
from pathlib import Path

from api.resources.company import CompanyListResource


def test_company_list_offers_opt_in_tenant_safe_pagination_without_breaking_legacy_list():
    source = inspect.getsource(CompanyListResource.get)

    assert "paginated = request.args.get('paginated', 'false').lower() == 'true'" in source
    assert "Employee.user_id == current_user.id" in source
    assert "query = query.filter(Company.id.in_(linked_company_ids))" in source
    assert "'pagination':" in source
    assert "return companies_schema.dump(companies), 200" in source


def test_company_list_empty_membership_returns_paginated_envelope():
    source = inspect.getsource(CompanyListResource.get)

    assert "if not linked_company_ids:" in source
    assert "if paginated:" in source
    assert "'items': []" in source
    assert "'has_more': False" in source


def test_companies_page_uses_server_filters_and_incremental_rendering():
    root = Path(__file__).resolve().parents[1]
    script = (root / "static" / "js" / "companies.js").read_text(encoding="utf-8")
    template = (root / "templates" / "modules" / "companies" / "companies_v2.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in script
    assert "params.set('search', search)" in script
    assert "params.set('segment', segment)" in script
    assert "params.set('size', size)" in script
    assert "Carregar mais (${allCompanies.length} de ${companyPagination.total})" in script
    assert 'id="companies-pagination"' in template
