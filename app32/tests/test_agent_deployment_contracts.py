"""Contratos do control plane de deploy: MCP (capability/surface), workflow, migration, OIDC e rota."""
from __future__ import annotations

import importlib.util
import inspect
import io
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
TOOLS = ("request_agent_deployment", "approve_agent_deployment", "get_agent_deployment", "list_agent_deployments")


# ------------------------------------------------------- capability e surface

def test_deploy_tools_have_canonical_admin_only_capabilities():
    from src.intelligence.tool_catalog import catalog

    for name in TOOLS:
        capability = catalog.get_tool_capability(name)
        assert capability is not None, f"{name} sem capability canônica"
        assert capability.scopes == ("mcp_admin",)
        assert capability.permissions and all(p.startswith("deployment.") for p in capability.permissions)
        assert "control_plane" in capability.tags
    approve = catalog.get_tool_capability("approve_agent_deployment")
    assert approve.human_gate and approve.risk.value == "critical"
    assert catalog.get_tool_capability("record_agent_deployment_run") is None


def test_no_mcp_tool_lets_an_agent_write_run_or_status():
    from src.core import mcp_agent_deployment_tools as tools

    recorded = {}

    class Recorder:
        def tool(self, *a, **k):
            return lambda fn: recorded.setdefault(fn.__name__, fn)

    tools.register_agent_deployment_mcp_tools(Recorder())
    assert set(recorded) == set(TOOLS)
    forbidden = {"company_id", "actor_kind", "status", "github_run_url", "github_run_id", "correlation_id"}
    for name, fn in recorded.items():
        assert not forbidden & set(inspect.signature(fn).parameters), name


def test_deploy_tools_are_listed_only_on_admin_surface():
    from src.core.mcp_surface_registry import iter_surface_tool_names

    assert set(TOOLS) <= set(iter_surface_tool_names("admin"))
    for surface in ("user", "analytics", "ops"):
        assert not set(TOOLS) & set(iter_surface_tool_names(surface)), surface


@pytest.mark.parametrize("surface,expected", [("admin", set(TOOLS)), ("user", set()), ("analytics", set()), ("ops", set())])
def test_deploy_tools_are_registered_only_where_the_capability_allows(surface, expected):
    """Registrars compartilhados não podem tornar a tool invocável fora da surface admin."""
    from src.core.mcp_surface_registry import _register_shared_registrars

    registered = set()

    class FakeMCP:
        def tool(self, *args, **kwargs):
            def decorator(fn):
                registered.add(kwargs.get("name") or fn.__name__)
                return fn
            return decorator

        def __getattr__(self, item):  # resource/prompt etc.
            return lambda *a, **k: (lambda fn: fn)

    _register_shared_registrars(FakeMCP(), tool_names=None, policy_surface=surface)
    assert registered & set(TOOLS) == expected


def _policy(name, *, permissions=(), role="admin", surface="admin", confirmed=False):
    from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
    from src.intelligence.tool_catalog import catalog
    from src.intelligence.tooling.capabilities import infer_tool_action

    capability = catalog.get_tool_capability(name)
    return evaluate_tool_policy(
        {"user_id": 10, "company_id": 1, "role": role, "permissions": permissions, "accessible_company_ids": (1,)},
        ToolPolicyRequest(
            tool_name=name, surface=surface, domain=capability.domain,
            action=infer_tool_action(name, capability.domain), risk=capability.risk.value,
            requested_company_id=1, accessible_company_ids=(1,),
            required_permissions=capability.permissions, confirmed_mutation=confirmed,
            required_context=capability.required_context,
        ),
    )


def test_approval_needs_persisted_human_gate_and_non_admin_roles_are_denied():
    denied = _policy("approve_agent_deployment")
    assert not denied.allowed and "confirmação explícita" in denied.reason
    assert _policy("approve_agent_deployment", confirmed=True).allowed
    assert not _policy("request_agent_deployment", role="colaborador").allowed


