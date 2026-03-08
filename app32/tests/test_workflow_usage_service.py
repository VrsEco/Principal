import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import workflow_usage_service as usage_service


class _FakeQueryResult:
    def __init__(self, item):
        self._item = item

    def first(self):
        return self._item


class _FakeOptionQuery:
    def __init__(self, item):
        self._item = item
        self.filters = []

    def filter_by(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._item


class _FakeUsageQuery:
    def __init__(self, item):
        self._item = item
        self.kwargs = []

    def filter_by(self, **kwargs):
        self.kwargs.append(kwargs)
        return self

    def order_by(self, *_args, **_kwargs):
        return _FakeQueryResult(self._item)


def test_record_workflow_usage_event_creates_log_and_updates_counter(monkeypatch):
    events = []

    class FakeSession:
        def add(self, obj):
            events.append(("add", obj))
            if getattr(obj, 'id', None) is None:
                obj.id = 801

        def commit(self):
            events.append(("commit", None))

    monkeypatch.setattr(usage_service, 'db', SimpleNamespace(session=FakeSession(), func=None))

    fake_option = SimpleNamespace(id=14, code='1.4', action_key='project_task.create', usage_count=2, last_used_at=None)
    fake_option_query = _FakeOptionQuery(fake_option)
    fake_option_model = SimpleNamespace(query=fake_option_query, sort_order=SimpleNamespace(asc=lambda: None))
    monkeypatch.setattr(usage_service, 'AgentMenuOption', fake_option_model)

    monkeypatch.setattr(usage_service, '_find_existing_usage_log', lambda **kwargs: None)

    class FakeWorkflowExecutionLog:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.id = None
            self.route_source = None
            self.interaction_count = 0
            self.completed_at = None
            self.updated_at = None
            self.created_at = None
            self.intercept_stage = None
            self.status = None
            self.confidence_route = None
            self.request_text = None
            self.response_text = None
            self.metadata_json = {}

    monkeypatch.setattr(usage_service, 'WorkflowExecutionLog', FakeWorkflowExecutionLog)

    log = usage_service.record_workflow_usage_event(
        user_id=3,
        company_id=9,
        channel='whatsapp',
        thread_id='wa_3_sapiens',
        request_text='criar atividade no projeto AA.J.31',
        response_text='Me informe o nome da atividade.',
        menu_metadata={
            'menu_engine': {
                'session_id': 55,
                'intercept_stage': 'awaiting_fields',
                'session_status': 'awaiting_fields',
                'selected_option_code': '1.4',
                'selected_action_key': 'project_task.create',
            },
            'workflow_discovery': {
                'strategy': 'hybrid',
                'confidence': {'route': 'select'},
            },
        },
    )

    assert log is not None
    assert log.id == 801
    assert log.workflow_code == '1.4'
    assert log.action_key == 'project_task.create'
    assert log.status == 'collecting_parameters'
    assert log.confidence_route == 'select'
    assert fake_option.usage_count == 3
    assert fake_option.last_used_at is not None
    assert any(kind == 'add' for kind, _ in events)
    assert any(kind == 'commit' for kind, _ in events)


def test_build_workflow_usage_metrics_aggregates_by_dimensions():
    items = [
        SimpleNamespace(action_key='summary.week', channel='whatsapp', status='completed'),
        SimpleNamespace(action_key='summary.week', channel='telegram', status='completed'),
        SimpleNamespace(action_key='project_task.create', channel='whatsapp', status='collecting_parameters'),
    ]

    metrics = usage_service.build_workflow_usage_metrics(items)

    assert metrics['total'] == 3
    assert metrics['by_action_key'][0] == {'action_key': 'summary.week', 'count': 2}
    assert {'channel': 'whatsapp', 'count': 2} in metrics['by_channel']
    assert {'status': 'completed', 'count': 2} in metrics['by_status']


def test_serialize_workflow_execution_log_returns_operational_payload():
    item = SimpleNamespace(
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

    payload = usage_service.serialize_workflow_execution_log(item)

    assert payload['workflow_code'] == '1.4'
    assert payload['status'] == 'collecting_parameters'
    assert payload['metadata']['workflow_discovery']['strategy'] == 'hybrid'
