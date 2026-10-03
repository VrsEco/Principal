"""Agenda, Fase 3: modo pessoa (um dia unico entre empresas), adaptador e privacidade."""
from __future__ import annotations

import os
import sys
from datetime import date, time

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, Meeting, PersonWorkBlock, Process, ProcessInstance, Project, ProjectTask,
                    WorkCalendarEvent, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock, WorkJourneyItem, db)
from services import block_assignment_service as assign
from services.agenda_block_view_service import build_block_view
from services.effective_blocks_service import get_effective_blocks
from services.work_journey_agenda_service import _preserve_manual_entries

MONDAY = date(2026, 10, 5)
USER = 1
OTHER_USER = 2


@pytest.fixture()
def ctx(monkeypatch):
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, WorkCalendarEvent,
            WorkJourneyBlock, WorkJourneyItem, WorkJourneyAgenda, WorkJourneyAgendaItem, PersonWorkBlock)])
        db.session.add_all([Company(id=1, name="Empresa A"), Company(id=2, name="Empresa B")])
        db.session.add_all([
            Employee(id=10, company_id=1, user_id=USER, name="Ana", status="active"),
            Employee(id=20, company_id=2, user_id=USER, name="Ana B", status="active"),
            Employee(id=30, company_id=1, user_id=OTHER_USER, name="Caio", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            PersonWorkBlock(id=1, user_id=USER, name="Manhã", start_time=time(8, 0), end_time=time(10, 0),
                            weekdays_json=[0, 1], block_mode="operational", preferred_item_types=["project_task"], order_index=1),
            PersonWorkBlock(id=2, user_id=USER, name="Tarde", start_time=time(14, 0), end_time=time(16, 0),
                            weekdays_json=[0], block_mode="operational", preferred_item_types=[], order_index=2),
            PersonWorkBlock(id=3, user_id=OTHER_USER, name="Do Caio", start_time=time(8, 0), end_time=time(9, 0),
                            weekdays_json=[0], block_mode="operational", preferred_item_types=[], order_index=1),
            WorkJourneyBlock(id=1, company_id=1, employee_id=10, name="Legado A", start_time=time(9, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=["project_task", "process_instance"]),
            WorkJourneyBlock(id=2, company_id=1, employee_id=30, name="Legado Caio", start_time=time(9, 0), end_time=time(12, 0),
                             weekdays_json=[0], block_mode="operational", accepted_item_types=["project_task"]),
        ])
        db.session.add_all([Project(id=1, company_id=1, name="PA", code_sequence=1), Project(id=2, company_id=2, name="PB", code_sequence=1)])
        db.session.flush()
        db.session.add_all([
            ProjectTask(id=1, project_id=1, code_sequence=1, what="Tarefa A 2h", employee_id=10, due_date=MONDAY, estimated_hours=2),
            ProjectTask(id=2, project_id=2, code_sequence=1, what="Tarefa B 1h", employee_id=20, due_date=MONDAY, estimated_hours=1),
            WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="project_task", source_id=1, title="Tarefa A 2h",
                            estimated_minutes=120, due_date=MONDAY),
            WorkJourneyItem(id=2, company_id=2, employee_id=20, item_type="project_task", source_id=2, title="Tarefa B 1h",
                            estimated_minutes=60, due_date=MONDAY),
        ])
        db.session.commit()

        def fake_agenda(company_id, employee_id, anchor, scope, force):
            agenda = WorkJourneyAgenda.query.filter_by(company_id=company_id, employee_id=employee_id,
                                                       anchor_date=anchor, scope=scope).first()
            if agenda is None:
                agenda = WorkJourneyAgenda(company_id=company_id, employee_id=employee_id, anchor_date=anchor, scope=scope)
                db.session.add(agenda)
                db.session.flush()
            return agenda

        monkeypatch.setattr(assign, "_get_or_build_agenda", fake_agenda)
        monkeypatch.setattr(assign, "recompute_agenda_summary", lambda agenda, entries=None: None)
        yield app


def _day(view):
    return view["days"][0]


def test_adaptador_escolhe_pessoa_ou_legado(ctx):
    person = get_effective_blocks(1, 10)
    assert person["source"] == "person" and [b["name"] for b in person["blocks"]] == ["Manhã", "Tarde"]
    assert person["blocks"][0]["accepted_types"] is None  # aceita qualquer item
    PersonWorkBlock.query.filter_by(user_id=USER).delete()
    db.session.commit()
    legacy = get_effective_blocks(1, 10)
    assert legacy["source"] == "legacy" and [b["name"] for b in legacy["blocks"]] == ["Legado A"]


def test_dia_unico_agrega_as_empresas_do_proprio_usuario(ctx):
    assign.assign_item(1, 10, "project_task", 1, MONDAY, 1, viewer_user_id=USER)
    assign.assign_item(2, 20, "project_task", 2, MONDAY, 1, viewer_user_id=USER)  # outra empresa, mesmo bloco da pessoa
    view = build_block_view(1, 10, MONDAY, MONDAY, viewer_user_id=USER)
    assert view["source"] == "person" and view["companies"] == 2
    morning = _day(view)["blocks"][0]
    assert morning["name"] == "Manhã" and morning["consumed_minutes"] == 180  # 2h + 1h
    assert morning["signal"]["label"] == "Acima 1h"  # 3h em 2h
    assert {i["company"] for i in morning["items"]} == {"Empresa A", "Empresa B"}
    entry = WorkJourneyAgendaItem.query.filter_by(journey_item_id=1).one()
    assert entry.person_block_id == 1 and entry.block_id is None and entry.manual_override is True


def test_vinculo_ativo_sem_permissao_na_empresa_nao_entra_no_dia_unico(ctx):
    assign.assign_item(1, 10, "project_task", 1, MONDAY, 1, viewer_user_id=USER)
    assign.assign_item(2, 20, "project_task", 2, MONDAY, 1, viewer_user_id=USER)
    # a pessoa ainda tem vínculo ativo na empresa 2, mas perdeu a permissão de ver a agenda de lá
    view = build_block_view(1, 10, MONDAY, MONDAY, viewer_user_id=USER, allowed_company_ids={1})
    morning = _day(view)["blocks"][0]
    assert view["companies"] == 1 and morning["consumed_minutes"] == 120  # só a empresa 1
    assert all(i.get("company") is None for i in morning["items"])  # sem rótulo de empresa quando é uma só
    full = build_block_view(1, 10, MONDAY, MONDAY, viewer_user_id=USER, allowed_company_ids={1, 2})
    assert _day(full)["blocks"][0]["consumed_minutes"] == 180
    # sugestão e desfazer também respeitam o conjunto permitido
    plan = assign.suggest_distribution(1, 10, MONDAY, viewer_user_id=USER, allowed_company_ids={1})
    assert all(p["title"] != "Tarefa B 1h" for p in plan["proposals"])


def test_gestor_nao_ve_o_dia_unico_nem_itens_de_outra_empresa(ctx):
    assign.assign_item(2, 20, "project_task", 2, MONDAY, 1, viewer_user_id=USER)
    # sem viewer (ou com outro usuário) a visão é a legada da empresa, sem dados da outra empresa
    for viewer in (None, 99, OTHER_USER):
        view = build_block_view(1, 10, MONDAY, MONDAY, viewer_user_id=viewer)
        assert view["source"] == "legacy"
        assert [b["name"] for b in _day(view)["blocks"]] == ["Legado A"]
        assert all(i["title"] != "Tarefa B 1h" for b in _day(view)["blocks"] for i in b["items"])


def test_blocos_de_um_usuario_nao_afetam_outro(ctx):
    view = build_block_view(1, 30, MONDAY, MONDAY, viewer_user_id=OTHER_USER)
    assert view["source"] == "person" and [b["name"] for b in _day(view)["blocks"]] == ["Do Caio"]
    with pytest.raises(assign.AssignmentError):
        assign.assign_item(1, 30, "project_task", 1, MONDAY, 1, viewer_user_id=OTHER_USER)  # item/bloco de outro usuário


def test_atribuir_em_bloco_da_pessoa_valida_dia_e_dono(ctx):
    with pytest.raises(assign.AssignmentError):
        assign.assign_item(1, 10, "project_task", 1, MONDAY, 3, viewer_user_id=USER)  # bloco do Caio
    with pytest.raises(assign.AssignmentError):
        assign.assign_item(1, 10, "project_task", 1, MONDAY, 2 + 100, viewer_user_id=USER)  # inexistente
    PersonWorkBlock.query.filter_by(id=1).update({"weekdays_json": [3]})
    db.session.commit()
    with pytest.raises(assign.AssignmentError, match="dia selecionado"):
        assign.assign_item(1, 10, "project_task", 1, MONDAY, 1, viewer_user_id=USER)


def test_opcoes_de_mover_usam_blocos_da_pessoa(ctx):
    out = assign.move_options(1, 10, "project_task", 1, today=MONDAY, viewer_user_id=USER)
    assert out["source"] == "person"
    assert {o["block_name"] for o in out["options"]} <= {"Manhã", "Tarde"}
    first = out["options"][0]
    assert first["same_day"] and first["fits"]
    assert any(o["preferred"] for o in out["options"] if o["block_name"] == "Manhã")  # prefere atividade


def test_sugestao_percorre_as_empresas_e_desfaz_so_o_sugerido(ctx):
    assign.assign_item(1, 10, "project_task", 1, MONDAY, 2, viewer_user_id=USER)  # a pessoa atribui a tarefa A
    plan = assign.suggest_distribution(1, 10, MONDAY, viewer_user_id=USER)
    assert [(p["title"], p["block_name"]) for p in plan["proposals"]] == [("Tarefa B 1h", "Manhã")]
    assert all(not k.startswith("_") for k in plan["proposals"][0])  # sem campos internos
    assert assign.apply_suggestions(1, 10, MONDAY, viewer_user_id=USER)["applied"] == 1
    assert build_block_view(1, 10, MONDAY, MONDAY, viewer_user_id=USER)["days"][0]["day"]["suggested_count"] == 1
    assert assign.undo_suggestions(1, 10, MONDAY, viewer_user_id=USER) == {"removed": 1}
    assert [e.journey_item_id for e in WorkJourneyAgendaItem.query.all()] == [1]  # atribuição da pessoa preservada


def test_regenerar_agenda_preserva_person_block_id(ctx):
    agenda = WorkJourneyAgenda(id=50, company_id=1, employee_id=10, anchor_date=MONDAY, scope="day")
    db.session.add(agenda)
    db.session.flush()
    db.session.add(WorkJourneyAgendaItem(agenda_id=50, company_id=1, employee_id=10, journey_item_id=1, person_block_id=2,
                                         planned_date=MONDAY, allocated_minutes=120, manual_override=True))
    db.session.commit()
    kept = _preserve_manual_entries(agenda)
    assert kept[1][0].person_block_id == 2
