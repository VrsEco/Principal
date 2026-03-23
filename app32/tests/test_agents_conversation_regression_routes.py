import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import agents as agents_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_run_conversation_regression_pipeline_returns_report(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import services.conversation_regression_service as service_module
    import services.conversation_regression_backlog_service as backlog_module

    monkeypatch.setattr(
        service_module.ConversationRegressionService,
        'collect_workflow_gap_candidates',
        staticmethod(lambda **kwargs: [SimpleNamespace(id=1)]),
    )
    monkeypatch.setattr(
        service_module.ConversationRegressionService,
        'build_snapshot',
        staticmethod(
            lambda **kwargs: {
                'report': {'summary': {'total_cases': 3}},
                'backlog_sync': {'project_code': 'AA.J.31', 'items': [{'case_id': 'x'}]},
            }
        ),
    )
    monkeypatch.setattr(
        backlog_module.ConversationRegressionBacklogService,
        'apply_sync_payload',
        staticmethod(
            lambda payload, user_id, allowed_company_ids=None, persist=True: {
                'processed': len(payload.get('items') or []),
                'allowed_company_ids': list(allowed_company_ids or []),
            }
        ),
    )

    with app.test_request_context(
        '/api/agents/conversation-regression/run',
        method='POST',
        json={'status': 'inbox', 'limit': 20, 'sync_backlog': True, 'persist_backlog': False},
    ):
        session['active_company_id'] = 9
        response = agents_route.run_conversation_regression_pipeline.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['report']['summary']['total_cases'] == 3
    assert body['backlog_sync']['processed'] == 1
    assert body['backlog_sync']['allowed_company_ids'] == [9]


def test_run_conversation_regression_pipeline_blocks_unauthorized(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='User', role='user'))

    with app.test_request_context(
        '/api/agents/conversation-regression/run',
        method='POST',
        json={'status': 'inbox'},
    ):
        session['active_company_id'] = 9
        response, status_code = agents_route.run_conversation_regression_pipeline.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False


def test_run_conversation_regression_pipeline_validates_inputs(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    with app.test_request_context(
        '/api/agents/conversation-regression/run',
        method='POST',
        json={'limit': 'abc'},
    ):
        session['active_company_id'] = 9
        response, status_code = agents_route.run_conversation_regression_pipeline.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert 'limit inválido' in body['error']


def test_run_conversation_regression_pipeline_blocks_unauthorized_company_scope(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))
    monkeypatch.setattr(agents_route, '_has_operational_full_access', lambda company_id=None: company_id == 9)

    with app.test_request_context(
        '/api/agents/conversation-regression/run',
        method='POST',
        json={'company_id': 10},
    ):
        session['active_company_id'] = 9
        response, status_code = agents_route.run_conversation_regression_pipeline.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False
