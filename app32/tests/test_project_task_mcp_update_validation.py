from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services import project_task_mcp_service as module


@pytest.fixture
def task_context(monkeypatch):
    task = SimpleNamespace(what="Original", status="planned", stage="inbox",
                           completion_date=None, is_deleted=False, project=None)
    lookup = Mock(return_value=(task, None))
    commit = Mock()
    monkeypatch.setattr(module.ProjectTaskMCPService, "get_task", lookup)
    monkeypatch.setattr(module.ProjectTaskMCPService, "_serialize_task", lambda t: vars(t).copy())
    monkeypatch.setattr(module, "db", SimpleNamespace(session=SimpleNamespace(commit=commit)))
    return task, lookup, commit


@pytest.mark.parametrize("changes", [None, [], {}, {"status": "bogus"},
    {"stage": "bogus"}, {"priority": "bogus"}, {"task_name": " "},
    {"status": "completed", "stage": "inbox"},
    {"status": "planned", "stage": "completed"}])
def test_rejected_payload_never_touches_task(task_context, changes):
    task, lookup, commit = task_context
    result, error = module.ProjectTaskMCPService.update_task(company_id=9, task_id=1, changes=changes)
    assert result is None and error
    lookup.assert_not_called()
    commit.assert_not_called()
    assert task.what == "Original"


def test_complete_and_reopen(task_context):
    task, lookup, commit = task_context
    service = module.ProjectTaskMCPService
    result, error = service.update_task(company_id=9, task_id=1, changes={"status": "completed"})
    assert not error
    assert task.stage == task.status == "completed"
    # O serviço grava a data de conclusão em UTC; comparar com o relógio local falhava depois das 21h em Brasília.
    assert task.completion_date == datetime.utcnow().date()
    result, error = service.update_task(company_id=9, task_id=1, changes={"stage": "executing"})
    assert not error
    assert task.status == "in_progress" and task.completion_date is None
    lookup.assert_called_with(company_id=9, task_id=1)
    assert commit.call_count == 2


# ---- append_notes, estimated_hours, worked_hours -------------------------------------------------
@pytest.fixture
def note_context(task_context, monkeypatch):
    task, lookup, commit = task_context
    task.notes = "Checklist\n- [ ] Passo 1"
    task.estimated_hours = None
    task.worked_hours = None
    monkeypatch.setattr(module.ProjectTaskMCPService, "_actor_label", staticmethod(lambda user_id: "Fabiano Diretor"))
    return task, lookup, commit


def test_append_notes_keeps_history_and_stamps_author_and_date(note_context):
    task, _lookup, commit = note_context
    result, error = module.ProjectTaskMCPService.update_task(
        company_id=9, task_id=1, changes={"append_notes": "Validado em produção."}, actor_user_id=3
    )
    assert not error
    assert task.notes.startswith("Checklist\n- [ ] Passo 1\n\n[")
    assert "· Fabiano Diretor] Validado em produção." in task.notes
    commit.assert_called_once()


def test_append_notes_starts_the_notes_when_empty(note_context):
    task, _lookup, _commit = note_context
    task.notes = None
    _result, error = module.ProjectTaskMCPService.update_task(company_id=9, task_id=1, changes={"append_notes": "Primeira"})
    assert not error and task.notes.startswith("[") and task.notes.endswith("Primeira")


@pytest.mark.parametrize("changes", [
    {"append_notes": " "}, {"append_notes": 5}, {"append_notes": "x" * 4001},
    {"append_notes": "a", "notes": "b"},
    {"estimated_hours": -1}, {"worked_hours": "abc"}, {"worked_hours": True}, {"estimated_hours": 10001},
    {"worked_hours": float("nan")},
])
def test_rejected_notes_and_hours_never_touch_the_task(note_context, changes):
    task, lookup, commit = note_context
    before = (task.notes, task.estimated_hours, task.worked_hours)
    result, error = module.ProjectTaskMCPService.update_task(company_id=9, task_id=1, changes=changes)
    assert result is None and error
    lookup.assert_not_called()
    commit.assert_not_called()
    assert (task.notes, task.estimated_hours, task.worked_hours) == before


def test_notes_limit_is_checked_before_any_assignment(note_context):
    task, _lookup, commit = note_context
    task.notes = "x" * (module.ProjectTaskMCPService.MAX_NOTES_CHARS - 5)
    result, error = module.ProjectTaskMCPService.update_task(
        company_id=9, task_id=1, changes={"task_name": "Novo nome", "append_notes": "texto longo"}
    )
    assert result is None and "limite" in error
    assert task.what == "Original", "recusa não pode deixar a atividade parcialmente alterada"
    commit.assert_not_called()


def test_hours_accept_numbers_and_decimal_comma(note_context):
    from decimal import Decimal

    task, _lookup, _commit = note_context
    _result, error = module.ProjectTaskMCPService.update_task(
        company_id=9, task_id=1, changes={"estimated_hours": 2, "worked_hours": "1,5"}
    )
    assert not error
    assert task.estimated_hours == Decimal("2.00") and task.worked_hours == Decimal("1.50")
