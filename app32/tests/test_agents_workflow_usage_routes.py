import os
import sys
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import agents as agents_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    return app


class _FakeUsageQuery:
    def __init__(self, items):
        self._items = list(items)
        self._limit = None

    def filter(self, *_args, **_kwargs):
        return self

    def filter_by(self, **kwargs):
        filtered = []
        for item in self._items:
            ok = True
            for key, value in kwargs.items():
                if getattr(item, key, None) != value:
                    ok = False
                    break
            if ok:
                filtered.append(item)
        self._items = filtered
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def all(self):
        items = list(self._items)
        if self._limit is not None:
            items = items[: self._limit]
        return items


def test_list_workflow_usage_returns_structured_payload(monkeypatch):
    app = _build_app()
    item_a = SimpleNamespace(
        id=801,
        company_id=9,
        user_id=3,
        session_id=55,
        workflow_option_id=14,
        workflow_code='1.4',
        action_key='project_task.create',
        channel='whatsapp',
        thread_id='wa_3_sapiens',
        route_source='lexical',
        intercept_stage='awaiting_fields',
        status='collecting_parameters',
        confidence_route='select',
        interaction_count=2,
        request_text='criar atividade',
        response_text='Me informe o nome da atividade',
        metadata_json={'workflow_discovery': {'strategy': 'hybrid'}},
        created_at=datetime(2026, 3, 8, 12, 40, 0),
        updated_at=datetime(2026, 3, 8, 12, 41, 0),
        completed_at=None,
    )
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import sqlalchemy
    import models.workflow_usage as workflow_usage_module
    monkeypatch.setattr(sqlalchemy, 'or_', lambda *args, **kwargs: None)

    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _value):
            return self

    fake_model = type(
        'FakeWorkflowExecutionLog',
        (),
        {
            'company_id': _FakeColumn(),
            'updated_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeUsageQuery([item_a]),
        },
    )
    monkeypatch.setattr(workflow_usage_module, 'WorkflowExecutionLog', fake_model)

    import services.workflow_usage_service as usage_service_module
    monkeypatch.setattr(usage_service_module, 'serialize_workflow_execution_log', lambda item: {'id': item.id, 'channel': item.channel, 'workflow_code': item.workflow_code})

    with app.test_request_context('/api/agents/workflow-usage?channel=whatsapp&limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.list_workflow_usage_logs.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['count'] == 1
    assert body['workflow_usage'][0]['workflow_code'] == '1.4'
    assert body['filters']['channel'] == 'whatsapp'


def test_workflow_usage_metrics_blocks_unauthorized_role(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/workflow-usage/metrics', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.workflow_usage_metrics.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False


def test_workflow_usage_metrics_returns_aggregated_payload(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    item_a = SimpleNamespace(company_id=9, action_key='summary.week', channel='whatsapp', status='completed')
    item_b = SimpleNamespace(company_id=9, action_key='summary.week', channel='telegram', status='completed')

    import models.workflow_usage as workflow_usage_module
    fake_model = type(
        'FakeWorkflowExecutionLog',
        (),
        {
            'updated_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeUsageQuery([item_a, item_b]),
        },
    )
    monkeypatch.setattr(workflow_usage_module, 'WorkflowExecutionLog', fake_model)

    import services.workflow_usage_service as usage_service_module
    monkeypatch.setattr(usage_service_module, 'build_workflow_usage_metrics', lambda items: {'total': len(list(items)), 'by_action_key': [{'action_key': 'summary.week', 'count': 2}], 'by_route_source': [{'route_source': 'semantic', 'count': 2}], 'by_user': [{'user_id': 3, 'count': 2}], 'by_day': [{'date': '2026-03-08', 'count': 2}]})

    with app.test_request_context('/api/agents/workflow-usage/metrics?limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.workflow_usage_metrics.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['metrics']['total'] == 2
    assert body['metrics']['by_route_source'][0]['route_source'] == 'semantic'
    assert body['metrics']['by_user'][0]['user_id'] == 3
