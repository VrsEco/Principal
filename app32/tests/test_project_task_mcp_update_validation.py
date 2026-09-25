from datetime import date
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
    assert task.completion_date == date.today()
    result, error = service.update_task(company_id=9, task_id=1, changes={"stage": "executing"})
    assert not error
    assert task.status == "in_progress" and task.completion_date is None
    lookup.assert_called_with(company_id=9, task_id=1)
    assert commit.call_count == 2
