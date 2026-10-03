"""Agenda, Fase 2: politica de estimativa (1 h nas novas, sem 15 min inventados) e Estimar em lote."""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import date, time
from decimal import Decimal

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, Process, ProcessInstance, Project, ProjectTask, WorkJourneyAgenda,
                    WorkJourneyAgendaItem, WorkJourneyBlock, WorkJourneyItem, db)
from services import work_journey_agenda_engine as engine
from services.estimate_batch_service import (EstimateError, list_without_estimate, save_estimates, valid_minutes)

MONDAY = date(2026, 10, 5)


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Process, ProcessInstance, Project, ProjectTask, WorkJourneyBlock, WorkJourneyItem,
            WorkJourneyAgenda, WorkJourneyAgendaItem)])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        db.session.add_all([
            Employee(id=10, company_id=1, name="Ana", status="active"),
            Employee(id=11, company_id=1, name="Bia", status="active"),
            Employee(id=20, company_id=2, name="Caio", status="active"),
        ])
        db.session.add_all([
            Project(id=1, company_id=1, name="Projeto A", code_sequence=1),
            Project(id=2, company_id=2, name="Projeto B", code_sequence=1),
            Process(id=1, company_id=1, macro_id=1, name="Processo X"),
        ])
        db.session.flush()
        yield app


def _task(**kw):
    task = ProjectTask(project_id=kw.pop("project_id", 1), code_sequence=kw.pop("seq"), what=kw.pop("what", "T"), **kw)
    db.session.add(task)
    db.session.flush()
    return task


def test_novas_atividades_e_instancias_nascem_com_30min(ctx):
    sem = _task(seq=1, employee_id=10)
    zero = _task(seq=2, employee_id=10, estimated_hours=0)
    informado = _task(seq=3, employee_id=10, estimated_hours=Decimal("2"))
    inst = ProcessInstance(id=1, company_id=1, process_id=1, title="I", responsible_id=10)
    inst_info = ProcessInstance(id=2, company_id=1, process_id=1, title="J", responsible_id=10, estimated_hours=Decimal("3"))
    db.session.add_all([inst, inst_info])
    db.session.flush()
    assert sem.estimated_hours == Decimal("0.50")
    assert zero.estimated_hours == Decimal("0.50")
    assert informado.estimated_hours == Decimal("2")
    assert inst.estimated_hours == Decimal("0.50")
    assert inst_info.estimated_hours == Decimal("3")


def test_registro_existente_nao_e_alterado_no_update(ctx):
    task = _task(seq=1, employee_id=10)
    db.session.commit()
    ProjectTask.query.filter_by(id=task.id).update({"estimated_hours": 0})
    db.session.commit()
    task.what = "Renomeada"
    db.session.commit()
    assert (ProjectTask.query.get(task.id).estimated_hours or 0) == 0  # a regra so vale no INSERT


def _legacy(seq, **kw):
    task = _task(seq=seq, **kw)
    ProjectTask.query.filter_by(id=task.id).update({"estimated_hours": 0})
    db.session.flush()
    return task


def test_listagem_ordena_por_prazo_e_isola_empresa(ctx):
    _legacy(1, employee_id=10, what="tarde", due_date=date(2026, 12, 1))
    _legacy(2, employee_id=10, what="cedo", due_date=date(2026, 10, 1))
    _legacy(3, employee_id=10, what="sem prazo")
    _legacy(4, employee_id=10, what="concluida", status="completed", due_date=date(2026, 9, 1))
    _legacy(5, employee_id=11, what="da Bia", due_date=date(2026, 9, 5))
    _legacy(6, project_id=2, employee_id=20, what="outra empresa", due_date=date(2026, 9, 5))
    db.session.add(ProcessInstance(id=1, company_id=1, process_id=1, title="inst", responsible_id=10, due_date=date(2026, 11, 1)))
    db.session.flush()
    ProcessInstance.query.update({"estimated_hours": 0})
    db.session.commit()

    out = list_without_estimate(1, employee_id=10)
    assert [i["title"] for i in out["items"]] == ["cedo", "inst", "tarde", "sem prazo"]
    assert out["total"] == 4
    assert out["shortcuts"] == [30, 60, 120, 240]
    only_tasks = list_without_estimate(1, employee_id=10, types=["project_task"])
    assert {i["type"] for i in only_tasks["items"]} == {"project_task"}
    assert "outra empresa" not in [i["title"] for i in list_without_estimate(1)["items"]]
    with pytest.raises(EstimateError):
        list_without_estimate(1, employee_id=20)  # colaborador de outra empresa


def test_valida_minutos():
    assert valid_minutes(30) == 30
    for bad in (0, 10, 20, 1500, "x", None):
        with pytest.raises(EstimateError):
            valid_minutes(bad)


def test_salvar_em_lote_respeita_permissao_e_espelha_na_jornada(ctx):
    ok = _legacy(1, employee_id=10)
    negada = _legacy(2, employee_id=10)
    fora = _legacy(3, project_id=2, employee_id=20)
    inst = ProcessInstance(id=1, company_id=1, process_id=1, title="inst", responsible_id=10)
    db.session.add(inst)
    db.session.flush()
    ProcessInstance.query.update({"estimated_hours": 0})
    db.session.add(WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=ok.id,
                                   title="espelho", estimated_minutes=0))
    db.session.commit()

    result = save_estimates(
        1,
        [
            {"type": "project_task", "id": ok.id, "minutes": 120},
            {"type": "project_task", "id": negada.id, "minutes": 60},
            {"type": "project_task", "id": fora.id, "minutes": 60},
            {"type": "process_instance", "id": 1, "minutes": 30},
            {"type": "project_task", "id": ok.id, "minutes": 240},  # repetido: ignorado
            {"type": "project_task", "id": 999, "minutes": 60},
            {"type": "project_task", "id": ok.id + 100, "minutes": 7},
            {"type": "meeting", "id": 1, "minutes": 60},
        ],
        can_edit_task=lambda task, project: task.id != negada.id,
        can_edit_instance=lambda instance: True,
    )
    assert set(result["saved"]) == {f"project_task:{ok.id}", "process_instance:1"}
    reasons = {s["key"]: s["reason"] for s in result["skipped"]}
    assert "Sem permissão" in reasons[f"project_task:{negada.id}"]
    assert f"project_task:{fora.id}" in reasons  # outra empresa: nao encontrada
    assert ProjectTask.query.get(ok.id).estimated_hours == Decimal(2)
    assert (ProjectTask.query.get(negada.id).estimated_hours or 0) == 0
    assert ProcessInstance.query.get(1).estimated_hours == Decimal("0.5")
    assert WorkJourneyItem.query.get(1).estimated_minutes == 120

    with pytest.raises(EstimateError):
        save_estimates(1, [], can_edit_task=lambda *_: True, can_edit_instance=lambda *_: True)


def test_motor_nao_inventa_15_minutos(ctx):
    block = WorkJourneyBlock(id=1, company_id=1, employee_id=10, name="B", start_time=time(8, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=[])
    agenda = WorkJourneyAgenda(id=1, company_id=1, employee_id=10, anchor_date=MONDAY, scope="day")
    item = WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", title="Sem estimativa",
                           estimated_minutes=0, due_date=MONDAY)
    db.session.add_all([block, agenda, item])
    db.session.commit()
    entries = engine.allocate_item(item, agenda, {MONDAY: [block]}, defaultdict(int), MONDAY, MONDAY)
    assert entries and all(e.allocated_minutes == 0 for e in entries)
