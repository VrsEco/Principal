from datetime import date
from pathlib import Path
import sys


ROOT_DIR = Path(r"C:\GestaoVersus\app32")
APP_ROOT = ROOT_DIR / "app32" if (ROOT_DIR / "app32").exists() else ROOT_DIR
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def test_get_tasks_today_uses_active_company_scope(monkeypatch):
    from src.intelligence.tools_domains import task_ops

    captured = {}

    def fake_get_user_activities_v2(**kwargs):
        captured.update(kwargs)
        return (
            [
                {
                    "id": 10,
                    "type": "project",
                    "title": "Fechar proposta",
                    "deadline_date": date(2026, 5, 16),
                    "status": "pending",
                    "responsible_name": "Fabiano",
                    "project_title": "[LAB M1] Projeto Base",
                },
                {
                    "id": 20,
                    "type": "process",
                    "title": "Revisar agenda",
                    "deadline_date": date(2026, 5, 15),
                    "status": "in_progress",
                    "collaborators_json": [{"name": "Fabiano"}],
                },
            ],
            {"me": 1, "company": 2, "general": 2},
        )

    monkeypatch.setattr(task_ops, "get_active_company_id", lambda: 10)
    monkeypatch.setattr(task_ops, "get_active_user_id", lambda: 3)
    monkeypatch.setattr(
        "services.my_work.discovery_service.get_user_activities_v2",
        fake_get_user_activities_v2,
    )

    result = task_ops.get_tasks_today(scope="company")

    assert captured["user_id"] == 3
    assert captured["scope"] == "company"
    assert captured["company_ids"] == [10]
    assert captured["active_company_id"] == 10
    assert captured["filters"]["delivery_tags"] == ["open"]
    assert "[LAB M1] Projeto Base" in result
    assert "Revisar agenda" in result


def test_get_tasks_today_maps_team_to_company(monkeypatch):
    from src.intelligence.tools_domains import task_ops

    captured = {}

    def fake_get_user_activities_v2(**kwargs):
        captured.update(kwargs)
        return ([], {"me": 0, "company": 0, "general": 0})

    monkeypatch.setattr(task_ops, "get_active_company_id", lambda: 10)
    monkeypatch.setattr(task_ops, "get_active_user_id", lambda: 3)
    monkeypatch.setattr(
        "services.my_work.discovery_service.get_user_activities_v2",
        fake_get_user_activities_v2,
    )

    task_ops.get_tasks_today(scope="team")

    assert captured["scope"] == "company"


def test_get_tasks_today_rejects_invalid_scope(monkeypatch):
    from src.intelligence.tools_domains import task_ops

    monkeypatch.setattr(task_ops, "get_active_company_id", lambda: 10)
    monkeypatch.setattr(task_ops, "get_active_user_id", lambda: 3)

    result = task_ops.get_tasks_today(scope="xpto")

    assert "scope inválido" in result
