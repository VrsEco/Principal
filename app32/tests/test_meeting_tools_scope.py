import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.intelligence import tools


class _FakeMeetingQuery:
    def __init__(self, meeting=None):
        self.meeting = meeting
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.meeting


def test_get_meeting_in_active_company_filters_by_context(monkeypatch):
    fake_query = _FakeMeetingQuery(SimpleNamespace(id=7, company_id=12, title='R1'))
    monkeypatch.setattr(tools, 'get_active_company_id', lambda: 12)
    monkeypatch.setattr(sys.modules['models.meeting'], 'Meeting', SimpleNamespace(query=fake_query))

    meeting, error = tools._get_meeting_in_active_company(7)

    assert error is None
    assert meeting.id == 7
    assert fake_query.last_filter_kwargs == {'id': 7, 'company_id': 12}


def test_get_meeting_in_active_company_blocks_cross_company(monkeypatch):
    fake_query = _FakeMeetingQuery(None)
    monkeypatch.setattr(tools, 'get_active_company_id', lambda: 12)
    monkeypatch.setattr(sys.modules['models.meeting'], 'Meeting', SimpleNamespace(query=fake_query))

    meeting, error = tools._get_meeting_in_active_company(99)

    assert meeting is None
    assert 'empresa ativa' in error
    assert fake_query.last_filter_kwargs == {'id': 99, 'company_id': 12}
