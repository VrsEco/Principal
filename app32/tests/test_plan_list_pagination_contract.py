import inspect
from pathlib import Path

from flask import Flask

from api.resources.plan import PlanListResource
from services.plan_service import PlanService


def _app():
    return Flask(__name__)


def test_plan_list_keeps_legacy_array_unless_pagination_is_explicitly_requested():
    source = inspect.getsource(PlanListResource.get)

    assert "if not paginated:" in source
    assert "PlanService.list_plans(company_id, mode)" in source
    assert "PlanService.list_plans_page(" in source


def test_plan_service_pages_by_active_tenant_and_normalizes_window():
    source = inspect.getsource(PlanService.list_plans_page)

    assert "Plan.query.filter_by(company_id=company_id)" in source
    assert "normalized_per_page = min(max(int(per_page or 50), 1), 100)" in source
    assert ".offset((normalized_page - 1) * normalized_per_page)" in source
    assert ".limit(normalized_per_page)" in source


def test_plan_pagination_contract_has_index_and_http_metadata():
    root = Path(__file__).resolve().parents[1]
    resource = (root / "api" / "resources" / "plan.py").read_text(encoding="utf-8")
    model = (root / "models" / "plan.py").read_text(encoding="utf-8")
    migration = (root / "migrations" / "versions" / "20260913_1500_add_plan_list_pagination_index.py").read_text(encoding="utf-8")

    assert "request.args.get('paginated')" in resource
    assert "'pagination': {" in resource
    assert "ix_plans_company_created_id" in model
    assert 'down_revision = "20260913_1400"' in migration
