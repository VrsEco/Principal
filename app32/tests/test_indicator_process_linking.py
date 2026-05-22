import os
import sys
from types import SimpleNamespace

from flask import Flask
from sqlalchemy.sql import column

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import indicator as indicator_resource


class _FakeIndicatorQuery:
    def __init__(self, results=None):
        self.results = results or []
        self.filters = []
        self.filter_conditions = []

    def filter_by(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def filter(self, *conditions):
        self.filter_conditions.extend(conditions)
        return self

    def all(self):
        return self.results


def _fake_indicator_model(query):
    return SimpleNamespace(
        query=query,
        process_id=column('indicators.process_id'),
        project_id=column('indicators.project_id'),
        source_module=column('indicators.source_module'),
        source_id=column('indicators.source_id'),
    )


def _build_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test'
    app.config['LOGIN_DISABLED'] = True
    return app


def test_sync_indicator_context_links_maps_process_source_to_process_id():
    payload = {
        'source_module': 'processo',
        'source_id': '2',
    }

    normalized = indicator_resource._sync_indicator_context_links(payload.copy())

    assert normalized['source_id'] == 2
    assert normalized['process_id'] == 2
    assert normalized['project_id'] is None


def test_sync_indicator_context_links_clears_process_link_when_source_changes():
    current_indicator = SimpleNamespace(
        source_module='processo',
        source_id=2,
        process_id=2,
        project_id=None,
    )
    payload = {
        'source_module': 'manual',
        'source_id': None,
    }

    normalized = indicator_resource._sync_indicator_context_links(payload.copy(), current_indicator=current_indicator)

    assert normalized['process_id'] is None
    assert 'project_id' not in normalized


def test_indicator_list_resource_filters_process_by_direct_or_source_link(monkeypatch):
    app = _build_app()
    fake_query = _FakeIndicatorQuery(results=[SimpleNamespace(id=8, name='Lead Time')])

    monkeypatch.setattr(indicator_resource, 'Indicator', _fake_indicator_model(fake_query))
    monkeypatch.setattr(indicator_resource, 'get_request_company_id', lambda: 17)
    monkeypatch.setattr(
        indicator_resource,
        'indicators_schema',
        SimpleNamespace(dump=lambda indicators: [{'id': indicator.id, 'name': indicator.name} for indicator in indicators]),
    )

    with app.test_request_context('/api/indicators?company_id=17&process_id=2'):
        response, status = indicator_resource.IndicatorListResource().get.__wrapped__(indicator_resource.IndicatorListResource())

    assert status == 200
    assert response == [{'id': 8, 'name': 'Lead Time'}]
    assert fake_query.filters == [{'company_id': 17}]
    assert len(fake_query.filter_conditions) == 1
    condition_repr = str(fake_query.filter_conditions[0])
    assert 'indicators.process_id' in condition_repr
    assert 'indicators.source_module' in condition_repr
    assert 'indicators.source_id' in condition_repr


def test_indicator_form_template_supports_query_prefill_for_process_context():
    template_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..',
        'templates',
        'modules',
        'indicators',
        'indicator_form_v2.html',
    ))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'function applyQueryContextDefaults()' in content
    assert "const processId = params.get('process_id');" in content
    assert "const resolvedModule = sourceModule || (processId ? 'processo' : (projectId ? 'projeto' : ''));" in content
    assert "labelEl.textContent = 'Processo Vinculado';" in content


def test_process_details_template_links_new_indicator_to_current_process():
    template_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..',
        'templates',
        'modules',
        'processes',
        'process_details_v2.html',
    ))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert "url_for('indicators.indicator_new') }}?source_module=processo&source_id={{ process.id }}" in content
    assert 'Novo indicador deste processo' in content
