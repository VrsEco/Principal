from pathlib import Path

from services.project_service import ProjectService


ROOT = Path(__file__).resolve().parents[1]


def test_plan_portfolio_code_is_stable_and_idempotent():
    assert ProjectService._plan_portfolio_code(21) == "PLAN-21"


def test_planning_project_form_uses_explicit_tenant_query():
    template = (
        ROOT / "templates" / "modules" / "plans" / "growth_projects.html"
    ).read_text(encoding="utf-8")

    assert "`/api/projects?company_id=${window.companyId}`" in template
    assert "`/api/projects/${projId}?company_id=${window.companyId}`" in template
    assert "`/api/projects/${id}?company_id=${window.companyId}`" in template
    assert "company_id: window.companyId" not in template


def test_project_creation_uses_canonical_service_and_create_permission():
    source = (ROOT / "api" / "resources" / "project.py").read_text(encoding="utf-8")

    assert "@permission_required('projects', 'create')" in source
    assert "ProjectService.create_project(" in source
    assert "Project.owner == employee.name" in source


def test_existing_plan_projects_receive_a_real_portfolio_backfill():
    migration = (
        ROOT
        / "migrations"
        / "versions"
        / "20260723_1000_backfill_plan_project_portfolios.py"
    ).read_text(encoding="utf-8")

    assert "INSERT INTO portfolios" in migration
    assert "UPDATE projects AS project" in migration
    assert "project.company_id = plan.company_id" in migration
    assert "project.portfolio_id IS NULL" in migration
