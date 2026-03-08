import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import agents as agents_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    return app


class _FakeQuery:
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


def test_workflow_catalog_returns_operational_payload(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import sqlalchemy
    monkeypatch.setattr(sqlalchemy, 'or_', lambda *args, **kwargs: None)

    import models.agent_menu as agent_menu_module
    import models.workflow_usage as workflow_usage_module
    import models.workflow_gap as workflow_gap_module
    import services.workflow_catalog_service as catalog_service_module

    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _value):
            return self

        def isnot(self, _value):
            return self

        def asc(self):
            return self

        def desc(self):
            return self

    option = SimpleNamespace(id=14, code='1.4', action_key='project_task.create', is_active=True, sort_order=14, company_id=None)
    fake_option_model = type('FakeAgentMenuOption', (), {
        'company_id': _FakeColumn(),
        'sort_order': _FakeColumn(),
        'code': _FakeColumn(),
        'query': _FakeQuery([option]),
    })
    monkeypatch.setattr(agent_menu_module, 'AgentMenuOption', fake_option_model)

    usage = SimpleNamespace(company_id=9, workflow_code='1.4', updated_at=None)
    fake_usage_model = type('FakeWorkflowExecutionLog', (), {
        'company_id': _FakeColumn(),
        'updated_at': _FakeColumn(),
        'query': _FakeQuery([usage]),
    })
    monkeypatch.setattr(workflow_usage_module, 'WorkflowExecutionLog', fake_usage_model)

    gap = SimpleNamespace(company_id=9, created_at=None)
    fake_gap_model = type('FakeWorkflowGapCandidate', (), {
        'company_id': _FakeColumn(),
        'created_at': _FakeColumn(),
        'query': _FakeQuery([gap]),
    })
    monkeypatch.setattr(workflow_gap_module, 'WorkflowGapCandidate', fake_gap_model)

    monkeypatch.setattr(catalog_service_module, 'build_workflow_catalog', lambda **kwargs: {
        'summary': {'workflow_count': 1, 'used_workflow_count': 1},
        'workflows': [{'code': '1.4', 'action_key': 'project_task.create'}],
    })

    with app.test_request_context('/api/agents/workflows/catalog?limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.workflow_catalog.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['summary']['workflow_count'] == 1
    assert body['workflows'][0]['code'] == '1.4'
    assert body['filters']['limit'] == 20


def test_workflow_catalog_blocks_unauthorized_role(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/workflows/catalog', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.workflow_catalog.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False
