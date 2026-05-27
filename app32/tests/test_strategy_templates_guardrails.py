from pathlib import Path


TPL = Path(__file__).resolve().parents[1] / "templates" / "modules" / "plans"
ROUTES = Path(__file__).resolve().parents[1] / "api" / "routes" / "plans.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_strategy_okr_templates_send_explicit_company_id_on_edit_and_delete():
    global_tpl = _read(TPL / "growth_okrs_global.html")
    area_tpl = _read(TPL / "growth_okrs_area.html")

    assert "?company_id=${window.companyId}" in global_tpl
    assert "company_id: window.companyId" in global_tpl
    assert "?company_id=${window.companyId}" in area_tpl
    assert "company_id: window.companyId" in area_tpl


def test_strategy_implantation_templates_use_web_complete_route():
    for name in [
        "implantation_alignment.html",
        "implantation_execution.html",
        "implantation_model.html",
        "implantation_finance.html",
    ]:
        content = _read(TPL / name)
        assert "/plans/{{ plan.id }}/sections/" in content
        assert "/api/plans/{{ plan.id }}/sections/" not in content


def test_strategy_complete_route_propagates_company_id_to_service():
    routes_text = _read(ROUTES)
    assert "PlanService.update_section_status(plan_id, section_key, 'completed', company_id=company.id if company else None)" in routes_text
