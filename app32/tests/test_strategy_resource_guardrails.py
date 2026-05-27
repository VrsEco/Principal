from pathlib import Path


BASE = Path(__file__).resolve().parents[1] / "api" / "resources"


def _read(name: str) -> str:
    return (BASE / name).read_text(encoding="utf-8")


def test_plan_resource_requires_company_id_and_tenant_validation():
    text = _read("plan.py")

    assert "def _get_request_company_id():" in text
    assert 'return {"error": "company_id is required"}, 400' in text
    assert "plan = PlanService.get_plan(plan_id, company_id)" in text
    assert "PlanService.list_participants(plan_id, company_id)" in text


def test_okr_resource_write_methods_have_permission_and_company_scope():
    text = _read("okr.py")

    assert "@permission_required('okrs', 'create')\n    def post(self):" in text
    assert "@permission_required('okrs', 'edit')\n    def put(self, okr_id):" in text
    assert "@permission_required('okrs', 'delete')\n    def delete(self, okr_id):" in text
    assert "OKRGlobal.query.filter_by(id=okr_id, company_id=company_id).first_or_404()" in text
    assert "OKRArea.query.filter_by(id=okr_id, company_id=company_id).first_or_404()" in text
    assert "KeyResult.query.filter_by(id=kr_id, company_id=company_id).first_or_404()" in text
    assert "KeyResultArea.query.filter_by(id=kr_id, company_id=company_id).first_or_404()" in text


def test_indicator_resource_goal_and_data_access_are_company_scoped():
    text = _read("indicator.py")

    assert "@permission_required('indicators', 'edit')\n    def patch(self, goal_id):" in text
    assert "IndicatorGoal.query.filter_by(id=goal_id, company_id=company_id).first_or_404()" in text
    assert "query = IndicatorData.query.filter_by(company_id=company_id)" in text
    assert "IndicatorData.query.filter_by(id=data_id, company_id=company_id).first_or_404()" in text
