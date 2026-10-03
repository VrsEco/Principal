"""Agenda, Fase 4: sinais da equipe para o gestor (privacidade, soma entre empresas so para migrados, carga em lote)."""
from __future__ import annotations

import json
import os
import sys
from datetime import date, time

import pytest
from flask import Flask
from sqlalchemy import event

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, Meeting, PersonWorkBlock, WorkCalendarEvent, WorkJourneyAgenda, WorkJourneyAgendaItem,
                    WorkJourneyBlock, WorkJourneyItem, db)
from services.agenda_block_view_service import BlockViewError
from services.team_block_signal_service import build_team_view

MONDAY = date(2026, 10, 5)
SECRET_ITEM = "SEGREDO-ITEM-OUTRA-EMPRESA"
SECRET_MEETING = "SEGREDO-REUNIAO-OUTRA-EMPRESA"
SECRET_PERSONAL = "SEGREDO-EVENTO-PESSOAL"


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Meeting, WorkCalendarEvent, WorkJourneyBlock, WorkJourneyItem, WorkJourneyAgenda,
            WorkJourneyAgendaItem, PersonWorkBlock)])
        db.session.add_all([Company(id=1, name="Empresa A"), Company(id=2, name="Empresa B")])
        db.session.add_all([
            Employee(id=10, company_id=1, user_id=1, name="Ana (migrada)", status="active"),
            Employee(id=20, company_id=2, user_id=1, name="Ana na B", status="active"),
            Employee(id=11, company_id=1, user_id=2, name="Bia (legado)", status="active"),
            Employee(id=21, company_id=2, user_id=2, name="Bia na B", status="active"),
            Employee(id=12, company_id=1, user_id=None, name="Caio sem login", status="active"),
            Employee(id=99, company_id=2, user_id=3, name="Só da B", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            PersonWorkBlock(id=1, user_id=1, name="Manhã da pessoa", start_time=time(8, 0), end_time=time(12, 0),
                            weekdays_json=[0], block_mode="operational", preferred_item_types=[]),
            WorkJourneyBlock(id=1, company_id=1, employee_id=11, name="Legado A", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=["project_task"]),
            WorkJourneyBlock(id=2, company_id=2, employee_id=21, name="Legado B da Bia", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=["project_task"]),
        ])
        db.session.add_all([WorkJourneyAgenda(id=1, company_id=1, employee_id=10, anchor_date=MONDAY, scope="day"),
                            WorkJourneyAgenda(id=2, company_id=2, employee_id=20, anchor_date=MONDAY, scope="day"),
                            WorkJourneyAgenda(id=3, company_id=1, employee_id=11, anchor_date=MONDAY, scope="day"),
                            WorkJourneyAgenda(id=4, company_id=2, employee_id=21, anchor_date=MONDAY, scope="day")])
        db.session.flush()
        db.session.add_all([
            WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=1, title="Item da empresa A",
                            estimated_minutes=60, due_date=MONDAY),
            WorkJourneyItem(id=2, company_id=2, employee_id=20, item_type="project_task", source_id=2, title=SECRET_ITEM,
                            estimated_minutes=90, due_date=MONDAY),
            WorkJourneyItem(id=3, company_id=1, employee_id=11, item_type="project_task", source_id=3, title="Item legado A",
                            estimated_minutes=60, due_date=MONDAY),
            WorkJourneyItem(id=4, company_id=2, employee_id=21, item_type="project_task", source_id=4, title=SECRET_ITEM + "-BIA",
                            estimated_minutes=120, due_date=MONDAY),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyAgendaItem(agenda_id=1, company_id=1, employee_id=10, journey_item_id=1, person_block_id=1, planned_date=MONDAY, manual_override=True),
            WorkJourneyAgendaItem(agenda_id=2, company_id=2, employee_id=20, journey_item_id=2, person_block_id=1, planned_date=MONDAY, manual_override=True),
            WorkJourneyAgendaItem(agenda_id=3, company_id=1, employee_id=11, journey_item_id=3, block_id=1, planned_date=MONDAY, manual_override=True),
            WorkJourneyAgendaItem(agenda_id=4, company_id=2, employee_id=21, journey_item_id=4, block_id=2, planned_date=MONDAY, manual_override=True),
        ])
        db.session.add(Meeting(id=1, company_id=2, title=SECRET_MEETING, scheduled_date=MONDAY, scheduled_time="09:00",
                               planned_duration_minutes=30, status="scheduled", participants_json='[{"employee_id": 20}]'))
        db.session.add(WorkCalendarEvent(id=1, company_id=2, employee_id=20, source_type="manual", title=SECRET_PERSONAL,
                                         event_date=MONDAY, start_time=time(10, 0), end_time=time(10, 30), status="planned"))
        db.session.commit()
        yield app


