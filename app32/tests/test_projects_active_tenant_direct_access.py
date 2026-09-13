from pathlib import Path


def test_direct_project_access_does_not_fallback_to_or_switch_another_tenant():
    source = (Path(__file__).resolve().parents[1] / 'api' / 'routes' / 'projects.py').read_text(encoding='utf-8')
    helper = source.split('def _get_project_page_with_access(project_id):', 1)[1].split('def get_active_company():', 1)[0]

    assert "Project.query.filter_by(id=project_id, company_id=company_id)" in helper
    assert "Project.query.filter_by(id=project_id).first_or_404()" not in helper
    assert "session['active_company_id'] = fallback_company.id" not in helper
    assert "Empresa ativa obrigatória para acessar projetos." in helper
