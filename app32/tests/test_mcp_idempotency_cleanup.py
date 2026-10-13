"""Limpeza diária das chaves de idempotência do mcp-versus: retenção, lotes, teto e desligamento."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from models import db
from models.mcp_idempotency import McpIdempotencyKey
from services import mcp_idempotency_service as svc
from services import scheduler_service as scheduler_module


# ---- tarefa agendada -------------------------------------------------------------------------------------
def test_the_daily_job_is_registered_at_03_30_with_a_stable_id(monkeypatch):
    captured = []
    monkeypatch.setattr(scheduler_module.scheduler_service, "add_job", lambda **kw: captured.append(kw))
    scheduler_module.setup_mcp_idempotency_cleanup_job(SimpleNamespace(config={}))
    assert len(captured) == 1
    job = captured[0]
    assert job["job_id"] == "mcp_idempotency_purge" and job["trigger"] == "cron"
    assert (job["hour"], job["minute"]) == (3, 30)


def test_the_job_can_be_turned_off_by_configuration(monkeypatch):
    captured = []
    monkeypatch.setattr(scheduler_module.scheduler_service, "add_job", lambda **kw: captured.append(kw))
    scheduler_module.setup_mcp_idempotency_cleanup_job(SimpleNamespace(config={"MCP_IDEMPOTENCY_PURGE_ENABLED": False}))
    assert captured == []


def test_the_job_is_part_of_the_scheduler_startup():
    import inspect

    assert "setup_mcp_idempotency_cleanup_job(app)" in inspect.getsource(scheduler_module.initialize_scheduler)


def test_the_job_is_listed_in_the_automation_registry():
    from services.ai_automation_registry_service import AIAutomationRegistryService

    specs = {item["key"]: item for item in AIAutomationRegistryService.DEFAULT_JOB_SPECS}
    assert specs["mcp_idempotency_purge"]["kind"] == "maintenance"
    assert "desligável" in " ".join(specs["mcp_idempotency_purge"]["governance"])


# ---- comportamento da limpeza (SQLite em memória) ------------------------------------------------------------
@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[McpIdempotencyKey.__table__])
        yield app
        db.session.remove()


def _add(key: str, expired_days_ago: float):
    now = datetime.utcnow()
    db.session.add(
        McpIdempotencyKey(
            company_id=1, principal_id="p", tool_name="t", idempotency_key=key, payload_digest="d",
            status="succeeded", result={"ok": True}, created_at=now, updated_at=now,
            expires_at=now - timedelta(days=expired_days_ago),
        )
    )


def _keys():
    return sorted(row.idempotency_key for row in McpIdempotencyKey.query.all())


def test_only_rows_expired_beyond_the_retention_are_removed(app):
    _add("vivo", -1)  # vence amanhã
    _add("vencido-ontem", 1)
    _add("vencido-ha-10-dias", 10)
    db.session.commit()
    assert svc.count_expired(timedelta(days=7)) == 1
    assert svc.purge_expired(older_than=timedelta(days=7)) == 1
    assert _keys() == ["vencido-ontem", "vivo"], "a retenção de 7 dias preserva o rastro recente"
    assert svc.purge_expired(older_than=timedelta(0)) == 1
    assert _keys() == ["vivo"], "uma chave ainda válida nunca é removida"


def test_purge_is_idempotent_and_works_in_batches(app):
    for i in range(5):
        _add(f"antigo-{i}", 30)
    db.session.commit()
    assert svc.purge_expired(limit=2, older_than=timedelta(days=7)) == 2
    assert svc.purge_expired(limit=2, older_than=timedelta(days=7)) == 2
    assert svc.purge_expired(limit=2, older_than=timedelta(days=7)) == 1
    assert svc.purge_expired(limit=2, older_than=timedelta(days=7)) == 0


def test_the_job_runs_batches_until_done_and_reports(app, monkeypatch):
    for i in range(7):
        _add(f"antigo-{i}", 30)
    _add("recente", 1)
    db.session.commit()
    app.config["MCP_IDEMPOTENCY_RETENTION_DAYS"] = 7
    result = scheduler_module.purge_mcp_idempotency_keys(app)
    assert result == {"purged": 7, "retention_days": 7}
    assert _keys() == ["recente"]


def test_the_job_respects_a_configured_retention(app):
    _add("vencido-3-dias", 3)
    db.session.commit()
    app.config["MCP_IDEMPOTENCY_RETENTION_DAYS"] = 1
    assert scheduler_module.purge_mcp_idempotency_keys(app)["purged"] == 1


def test_a_failure_is_rolled_back_and_reported_without_raising(app, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(svc, "purge_expired", boom)
    result = scheduler_module.purge_mcp_idempotency_keys(app)
    assert result == {"error": "purge_failed", "purged": 0}
