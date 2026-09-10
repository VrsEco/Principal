from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_people_hub_is_company_scoped_and_renders_the_canonical_workspace():
    source = (ROOT / 'api' / 'routes' / 'companies.py').read_text(encoding='utf-8')
    assert "@companies_bp.route('/companies/<int:company_id>/people')" in source
    assert "@permission_required('companies', 'view')" in source
    assert 'def company_people_hub(company_id):' in source
    assert '_ensure_company_access(company_id)' in source
    assert "PeopleWorkspaceService.build_workspace(company_id)" in source
    assert "'modules/companies/company_people_v3.html'" in source


def test_people_workspace_has_real_sections_and_no_technical_credentials():
    template = (ROOT / 'templates' / 'modules' / 'companies' / 'company_people_v3.html').read_text(encoding='utf-8').lower()
    assert 'mcp' not in template
    assert 'token' not in template
    assert 'data-company-id="{{ company.id }}"' in template
    for label in ('usuários e acessos', 'cargos', 'organograma', 'colaboradores', 'relatórios'):
        assert label in template
    script = (ROOT / 'static' / 'js' / 'company_people_v3.js').read_text(encoding='utf-8')
    assert '/api/companies/${companyId}/people/workspace' in script
    assert '/api/companies/${companyId}/people/users' in script
    assert '/api/companies/${companyId}/people/employees' in script


def test_people_workspace_uses_the_app32_visual_composition():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates' / 'modules' / 'companies' / 'company_people_v3.html').read_text(encoding='utf-8')
    stylesheet = (root / 'static' / 'css' / 'company_people_v3.css').read_text(encoding='utf-8')
    script = (root / 'static' / 'js' / 'company_people_v3.js').read_text(encoding='utf-8')

    assert 'people-hero card' in template
    assert 'people-hero__metrics' in template
    assert 'people-guidance' in template
    assert 'people-journey' not in template
    assert 'data-people-org-action="fit"' in template
    assert 'data-people-org-action="export-png"' in template
    assert 'data-people-role-panel="profile"' in template
    assert 'data-people-role-panel="quantity"' in template
    assert 'data-people-report-panel="capacity"' in template
    assert 'data-people-open="occupancy"' in template
    assert 'data-people-open="cost"' in template
    assert 'people-org-tree-shell' in script
    assert 'buildOrgChartSvg' in script
    assert 'exportOrgPng' in script
    assert 'visibleOrgEntries' in script
    assert 'app32ExportHeader' in script
    assert 'app32NodeShadow' in script
    assert 'getBoundingClientRect' in script
    assert 'renderCapacityReport' in script
    assert 'saveOccupancy' in script
    assert 'saveCost' in script
    assert "image/png" in script
    assert "v='20260910_people_org_hierarchy_v4'" in template
    assert '.people-tabs' in stylesheet
    assert 'border-radius: 999px' in stylesheet
    assert '.people-table-wrap .table-v2 td' in stylesheet
    assert '.people-org-tree-shell li::before' in stylesheet


def test_sidebar_uses_active_company_for_people_navigation():
    sidebar = (ROOT / 'templates' / 'partials' / 'sidebar_standard.html').read_text(encoding='utf-8')
    assert "'/companies/%s/people' % active_company_id" in sidebar
    assert '>Pessoas</a>' in sidebar
