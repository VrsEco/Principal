"""Control plane de deploy: tenant, identidade, transições e callbacks OIDC (service + ledger)."""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import db
from models.agent_deployment import AgentDeployment, AgentDeploymentEvent
from models.company import Company
from services import agent_deployment_service as svc
from services.agent_deployment_policy import DeploymentCallbackError, DeploymentRequestError

SHA = "a" * 40
REPO = "acme/app32"
KINDS = {"gv-codex-deploy": "codex", "gv-claude-deploy": "claude", "app32-ui": "human"}


@pytest.fixture()
def ledger(monkeypatch):
    monkeypatch.setenv("AGENT_DEPLOY_GOVERNANCE_COMPANY_ID", "1")
    monkeypatch.setenv("AGENT_DEPLOY_CLIENT_KINDS", json.dumps(KINDS))
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[
            Company.__table__, AgentDeployment.__table__, AgentDeploymentEvent.__table__])
        db.session.add_all([Company(id=1, name="Governança"), Company(id=2, name="Outro tenant")])
        db.session.commit()
        yield app
        db.session.remove()


def ident(client="gv-codex-deploy", *, company_id=1, user_id=None, subject=None):
    return SimpleNamespace(client_id=client, subject=subject or f"sub:{client}", company_id=company_id,
                           user_id=user_id, principal_id=None)


HUMAN = dict(client="app32-ui", user_id=7)


def request_deploy(identity=None, **overrides):
    args = dict(company_id=1, identity=identity or ident(), mode="quick", restart_mcp=False, target_sha=SHA)
    args.update(overrides)
    return svc.create_agent_deployment(**args)


def approved(dispatcher=None):
    created = request_deploy()
    calls = []
    result = svc.approve_agent_deployment(
        company_id=1, identity=ident(**HUMAN), deployment_id=created["deployment_id"],
        dispatcher=dispatcher or (lambda **kw: calls.append(kw)))
    return created, result, calls


def claims(**overrides):
    base = {"repository": REPO, "ref": "refs/heads/main", "event_name": "workflow_dispatch",
            "environment": "production", "sha": SHA, "run_id": "9001", "run_attempt": "1",
            "actor": "gv-app-dispatcher[bot]",
            "workflow_ref": f"{REPO}/.github/workflows/deploy-app32.yml@refs/heads/main"}
    base.update(overrides)
    return base


def callback(correlation_id, event, **kw):
    kw.setdefault("claims", claims())
    return svc.apply_workflow_callback(repository=REPO, correlation_id=correlation_id, event=event, **kw)


GOOD_EVIDENCE = {"health_status": 200, "smoke": {"/static/vendor/chartjs/chart.umd.min.js": 200}}


# ------------------------------------------------------------- identidade/ator

def test_actor_kind_is_derived_from_client_and_cannot_be_supplied(ledger):
    assert request_deploy(ident("gv-claude-deploy"))["actor_kind"] == "claude"
    assert request_deploy(ident("gv-codex-deploy"))["actor_kind"] == "codex"
    with pytest.raises(TypeError):
        svc.create_agent_deployment(company_id=1, identity=ident(), mode="quick", restart_mcp=False,
                                    target_sha=SHA, actor_kind="human")


def test_unmapped_client_cannot_request(ledger):
    with pytest.raises(DeploymentRequestError, match="client_id não autorizado"):
        request_deploy(ident("random-oauth-client"))


def test_client_kinds_missing_config_is_fail_closed(ledger, monkeypatch):
    monkeypatch.delenv("AGENT_DEPLOY_CLIENT_KINDS")
    with pytest.raises(DeploymentRequestError, match="client_id não autorizado"):
        request_deploy()


def test_human_client_without_user_is_rejected(ledger):
    with pytest.raises(DeploymentRequestError, match="usuário"):
        request_deploy(ident("app32-ui", user_id=None))


@pytest.mark.parametrize("client", ["gv-codex-deploy", "gv-claude-deploy"])
def test_agent_can_never_approve(ledger, client):
    created = request_deploy()
    with pytest.raises(DeploymentRequestError, match="somente um humano"):
        svc.approve_agent_deployment(company_id=1, identity=ident(client, user_id=7),
                                     deployment_id=created["deployment_id"], dispatcher=lambda **kw: None)
    assert svc.get_agent_deployment(company_id=1, identity=ident(), deployment_id=created["deployment_id"])["status"] == "pending_approval"


# ------------------------------------------------------------------- tenant

