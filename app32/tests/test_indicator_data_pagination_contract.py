import inspect
from pathlib import Path

from api.routes.indicators import indicator_data_list


def test_indicator_data_history_is_paginated_with_tenant_scope_and_eager_relations():
    source = inspect.getsource(indicator_data_list)

    assert "IndicatorData.query.filter_by(company_id=int(company_id))" in source
    assert "joinedload(IndicatorData.indicator)" in source
    assert "joinedload(IndicatorData.routine)" in source
    assert "joinedload(IndicatorData.employee)" in source
    assert "total_records = records_query.order_by(None).count()" in source
    assert "records_query.offset((page - 1) * per_page).limit(per_page).all()" in source
    assert "per_page = 50" in source
    assert "page = min(page, last_page)" in source
    assert "pagination=pagination" in source


def test_indicator_data_page_exposes_bounded_navigation():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "modules" / "indicators" / "indicator_data_list.html").read_text(encoding="utf-8")

    assert "Exibindo {{ pagination.first_item }}–{{ pagination.last_item }} de {{ pagination.total }} registros" in template
    assert "pagination.has_previous" in template
    assert "Próximos 50" in template
    assert "url_for('indicators.indicator_data_list', page=pagination.page + 1)" in template