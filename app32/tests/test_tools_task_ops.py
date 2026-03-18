from datetime import date
from types import SimpleNamespace


def test_complete_task_project_task_commits_once(monkeypatch):
    from src.intelligence import tools as tools_module
    from models import project as project_module

    class _FakeQuery:
        def __init__(self, task):
            self._task = task

        def get(self, task_id):
            return self._task if task_id == 24 else None

    class _FakeProjectTask:
        query = None

    commit_count = {"value": 0}
    rollback_count = {"value": 0}

    fake_project = SimpleNamespace(
        name="Projeto Sapiens",
        progress_updated=False,
    )

    def _update_progress():
        fake_project.progress_updated = True

    fake_project.update_progress = _update_progress

    fake_task = SimpleNamespace(
        id=24,
        what="Fechar atividade",
        project=fake_project,
        project_id=31,
        status="in_progress",
        stage="executing",
        completion_date=None,
        how="",
    )

    _FakeProjectTask.query = _FakeQuery(fake_task)

    monkeypatch.setattr(project_module, "ProjectTask", _FakeProjectTask)
    monkeypatch.setattr(
        tools_module,
        "db",
        SimpleNamespace(
            session=SimpleNamespace(
                commit=lambda: commit_count.__setitem__("value", commit_count["value"] + 1),
                rollback=lambda: rollback_count.__setitem__("value", rollback_count["value"] + 1),
            )
        ),
    )

    result = tools_module.complete_task.func(
        task_type="project_task",
        task_id=24,
        evidence_description="Tudo validado",
        completion_date="2026-03-18",
    )

    assert "marcada como concluída" in result
    assert fake_task.status == "completed"
    assert fake_task.stage == "completed"
    assert fake_task.completion_date == date(2026, 3, 18)
    assert fake_project.progress_updated is True
    assert commit_count["value"] == 1
    assert rollback_count["value"] == 0


def test_get_tasks_today_uses_project_title_column():
    from pathlib import Path

    content = Path(r"C:\GestaoVersus\app32\src\intelligence\tools.py").read_text(encoding="utf-8")

    assert "p.title as project_name" in content