# ------------------------------------------------------------------ workflow

@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load((REPO_ROOT / ".github/workflows/deploy-app32.yml").read_text(encoding="utf-8"))


def _steps(workflow, job):
    return workflow["jobs"][job]["steps"]


def test_workflow_only_dispatches_and_never_cancels_production(workflow):
    triggers = workflow.get(True) or workflow.get("on")  # PyYAML lê `on` como True
    assert set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"mode", "restart_mcp", "deployment_id"}  # sem DEPLOY_ALLOW_DIRTY livre
    assert workflow["concurrency"] == {"group": "app32-production", "cancel-in-progress": False}
    assert workflow["permissions"] == {"contents": "read"}


def test_only_the_deploy_job_gets_oidc_and_production_environment(workflow):
    deploy = workflow["jobs"]["deploy"]
    assert deploy["environment"]["name"] == "production"
    assert deploy["permissions"] == {"contents": "read", "id-token": "write"}
    assert "permissions" not in workflow["jobs"]["validate"] and "environment" not in workflow["jobs"]["validate"]


def test_ledger_started_gates_the_ssh_step_and_closing_is_evidence_based(workflow):
    steps = _steps(workflow, "deploy")
    text = [str(s.get("run", "")) + str(s.get("uses", "")) for s in steps]
    started = next(i for i, t in enumerate(text) if "deploy_callback.sh started" in t)
    ssh = next(i for i, t in enumerate(text) if "ssh-action" in t)
    smoke = next(i for i, t in enumerate(text) if "deploy_smoke.sh" in t)
    succeeded = next(i for i, t in enumerate(text) if "deploy_callback.sh succeeded" in t)
    assert started < ssh < smoke < succeeded
    assert steps[succeeded]["env"]["EVIDENCE_JSON"] == "${{ steps.smoke.outputs.evidence }}"
    assert "failure()" in next(s["if"] for s in steps if "deploy_callback.sh failed" in str(s.get("run", "")))


def test_workflow_has_no_expression_injection_of_free_text_input(workflow):
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            assert "inputs.deployment_id" not in str(step.get("run", "")), step.get("name")
            assert "secrets." not in str(step.get("run", ""))  # segredos só em with:/env:


def test_workflow_helper_scripts_exist_and_never_accept_secrets():
    for name in ("deploy_callback.sh", "deploy_smoke.sh", "deploy_configr.sh"):
        assert (APP_ROOT / "scripts" / name).is_file(), name
    callback = (APP_ROOT / "scripts/deploy_callback.sh").read_text(encoding="utf-8")
    assert "::add-mask::" in callback and "id-token" in callback
    assert "SSH_PRIVATE_KEY" not in callback and "GITHUB_TOKEN" not in callback


# -------------------------------------------------------- migration e modelo

