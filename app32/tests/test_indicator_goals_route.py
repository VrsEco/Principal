import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import models
from api.routes import indicators as indicators_route


class _FakeColumn:
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def isnot(self, other):
        return lambda row: getattr(row, self.attr_name, None) is not other

    def desc(self):
        return self


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        filtered = self._rows
        for key, value in kwargs.items():
            filtered = [row for row in filtered if getattr(row, key, None) == value]
        return _FakeQuery(filtered)

    def filter(self, *conditions):
        filtered = self._rows
        for condition in conditions:
            if callable(condition):
                filtered = [row for row in filtered if condition(row)]
        return _FakeQuery(filtered)

    def order_by(self, column):
        attr_name = getattr(column, 'attr_name', 'name')
        return _FakeQuery(sorted(self._rows, key=lambda row: getattr(row, attr_name, '') or ''))

    def all(self):
        return list(self._rows)


def _build_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_indicator_goals_page_excludes_inactive_indicators(monkeypatch):
    app = _build_app()

    indicators = [
        SimpleNamespace(id=1, company_id=9, name='Indicador Ativo', code='ATV', unit='R$', is_active=True),
        SimpleNamespace(id=2, company_id=9, name='Indicador Inativo', code='INA', unit='R$', is_active=False),
        SimpleNamespace(id=3, company_id=9, name='Indicador Legado', code='LEG', unit='R$', is_active=None),
    ]
    goals = [SimpleNamespace(id=10, company_id=9, goal_date=None, period_start=None)]
    routines = [SimpleNamespace(id=1, code='RT', name='Rotina')]

    monkeypatch.setattr(
        indicators_route,
        'Indicator',
        SimpleNamespace(
            query=_FakeQuery(indicators),
            is_active=_FakeColumn('is_active'),
            name=_FakeColumn('name'),
        ),
    )
    monkeypatch.setattr(
        indicators_route,
        'IndicatorGoal',
        SimpleNamespace(
            query=_FakeQuery(goals),
            goal_date=_FakeColumn('goal_date'),
            period_start=_FakeColumn('period_start'),
        ),
    )
    monkeypatch.setattr(
        indicators_route,
        '_get_form_context',
        lambda company_id: {'employees_json': '[]', 'teams_json': '[]'},
    )

    captured = {}

    def _fake_render(template_name, **context):
        captured['template'] = template_name
        captured['context'] = context
        return 'ok'

    monkeypatch.setattr(indicators_route, 'render_template', _fake_render)
    monkeypatch.setattr(models, 'Routine', SimpleNamespace(query=_FakeQuery(routines)), raising=False)

    with app.test_request_context('/indicators/goals'):
        session['active_company_id'] = 9
        response = indicators_route.indicator_goals.__wrapped__()

    assert response == 'ok'
    assert captured['template'] == 'modules/indicators/indicator_goals.html'
    assert [indicator.id for indicator in captured['context']['indicators']] == [1, 3]
