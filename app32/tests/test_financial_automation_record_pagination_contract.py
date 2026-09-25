import inspect
from pathlib import Path

from api.resources.financial_automation import FinancialAutomationRecordListResource
from services.financial_automation_service import FinancialAutomationService


def test_financial_automation_records_keep_tenant_scope_and_opt_in_legacy_contract():
    source = inspect.getsource(FinancialAutomationService.list_records)

    assert "FinancialAutomationRecord.company_id == company_id" in source
    assert "if not paginated:" in source
    assert "normalized_per_page = min(max(int(per_page or 50), 1), 100)" in source
    assert "ordered_query" in source
    assert ".offset((normalized_page - 1) * normalized_per_page)" in source
    assert '"pagination": {' in source


def test_financial_automation_resource_forwards_opt_in_pagination():
    source = inspect.getsource(FinancialAutomationRecordListResource.get)

    assert 'request.args.get("paginated")' in source
    assert 'page=request.args.get("page", 1, type=int)' in source
    assert 'per_page=request.args.get("per_page", 50, type=int)' in source
    assert "allowed_company_ids=get_accessible_company_ids()" in source


def test_financial_automation_center_requests_pages_and_appends_records():
    root = Path(__file__).resolve().parents[1]
    script = (root.parent / "static" / "js" / "financial_automation_center.js").read_text(encoding="utf-8")
    template = (root / "templates" / "modules" / "financial" / "automation_center.html").read_text(encoding="utf-8")
    model = (root / "models" / "financial_automation.py").read_text(encoding="utf-8")
    migration = (root / "migrations" / "versions" / "20260913_1400_add_financial_automation_record_pagination_index.py").read_text(encoding="utf-8")

    assert "paginated: 'true'" in script
    assert "loadRecords({ append: true })" in script
    assert "Carregar mais (${state.records.length} de ${state.pagination.total})" in script
    assert 'id="fa-records-pagination"' in template
    assert "ix_financial_automation_records_company_created_id" in model
    assert 'down_revision = "20260913_1300"' in migration
