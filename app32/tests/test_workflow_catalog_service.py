import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.workflow_catalog_service import build_workflow_catalog


class _Field:
    def __init__(self, key, label, required=True):
        self.key = key
        self.label = label
        self.required = required

    def model_dump(self):
        return {'key': self.key, 'label': self.label, 'required': self.required}


class _Workflow:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Registry:
    def __init__(self, workflows):
        self._workflows = workflows

    def list(self):
        return list(self._workflows)


def test_build_workflow_catalog_aggregates_usage_and_gaps(monkeypatch):
    option = SimpleNamespace(
        id=14,
        code='1.4',
        title='Cadastrar Atividade',
        action_key='project_task.create',
        description='Cria atividade de projeto',
        keywords=['criar atividade'],
        required_fields=[{'key': 'codigo_projeto', 'label': 'Projeto'}],
        sort_order=14,
        company_id=None,
        usage_count=5,
        last_used_at=datetime(2026, 3, 8, 12, 0, 0),
        is_active=True,
        parent=SimpleNamespace(code='1'),
    )
    workflow = _Workflow(
        code='1.4',
        title='Cadastrar Atividade',
        action_key='project_task.create',
        description='Cria atividade de projeto',
        sort_order=14,
        company_id=None,
        source_option_id=14,
        required_fields=[_Field('codigo_projeto', 'Projeto')],
        keywords=['criar atividade'],
        intent_examples=['criar atividade', 'atividade de projeto'],
    )
    monkeypatch.setattr('services.workflow_catalog_service.WorkflowRegistry.from_menu_options', lambda options, preferred_company_id=None: _Registry([workflow]))

    usage_logs = [
        SimpleNamespace(workflow_code='1.4', channel='whatsapp', status='completed', route_source='lexical'),
        SimpleNamespace(workflow_code='1.4', channel='telegram', status='completed', route_source='semantic'),
    ]
    gaps = [
        SimpleNamespace(matched_workflow_codes=['1.4'], created_at=datetime(2026, 3, 8, 11, 0, 0)),
    ]

    payload = build_workflow_catalog(
        options=[option],
        usage_logs=usage_logs,
        gap_candidates=gaps,
        preferred_company_id=9,
    )

    assert payload['summary']['workflow_count'] == 1
    assert payload['summary']['used_workflow_count'] == 1
    assert payload['summary']['workflow_with_gap_count'] == 1
    item = payload['workflows'][0]
    assert item['code'] == '1.4'
    assert item['usage']['count'] == 5
    assert item['usage']['log_count'] == 2
    assert {'channel': 'telegram', 'count': 1} in item['usage']['by_channel']
    assert {'route_source': 'lexical', 'count': 1} in item['usage']['by_route_source']
    assert item['gaps']['count'] == 1
    assert item['parent_code'] == '1'
    assert {'telegram', 'whatsapp'}.issubset({channel['name'] for channel in item['channels']})
    assert any(contract['name'] == 'project_task.runtime' for contract in item['api_mcp_contracts'])
    assert any(contract['name'] == 'project_task_toolkit' for contract in item['tools'])
    assert any(contract['name'] == 'Escopo tenant' for contract in item['permissions'])
    assert any(contract['name'] == 'Parâmetros operacionais' for contract in item['configurations'])
