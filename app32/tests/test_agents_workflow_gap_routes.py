import os
import sys
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import agents as agents_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


class _FakeGapQuery:
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


def test_list_workflow_gaps_returns_structured_payload(monkeypatch):
    app = _build_app()
    gap_a = SimpleNamespace(
        id=901,
        company_id=9,
        user_id=3,
        channel='whatsapp',
        thread_id='wa_3_sapiens',
        source='ai_fallback',
        status='inbox',
        resolution_type='resolved_by_ai',
        title='[FLOW GAP][whatsapp] Preciso da ocupação do usuário X',
        user_request_text='Preciso da ocupação do usuário X',
        normalized_intent='preciso da ocupação do usuário x',
        suggested_flow_name='ocupacao_usuario_x',
        business_outcome='Criar fluxo de ocupação',
        matched_workflow_codes=['3.1'],
        telemetry={'workflow_discovery': {'strategy': 'hybrid'}},
        app_project_id=31,
        app_task_id=204,
        app_task_code='AA.J.31.204',
        created_at=datetime(2026, 3, 8, 11, 40, 0),
        updated_at=datetime(2026, 3, 8, 11, 40, 0),
    )
    gap_b = SimpleNamespace(
        id=902,
        company_id=9,
        user_id=4,
        channel='telegram',
        thread_id='tg_4_sapiens',
        source='ai_fallback',
        status='inbox',
        resolution_type='not_resolved',
        title='[FLOW GAP][telegram] Quero novo fluxo',
        user_request_text='Quero novo fluxo',
        normalized_intent='quero novo fluxo',
        suggested_flow_name='novo_fluxo',
        business_outcome='Criar fluxo novo',
        matched_workflow_codes=[],
        telemetry={},
        app_project_id=31,
        app_task_id=205,
        app_task_code='AA.J.31.205',
        created_at=datetime(2026, 3, 8, 11, 41, 0),
        updated_at=datetime(2026, 3, 8, 11, 41, 0),
    )

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import sqlalchemy
    import models.workflow_gap as workflow_gap_module

    monkeypatch.setattr(sqlalchemy, 'or_', lambda *args, **kwargs: None)

    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _value):
            return self

    fake_gap_class = type(
        'FakeWorkflowGapCandidate',
        (),
        {
            'company_id': _FakeColumn(),
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeGapQuery([gap_a, gap_b]),
        },
    )
    monkeypatch.setattr(workflow_gap_module, 'WorkflowGapCandidate', fake_gap_class)

    with app.test_request_context('/api/agents/workflow-gaps?channel=whatsapp&limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.list_workflow_gaps.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['count'] == 1
    assert body['filters'] == {
        'status': 'all',
        'channel': 'whatsapp',
        'source': None,
        'resolution_type': None,
        'user_id': None,
        'limit': 20,
        'active_company_id': 9,
    }
    assert body['workflow_gaps'][0]['channel'] == 'whatsapp'
    assert body['workflow_gaps'][0]['app_card']['task_code'] == 'AA.J.31.204'


def test_list_workflow_gaps_blocks_unauthorized_role(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/workflow-gaps', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.list_workflow_gaps.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False
    assert 'Sem permissão' in body['error']


def test_list_workflow_gaps_validates_limit_and_user(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    with app.test_request_context('/api/agents/workflow-gaps?limit=abc', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.list_workflow_gaps.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert body['success'] is False
    assert 'limit inválido' in body['error']

    with app.test_request_context('/api/agents/workflow-gaps?user_id=oops', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.list_workflow_gaps.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert body['success'] is False
    assert 'user_id inválido' in body['error']



def test_get_workflow_gap_link_returns_gap_for_task(monkeypatch):
    app = _build_app()
    gap = {
        'id': 901,
        'channel': 'whatsapp',
        'app_card': {'task_id': 204, 'task_code': 'AA.J.31.204'},
    }

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import services.workflow_gap_service as gap_service_module

    monkeypatch.setattr(gap_service_module, 'find_workflow_gap_by_task', lambda **kwargs: SimpleNamespace(company_id=9))
    monkeypatch.setattr(gap_service_module, 'serialize_workflow_gap_candidate', lambda candidate: gap)

    with app.test_request_context('/api/agents/workflow-gaps/link?task_id=204', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.get_workflow_gap_link.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['found'] is True
    assert body['workflow_gap']['app_card']['task_code'] == 'AA.J.31.204'


def test_get_workflow_gap_link_validates_and_blocks(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/workflow-gaps/link?task_id=204', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.get_workflow_gap_link.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    with app.test_request_context('/api/agents/workflow-gaps/link', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.get_workflow_gap_link.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert 'Informe task_id ou task_code' in body['error']


def test_workflow_gap_metrics_returns_operational_summary(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import sqlalchemy
    import models.workflow_gap as workflow_gap_module

    monkeypatch.setattr(sqlalchemy, 'or_', lambda *args, **kwargs: None)

    gap_a = SimpleNamespace(company_id=9, created_at=datetime(2026, 3, 8, 11, 40, 0))
    gap_b = SimpleNamespace(company_id=9, created_at=datetime(2026, 3, 8, 11, 41, 0))

    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _value):
            return self

    fake_gap_class = type(
        'FakeWorkflowGapCandidateMetrics',
        (),
        {
            'company_id': _FakeColumn(),
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeGapQuery([gap_a, gap_b]),
        },
    )
    monkeypatch.setattr(workflow_gap_module, 'WorkflowGapCandidate', fake_gap_class)

    import services.workflow_gap_service as gap_service_module
    monkeypatch.setattr(
        gap_service_module,
        'build_workflow_gap_metrics',
        lambda items: {'total': len(items), 'duplicate_cluster_count': 1, 'duplicate_clusters': []},
    )

    with app.test_request_context('/api/agents/workflow-gaps/metrics?limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.workflow_gap_metrics.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['metrics']['total'] == 2
    assert body['limit'] == 20


def test_reclassify_workflow_gaps_returns_report(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import sqlalchemy
    import models.workflow_gap as workflow_gap_module

    monkeypatch.setattr(sqlalchemy, 'or_', lambda *args, **kwargs: None)

    gap_a = SimpleNamespace(company_id=9, status='inbox', created_at=datetime(2026, 3, 8, 11, 40, 0))

    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _value):
            return self

    fake_gap_class = type(
        'FakeWorkflowGapCandidateReclassify',
        (),
        {
            'company_id': _FakeColumn(),
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeGapQuery([gap_a]),
        },
    )
    monkeypatch.setattr(workflow_gap_module, 'WorkflowGapCandidate', fake_gap_class)

    import services.workflow_gap_service as gap_service_module
    monkeypatch.setattr(
        gap_service_module,
        'reclassify_workflow_gap_candidates',
        lambda items, persist=False: {'processed': len(items), 'updated': 1, 'metrics': {'total': len(items)}},
    )

    with app.test_request_context(
        '/api/agents/workflow-gaps/maintenance/reclassify',
        method='POST',
        json={'status': 'inbox', 'limit': 30, 'persist': False},
    ):
        session['active_company_id'] = 9
        response = agents_route.reclassify_workflow_gaps.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['processed'] == 1
    assert body['updated'] == 1
    assert body['persist'] is False