def _render_migration(monkeypatch):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = APP_ROOT / "migrations/versions/20260924_1300_agent_deployments.py"
    spec = importlib.util.spec_from_file_location("agent_deployments_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    buffer = io.StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buffer})
    fake_bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(module.sa, "inspect", lambda bind: SimpleNamespace(has_table=lambda name: False))
    with Operations.context(context):
        monkeypatch.setattr(module.op, "get_bind", lambda: fake_bind)
        module.upgrade()
    return module, buffer.getvalue()


def test_migration_chain_and_ddl_cover_model_columns(monkeypatch):
    from models.agent_deployment import AgentDeployment, AgentDeploymentEvent

    module, sql = _render_migration(monkeypatch)
    assert (module.revision, module.down_revision) == ("20260924_1300", "20260923_1200")
    ledger_sql = sql.split("CREATE TABLE agent_deployment_events")[0]
    events_sql = sql.split("CREATE TABLE agent_deployment_events")[1].split("CREATE INDEX")[0]
    for column in AgentDeployment.__table__.columns:
        assert column.name in ledger_sql, column.name
    for column in AgentDeploymentEvent.__table__.columns:
        assert column.name in events_sql, column.name
    assert "company_id INTEGER NOT NULL" in ledger_sql and "company_id INTEGER NOT NULL" in events_sql
    assert "UNIQUE (correlation_id)" in ledger_sql
    assert "BEFORE UPDATE OR DELETE ON agent_deployment_events" in sql  # append-only no banco


def test_migration_is_a_single_head_after_the_merge_revision():
    revisions, downs = set(), set()
    for path in (APP_ROOT / "migrations/versions").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("revision ="):
                revisions.add(line.split("=")[1].strip().strip("\"'"))
            if line.startswith("down_revision ="):
                downs.update(part.strip().strip("\"'") for part in line.split("=")[1].replace("(", "").replace(")", "").split(","))
    heads = revisions - downs
    assert "20260924_1300" in heads


def test_model_requires_tenant_and_unique_correlation():
    from models.agent_deployment import AgentDeployment

    assert AgentDeployment.__table__.c.company_id.nullable is False
    assert any(c.name == "uq_agent_deployment_correlation" for c in AgentDeployment.__table__.constraints)
    item = AgentDeployment(company_id=1, correlation_id="a" * 32, actor_subject="s", actor_client_id="c",
                           actor_kind="codex", mode="quick", target_sha="a" * 40)
    assert "correlation_id" not in item.to_dict()  # vínculo do workflow não é exposto


# ---------------------------------------------------------- OIDC do GitHub

@pytest.fixture()
def oidc(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt
    from services import agent_deployment_github as github

    monkeypatch.setenv("AGENT_DEPLOY_OIDC_AUDIENCE", "app32-deploy")
    monkeypatch.setenv("AGENT_DEPLOY_GITHUB_REPOSITORY", "acme/app32")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJWKClient:
        def __init__(self, *a, **k):
            pass

        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=key.public_key())

    monkeypatch.setattr(jwt, "PyJWKClient", FakeJWKClient)

    def sign(**overrides):
        now = int(time.time())
        claims = {"iss": github.GITHUB_OIDC_ISSUER, "aud": "app32-deploy", "iat": now, "exp": now + 300,
                  "repository": "acme/app32"}
        claims.update(overrides)
        return jwt.encode({k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256")

    return github, sign


def test_oidc_accepts_only_valid_github_tokens(oidc):
    from services.agent_deployment_policy import DeploymentCallbackError

    github, sign = oidc
    assert github.verify_github_oidc_token(sign())["repository"] == "acme/app32"
    for bad in (sign(aud="other"), sign(iss="https://evil.example"), sign(exp=int(time.time()) - 10), sign(exp=None)):
        with pytest.raises(DeploymentCallbackError):
            github.verify_github_oidc_token(bad)
    for garbage in ("", "abc", "a.b", None):
        with pytest.raises(DeploymentCallbackError):
            github.verify_github_oidc_token(garbage)


def test_oidc_rejects_symmetric_algorithm_confusion(oidc):
    import jwt
    from services.agent_deployment_policy import DeploymentCallbackError

    github, _ = oidc
    now = int(time.time())
    forged = jwt.encode({"iss": github.GITHUB_OIDC_ISSUER, "aud": "app32-deploy", "iat": now, "exp": now + 60},
                        "x" * 64, algorithm="HS256")
    with pytest.raises(DeploymentCallbackError):
        github.verify_github_oidc_token(forged)


def test_oidc_unconfigured_fails_closed(monkeypatch):
    from services import agent_deployment_github as github
    from services.agent_deployment_policy import DeploymentCallbackError

    monkeypatch.delenv("AGENT_DEPLOY_OIDC_AUDIENCE", raising=False)
    with pytest.raises(DeploymentCallbackError, match="não configurado"):
        github.verify_github_oidc_token("a.b.c")


# ---------------------------------------------------------------- dispatch

def test_dispatch_targets_official_workflow_on_main_without_leaking_token(monkeypatch):
    import requests
    from services import agent_deployment_github as github
    from services.agent_deployment_policy import DeploymentRequestError

    monkeypatch.setenv("AGENT_DEPLOY_GITHUB_REPOSITORY", "acme/app32")
    monkeypatch.setenv("AGENT_DEPLOY_GITHUB_DISPATCH_TOKEN", "ghs_secret")
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json, timeout=timeout)
        return SimpleNamespace(status_code=204)

    monkeypatch.setattr(requests, "post", fake_post)
    github.dispatch_deployment_workflow(correlation_id="c" * 32, mode="quick", restart_mcp=True)
    assert seen["url"].endswith("/repos/acme/app32/actions/workflows/deploy-app32.yml/dispatches")
    assert seen["json"] == {"ref": "main", "inputs": {"mode": "quick", "restart_mcp": "true", "deployment_id": "c" * 32}}
    assert "ghs_secret" not in str(seen["json"]) and seen["timeout"] <= 10

    monkeypatch.setattr(requests, "post", lambda *a, **k: SimpleNamespace(status_code=422))
    with pytest.raises(DeploymentRequestError, match="422"):
        github.dispatch_deployment_workflow(correlation_id="c" * 32, mode="quick", restart_mcp=False)
    monkeypatch.delenv("AGENT_DEPLOY_GITHUB_DISPATCH_TOKEN")
    with pytest.raises(DeploymentRequestError, match="não configurado"):
        github.dispatch_deployment_workflow(correlation_id="c" * 32, mode="quick", restart_mcp=False)


# -------------------------------------------------------------------- rota

@pytest.fixture()
def client(monkeypatch):
    from flask import Flask
    from api.webhooks.agent_deployment_webhook import agent_deployment_webhook_bp
    from services import agent_deployment_github as github
    from services import agent_deployment_service as svc
    from services.agent_deployment_policy import DeploymentCallbackError, DeploymentRequestError

    calls = []
    monkeypatch.setattr(github, "deploy_repository", lambda: "acme/app32")

    def verify(token):
        if token != "good":
            raise DeploymentCallbackError("token OIDC inválido")
        return {"repository": "acme/app32"}

    def apply(**kwargs):
        calls.append(kwargs)
        if kwargs["event"] == "conflict":
            raise DeploymentRequestError("transição de status inválida")
        if kwargs["event"] == "denied":
            raise DeploymentCallbackError("SHA")
        return {"deployment_id": 3, "status": "running", "target_sha": "leak?"}

    monkeypatch.setattr(github, "verify_github_oidc_token", verify)
    monkeypatch.setattr(svc, "apply_workflow_callback", apply)
    app = Flask(__name__)
    app.register_blueprint(agent_deployment_webhook_bp, url_prefix="/webhook")
    test_client = app.test_client()
    test_client.calls = calls
    return test_client


URL = "/webhook/agent-deployments/github"


def test_route_requires_valid_oidc_and_is_a_thin_adapter(client):
    assert client.post(URL, json={}).status_code == 401
    assert client.post(URL, json={}, headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.post(URL, json={}, headers={"Authorization": "Bearer bad"}).status_code == 403
    assert client.post(URL, data="x", headers={"Authorization": "Bearer good"}).status_code == 400
    assert client.calls == []
    ok = client.post(URL, json={"correlation_id": "c" * 32, "event": "started", "company_id": 99},
                     headers={"Authorization": "Bearer good"})
    assert ok.status_code == 200 and ok.get_json() == {"deployment_id": 3, "status": "running"}
    assert "company_id" not in client.calls[0]  # tenant nunca vem do corpo
    assert client.post(URL, json={"event": "denied"}, headers={"Authorization": "Bearer good"}).status_code == 403
    assert client.post(URL, json={"event": "conflict"}, headers={"Authorization": "Bearer good"}).status_code == 409
