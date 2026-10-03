"""Agenda, Fase 2: sinais por bloco carregados do banco (somente leitura, isolados por empresa)."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, Meeting, WorkCalendarEvent, WorkJourneyAgenda, WorkJourneyAgendaItem,
                    WorkJourneyBlock, WorkJourneyItem, db)
from services.agenda_block_view_service import BlockViewError, build_block_view

MONDAY = date(2026, 10, 5)


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Meeting, WorkCalendarEvent, WorkJourneyBlock, WorkJourneyItem, WorkJourneyAgenda,
            WorkJourneyAgendaItem)])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        db.session.add_all([
            Employee(id=10, company_id=1, name="Ana", status="active"),
            Employee(id=20, company_id=2, name="Ana B", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyBlock(id=1, company_id=1, employee_id=10, name="Manhã", start_time=time(7, 30),
                             end_time=time(10, 0), weekdays_json=[0], block_mode="operational"),
            WorkJourneyBlock(id=2, company_id=1, employee_id=10, name="Meio", start_time=time(10, 0),
                             end_time=time(12, 0), weekdays_json=[0], block_mode="operational"),
            WorkJourneyBlock(id=3, company_id=1, employee_id=10, name="Terça", start_time=time(8, 0),
                             end_time=time(9, 0), weekdays_json=[1], block_mode="operational"),
            WorkJourneyBlock(id=4, company_id=2, employee_id=20, name="Outra empresa", start_time=time(8, 0),
                             end_time=time(18, 0), weekdays_json=[0], block_mode="operational"),
        ])
        db.session.add_all([
            WorkJourneyAgenda(id=1, company_id=1, employee_id=10, anchor_date=MONDAY, scope="day"),
            WorkJourneyAgenda(id=2, company_id=2, employee_id=20, anchor_date=MONDAY, scope="day"),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyItem(id=1, company_id=1, employee_id=10, title="Atividade 2h", estimated_minutes=120),
            WorkJourneyItem(id=2, company_id=1, employee_id=10, title="Sem estimativa", estimated_minutes=0),
            WorkJourneyItem(id=3, company_id=1, employee_id=10, title="Concluída", estimated_minutes=60, status="completed"),
            WorkJourneyItem(id=4, company_id=2, employee_id=20, title="Outra empresa", estimated_minutes=480),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyAgendaItem(id=1, agenda_id=1, company_id=1, employee_id=10, journey_item_id=1, block_id=2,
                                  planned_date=MONDAY, allocated_minutes=120),
            WorkJourneyAgendaItem(id=2, agenda_id=1, company_id=1, employee_id=10, journey_item_id=2, block_id=2,
                                  planned_date=MONDAY, allocated_minutes=15),
            WorkJourneyAgendaItem(id=3, agenda_id=1, company_id=1, employee_id=10, journey_item_id=3, block_id=1,
                                  planned_date=MONDAY, allocated_minutes=60),
            WorkJourneyAgendaItem(id=4, agenda_id=2, company_id=2, employee_id=20, journey_item_id=4, block_id=4,
                                  planned_date=MONDAY, allocated_minutes=480),
        ])
        db.session.add(Meeting(id=1, company_id=1, title="Reunião 1h30", scheduled_date=MONDAY,
                               scheduled_time="10:00", planned_duration_minutes=90, status="scheduled",
                               participants_json='[{"employee_id": 10}]'))
        db.session.commit()
        yield app


def _day(view, iso):
    return next(d for d in view["days"] if d["date"] == iso)


def test_exemplo_da_spec_no_banco(ctx):
    view = build_block_view(1, 10, MONDAY, MONDAY)
    day = _day(view, "2026-10-05")
    morning, middle = day["blocks"]
    assert morning["signal"]["label"] == "Livre 2h30"  # item concluído não consome
    assert middle["consumed_minutes"] == 120 + 90  # atividade 2h + reunião 1h30 que começa às 10:00
    assert middle["signal"]["label"] == "Acima 1h30"
    assert middle["without_estimate"] == 1  # fora da conta, marcado
    assert day["day"]["capacity_minutes"] == 270


def test_evento_encerrado_nao_consome(ctx):
    Meeting.query.filter_by(id=1).update({"status": "completed"})
    db.session.commit()
    view = build_block_view(1, 10, MONDAY, MONDAY)
    assert _day(view, "2026-10-05")["blocks"][1]["consumed_minutes"] == 120


def test_mesmo_item_em_duas_agendas_conta_uma_vez(ctx):
    db.session.add(WorkJourneyAgenda(id=3, company_id=1, employee_id=10, anchor_date=date(2026, 10, 4), scope="week"))
    db.session.flush()
    db.session.add(WorkJourneyAgendaItem(id=10, agenda_id=3, company_id=1, employee_id=10, journey_item_id=1,
                                         block_id=2, planned_date=MONDAY, allocated_minutes=120))
    db.session.commit()
    middle = _day(build_block_view(1, 10, MONDAY, MONDAY), "2026-10-05")["blocks"][1]
    assert middle["consumed_minutes"] == 120 + 90
    assert [i["title"] for i in middle["items"]] == ["Atividade 2h", "Sem estimativa"]


def test_item_adiado_nao_consome(ctx):
    WorkJourneyItem.query.filter_by(id=1).update({"status": "postponed"})
    db.session.commit()
    middle = _day(build_block_view(1, 10, MONDAY, MONDAY), "2026-10-05")["blocks"][1]
    assert middle["consumed_minutes"] == 90


def test_atrasado_so_consome_depois_de_planejado_pela_pessoa(ctx):
    WorkJourneyItem.query.filter_by(id=1).update({"due_date": date(2026, 9, 1)})
    db.session.commit()
    middle = lambda: _day(build_block_view(1, 10, MONDAY, MONDAY), "2026-10-05")["blocks"][1]
    assert middle()["consumed_minutes"] == 90  # sugestão do motor para item atrasado não conta
    WorkJourneyAgendaItem.query.filter_by(id=1).update({"manual_override": True})
    db.session.commit()
    assert middle()["consumed_minutes"] == 120 + 90  # a pessoa planejou: passa a contar


def test_nao_bloqueia_nem_cria_nada(ctx):
    before = WorkJourneyAgenda.query.count(), WorkJourneyAgendaItem.query.count()
    build_block_view(1, 10, MONDAY, MONDAY)
    assert (WorkJourneyAgenda.query.count(), WorkJourneyAgendaItem.query.count()) == before


def test_dia_sem_bloco_mostra_sem_expediente(ctx):
    view = build_block_view(1, 10, date(2026, 10, 10), date(2026, 10, 10))  # sábado
    assert _day(view, "2026-10-10")["day"]["label"] == "Sem expediente"


def test_isolamento_por_empresa(ctx):
    view = build_block_view(1, 10, MONDAY, MONDAY)
    names = [b["name"] for b in _day(view, "2026-10-05")["blocks"]]
    assert "Outra empresa" not in names
    with pytest.raises(BlockViewError):
        build_block_view(1, 20, MONDAY, MONDAY)  # colaborador de outra empresa


def test_periodo_invalido_ou_grande(ctx):
    with pytest.raises(BlockViewError):
        build_block_view(1, 10, MONDAY, date(2026, 9, 1))
    with pytest.raises(BlockViewError):
        build_block_view(1, 10, MONDAY, date(2026, 12, 1))
