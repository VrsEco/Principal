from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_people_hub_is_company_scoped_and_uses_existing_permission_guard():
    source = (ROOT / 'api' / 'routes' / 'companies.py').read_text(encoding='utf-8')
    assert "@companies_bp.route('/companies/<int:company_id>/people')" in source
    assert "@permission_required('companies', 'view')" in source
    assert 'def company_people_hub(company_id):' in source
    assert '_ensure_company_access(company_id)' in source
    assert "company_people_hub.html" in source


def test_people_hub_does_not_expose_mcp_token_management():
    template = (ROOT / 'templates' / 'modules' / 'companies' / 'company_people_hub.html').read_text(encoding='utf-8').lower()
    assert 'mcp' not in template
    assert 'token' not in template
    assert 'data-company-id="{{ company.id }}"' in template
    script = (ROOT / 'static' / 'js' / 'company_people_hub.js').read_text(encoding='utf-8')
    assert '/api/companies/${companyId}/users' in script
    assert '/api/companies/${companyId}/usage-telemetry' in script
    assert 'uso da empresa' in template


def test_sidebar_uses_active_company_for_people_navigation():
    sidebar = (ROOT / 'templates' / 'partials' / 'sidebar_standard.html').read_text(encoding='utf-8')
    assert "'/companies/%s/people' % active_company_id" in sidebar
    assert 'Pessoas da empresa' in sidebar
