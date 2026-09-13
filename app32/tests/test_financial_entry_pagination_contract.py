import inspect
from pathlib import Path

from api.resources.financial import FinancialEntryListResource
from services.financial_service import FinancialService


def test_financial_entries_keep_tenant_scope_and_offer_opt_in_pagination():
    source = inspect.getsource(FinancialService.list_entries)

    assert "FinancialEntry.company_id == company_id" in source
    assert "if not paginated:" in source
    assert "normalized_per_page = min(max(int(per_page or 50), 1), 100)" in source
    assert '"pagination": {' in source
    assert ".offset((normalized_page - 1) * normalized_per_page)" in source


def test_financial_entry_resource_forwards_pagination_without_changing_legacy_calls():
    source = inspect.getsource(FinancialEntryListResource.get)

    assert 'request.args.get("paginated")' in source
    assert 'page=request.args.get("page", 1, type=int) or 1' in source
    assert 'per_page=request.args.get("per_page", 50, type=int) or 50' in source
    assert "allowed_company_ids=get_accessible_company_ids()" in source


def test_financial_entries_page_uses_incremental_batches_and_clear_batch_totals():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "modules" / "financial" / "entries_list.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in template
    assert "loadedEntries = append ? loadedEntries.concat(payload.items) : payload.items" in template
    assert "Carregar mais (${items.length} de ${entriesPagination.total})" in template
    assert "Recebido (lote)" in template
    assert 'id="entries-pagination"' in template