import inspect
from pathlib import Path
from api.resources.occurrence import OccurrenceListResource


def test_occurrences_keep_active_tenant_scope_and_offer_opt_in_pagination():
    source = inspect.getsource(OccurrenceListResource.get)
    assert "Occurrence.query.filter_by(company_id=company_id)" in source
    assert "paginated = (request.args.get('paginated') or 'false').lower() == 'true'" in source
    assert "_occurrence_visible_to_employee" in source
    assert "'pagination': {'page': page" in source


def test_occurrences_page_uses_server_batches_and_incremental_rendering():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates' / 'modules' / 'processes' / 'process_occurrences_list.html').read_text(encoding='utf-8')
    assert "paginated: 'true'" in template
    assert "loadOccurrences({ append: true })" in template
    assert "Carregar mais (${data.length} de ${occurrencesPagination.total})" in template