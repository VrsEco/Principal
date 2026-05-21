import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_pop_copilot_service import build_process_pop_step_media_context


class _FakeJoinedQuery:
    def __init__(self, item):
        self.item = item

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.item


class _FakeRoutineQuery:
    def __init__(self, item):
        self.item = item

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.item


def test_build_process_pop_step_media_context_flags_missing_assets(monkeypatch):
    step = SimpleNamespace(
        id=9,
        routine_id=11,
        name='Abrir tela',
        description='',
        expected_result='Tela aberta',
        layout='single',
        image_path=None,
        video_path='pop/video/passo.mp4',
        video_duration_seconds=42,
    )
    routine = SimpleNamespace(id=11, process_id=77, code='P.01', name='Abrir sistema', bpmn_element_id='Task_01')

    monkeypatch.setattr('services.process_pop_copilot_service.ProcessStep', SimpleNamespace(
        id='id',
        routine_id='routine_id',
        query=_FakeJoinedQuery(step),
    ))
    monkeypatch.setattr('services.process_pop_copilot_service.ProcessRoutine', SimpleNamespace(
        id='id',
        company_id='company_id',
        query=_FakeRoutineQuery(routine),
    ))

    payload = build_process_pop_step_media_context(company_id=9, step_id=9)

    assert payload['coverage']['has_video'] is True
    assert payload['coverage']['has_image'] is False
    assert payload['coverage']['has_description'] is False
    assert 'capture_key_frame' in payload['recommended_actions']
    assert 'draft_step_description' in payload['recommended_actions']


def test_build_process_pop_step_media_context_rejects_unknown_step(monkeypatch):
    monkeypatch.setattr('services.process_pop_copilot_service.ProcessStep', SimpleNamespace(
        id='id',
        routine_id='routine_id',
        query=_FakeJoinedQuery(None),
    ))
    monkeypatch.setattr('services.process_pop_copilot_service.ProcessRoutine', SimpleNamespace(
        id='id',
        company_id='company_id',
        query=_FakeRoutineQuery(None),
    ))

    with pytest.raises(ValueError, match='Passo POP não encontrado'):
        build_process_pop_step_media_context(company_id=9, step_id=99)
