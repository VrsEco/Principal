from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    ProjectTaskCompleteExecutionHandler,
    ProjectTaskCompleteRequest,
    ProjectTaskCreateExecutionHandler,
    ProjectTaskCreateRequest,
)


class DummyTask:
    def __init__(self, task_id: int, what: str, code: str = ""):
        self.id = task_id
        self.what = what
        self.code = code


class DummyProject:
    def __init__(self, project_id: int, name: str, code: str = "", company_id: int = 9):
        self.id = project_id
        self.name = name
        self.code = code
        self.company_id = company_id
        self.progress_updated = False

    def update_progress(self):
        self.progress_updated = True


class DummyCompany:
    def __init__(self, client_code: str, name: str):
        self.client_code = client_code
        self.name = name


def _build_handler(**overrides):
    captured = {}

    def fake_resolve_company_ids_for_payload(payload, active_company_id, user_id):
        captured["resolved"] = {
            "payload": dict(payload or {}),
            "active_company_id": active_company_id,
            "user_id": user_id,
        }
        return [9], "empresa AA - Versus"

    def fake_create_project_task(**kwargs):
        captured["create_kwargs"] = dict(kwargs)
        return (
            {
                "task": DummyTask(31, "Configurar dashboards", "AA.J.17.31"),
                "project": DummyProject(17, "Projeto V3", "AA.J.17"),
                "company": DummyCompany("AA", "Versus"),
                "responsible_name": "Fabiano Ferreira",
            },
            None,
        )

    defaults = {
        "resolve_company_ids_for_payload": fake_resolve_company_ids_for_payload,
        "create_project_task": fake_create_project_task,
    }
    defaults.update(overrides)
    return ProjectTaskCreateExecutionHandler(**defaults), captured


def _build_complete_handler(**overrides):
    captured = {}
    project = DummyProject(17, "Projeto V3", "AA.J.17", company_id=9)

    class DummyCompleteTask(DummyTask):
        def __init__(self):
            super().__init__(31, "Configurar dashboards", "AA.J.17.31")
            self.project = project
            self.status = "in_progress"
            self.stage = "executing"
            self.completion_date = None

    task = DummyCompleteTask()

    def fake_commit_changes():
        captured["commits"] = captured.get("commits", 0) + 1

    def fake_rollback_changes():
        captured["rolled_back"] = True

    defaults = {
        "extract_id_from_code": lambda code: 31 if code == "AA.J.17.31" else None,
        "parse_completion_date": lambda raw: date(2026, 3, 20) if raw == "20/03/2026" else None,
        "today_provider": lambda: date(2026, 3, 21),
        "load_task_by_id": lambda task_id: task if task_id == 31 else None,
        "load_company_by_id": lambda company_id: DummyCompany("AA", "Versus"),
        "user_can_access_company": lambda user_id, company_id: True,
        "commit_changes": fake_commit_changes,
        "rollback_changes": fake_rollback_changes,
    }
    defaults.update(overrides)
    return ProjectTaskCompleteExecutionHandler(**defaults), captured, task, project


def test_project_task_create_handler_requires_project_code():
    handler, _ = _build_handler()

    result = handler.execute(
        ProjectTaskCreateRequest(
            payload={"nome_atividade": "Nova tarefa"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei o codigo do projeto. Informe no formato: codigo_projeto: AA.J.12"


def test_project_task_create_handler_calls_service_and_formats_success():
    handler, captured = _build_handler()

    result = handler.execute(
        ProjectTaskCreateRequest(
            payload={
                "codigo_projeto": "AA.J.17",
                "nome_atividade": "Configurar dashboards",
                "responsavel": "Fabiano Ferreira",
                "prazo": "20/03/2026",
                "como": "Criar painéis por diretoria",
                "prioridade": "high",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["resolved"]["active_company_id"] == 9
    assert captured["create_kwargs"]["project_code"] == "AA.J.17"
    assert captured["create_kwargs"]["task_name"] == "Configurar dashboards"
    assert captured["create_kwargs"]["allowed_company_ids"] == [9]
    assert captured["create_kwargs"]["responsible_name"] == "Fabiano Ferreira"
    assert captured["create_kwargs"]["due_date"] == "20/03/2026"
    assert captured["create_kwargs"]["description"] == "Criar painéis por diretoria"
    assert captured["create_kwargs"]["priority"] == "high"
    assert "AA.J.17.31" in result.response_text
    assert "Fabiano Ferreira" in result.response_text


def test_project_task_create_handler_returns_scope_error():
    handler, _ = _build_handler(
        resolve_company_ids_for_payload=lambda payload, active_company_id, user_id: (
            [],
            "Nao encontrei empresa para 'Gas Evolution'.",
        )
    )

    result = handler.execute(
        ProjectTaskCreateRequest(
            payload={
                "codigo_projeto": "AA.J.17",
                "nome_atividade": "Configurar dashboards",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei empresa para 'Gas Evolution'."


def test_project_task_complete_handler_requires_activity_code():
    handler, _, _, _ = _build_complete_handler()

    result = handler.execute(
        ProjectTaskCompleteRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei o codigo da atividade. Informe no formato: codigo_atividade: AA.J.26.175"


def test_project_task_complete_handler_formats_success():
    handler, captured, task, project = _build_complete_handler()

    result = handler.execute(
        ProjectTaskCompleteRequest(
            payload={"codigo_atividade": "AA.J.17.31", "data_finalizacao": "20/03/2026"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["commits"] == 1
    assert task.status == "completed"
    assert task.stage == "completed"
    assert task.completion_date == date(2026, 3, 20)
    assert project.progress_updated is True
    assert "AA.J.17.31" in result.response_text
    assert "Projeto: AA.J.17 - Projeto V3" in result.response_text
    assert "Data de Conclusao: 2026-03-20" in result.response_text


def test_project_task_complete_handler_rolls_back_when_progress_update_fails():
    project = DummyProject(17, "Projeto V3", "AA.J.17", company_id=9)

    def _broken_update_progress():
        raise RuntimeError("boom")

    project.update_progress = _broken_update_progress

    class DummyCompleteTask(DummyTask):
        def __init__(self):
            super().__init__(31, "Configurar dashboards", "AA.J.17.31")
            self.project = project
            self.status = "in_progress"
            self.stage = "executing"
            self.completion_date = None

    task = DummyCompleteTask()
    captured = {}

    def fake_commit_changes():
        captured["commits"] = captured.get("commits", 0) + 1

    def fake_rollback_changes():
        captured["rolled_back"] = True

    handler = ProjectTaskCompleteExecutionHandler(
        extract_id_from_code=lambda code: 31 if code == "AA.J.17.31" else None,
        parse_completion_date=lambda raw: date(2026, 3, 20) if raw == "20/03/2026" else None,
        today_provider=lambda: date(2026, 3, 21),
        load_task_by_id=lambda task_id: task if task_id == 31 else None,
        load_company_by_id=lambda company_id: DummyCompany("AA", "Versus"),
        user_can_access_company=lambda user_id, company_id: True,
        commit_changes=fake_commit_changes,
        rollback_changes=fake_rollback_changes,
    )

    result = handler.execute(
        ProjectTaskCompleteRequest(
            payload={"codigo_atividade": "AA.J.17.31", "data_finalizacao": "20/03/2026"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured.get("rolled_back") is True
    assert "AA.J.17.31" in result.response_text


def test_project_task_complete_handler_returns_invalid_date():
    handler, _, _, _ = _build_complete_handler()

    result = handler.execute(
        ProjectTaskCompleteRequest(
            payload={"codigo_atividade": "AA.J.17.31", "data_finalizacao": "amanha cedo"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."