def test_tenant_must_be_governance_company_and_match_identity(ledger):
    with pytest.raises(DeploymentRequestError, match="tenant de governança"):
        request_deploy(company_id=2, identity=ident(company_id=2))
    with pytest.raises(DeploymentRequestError, match="não corresponde"):
        request_deploy(identity=ident(company_id=2))


def test_unconfigured_governance_tenant_fails_closed(ledger, monkeypatch):
    monkeypatch.delenv("AGENT_DEPLOY_GOVERNANCE_COMPANY_ID")
    with pytest.raises(DeploymentRequestError, match="não configurado"):
        request_deploy()


def test_cross_tenant_rows_are_invisible(ledger):
    foreign = AgentDeployment(company_id=2, actor_subject="x", actor_client_id="gv-codex-deploy",
                              actor_kind="codex", mode="quick", target_sha=SHA, correlation_id="f" * 32)
    db.session.add(foreign)
    db.session.commit()
    mine = request_deploy()
    listed = svc.list_agent_deployments(company_id=1, identity=ident())
    assert [item["deployment_id"] for item in listed] == [mine["deployment_id"]]
    with pytest.raises(DeploymentRequestError, match="não encontrado"):
        svc.get_agent_deployment(company_id=1, identity=ident(), deployment_id=foreign.id)
    with pytest.raises(DeploymentRequestError, match="não encontrado"):
        svc.approve_agent_deployment(company_id=1, identity=ident(**HUMAN), deployment_id=foreign.id,
                                     dispatcher=lambda **kw: None)


@pytest.mark.parametrize("sha", ["ac292f1ac", "g" * 40, "A" * 39, ""])
def test_target_sha_must_be_full_hex(ledger, sha):
    with pytest.raises(DeploymentRequestError, match="target_sha"):
        request_deploy(target_sha=sha)


def test_full_mode_requires_migration_confirmation(ledger):
    with pytest.raises(DeploymentRequestError, match="migration_confirmed"):
        request_deploy(mode="full")
    assert request_deploy(mode="full", migration_confirmed=True)["mode"] == "full"


# ---------------------------------------------------- aprovação e dispatch

def test_approval_dispatches_with_correlation_only_and_records_events(ledger):
    created, result, calls = approved()
    assert result["status"] == "dispatched"
    assert calls == [{"correlation_id": AgentDeployment.query.one().correlation_id, "mode": "quick", "restart_mcp": False}]
    events = svc.get_agent_deployment(company_id=1, identity=ident(), deployment_id=created["deployment_id"])["events"]
    assert [e["event_type"] for e in events] == ["requested", "approved", "dispatched"]
    assert "correlation_id" not in result  # vínculo do workflow não é exposto ao agente


def test_dispatch_failure_marks_failed_without_retry(ledger):
    def boom(**kw):
        raise RuntimeError("github down")
    created, result, _ = approved(dispatcher=boom)
    assert result["status"] == "failed" and result["failure_reason"] == "dispatch_failed"
    with pytest.raises(DeploymentRequestError, match="não está pendente"):
        svc.approve_agent_deployment(company_id=1, identity=ident(**HUMAN),
                                     deployment_id=created["deployment_id"], dispatcher=lambda **kw: None)


def test_only_one_active_deploy_per_tenant(ledger):
    approved()
    second = request_deploy()
    with pytest.raises(DeploymentRequestError, match="deploy ativo"):
        svc.approve_agent_deployment(company_id=1, identity=ident(**HUMAN),
                                     deployment_id=second["deployment_id"], dispatcher=lambda **kw: None)


# ---------------------------------------------------- callback do GitHub / OIDC

def _correlation():
    return AgentDeployment.query.first().correlation_id


def test_started_binds_run_and_full_lifecycle_succeeds(ledger):
    approved()
    cid = _correlation()
    started = callback(cid, "started")
    assert started["status"] == "running" and started["github_run_id"] == 9001
    assert started["github_run_url"] == f"https://github.com/{REPO}/actions/runs/9001"
    callback(cid, "stage", stage="smoke", evidence={"ok": True})
    done = callback(cid, "succeeded", evidence=GOOD_EVIDENCE)
    assert done["status"] == "succeeded" and done["finished_at"]
    types = [e.event_type for e in AgentDeploymentEvent.query.order_by(AgentDeploymentEvent.id)]
    assert types == ["requested", "approved", "dispatched", "started", "stage:smoke", "succeeded"]


def test_started_is_refused_for_unapproved_deployment(ledger):
    request_deploy()
    with pytest.raises(DeploymentRequestError, match="transição de status inválida"):
        callback(_correlation(), "started")
    assert AgentDeployment.query.one().status == "pending_approval"


