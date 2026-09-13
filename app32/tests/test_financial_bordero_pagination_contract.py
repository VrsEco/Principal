import inspect
from pathlib import Path

from api.resources.financial import FinancialBorderoListResource
from services.financial_bordero_service import FinancialBorderoService


def test_bordero_list_keeps_tenant_scope_and_exposes_opt_in_pagination():
    source = inspect.getsource(FinancialBorderoService.list_borderos)

    assert "FinancialBordero.company_id == company_id" in source
    assert "if not paginated:" in source
    assert '"pagination"' in source
    assert "normalized_per_page = min(max(int(per_page or 50), 1), 100)" in source
    assert "FinancialBordero.bordero_code.ilike(pattern)" in source


def test_bordero_resource_forwards_opt_in_pagination_and_server_filters():
    source = inspect.getsource(FinancialBorderoListResource.get)

    assert 'request.args.get("paginated")' in source
    assert 'search=request.args.get("search")' in source
    assert 'page=request.args.get("page", 1, type=int)' in source
    assert "allowed_company_ids=get_accessible_company_ids()" in source


def test_bordero_page_uses_server_side_batches_and_full_filtered_summary():
    root = Path(__file__).resolve().parents[1]
    script = (root / "static" / "js" / "financial_borderos_list.js").read_text(encoding="utf-8")
    template = (root / "templates" / "modules" / "financial" / "borderos_list.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in script
    assert "params.set('search', search)" in script
    assert "params.set('bordero_type', type)" in script
    assert "borderoSummary.signed_open_amount" in script
    assert "Carregar mais (${borderos.length} de ${borderoPagination.total})" in script
    assert 'id="bordero-pagination"' in template
