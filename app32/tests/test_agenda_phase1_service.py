"""Agenda, Fase 1: eventos avulsos no feed, atrasadas ordenáveis e telemetria sem conteúdo."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (AgendaUiEvent, Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask,
                    WorkCalendarEvent, db)
from services.agenda_telemetry_service import MAX_EVENTS_PER_CALL, record_events
from services.unified_calendar_service import (GOOGLE_SYNC_TYPES, UnifiedCalendarError, list_overdue,
                                               list_unified_events)

TODAY = date(2026, 10, 5)


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, WorkCalendarEvent,
            AgendaUiEvent)])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        db.session.add_all([
            Employee(id=10, company_id=1, name="Ana", status="active"),
            Employee(id=11, company_id=1, name="Bia", status="active"),
            Employee(id=20, company_id=2, name="Caio", status="active"),
        ])
        db.session.add_all([
            Project(id=1, company_id=1, name="Projeto Zeta", code_sequence=1),
            Project(id=2, company_id=1, name="Projeto Alfa", code_sequence=2),
            Project(id=3, company_id=2, name="Outra empresa"),
            Process(id=1, company_id=1, macro_id=1, name="Processo Beta"),
        ])
        db.session.flush()
        db.session.add_all([
            # atrasadas de Ana
            ProjectTask(id=1, project_id=1, code_sequence=1, what="Tarefa antiga", employee_id=10, due_date=date(2026, 9, 1)),
            ProjectTask(id=2, project_id=2, code_sequence=1, what="Tarefa recente", employee_id=10, due_date=date(2026, 10, 3)),
            ProjectTask(id=3, project_id=1, code_sequence=2, what="Concluída", employee_id=10, due_date=date(2026, 9, 2), status="completed"),
            ProjectTask(id=4, project_id=1, code_sequence=3, what="Apagada", employee_id=10, due_date=date(2026, 9, 3), is_deleted=True),
            ProjectTask(id=5, project_id=1, code_sequence=4, what="Hoje não é atrasada", employee_id=10, due_date=TODAY),
            ProjectTask(id=6, project_id=1, code_sequence=5, what="Da Bia", employee_id=11, due_date=date(2026, 9, 5)),
            ProjectTask(id=7, project_id=3, code_sequence=1, what="Outra empresa", employee_id=20, due_date=date(2026, 9, 5)),
            ProcessInstance(id=1, company_id=1, process_id=1, title="Instância do meio", due_date=date(2026, 9, 20), responsible_id=10),
            ProcessInstance(id=2, company_id=1, process_id=1, title="Instância feita", due_date=date(2026, 9, 21), responsible_id=10, status="completed"),
            # eventos avulsos
            WorkCalendarEvent(id=1, company_id=1, employee_id=10, source_type="manual", title="Dentista", event_date=date(2026, 10, 6),
                              start_time=time(14, 0), end_time=time(15, 30), status="planned"),
            WorkCalendarEvent(id=2, company_id=1, employee_id=10, source_type="manual", title="Sem horário", event_date=date(2026, 10, 6)),
            WorkCalendarEvent(id=3, company_id=1, employee_id=10, source_type="manual", title="Feito", event_date=date(2026, 10, 7), status="done"),
            WorkCalendarEvent(id=4, company_id=1, employee_id=11, source_type="manual", title="Da Bia", event_date=date(2026, 10, 6)),
            WorkCalendarEvent(id=5, company_id=1, employee_id=10, source_type="project_task", source_id=1, title="Evento ligado",
                              event_date=date(2026, 10, 6)),
        ])
        db.session.commit()
        yield app
        db.session.remove()


START, END = date(2026, 10, 1), date(2026, 10, 31)


def test_manual_events_only_with_employee_and_with_fields(ctx):
    mine = [e for e in list_unified_events(1, START, END, employee_id=10) if e["type"] == "manual"]
    assert [e["title"] for e in mine] == ["Sem horário", "Dentista", "Feito"] or [e["title"] for e in mine] == ["Dentista", "Sem horário", "Feito"]
    dentist = next(e for e in mine if e["title"] == "Dentista")
    assert dentist["time"] == "14:00" and dentist["end_time"] == "15:30" and dentist["duration_minutes"] == 90
    assert dentist["all_day"] is False and dentist["editable"] is True and dentist["url"] is None
    assert next(e for e in mine if e["title"] == "Sem horário")["all_day"] is True
    assert next(e for e in mine if e["title"] == "Feito")["closed"] is True
    # outro colaborador e eventos ligados a origens não vazam para o feed de Ana
    assert "Da Bia" not in {e["title"] for e in mine} and "Evento ligado" not in {e["title"] for e in mine}
    # sem colaborador (visão da empresa) os avulsos pessoais não aparecem
    assert not [e for e in list_unified_events(1, START, END) if e["type"] == "manual"]


def test_manual_events_stay_out_of_google_sync_types(ctx):
    assert "manual" not in GOOGLE_SYNC_TYPES
    events = list_unified_events(1, START, END, employee_id=10, types=GOOGLE_SYNC_TYPES)
    assert all(e["type"] != "manual" for e in events)


def test_overdue_default_order_oldest_first_and_filters(ctx):
    out = list_overdue(1, TODAY, employee_id=10)
    assert [e["title"] for e in out["items"]] == ["Tarefa antiga", "Instância do meio", "Tarefa recente"]
    assert out["total"] == 3 and out["sort"] == "old"
    assert [e["days_late"] for e in out["items"]] == [34, 15, 2]
    # concluída, apagada, de hoje, de outro colaborador e de outra empresa ficam de fora
    titles = {e["title"] for e in out["items"]}
    assert not titles & {"Concluída", "Apagada", "Hoje não é atrasada", "Da Bia", "Outra empresa", "Instância feita"}


def test_overdue_other_sorts_and_type_filter(ctx):
    assert [e["title"] for e in list_overdue(1, TODAY, employee_id=10, sort="new")["items"]] == ["Tarefa recente", "Instância do meio", "Tarefa antiga"]
    by_type = [e["type"] for e in list_overdue(1, TODAY, employee_id=10, sort="type")["items"]]
    assert by_type == sorted(by_type)
    by_source = [e["subtitle"] for e in list_overdue(1, TODAY, employee_id=10, sort="source")["items"]]
    assert by_source == ["Processo Beta", "Projeto Alfa", "Projeto Zeta"]
    only_tasks = list_overdue(1, TODAY, employee_id=10, types={"project_task"})
    assert {e["type"] for e in only_tasks["items"]} == {"project_task"} and only_tasks["total"] == 2
    assert list_overdue(1, TODAY, employee_id=10, sort="invalida")["sort"] == "old"


def test_overdue_company_scope_and_limit_and_validation(ctx):
    company = list_overdue(1, TODAY)
    assert {e["title"] for e in company["items"]} >= {"Da Bia", "Tarefa antiga"} and "Outra empresa" not in {e["title"] for e in company["items"]}
    limited = list_overdue(1, TODAY, employee_id=10, limit=2)
    assert len(limited["items"]) == 2 and limited["total"] == 3
    with pytest.raises(UnifiedCalendarError):
        list_overdue(1, TODAY, employee_id=20)  # colaborador de outra empresa


def test_telemetry_whitelist_and_no_content(ctx):
    saved = record_events(1, 7, "mobile", [
        {"event": "agenda_open", "detail": "week"},
        {"event": "create_choose", "detail": "manual", "title": "Dentista do Fulano"},  # campo extra é ignorado
        {"event": "late_sort", "detail": "old"},
        {"event": "evento_invalido", "detail": "x"},
        {"event": "view_change", "detail": "<script>"},   # detail fora da lista vira nulo
        "lixo",
    ])
    assert saved == 4
    rows = AgendaUiEvent.query.order_by(AgendaUiEvent.id).all()
    assert [(r.event, r.detail) for r in rows] == [("agenda_open", "week"), ("create_choose", "manual"), ("late_sort", "old"), ("view_change", None)]
    assert all(r.company_id == 1 and r.user_id == 7 and r.device == "mobile" for r in rows)
    assert record_events(1, 7, "tv", [{"event": "legacy_open"}]) == 1
    assert AgendaUiEvent.query.filter_by(event="legacy_open").one().device is None


def test_telemetry_caps_batch_size(ctx):
    n = record_events(1, 7, "desktop", [{"event": "late_open"}] * (MAX_EVENTS_PER_CALL + 15))
    assert n == MAX_EVENTS_PER_CALL
