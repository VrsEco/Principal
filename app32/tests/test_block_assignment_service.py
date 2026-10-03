"""Agenda, Fase 2: mover/atribuir/sugerir em blocos (regras da SPEC, secao 5.5)."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, WorkCalendarEvent,
                    WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock, WorkJourneyItem, db)
from services import block_assignment_service as svc
from services.block_assignment_service import AssignmentError, rank_options

MONDAY = date(2026, 10, 5)
TUESDAY = date(2026, 10, 6)
ALL_TYPES = ["manual", "process_instance", "project_task", "meeting"]


@pytest.fixture()
def ctx(monkeypatch):
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, WorkCalendarEvent,
            WorkJourneyBlock, WorkJourneyItem, WorkJourneyAgenda, WorkJourneyAgendaItem)])
        db.session.add_all([Company(id=1, name="A")])
        db.session.add_all([Employee(id=10, company_id=1, name="Ana", status="active")])
        db.session.flush()
        db.session.add_all([
            WorkJourneyBlock(id=1, company_id=1, employee_id=10, name="Manhã", start_time=time(7, 30), end_time=time(10, 0),
                             weekdays_json=[0, 1], block_mode="operational", accepted_item_types=ALL_TYPES),
            WorkJourneyBlock(id=2, company_id=1, employee_id=10, name="Meio", start_time=time(10, 0), end_time=time(12, 0),
                             weekdays_json=[0, 1], block_mode="operational", accepted_item_types=ALL_TYPES),
            WorkJourneyBlock(id=3, company_id=1, employee_id=10, name="Só instâncias", start_time=time(14, 0),
                             end_time=time(16, 0), weekdays_json=[0], block_mode="operational",
                             accepted_item_types=["process_instance"]),
        ])
        db.session.add(Project(id=1, company_id=1, name="P", code_sequence=1))
        db.session.add(Process(id=1, company_id=1, macro_id=1, name="Proc"))
        db.session.flush()
        db.session.add(ProjectTask(id=1, project_id=1, code_sequence=1, what="Tarefa 2h", employee_id=10,
                                   due_date=MONDAY, estimated_hours=2))
        db.session.add(ProcessInstance(id=1, company_id=1, process_id=1, title="Inst", responsible_id=10, due_date=MONDAY,
                                       estimated_hours=1))
        db.session.add(WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=1,
                                       title="Tarefa 2h", estimated_minutes=120, due_date=MONDAY))
        db.session.add(WorkJourneyItem(id=2, company_id=1, employee_id=10, item_type="process_instance", source_id=1,
                                       title="Inst", estimated_minutes=60, due_date=MONDAY))
        db.session.commit()

        def fake_agenda(company_id, employee_id, anchor, scope, force):
            agenda = WorkJourneyAgenda.query.filter_by(company_id=company_id, employee_id=employee_id,
                                                       anchor_date=anchor, scope=scope).first()
            if agenda is None:
                agenda = WorkJourneyAgenda(company_id=company_id, employee_id=employee_id, anchor_date=anchor, scope=scope)
                db.session.add(agenda)
                db.session.flush()
            return agenda

        monkeypatch.setattr(svc, "_get_or_build_agenda", fake_agenda)
        monkeypatch.setattr(svc, "recompute_agenda_summary", lambda agenda, entries=None: None)
        yield app


def test_rank_options_ordem_da_spec():
    opts = [
        {"fits": False, "same_day": True, "date": "2026-10-05", "start_minutes": 100},
        {"fits": True, "same_day": False, "date": "2026-10-06", "start_minutes": 100},
        {"fits": True, "same_day": True, "date": "2026-10-05", "start_minutes": 700},
        {"fits": True, "same_day": True, "date": "2026-10-05", "start_minutes": 300},
    ]
    ranked = rank_options(opts)
    assert [(o["fits"], o["same_day"], o["start_minutes"]) for o in ranked] == [
        (True, True, 300), (True, True, 700), (True, False, 100), (False, True, 100)]


def test_opcoes_respeitam_tipo_e_mostram_antes_e_depois(ctx):
    out = svc.move_options(1, 10, "project_task", 1, today=MONDAY)
    options = out["options"]
    assert len(options) <= 5
    assert all(o["block_id"] != 3 for o in options)  # bloco só de instâncias não aceita atividade
    first = options[0]
    assert first["same_day"] and first["date"] == "2026-10-05"
    assert first["block_id"] == 1 and first["fits"]  # 2h cabem em 2h30
    assert first["before"]["label"] == "Livre 2h30" and first["after"]["label"] == "Livre 30min"
    assert first["changes_due_date"] is False and first["needs_reason"] is False
    other_day = [o for o in options if o["date"] == "2026-10-06"]
    assert other_day and all(o["needs_reason"] and o["changes_due_date"] for o in other_day)


def test_instancia_so_tem_opcoes_no_mesmo_dia(ctx):
    options = svc.move_options(1, 10, "process_instance", 1, today=MONDAY)["options"]
    assert options and all(o["date"] == "2026-10-05" for o in options)
    assert {o["block_id"] for o in options} >= {3}  # bloco só de instâncias aceita


def test_item_sem_estimativa_nao_muda_o_estado(ctx):
    WorkJourneyItem.query.filter_by(id=1).update({"estimated_minutes": 0})
    db.session.commit()
    out = svc.move_options(1, 10, "project_task", 1, today=MONDAY)
    assert out["item"]["without_estimate"] is True
    first = out["options"][0]
    assert first["before"] == first["after"]


def test_atribuir_mesmo_dia_nao_altera_prazo_e_nao_e_sugestao(ctx):
    result = svc.assign_item(1, 10, "project_task", 1, MONDAY, 1)
    assert result["status"] == "assigned"
    entry = WorkJourneyAgendaItem.query.one()
    assert entry.block_id == 1 and entry.manual_override is True
    assert "suggested_by" not in (entry.metadata_json or {})
    assert ProjectTask.query.get(1).due_date == MONDAY


def test_outro_dia_exige_motivo_e_instancia_nao_muda_de_dia(ctx):
    with pytest.raises(AssignmentError, match="motivo"):
        svc.assign_item(1, 10, "project_task", 1, TUESDAY, 1)
    with pytest.raises(AssignmentError, match="mesmo dia"):
        svc.assign_item(1, 10, "process_instance", 1, TUESDAY, 1, reason="x")


def test_outro_dia_aplica_pelo_fluxo_de_prazo(ctx, monkeypatch):
    calls = []

    def fake_flow(**kw):
        calls.append(kw)
        return object(), None, True, None

    from services.project_task_due_date_change_service import ProjectTaskDueDateChangeService
    monkeypatch.setattr(ProjectTaskDueDateChangeService, "create_or_apply_request", staticmethod(fake_flow))
    result = svc.assign_item(1, 10, "project_task", 1, TUESDAY, 1, reason="Reunião surgiu")
    assert result["status"] == "assigned"
    assert calls and calls[0]["reason"] == "Reunião surgiu" and calls[0]["requested_due_date"] == TUESDAY
    assert WorkJourneyItem.query.get(1).due_date == TUESDAY
    assert WorkJourneyAgendaItem.query.one().planned_date == TUESDAY


def test_outro_dia_pendente_nao_move_nada(ctx, monkeypatch):
    from services.project_task_due_date_change_service import ProjectTaskDueDateChangeService
    monkeypatch.setattr(ProjectTaskDueDateChangeService, "create_or_apply_request",
                        staticmethod(lambda **kw: (object(), None, False, None)))
    result = svc.assign_item(1, 10, "project_task", 1, TUESDAY, 1, reason="Preciso adiar")
    assert result["status"] == "pending"
    assert WorkJourneyAgendaItem.query.count() == 0
    assert WorkJourneyItem.query.get(1).due_date == MONDAY


def test_bloco_invalido_ou_tipo_nao_aceito(ctx):
    with pytest.raises(AssignmentError):
        svc.assign_item(1, 10, "project_task", 1, MONDAY, 3)  # bloco só aceita instâncias
    with pytest.raises(AssignmentError):
        svc.assign_item(1, 10, "meeting", 1, MONDAY, 1)


def test_sugerir_respeita_capacidade_e_nao_forca(ctx):
    db.session.add(WorkJourneyItem(id=3, company_id=1, employee_id=10, item_type="project_task", source_id=3,
                                   title="Enorme", estimated_minutes=600, due_date=MONDAY))
    db.session.commit()
    plan = svc.suggest_distribution(1, 10, MONDAY)
    placed = {(p["type"], p["id"]): p["block_id"] for p in plan["proposals"]}
    assert placed[("project_task", 1)] == 1
    assert ("process_instance", 1) in placed
    assert [u["title"] for u in plan["unplaced"]] == ["Enorme"]  # não cabe: fica sem bloco
    assert WorkJourneyAgendaItem.query.count() == 0  # sugerir não grava


def test_aplicar_desfazer_so_remove_o_sugerido(ctx):
    svc.assign_item(1, 10, "project_task", 1, MONDAY, 2)  # a pessoa atribui a tarefa
    applied = svc.apply_suggestions(1, 10, MONDAY)
    assert applied["applied"] == 1  # só a instância estava sem bloco
    suggested = [e for e in WorkJourneyAgendaItem.query.all() if (e.metadata_json or {}).get("suggested_by") == "system"]
    assert len(suggested) == 1 and suggested[0].journey_item_id == 2

    assert svc.undo_suggestions(1, 10, MONDAY) == {"removed": 1}
    remaining = WorkJourneyAgendaItem.query.all()
    assert [e.journey_item_id for e in remaining] == [1]  # atribuição da pessoa preservada


def test_aceitar_sugestao_vira_atribuicao_da_pessoa(ctx):
    svc.apply_suggestions(1, 10, MONDAY)
    assert svc.accept_suggestions(1, 10, MONDAY)["accepted"] == 2
    assert svc.undo_suggestions(1, 10, MONDAY) == {"removed": 0}
    assert WorkJourneyAgendaItem.query.count() == 2
