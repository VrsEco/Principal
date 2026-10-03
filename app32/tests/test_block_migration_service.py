"""Agenda, Fase 3: assistente de migracao dos blocos por empresa para os blocos da pessoa."""
from __future__ import annotations

import itertools
import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, PersonWorkBlock, RoutineJourneyBinding, UserLog, WorkCalendarEvent,
                    WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock, db)
from services import block_migration_service as mig
from services.block_migration_service import group_legacy_blocks, normalize_name
from services.person_work_block_service import PersonBlockError

USER = 1
WEEK = [0, 1, 2, 3, 4]


def _legacy(i, company, employee, name, start, end, days=WEEK, mode="operational", types=("project_task",)):
    return WorkJourneyBlock(id=i, company_id=company, employee_id=employee, name=name, start_time=time(*start),
                            end_time=time(*end), weekdays_json=list(days), block_mode=mode, accepted_item_types=list(types))


@pytest.fixture()
def ctx(monkeypatch):
    import models.user_log as user_log_module

    counter = itertools.count(1)
    monkeypatch.setattr(user_log_module, "_allocate_user_log_id", lambda connection: next(counter))
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, WorkJourneyBlock, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkCalendarEvent,
            PersonWorkBlock, RoutineJourneyBinding, UserLog)])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B"), Company(id=3, name="C")])
        db.session.add_all([
            Employee(id=10, company_id=1, user_id=USER, name="Ana A", status="active"),
            Employee(id=20, company_id=2, user_id=USER, name="Ana B", status="active"),
            Employee(id=30, company_id=3, user_id=USER, name="Ana C", status="active"),
            Employee(id=40, company_id=1, user_id=2, name="Outro", status="active"),
            Employee(id=50, company_id=1, user_id=None, name="Sem login", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            _legacy(1, 1, 10, "Almoço", (12, 0), (13, 0)),
            _legacy(2, 2, 20, "almoco", (12, 0), (13, 30)),
            _legacy(3, 3, 30, "Almoço", (12, 0), (13, 0)),
            _legacy(4, 1, 10, "Foco", (8, 0), (10, 0), types=("project_task", "process_instance")),
            _legacy(5, 2, 20, "Foco", (14, 0), (16, 0)),  # mesmo nome, sem sobreposição: NÃO agrupa
            _legacy(6, 3, 30, "Reunião", (9, 0), (11, 0)),  # sobrepõe "Foco" mas tem outro nome: não agrupa
            _legacy(7, 1, 10, "Buffer", (16, 0), (17, 0), mode="buffer"),
            _legacy(8, 1, 40, "De outro usuário", (8, 0), (9, 0)),
            _legacy(9, 1, 50, "Sem login", (8, 0), (9, 0)),
            _legacy(10, 1, 10, "Inativo", (7, 0), (8, 0)),
        ])
        WorkJourneyBlock.query.filter_by(id=10).update({"is_active": False})
        db.session.add(RoutineJourneyBinding(id=1, company_id=1, routine_id=1, employee_id=10, block_id=4))
        db.session.add(RoutineJourneyBinding(id=2, company_id=2, routine_id=2, employee_id=20, block_id=5))
        db.session.add(RoutineJourneyBinding(id=3, company_id=1, routine_id=3, employee_id=40, block_id=8))
        db.session.commit()
        yield app


def test_normaliza_nomes():
    assert normalize_name("  Almoço  ") == normalize_name("almoco") == "almoco"
    assert normalize_name("Gerir & Executar!") == "gerir executar"


def test_agrupamento_puro():
    mk = lambda n, s, e, d=(0, 1), m="operational": {"name": n, "mode": m, "start_minutes": s, "end_minutes": e, "weekdays": list(d)}
    groups = group_legacy_blocks([mk("A", 480, 600), mk("a", 540, 660), mk("A", 900, 960), mk("A", 480, 600, d=(3,)), mk("A", 480, 600, m="buffer")])
    sizes = sorted(len(g) for g in groups)
    assert sizes == [1, 1, 1, 2]  # só o par de mesmo nome que se sobrepõe em dia comum se junta


def test_proposta_agrupa_almoco_e_nao_mistura_usuarios(ctx):
    out = mig.propose(USER)
    assert out["legacy_count"] == 7 and out["companies"] == 3 and not out["already_migrated"]
    by_name = {p["name"]: p for p in out["proposals"]}
    lunch = by_name["Almoço"]
    assert lunch["merged"] and len(lunch["sources"]) == 3
    assert (lunch["start"], lunch["end"]) == ("12:00", "13:30")  # janela mais ampla
    assert lunch["note"] and lunch["weekdays"] == WEEK
    assert len([p for p in out["proposals"] if p["name"] == "Foco"]) == 2  # sem sobreposição: separados
    assert "De outro usuário" not in by_name and "Sem login" not in by_name and "Inativo" not in by_name
    assert PersonWorkBlock.query.count() == 0  # propor não grava


def test_aplicar_cria_so_o_confirmado_e_reaponta_rotinas(ctx):
    plan = {p["name"] + p["start"]: p["id"] for p in mig.propose(USER)["proposals"]}
    foco_manha, foco_tarde = plan["Foco08:00"], plan["Foco14:00"]
    out = mig.apply(USER, [
        {"id": foco_manha, "accept": True, "name": "Foco profundo", "end": "09:30"},
        {"id": foco_tarde, "accept": False},
    ])
    assert [b["name"] for b in out["created"]] == ["Foco profundo"]
    block = PersonWorkBlock.query.one()
    assert block.user_id == USER and block.end_time == time(9, 30)
    assert out["routines_rebound"] == 1
    assert RoutineJourneyBinding.query.get(1).person_block_id == block.id  # veio do bloco legado 4
    assert RoutineJourneyBinding.query.get(2).person_block_id is None  # proposta recusada
    assert RoutineJourneyBinding.query.get(3).person_block_id is None  # outro usuário
    assert RoutineJourneyBinding.query.get(1).block_id == 4  # legado intacto
    assert WorkJourneyBlock.query.count() == 10  # nenhum bloco legado removido


def test_nao_cria_sem_confirmacao_nem_duas_vezes(ctx):
    with pytest.raises(PersonBlockError):
        mig.apply(USER, [])
    with pytest.raises(PersonBlockError):
        mig.apply(USER, [{"id": 999, "accept": True}])
    first = mig.propose(USER)["proposals"][0]["id"]
    mig.apply(USER, [{"id": first}])
    assert mig.propose(USER)["already_migrated"] is True
    with pytest.raises(PersonBlockError, match="já usa"):
        mig.apply(USER, [{"id": first}])


def test_reverter_devolve_o_comportamento_anterior(ctx):
    first = mig.propose(USER)["proposals"][0]["id"]
    mig.apply(USER, [{"id": first}])
    person_id = PersonWorkBlock.query.one().id
    db.session.add(WorkJourneyAgenda(id=1, company_id=1, employee_id=10, anchor_date=date(2026, 10, 5), scope="day"))
    db.session.flush()
    db.session.add(WorkJourneyAgendaItem(agenda_id=1, company_id=1, employee_id=10, journey_item_id=1, person_block_id=person_id,
                                         planned_date=date(2026, 10, 5), manual_override=True))
    db.session.commit()

    out = mig.revert(USER)
    assert out == {"removed": 1, "released_entries": 1}
    assert PersonWorkBlock.query.count() == 0
    entry = WorkJourneyAgendaItem.query.one()
    assert entry.person_block_id is None and entry.manual_override is False
    assert WorkJourneyBlock.query.filter_by(is_active=True).count() == 9  # blocos legados intactos
    assert mig.revert(USER) == {"removed": 0, "released_entries": 0}  # idempotente
