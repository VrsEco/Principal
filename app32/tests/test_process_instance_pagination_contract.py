import inspect
from pathlib import Path

from api.resources.process import ProcessInstanceListResource


def test_process_instance_list_exposes_opt_in_pagination_without_breaking_legacy_list():
    source = inspect.getsource(ProcessInstanceListResource.get)

    assert "ProcessInstance.query.filter_by(company_id=company_id)" in source
    assert "paginated = (request.args.get('paginated') or 'false').lower() == 'true'" in source
    assert "query = query.filter(ProcessInstance.status == status)" in source
    assert "ProcessInstance.instance_code.ilike(pattern)" in source
    assert "per_page = min(max(request.args.get('per_page', 50, type=int) or 50, 1), 100)" in source
    assert "query.offset((page - 1) * per_page).limit(per_page).all()" in source
    assert "'pagination': {'page': page" in source
    assert "return results, 200" in source


def test_process_instances_page_uses_server_filters_and_incremental_rendering():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "modules" / "processes" / "process_instances_list.html").read_text(encoding="utf-8")

    assert "paginated: 'true'" in template
    assert "params.set(['status', 'priority', 'process_id'][index], value)" in template
    assert "params.set('search', search)" in template
    assert "loadInstances({ append: true })" in template
    assert "Carregar mais (${allInstances.length} de ${instancesPagination.total})" in template