from datetime import date

import pytest
from flask import Flask
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from models import db
from models.process import ProcessInstance
from src.intelligence.tools_domains import process_instance_ops as ops


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[ProcessInstance.__table__])
        db.session.add_all(
            [
                ProcessInstance(id=1, company_id=10, process_id=5, title="Fechamento mensal", status="in_progress", notes="Histórico"),
                ProcessInstance(id=2, company_id=11, process_id=5, title="De outra empresa", status="pending"),
                ProcessInstance(id=3, company_id=10, process_id=5, title="Já concluída", status="completed", notes="ok"),
            ]
        )
        db.session.commit()
        yield app
        db.session.remove()


def _update(instance_id=1, changes=None, company_id=10):
    return ops.update_process_instance(company_id=company_id, instance_id=instance_id, changes=changes)


def _instance(instance_id=1):
    return db.session.get(ProcessInstance, instance_id)


def test_edits_fields_and_records_an_audit_line(app):
    result = _update(changes={"title": "Fechamento de outubro", "priority": "high", "due_date": "2026-10-31", "estimated_hours": "2,5"})
    assert result["success"] is True
    item = _instance()
    assert item.title == "Fechamento de outubro" and item.priority == "high"
    assert item.due_date == date(2026, 10, 31)
    assert float(item.estimated_hours) == 2.5
    assert item.notes.startswith("Histórico\n[MCP update_process_instance] campos: due_date, estimated_hours, priority, title;")


def test_append_notes_keeps_the_history_without_an_audit_line(app):
    result = _update(changes={"append_notes": "Validado em produção."})
    assert result["success"] is True
    notes = _instance().notes
    assert notes.startswith("Histórico\n\n[") and notes.endswith("Validado em produção.")
    assert "update_process_instance" not in notes


def test_cancel_needs_no_approval_and_closes_the_dates(app):
    result = _update(changes={"status": "cancelled", "append_notes": "Duplicada"})
    assert result["success"] is True
    item = _instance()
    assert item.status == "cancelled"
    assert item.actual_end_date == date.today() and item.completed_at is not None


def test_pause_and_resume_track_paused_at(app):
    assert _update(changes={"status": "paused", "pause_reason": "Aguardando fornecedor"})["success"]
    assert _instance().paused_at is not None and _instance().pause_reason == "Aguardando fornecedor"
    assert _update(changes={"status": "in_progress"})["success"]
    assert _instance().paused_at is None and _instance().status == "in_progress"


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_completing_or_failing_must_go_through_close_with_evidence(app, status):
    result = _update(changes={"status": status})
    assert result["success"] is False and "close_process_instance" in result["error"]
    assert _instance().status == "in_progress"


def test_a_closed_instance_only_accepts_notes(app):
    refused = _update(instance_id=3, changes={"title": "Novo"})
    assert refused["success"] is False and "encerrada" in refused["error"]
    assert _instance(3).title == "Já concluída"
    assert _update(instance_id=3, changes={"append_notes": "Registro tardio"})["success"] is True


def test_tenant_isolation_never_edits_another_company(app):
    result = _update(instance_id=2, changes={"title": "Invadido"})
    assert result["success"] is False and "não encontrada" in result["error"]
    assert _instance(2).title == "De outra empresa"


@pytest.mark.parametrize(
    "changes",
    [
        None, {}, {"company_id": 11}, {"status": "inexistente"}, {"priority": "urgentissimo"}, {"title": " "},
        {"due_date": "31/10/2026"}, {"estimated_hours": -1}, {"worked_hours": "abc"}, {"append_notes": "x" * 4001},
        {"notes": "a", "append_notes": "b"},
        {f"f{i}": i for i in range(9)},
    ],
)
def test_invalid_payloads_are_refused_without_touching_the_instance(app, changes):
    before = (_instance().title, _instance().notes, _instance().status)
    result = _update(changes=changes)
    assert result["success"] is False
    assert (_instance().title, _instance().notes, _instance().status) == before


def test_company_id_is_required_when_there_is_no_active_context(app):
    result = ops.update_process_instance(company_id=None, instance_id=1, changes={"title": "x"})
    assert result["success"] is False and "empresa" in result["error"].lower()