def _team(**kw):
    return build_team_view(1, MONDAY, MONDAY, **kw)


def _emp(view, name):
    return next(e for e in view["employees"] if e["name"] == name)


def test_migrado_soma_entre_empresas_com_divisao_desta_e_outras(ctx):
    ana = _emp(_team(), "Ana (migrada)")
    assert ana["source"] == "person"
    block = ana["days"][0]["blocks"][0]
    # A: 60 min + B: item 90 + reunião 30 + evento pessoal 30 = 210 min
    assert block["consumed_minutes"] == 210
    assert block["this_company_minutes"] == 60 and block["other_companies_minutes"] == 150
    assert block["signal"]["label"] == "Livre 30min"  # 4h de capacidade
    assert [i["title"] for i in block["items"]] == ["Item da empresa A"]  # só itens desta empresa têm título
    day = ana["days"][0]["day"]
    assert day["capacity_minutes"] == 240 and day["consumed_minutes"] == 210 and day["other_companies_minutes"] == 150


def test_nao_migrado_nao_soma_entre_empresas(ctx):
    bia = _emp(_team(), "Bia (legado)")
    assert bia["source"] == "legacy"
    block = bia["days"][0]["blocks"][0]
    assert block["name"] == "Legado A" and block["consumed_minutes"] == 60  # sem os 120 min da empresa B
    assert block["other_companies_minutes"] == 0


def test_colaborador_sem_login_aparece_sem_blocos(ctx):
    caio = _emp(_team(), "Caio sem login")
    assert caio["source"] == "legacy" and caio["days"][0]["blocks"] == []
    assert caio["days"][0]["day"]["label"] == "Sem expediente"


def test_nenhum_dado_de_outra_empresa_vaza_na_resposta(ctx):
    raw = json.dumps(_team(), ensure_ascii=False)
    for secret in (SECRET_ITEM, SECRET_MEETING, SECRET_PERSONAL, "Empresa B", "Legado B da Bia", "Ana na B", "Bia na B", "Só da B"):
        assert secret not in raw, secret
    assert "Item da empresa A" in raw


def test_lista_so_colaboradores_da_empresa_do_gestor(ctx):
    names = [e["name"] for e in _team()["employees"]]
    assert names == ["Ana (migrada)", "Bia (legado)", "Caio sem login"]
    other = build_team_view(2, MONDAY, MONDAY)
    assert {e["name"] for e in other["employees"]} == {"Ana na B", "Bia na B", "Só da B"}


def test_campos_permitidos_por_bloco(ctx):
    block = _emp(_team(), "Ana (migrada)")["days"][0]["blocks"][0]
    assert set(block) == {"id", "name", "start", "end", "mode", "capacity_minutes", "consumed_minutes", "this_company_minutes",
                          "other_companies_minutes", "without_estimate", "signal", "items"}
    assert set(block["items"][0]) == {"type", "title", "minutes"}


def test_periodo_invalido(ctx):
    with pytest.raises(BlockViewError):
        build_team_view(1, MONDAY, date(2026, 9, 1))
    with pytest.raises(BlockViewError):
        build_team_view(1, MONDAY, date(2026, 12, 1))


def test_quantidade_de_consultas_nao_cresce_com_a_equipe(ctx):
    def count_queries(fn):
        statements = []
        engine = db.engine

        def before(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", before)
        try:
            fn()
        finally:
            event.remove(engine, "before_cursor_execute", before)
        return len(statements)

    small = count_queries(lambda: _team())
    for i in range(60):  # dezenas de colaboradores, metade migrada
        db.session.add(Employee(id=1000 + i, company_id=1, user_id=(500 + i), name=f"Colab {i:02d}", status="active"))
        if i % 2 == 0:
            db.session.add(PersonWorkBlock(user_id=500 + i, name="Bloco", start_time=time(8, 0), end_time=time(10, 0),
                                           weekdays_json=[0], preferred_item_types=[]))
    db.session.commit()
    large = count_queries(lambda: _team())
    assert len(_team()["employees"]) == 63
    assert large <= small + 2, (small, large)  # lote: não há consulta por colaborador
