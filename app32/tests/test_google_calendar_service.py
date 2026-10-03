"""Google Calendar: criptografia de tokens, corpo do evento e sincronização idempotente (API do Google simulada)."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime

import pytest
from cryptography.fernet import Fernet
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (Company, Employee, GoogleCalendarConnection, GoogleCalendarEventLink, Meeting, Process,
                    ProcessInstance, Project, ProjectTask, User, db)
from services import google_calendar_service as svc

START, END = date(2026, 10, 1), date(2026, 10, 31)


class FakeGoogle:
    def __init__(self, conn=None):
        self.events, self.calls, self.seq, self.remote = {}, [], 0, []

    def insert(self, body):
        self.seq += 1
        self.events[f"g{self.seq}"] = body
        self.calls.append("insert")
        return {"id": f"g{self.seq}"}

    def patch(self, event_id, body):
        self.calls.append("patch")
        if event_id not in self.events:
            return 404
        self.events[event_id] = body
        return 200

    def list_events(self, params):
        self.calls.append("list")
        return self.remote

    def delete(self, event_id):
        self.calls.append("delete")
        self.events.pop(event_id, None)
        return True


@pytest.fixture()
def ctx(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://app.test/agenda/google/callback")
    monkeypatch.setenv("GOOGLE_CALENDAR_TOKEN_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("APP_PUBLIC_BASE_URL", "https://app.test")
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True,
                      SECRET_KEY="k")
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (
            Company, User, Employee, Meeting, Process, ProcessInstance, Project, ProjectTask,
            GoogleCalendarConnection, GoogleCalendarEventLink)])
        db.session.add(Company(id=1, name="A"))
        db.session.add(Employee(id=10, company_id=1, name="Ana", status="active"))
        db.session.add(Project(id=1, company_id=1, name="Proj"))
        db.session.flush()
        db.session.add(Meeting(id=1, company_id=1, title="Reunião", scheduled_date=date(2026, 10, 5),
                               scheduled_time="14:30", planned_duration_minutes=45,
                               participants_json='[{"id": 10}]'))
        db.session.add(ProjectTask(id=1, project_id=1, code_sequence=1, what="Tarefa", employee_id=10,
                                   due_date=date(2026, 10, 6)))
        db.session.add(Company(id=2, name="B"))
        db.session.add(Employee(id=20, company_id=2, name="Ana B", status="active"))
        db.session.add(Project(id=2, company_id=2, name="Proj B"))
        db.session.flush()
        db.session.add(ProjectTask(id=10, project_id=2, code_sequence=1, what="Tarefa B", employee_id=20,
                                   due_date=date(2026, 10, 7)))
        conn = GoogleCalendarConnection(user_id=1, refresh_token_enc=svc._encrypt("refresh"),
                                        access_token_enc=svc._encrypt("access"),
                                        token_expires_at=datetime(2099, 1, 1))
        db.session.add(conn)
        db.session.commit()
        fake = FakeGoogle()
        monkeypatch.setattr(svc, "_GoogleSession", lambda c: fake)
        yield app, fake
        db.session.remove()


def test_token_encryption_roundtrip_and_ciphertext(ctx):
    enc = svc._encrypt("abc")
    assert enc != "abc" and svc._decrypt(enc) == "abc"


def test_event_body_timed_and_all_day(ctx):
    timed = svc._event_body(1, {"type": "meeting", "id": 1, "title": "R", "date": "2026-10-05", "time": "14:30",
                                "all_day": False, "duration_minutes": 45, "status": "draft", "url": "/x"})
    assert timed["start"]["dateTime"] == "2026-10-05T14:30:00" and timed["end"]["dateTime"] == "2026-10-05T15:15:00"
    assert "https://app.test/x" in timed["description"]
    allday = svc._event_body(1, {"type": "project_task", "id": 2, "title": "T", "date": "2026-10-31",
                                 "time": None, "all_day": True, "closed": True})
    assert allday["start"] == {"date": "2026-10-31"} and allday["end"] == {"date": "2026-11-01"}
    assert allday["summary"].startswith("✔ [Atividade]")


def test_sync_is_idempotent_updates_and_removes(ctx):
    _, fake = ctx
    first = svc.sync_range(1, [(1, 10)], START, END)
    assert first["created"] == 2 and fake.calls == ["insert", "insert"]
    assert svc.sync_range(1, [(1, 10)], START, END)["unchanged"] == 2

    ProjectTask.query.get(1).what = "Tarefa renomeada"
    db.session.commit()
    assert svc.sync_range(1, [(1, 10)], START, END)["updated"] == 1

    ProjectTask.query.get(1).is_deleted = True
    db.session.commit()
    assert svc.sync_range(1, [(1, 10)], START, END)["deleted"] == 1
    assert GoogleCalendarEventLink.query.count() == 1


def test_sync_recreates_event_deleted_in_google(ctx):
    _, fake = ctx
    svc.sync_range(1, [(1, 10)], START, END)
    fake.events.clear()
    ProjectTask.query.get(1).what = "Mudou"
    db.session.commit()
    stats = svc.sync_range(1, [(1, 10)], START, END)
    assert stats["created"] == 1 and stats["failed"] == 0


def test_state_rejects_tampering_and_requires_connection(ctx):
    app, _ = ctx
    good = svc.build_auth_url(7, "nonce").split("state=")[1].split("&")[0]
    from urllib.parse import unquote
    assert svc.parse_state(unquote(good))["u"] == 7
    with pytest.raises(svc.GoogleCalendarError):
        svc.parse_state(unquote(good) + "x")
    GoogleCalendarConnection.query.delete()
    db.session.commit()
    with pytest.raises(svc.GoogleCalendarError):
        svc.sync_range(1, [(1, 10)], START, END)


def test_list_google_events_normalizes_and_skips_versus_origin(ctx):
    _, fake = ctx
    fake.remote = [
        {"id": "a", "summary": "Dentista", "status": "confirmed", "htmlLink": "https://g/a",
         "start": {"dateTime": "2026-10-08T17:00:00Z"}, "end": {"dateTime": "2026-10-08T18:30:00Z"}},
        {"id": "b", "summary": "Viagem", "start": {"date": "2026-10-10"}, "end": {"date": "2026-10-13"}},
        {"id": "c", "summary": "Enviado pelo Versus", "start": {"date": "2026-10-09"}, "end": {"date": "2026-10-10"},
         "extendedProperties": {"private": {"versus_source": "meeting:1"}}},
        {"id": "d", "summary": "Cancelado", "status": "cancelled", "start": {"date": "2026-10-09"},
         "end": {"date": "2026-10-10"}},
    ]
    events = svc.list_google_events(1, START, END)
    titles = [(e["title"], e["date"]) for e in events]
    assert ("Dentista", "2026-10-08") in titles
    assert [d for t, d in titles if t == "Viagem"] == ["2026-10-10", "2026-10-11", "2026-10-12"]
    assert all(t not in {"Enviado pelo Versus", "Cancelado"} for t, _ in titles)
    timed = next(e for e in events if e["title"] == "Dentista")
    assert timed["duration_minutes"] == 90 and timed["external"] is True and timed["url"] == "https://g/a"


def test_check_connection_flags_revoked_and_reconnect_restores(ctx, monkeypatch):
    conn = GoogleCalendarConnection.query.first()
    conn.token_expires_at = datetime(2000, 1, 1)  # força renovação
    db.session.commit()

    def revoked(_data):
        raise svc._InvalidGrant()

    monkeypatch.setattr(svc, "_token_request", revoked)
    status = svc.check_connection(1)
    assert status["needs_reconnect"] is True and status["connected"] is False and status["status"] == "revoked"
    # conexão revogada não consulta o Google nem sincroniza
    with pytest.raises(svc.GoogleCalendarError):
        svc.sync_range(1, [(1, 10)], START, END)
    assert svc.list_google_events(1, START, END) == []

    # reconexão: novo código OAuth reativa a mesma linha, sem duplicar
    monkeypatch.setattr(svc, "_token_request", lambda _d: {
        "access_token": "new", "refresh_token": "r2", "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/calendar.events openid email"})
    monkeypatch.setattr(svc, "_fetch_email", lambda _t: "ana@example.com")
    svc.complete_connection(1, "code")
    status = svc.connection_status(1)
    assert status["connected"] is True and status["needs_reconnect"] is False and status["email"] == "ana@example.com"
    assert GoogleCalendarConnection.query.count() == 1
    assert svc.sync_range(1, [(1, 10)], START, END)["created"] == 2


def test_network_failure_does_not_mark_revoked(ctx, monkeypatch):
    conn = GoogleCalendarConnection.query.first()
    conn.token_expires_at = datetime(2000, 1, 1)
    db.session.commit()

    def down(_data):
        raise svc.GoogleCalendarError("Falha de comunicação com o Google.")

    monkeypatch.setattr(svc, "_token_request", down)
    assert svc.check_connection(1)["needs_reconnect"] is False


def test_company_sync_vs_global_sync_are_isolated(ctx):
    _, fake = ctx
    only_a = svc.sync_range(1, [(1, 10)], START, END)
    assert only_a["created"] == 2 and [c["company_id"] for c in only_a["companies"]] == [1]
    assert GoogleCalendarEventLink.query.filter_by(company_id=2).count() == 0

    both = svc.sync_range(1, [(1, 10), (2, 20)], START, END)
    assert both["created"] == 1 and both["unchanged"] == 2
    assert {c["company_id"]: c["created"] for c in both["companies"]} == {1: 0, 2: 1}

    # sincronizar só a empresa A não apaga nem mexe nos eventos da empresa B
    ProjectTask.query.get(10).is_deleted = True
    db.session.commit()
    svc.sync_range(1, [(1, 10)], START, END)
    assert GoogleCalendarEventLink.query.filter_by(company_id=2).count() == 1
    again = svc.sync_range(1, [(1, 10), (2, 20)], START, END)
    assert again["deleted"] == 1 and GoogleCalendarEventLink.query.filter_by(company_id=2).count() == 0


def test_check_connection_revalidates_when_stale_and_detects_revocation(ctx, monkeypatch):
    conn = GoogleCalendarConnection.query.first()  # token de acesso ainda válido por anos (fixture)
    calls = []

    def revoked(_data):
        calls.append(1)
        raise svc._InvalidGrant()

    monkeypatch.setattr(svc, "_token_request", revoked)
    # verificação recente: não consulta o Google
    assert svc.check_connection(1)["needs_reconnect"] is False and calls == []
    # verificação antiga: consulta o Google e percebe a revogação
    conn.updated_at = datetime(2000, 1, 1)
    db.session.commit()
    GoogleCalendarConnection.query.update({"updated_at": datetime(2000, 1, 1)})
    db.session.commit()
    assert svc.check_connection(1)["needs_reconnect"] is True and calls == [1]
