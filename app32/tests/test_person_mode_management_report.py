"""Etapa 4c: relatorio gerencial usa os blocos da pessoa para quem migrou e segue igual para os demais."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, PersonWorkBlock, Process, Project, ProjectActivityCollaborator, ProjectTask, Routine,
                    RoutineCollaborator, RoutineJourneyBinding, WorkCalendarEvent, WorkJourneyBlock, WorkJourneyItem, db)
from services.work_journey_report_service import build_work_journey_management_report

MONDAY = date(2026, 10, 5)
ALL = ["manual", "process_instance", "project_task", "meeting"]


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, WorkJourneyBlock, WorkJourneyItem, WorkCalendarEvent, PersonWorkBlock, RoutineJourneyBinding,
            Routine, RoutineCollaborator, Process, Project, ProjectTask, ProjectActivityCollaborator)])
        db.session.add(Company(id=1, name="A"))
        db.session.add_all([
            Employee(id=10, company_id=1, user_id=1, name="Migrada", status="active", weekly_hours=40),
            Employee(id=11, company_id=1, user_id=2, name="Legada", status="active", weekly_hours=40),
        ])
        db.session.flush()
        db.session.add_all([
            PersonWorkBlock(id=7, user_id=1, name="Dia da pessoa", start_time=time(8, 0), end_time=time(12, 0),
                            weekdays_json=[0, 1, 2, 3, 4], block_mode="operational", preferred_item_types=[]),
            WorkJourneyBlock(id=7, company_id=1, employee_id=10, name="Legado dela", start_time=time(8, 0), end_time=time(10, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=ALL),
            WorkJourneyBlock(id=8, company_id=1, employee_id=11, name="Legado da outra", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0, 1, 2, 3, 4], block_mode="operational", accepted_item_types=ALL),
        ])
        # os dois itens apontam para o bloco legado de id 7 e 8; para a migrada isso NÃO pode cair no bloco da pessoa de id 7
        db.session.add_all([
            WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=1, title="Item dela",
                            estimated_minutes=60, due_date=MONDAY, occurrence_date=MONDAY, block_id=7),
            WorkJourneyItem(id=2, company_id=1, employee_id=11, item_type="project_task", source_id=2, title="Item da outra",
                            estimated_minutes=60, due_date=MONDAY, occurrence_date=MONDAY, block_id=8),
        ])
        db.session.add(WorkCalendarEvent(id=1, company_id=1, employee_id=10, source_type="manual", title="Evento", event_date=MONDAY,
                                         start_time=time(9, 0), end_time=time(10, 0), person_block_id=7, status="planned"))
        db.session.commit()
        yield app


def _emp(report, name):
    return next(e for e in report["employees"] if e["employee"]["name"] == name)


def test_relatorio_usa_blocos_da_pessoa_para_migrado_e_legado_para_os_demais(ctx):
    report = build_work_journey_management_report(1, MONDAY)
    migrated, legacy = _emp(report, "Migrada"), _emp(report, "Legada")
    assert [b["name"] for b in migrated["blocks"]] == ["Dia da pessoa"]
    assert [b["name"] for b in legacy["blocks"]] == ["Legado da outra"]
    # capacidade semanal da migrada: 5 dias x 4 h (bloco da pessoa), não 1 dia x 2 h do bloco legado
    assert migrated["blocks"][0]["week_capacity"] == 5 * 240


def test_item_com_bloco_legado_nao_cai_no_bloco_da_pessoa_de_mesmo_numero(ctx):
    report = build_work_journey_management_report(1, MONDAY)
    migrated, legacy = _emp(report, "Migrada"), _emp(report, "Legada")
    assert migrated["blocks"][0]["items_week"] == 0  # o item continuava apontando para o bloco legado 7
    assert legacy["blocks"][0]["items_week"] == 1  # comportamento antigo preservado
    assert migrated["blocks"][0]["events_week"] == 1  # evento com person_block_id entra no bloco da pessoa
