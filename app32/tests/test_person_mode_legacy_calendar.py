"""Etapa 4c: Calendario Operacional antigo, motor e mover respeitam os blocos da pessoa (e nao mudam para quem nao migrou)."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, PersonWorkBlock, ProcessInstance, ProcessInstanceExecution, WorkCalendarEvent,
                    WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock, WorkJourneyItem, db)
from services import work_journey_agenda_service as svc
from services.effective_blocks_service import PersonBlockProxy, PersonModeView, person_mode_user
from services.work_journey_base import WorkJourneyError

MONDAY = date(2026, 10, 5)
ALL = ["manual", "process_instance", "project_task", "meeting"]


@pytest.fixture()
def ctx(monkeypatch):
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, WorkJourneyBlock, WorkJourneyItem, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkCalendarEvent,
            PersonWorkBlock, ProcessInstance, ProcessInstanceExecution)])
        db.session.add(Company(id=1, name="A"))
        db.session.add_all([
            Employee(id=10, company_id=1, user_id=1, name="Migrada", status="active"),
            Employee(id=11, company_id=1, user_id=2, name="Legada", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            PersonWorkBlock(id=1, user_id=1, name="Manhã da pessoa", start_time=time(8, 0), end_time=time(12, 0),
                            weekdays_json=[0], block_mode="operational", preferred_item_types=[]),
            WorkJourneyBlock(id=1, company_id=1, employee_id=10, name="Legado dela", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=ALL),
            WorkJourneyBlock(id=2, company_id=1, employee_id=11, name="Legado da outra", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=ALL),
        ])
        db.session.add_all([
            WorkJourneyAgenda(id=1, company_id=1, employee_id=10, anchor_date=MONDAY, scope="day"),
            WorkJourneyAgenda(id=2, company_id=1, employee_id=11, anchor_date=MONDAY, scope="day"),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=1, title="Item A",
                            estimated_minutes=60, due_date=MONDAY),
            WorkJourneyItem(id=2, company_id=1, employee_id=10, item_type="project_task", source_id=2, title="Item B",
                            estimated_minutes=30, due_date=MONDAY),
            WorkJourneyItem(id=3, company_id=1, employee_id=11, item_type="project_task", source_id=3, title="Item C",
                            estimated_minutes=60, due_date=MONDAY),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyAgendaItem(id=1, agenda_id=1, company_id=1, employee_id=10, journey_item_id=1, person_block_id=1,
                                  planned_date=MONDAY, allocated_minutes=60, manual_override=True),
            WorkJourneyAgendaItem(id=2, agenda_id=1, company_id=1, employee_id=10, journey_item_id=2, block_id=1,  # antiga, legada
                                  planned_date=MONDAY, allocated_minutes=30),
            WorkJourneyAgendaItem(id=3, agenda_id=2, company_id=1, employee_id=11, journey_item_id=3, block_id=2,
                                  planned_date=MONDAY, allocated_minutes=60),
        ])
        db.session.commit()
        yield app


def _agenda(employee_id):
    agenda = WorkJourneyAgenda.query.filter_by(employee_id=employee_id).one()
    return svc._serialize(agenda, Employee.query.get(employee_id))


def _day(payload):
    return next(d for d in payload["days"] if d["date"] == MONDAY.isoformat())


def test_usuario_migrado_ve_os_blocos_da_pessoa_no_calendario_antigo(ctx):
    payload = _agenda(10)
    assert payload["person_mode"] is True and payload["blocks_source"] == "person"
    day = _day(payload)
    assert [b["name"] for b in day["blocks"]] == ["Manhã da pessoa"]
    assert [i["title"] for i in day["blocks"][0]["items"]] == ["Item A"]  # entrada com person_block_id
    assert day["blocks"][0]["items"][0]["block_name"] == "Manhã da pessoa"
    # a entrada antiga (só com block_id legado) não é atribuída a um bloco da pessoa: aparece sem bloco
    assert [i["title"] for i in day["unassigned_items"]] == ["Item B"]


def test_usuario_nao_migrado_continua_exatamente_como_antes(ctx):
    payload = _agenda(11)
    assert payload["person_mode"] is False and payload["blocks_source"] == "legacy"
    day = _day(payload)
    assert [b["name"] for b in day["blocks"]] == ["Legado da outra"]
    assert [i["title"] for i in day["blocks"][0]["items"]] == ["Item C"]
    assert day["unassigned_items"] == []


def test_mover_no_calendario_antigo_e_bloqueado_para_migrado(ctx):
    payload = {"target_date": MONDAY, "target_block_id": 1}
    with pytest.raises(WorkJourneyError, match="blocos da pessoa"):
        svc.move_work_journey_agenda_item(1, 10, MONDAY, "day", 1, payload)


def test_person_mode_user(ctx):
    assert person_mode_user(Employee.query.get(10)) == 1
    assert person_mode_user(Employee.query.get(11)) is None
    assert person_mode_user(None) is None


def test_visoes_nao_alteram_as_entidades(ctx):
    entry = WorkJourneyAgendaItem.query.get(1)
    proxies = {1: PersonBlockProxy(PersonWorkBlock.query.get(1))}
    view = PersonModeView(entry, proxies)
    assert view.block_id == 1 and view.block.name == "Manhã da pessoa" and view.journey_item_id == 1
    assert entry.block_id is None and entry.person_block_id == 1  # a entidade segue intacta
    db.session.flush()
    assert WorkJourneyAgendaItem.query.get(1).block_id is None  # nada foi gravado pelo proxy


def test_motor_nao_aloca_em_bloco_por_empresa_para_migrado(ctx, monkeypatch):
    # Regenerar a agenda de quem migrou: itens sem atribuição manual ficam sem bloco; manual da pessoa é preservado.
    monkeypatch.setattr(svc, "sync_work_journey_items", lambda *a, **k: None)
    monkeypatch.setattr(svc, "load_source_items", lambda company_id, employee_id, a, b: WorkJourneyItem.query.filter_by(employee_id=employee_id).all())
    monkeypatch.setattr(svc, "recompute_agenda_summary", lambda agenda, entries=None: None)
    agenda = WorkJourneyAgenda.query.filter_by(employee_id=10).one()
    svc._build_agenda_snapshot(agenda)
    db.session.commit()
    rows = {r.journey_item_id: r for r in WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda.id).all()}
    assert rows[1].person_block_id == 1 and rows[1].manual_override is True  # escolha da pessoa preservada
    assert rows[2].block_id is None and rows[2].person_block_id is None  # sem sugestão em bloco por empresa
    assert all(r.block_id is None for r in rows.values())


def test_motor_segue_alocando_para_quem_nao_migrou(ctx, monkeypatch):
    monkeypatch.setattr(svc, "sync_work_journey_items", lambda *a, **k: None)
    monkeypatch.setattr(svc, "load_source_items", lambda company_id, employee_id, a, b: WorkJourneyItem.query.filter_by(employee_id=employee_id).all())
    monkeypatch.setattr(svc, "recompute_agenda_summary", lambda agenda, entries=None: None)
    agenda = WorkJourneyAgenda.query.filter_by(employee_id=11).one()
    svc._build_agenda_snapshot(agenda)
    db.session.commit()
    entry = WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda.id, journey_item_id=3).one()
    assert entry.block_id == 2  # comportamento legado: aloca no bloco por empresa


def test_extras_aditivos_so_aparecem_para_quem_migrou(ctx):
    from services.effective_blocks_service import person_mode_extras

    migrated = person_mode_extras(1, 10)
    assert migrated["person_mode"] is True and "Meus blocos" in migrated["person_mode_note"]
    assert [b["name"] for b in migrated["person_blocks"]] == ["Manhã da pessoa"]
    assert person_mode_extras(1, 11) == {}  # contrato intacto para quem não migrou
    assert person_mode_extras(1, None) == {}
    assert "person_blocks" not in person_mode_extras(1, 10, with_blocks=False)
