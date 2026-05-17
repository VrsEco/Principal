from datetime import date
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT_DIR = Path(r"C:\GestaoVersus\app32")
APP_ROOT = ROOT_DIR / "app32" if (ROOT_DIR / "app32").exists() else ROOT_DIR
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def _get_tasks_today_function_source() -> str:
    content = (APP_ROOT / "src" / "intelligence" / "tools_domains" / "task_ops.py").read_text(encoding="utf-8")
    start = content.index("def get_tasks_today")
    end = content.index("def create_project_task", start + 1)
    return content[start:end]


def test_complete_task_project_task_commits_once(monkeypatch):
    from src.intelligence import tools as tools_module

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
    monkeypatch.setattr(
        "src.intelligence.tools_domains.task_ops.get_project_task_in_active_company",
        lambda task_id: (fake_task, None) if task_id == 24 else (None, "not-found"),
    )
    fake_db = SimpleNamespace(
        session=SimpleNamespace(
            commit=lambda: commit_count.__setitem__("value", commit_count["value"] + 1),
            rollback=lambda: rollback_count.__setitem__("value", rollback_count["value"] + 1),
        )
    )
    monkeypatch.setattr(tools_module, "db", fake_db)
    monkeypatch.setattr("src.intelligence.tools_domains.task_ops.db", fake_db)

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
    function_source = _get_tasks_today_function_source()

    assert 'activity.get("project_title")' in function_source


def test_get_tasks_today_uses_current_process_assignment_fields():
    function_source = _get_tasks_today_function_source()

    assert "get_user_activities_v2" in function_source
    assert "company_ids=[company_id]" in function_source
    assert "active_company_id=company_id" in function_source
