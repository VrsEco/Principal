import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import process as process_resource


class _FakeStepQuery:
    def __init__(self, step):
        self.step = step

    def get_or_404(self, step_id):
        return self.step


class _FakeRoutineFilter:
    def __init__(self, routine):
        self.routine = routine

    def first(self):
        return self.routine


class _FakeRoutineQuery:
    def __init__(self, routine):
        self.routine = routine

    def filter_by(self, **kwargs):
        return _FakeRoutineFilter(self.routine)


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_step_ai_draft_resource_applies_description(monkeypatch):
    app = _build_app()
    committed = {'value': False}
    step = SimpleNamespace(id=33, routine_id=7, description='', expected_result='')
    routine = SimpleNamespace(id=7, company_id=22)

    monkeypatch.setattr(process_resource, 'ProcessStep', SimpleNamespace(query=_FakeStepQuery(step)))
    monkeypatch.setattr(process_resource, 'ProcessRoutine', SimpleNamespace(query=_FakeRoutineQuery(routine)))
    monkeypatch.setattr(process_resource, 'has_permission', lambda company_id, resource, action: company_id == 22)
    monkeypatch.setattr(process_resource.db.session, 'commit', lambda: committed.__setitem__('value', True))
    monkeypatch.setattr(process_resource, 'suggest_process_pop_step_description', lambda **kwargs: {
        'context': {'step': {'id': 33}},
        'draft': {
            'suggested_description': 'Abra o módulo e confirme a importação.',
            'suggested_expected_result': 'A importação é concluída com sucesso.',
            'source': 'heuristic',
            'warnings': [],
            'title': 'Importar extrato',
        }
    })

    with app.test_request_context('/api/process-steps/33/ai-draft', method='POST', json={'apply_to_step': True}):
        response, status = process_resource.ProcessStepAIDraftResource().post.__wrapped__(process_resource.ProcessStepAIDraftResource(), 33)

    assert status == 200
    assert response['applied'] is True
    assert step.description == 'Abra o módulo e confirme a importação.'
    assert step.expected_result == 'A importação é concluída com sucesso.'
    assert committed['value'] is True
