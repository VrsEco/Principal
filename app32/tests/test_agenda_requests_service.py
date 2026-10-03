"""Agenda, Fase 5: ausencias e transferencias com escopo (privacidade) e contagem de pendencias."""
from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Company, Employee, WorkJourneyAbsenceRequest, WorkJourneyItem, WorkJourneyTransferRequest, db
from services.agenda_requests_service import list_requests


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, Employee, WorkJourneyItem, WorkJourneyAbsenceRequest, WorkJourneyTransferRequest)])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        db.session.add_all([
            Employee(id=10, company_id=1, name="Ana", status="active"),
            Employee(id=11, company_id=1, name="Bia", status="active"),
            Employee(id=12, company_id=1, name="Caio", status="active"),
            Employee(id=20, company_id=2, name="Outra empresa", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyItem(id=1, company_id=1, employee_id=10, item_type="manual", title="Tarefa da Ana"),
            WorkJourneyItem(id=2, company_id=2, employee_id=20, item_type="manual", title="SEGREDO OUTRA EMPRESA"),
        ])
        db.session.flush()
        db.session.add_all([
            WorkJourneyAbsenceRequest(id=1, company_id=1, employee_id=10, absence_type="vacation", start_date=date(2026, 11, 1),
                                      end_date=date(2026, 11, 10), reason="Férias da Ana", status="pending"),
            WorkJourneyAbsenceRequest(id=2, company_id=1, employee_id=11, absence_type="medical_leave", start_date=date(2026, 10, 6),
                                      end_date=date(2026, 10, 7), reason="ATESTADO DA BIA", status="approved"),
            WorkJourneyAbsenceRequest(id=3, company_id=2, employee_id=20, absence_type="absence", start_date=date(2026, 10, 6),
                                      end_date=date(2026, 10, 6), reason="SEGREDO OUTRA EMPRESA", status="pending"),
            WorkJourneyTransferRequest(id=1, company_id=1, item_id=1, from_employee_id=10, to_employee_id=12, reason="Sobrecarga", status="pending"),
            WorkJourneyTransferRequest(id=2, company_id=1, item_id=1, from_employee_id=11, to_employee_id=12, reason="Outra", status="approved"),
            WorkJourneyTransferRequest(id=3, company_id=2, item_id=2, from_employee_id=20, to_employee_id=20, reason="x", status="pending"),
        ])
        db.session.commit()
        yield app


def test_gestor_ve_a_empresa_toda_e_so_dela(ctx):
    out = list_requests(1, viewer_employee_id=12, is_manager=True)
    assert {a["id"] for a in out["absences"]} == {1, 2} and {t["id"] for t in out["transfers"]} == {1, 2}
    assert out["pending_total"] == 2  # 1 ausência + 1 transferência pendentes (da empresa 1)
    assert out["is_manager"] is True
    assert all(a["can_approve"] == (a["status"] == "pending") for a in out["absences"])
    assert out["absences"][0]["employee_name"] in {"Ana", "Bia"} and out["transfers"][0]["item_title"] == "Tarefa da Ana"


def test_colaborador_so_ve_as_proprias_ausencias_e_transferencias(ctx):
    ana = list_requests(1, viewer_employee_id=10, is_manager=False)
    assert [a["id"] for a in ana["absences"]] == [1]
    assert [t["id"] for t in ana["transfers"]] == [1]
    assert ana["pending_total"] == 0 and all(not a["can_approve"] for a in ana["absences"])
    bia = list_requests(1, viewer_employee_id=11, is_manager=False)
    assert [a["id"] for a in bia["absences"]] == [2] and [t["id"] for t in bia["transfers"]] == [2]
    # destino da transferência também enxerga
    caio = list_requests(1, viewer_employee_id=12, is_manager=False)
    assert caio["absences"] == [] and {t["id"] for t in caio["transfers"]} == {1, 2}


def test_sem_colaborador_vinculado_e_nao_gestor_nao_ve_nada(ctx):
    assert list_requests(1, viewer_employee_id=None, is_manager=False) == {"absences": [], "transfers": [], "pending_total": 0, "is_manager": False}


def test_nada_de_outra_empresa_vaza(ctx):
    import json

    for viewer, manager in ((12, True), (10, False)):
        raw = json.dumps(list_requests(1, viewer_employee_id=viewer, is_manager=manager), ensure_ascii=False)
        assert "SEGREDO OUTRA EMPRESA" not in raw and "Outra empresa" not in raw
    other = list_requests(2, viewer_employee_id=20, is_manager=True)
    assert "ATESTADO DA BIA" not in json.dumps(other, ensure_ascii=False)


def test_motivo_do_atestado_nao_chega_a_outro_colaborador(ctx):
    import json

    assert "ATESTADO DA BIA" not in json.dumps(list_requests(1, viewer_employee_id=10, is_manager=False), ensure_ascii=False)
    assert "ATESTADO DA BIA" in json.dumps(list_requests(1, viewer_employee_id=11, is_manager=False), ensure_ascii=False)
