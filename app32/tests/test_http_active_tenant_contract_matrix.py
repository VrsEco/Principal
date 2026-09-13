"""Regression matrix for HTTP tenant-boundary controls.

The individual route tests exercise behavior.  This matrix prevents a future
refactor from silently replacing the active-tenant guard in one of the
high-impact HTTP surfaces hardened during P1.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_company_url_surfaces_keep_the_active_tenant_guard():
    expected = {
        'api/routes/work_journey.py': 26,
        'api/routes/work_journey_agendas.py': 6,
        'api/routes/work_journey_report.py': 2,
        'api/routes/portfolios.py': 9,
    }
    for relative_path, minimum_guards in expected.items():
        source = _source(relative_path)
        assert source.count('@active_company_permission_required(') >= minimum_guards


def test_direct_object_surfaces_keep_their_active_tenant_boundary():
    projects = _source('api/routes/projects.py')
    occurrences = _source('api/resources/occurrence.py')
    indicators = _source('api/routes/indicators.py')
    audit = _source('api/resources/operational_audit.py')

    assert "Project.query.filter_by(id=project_id, company_id=company_id)" in projects
    assert "Project.query.filter_by(id=project_id).first_or_404()" not in projects
    assert "company_id != get_active_company_id()" in occurrences
    assert occurrences.count('@active_company_permission_required(') == 5
    assert indicators.count('@active_company_permission_required(') >= 16
    assert "@active_company_permission_required(\"financial\", \"view\")" in audit
