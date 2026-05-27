from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_plan_resource_create_forces_company_from_request_context():
    text = (ROOT / "api" / "resources" / "plan.py").read_text(encoding="utf-8")

    assert "company_id = _get_request_company_id()" in text
    assert "data['company_id'] = company_id" in text


def test_plan_service_recalculates_strategy_status_with_company_scope():
    text = (ROOT / "services" / "plan_service.py").read_text(encoding="utf-8")

    assert "def update_section_status(plan_id: int, section_key: str, status: str, company_id: Optional[int] = None):" in text
    assert "PlanService._recalculate_progress(plan_id, company_id=plan.company_id)" in text
    assert "okrs_count = OKRGlobal.query.filter_by(plan_id=plan_id, company_id=company_id).count()" in text


def test_indicator_schema_scopes_performance_queries_by_company():
    text = (ROOT / "schemas" / "indicator.py").read_text(encoding="utf-8")

    assert "sqla_session = db.session" in text
    assert "indicator_id=obj.id," in text
    assert "company_id=obj.company_id," in text
    assert "status='active'," in text