@pytest.mark.parametrize("override", [
    {"sha": "b" * 40},                       # SHA diferente do aprovado
    {"repository": "evil/app32"},            # outro repositório
    {"ref": "refs/heads/feature"},           # fora de main
    {"event_name": "push"},                  # não é dispatch
    {"environment": None},                   # não passou por production
    {"workflow_ref": f"{REPO}/.github/workflows/other.yml@refs/heads/main"},
    {"run_id": "abc"},
])
def test_invalid_github_claims_are_rejected(ledger, override):
    approved()
    with pytest.raises(DeploymentCallbackError):
        callback(_correlation(), "started", claims=claims(**override))
    assert AgentDeployment.query.one().status == "dispatched"


def test_unknown_or_malformed_correlation_is_rejected(ledger):
    approved()
    with pytest.raises(DeploymentCallbackError, match="não encontrado"):
        callback("0" * 32, "started")
    with pytest.raises(DeploymentCallbackError, match="inválido"):
        callback("../etc", "started")


def test_agent_supplied_run_url_and_status_cannot_close_a_deploy(ledger):
    """Não há API de service para agente registrar run/status: só o callback verificado."""
    assert not hasattr(svc, "record_agent_deployment_run")
    with pytest.raises(DeploymentCallbackError):
        callback("x" * 32, "succeeded", claims={})


def test_run_is_bound_and_other_run_cannot_report(ledger):
    approved()
    cid = _correlation()
    callback(cid, "started")
    with pytest.raises(DeploymentCallbackError, match="run diferente"):
        callback(cid, "succeeded", claims=claims(run_id="9002"), evidence=GOOD_EVIDENCE)
    with pytest.raises(DeploymentCallbackError, match="run diferente"):
        callback(cid, "failed", claims=claims(run_attempt="2"))
    with pytest.raises(DeploymentCallbackError, match="já vinculado"):
        callback(cid, "started")


@pytest.mark.parametrize("evidence", [
    {}, {"health_status": 500, "smoke": {"/a": 200}}, {"health_status": 200},
    {"health_status": 200, "smoke": {"/a": 404}}, {"health_status": 200, "smoke": {}},
])
def test_success_requires_health_and_smoke_evidence(ledger, evidence):
    approved()
    cid = _correlation()
    callback(cid, "started")
    with pytest.raises(DeploymentCallbackError):
        callback(cid, "succeeded", evidence=evidence)
    assert AgentDeployment.query.one().status == "running"


def test_terminal_states_are_final_and_invalid_transitions_rejected(ledger):
    approved()
    cid = _correlation()
    callback(cid, "started")
    failed = callback(cid, "failed", failure_reason="health_check")
    assert failed["status"] == "failed" and failed["failure_reason"] == "health_check"
    for event, extra in (("succeeded", {"evidence": GOOD_EVIDENCE}), ("failed", {}), ("stage", {"stage": "smoke"})):
        with pytest.raises(DeploymentRequestError):
            callback(cid, event, **extra)


def test_stage_requires_running_and_known_stage(ledger):
    approved()
    cid = _correlation()
    with pytest.raises(DeploymentCallbackError):
        callback(cid, "stage", stage="smoke")  # sem run vinculado
    callback(cid, "started")
    with pytest.raises(DeploymentCallbackError, match="estágio inválido"):
        callback(cid, "stage", stage="rm -rf")


@pytest.mark.parametrize("evidence", [{"ssh_private_key": "x"}, {"nested": {"api_token": "x"}}, {"x": object()}])
def test_evidence_with_secret_like_keys_or_types_is_rejected(ledger, evidence):
    approved()
    cid = _correlation()
    callback(cid, "started")
    with pytest.raises(DeploymentCallbackError):
        callback(cid, "stage", stage="smoke", evidence=evidence)


def test_failure_before_started_is_recorded_from_dispatched(ledger):
    approved()
    result = callback(_correlation(), "failed", failure_reason="validate")
    assert result["status"] == "failed" and result["github_run_id"] == 9001


# -------------------------------------------------------------- append-only

def test_events_are_append_only(ledger):
    request_deploy()
    event = AgentDeploymentEvent.query.first()
    event.evidence_json = {"tampered": True}
    with pytest.raises(ValueError, match="append-only"):
        db.session.flush()
    db.session.rollback()
    db.session.delete(AgentDeploymentEvent.query.first())
    with pytest.raises(ValueError, match="append-only"):
        db.session.flush()
    db.session.rollback()
