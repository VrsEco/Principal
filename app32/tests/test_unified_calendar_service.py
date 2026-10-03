"""Agenda unificada: projeção de reuniões, atividades e instâncias, com escopo por empresa e colaborador."""
from __future__ import annotations

import json
import os
import sys
from datetime import date

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, db
from services.unified_calendar_service import UnifiedCalendarError, list_unified_events

START, END = date(2026, 10, 1), date(2026, 10, 31)


@pytest.fixture()
def app_ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[m.__table__ for m in (Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask)],
        )
        yield app
        db.session.remove()


def _seed():
    db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
    db.session.add_all([
        Employee(id=10, company_id=1, name="Ana", status="active"),
        Employee(id=11, company_id=1, name="Bia", status="active"),
        Employee(id=20, company_id=2, name="Caio", status="active"),
    ])
    db.session.add_all([
        Project(id=1, company_id=1, name="Projeto A"),
        Project(id=2, company_id=2, name="Projeto B"),
        Process(id=1, company_id=1, macro_id=1, name="Processo A"),
    ])
    db.session.flush()
    db.session.add_all([
        Meeting(id=1, company_id=1, title="Reunião Ana", scheduled_date=date(2026, 10, 5), scheduled_time="09:00",
                participants_json=json.dumps([{"id": 10, "name": "Ana"}])),
        Meeting(id=2, company_id=1, title="Reunião sem data"),
        Meeting(id=3, company_id=2, title="Outra empresa", scheduled_date=date(2026, 10, 5)),
        ProjectTask(id=1, code_sequence=1, project_id=1, what="Tarefa Ana", employee_id=10, due_date=date(2026, 10, 6)),
        ProjectTask(id=2, code_sequence=2, project_id=1, what="Tarefa Bia", employee_id=11, due_date=date(2026, 10, 6)),
        ProjectTask(id=3, code_sequence=3, project_id=1, what="Apagada", employee_id=10, due_date=date(2026, 10, 6), is_deleted=True),
        ProjectTask(id=4, code_sequence=4, project_id=2, what="Outra empresa", employee_id=20, due_date=date(2026, 10, 6)),
        ProjectTask(id=5, code_sequence=5, project_id=1, what="Fora do período", employee_id=10, due_date=date(2026, 11, 3)),
        ProcessInstance(id=1, company_id=1, process_id=1, title="Instância Ana", due_date=date(2026, 10, 7),
                        responsible_id=10),
        ProcessInstance(id=2, company_id=1, process_id=1, title="Instância Bia", due_date=date(2026, 10, 7),
                        responsible_id=11, status="completed"),
    ])
    db.session.commit()


def test_company_scope_returns_all_types_and_urls(app_ctx):
    _seed()
    events = list_unified_events(1, START, END)
    keys = {e["key"] for e in events}
    assert keys == {"meeting:1", "project_task:1", "project_task:2", "process_instance:1", "process_instance:2"}
    by_key = {e["key"]: e for e in events}
    assert by_key["meeting:1"]["url"] == "/meetings/company/1?meeting_id=1"
    assert by_key["project_task:1"]["url"].startswith("/my-work/project-task/1")
    assert by_key["process_instance:1"]["url"].startswith("/my-work/process-instance/1?company_id=1")
    assert by_key["process_instance:2"]["closed"] is True


def test_employee_scope_filters_each_source(app_ctx):
    _seed()
    keys = {e["key"] for e in list_unified_events(1, START, END, employee_id=10)}
    assert keys == {"meeting:1", "project_task:1", "process_instance:1"}


def test_type_filter_and_ordering(app_ctx):
    _seed()
    events = list_unified_events(1, START, END, types={"project_task"})
    assert [e["type"] for e in events] == ["project_task", "project_task"]
    assert [e["date"] for e in events] == sorted(e["date"] for e in events)


def test_rejects_foreign_employee_and_bad_range(app_ctx):
    _seed()
    with pytest.raises(UnifiedCalendarError):
        list_unified_events(1, START, END, employee_id=20)
    with pytest.raises(UnifiedCalendarError):
        list_unified_events(1, END, START)
    with pytest.raises(UnifiedCalendarError):
        list_unified_events(1, date(2026, 1, 1), date(2026, 12, 31))
