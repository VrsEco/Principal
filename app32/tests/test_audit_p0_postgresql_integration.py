"""Opt-in real PostgreSQL lab. Never reads the application's DATABASE_URL."""
import importlib.util
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
import jwt
from alembic.migration import MigrationContext
from alembic.operations import Operations
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask
from sqlalchemy import Column, DateTime, Integer, String, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from services.tool_approval_service import ToolApprovalBinding, ToolApprovalService
from services.principal_authorization_service import PrincipalAuthorizationService
from src.core.mcp_http_auth import reset_http_request_context, set_http_request_context
from src.core.mcp_runtime import _emit_mcp_policy_audit, resolve_mcp_execution_context
from src.intelligence.audit import build_ai_execution_audit_record, persist_ai_execution_audit_event
from src.intelligence.security.oauth_token_verifier import OAuthAccessTokenVerifier, OAuthTokenVerifierSettings
from src.intelligence.security.tool_policy import ToolPolicyRequest


@pytest.fixture
def lab(monkeypatch):
    raw_url = os.environ.get("APP32_AUDIT_P0_TEST_URL")
    if not raw_url:
        pytest.skip("APP32_AUDIT_P0_TEST_URL not configured")
    url = make_url(raw_url)
    if (url.get_backend_name() != "postgresql" or url.host not in {"127.0.0.1", "localhost"}
            or not (url.database or "").startswith("app32_audit_p0_")):
        pytest.fail("lab requires explicit loopback PostgreSQL and app32_audit_p0_ database")
    schema = "audit_p0_" + uuid.uuid4().hex
    root = create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema} -clock_timeout=10000"})
    session = scoped_session(sessionmaker(bind=engine))
    base = declarative_base()
    base.query = session.query_property()

    class AgentAction(base):
        __tablename__ = "agent_actions"
        id = Column(Integer, primary_key=True)
        type = Column(String(50), nullable=False)
        status = Column(String(20), nullable=False)
        company_id = Column(Integer, nullable=False)
        user_id = Column(Integer)
        payload = Column(JSONB)
        resolved_at = Column(DateTime)
        executed_at = Column(DateTime)

    base.metadata.create_all(engine)
    db = SimpleNamespace(engine=engine, session=session)
    monkeypatch.setitem(sys.modules, "models", SimpleNamespace(db=db))
    monkeypatch.setitem(sys.modules, "models.agent_action", SimpleNamespace(AgentAction=AgentAction))
    path = Path(__file__).parents[1] / "migrations/versions/20260916_1000_ai_mcp_audit_schema_v2.py"
    spec = importlib.util.spec_from_file_location("audit_p0_pg_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    def upgrade():
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration.upgrade()

    try:
        yield SimpleNamespace(engine=engine, session=session, action=AgentAction,
                              migration=migration, upgrade=upgrade, schema=schema)
    finally:
        session.remove()
        engine.dispose()
        # Generated schema only, inside explicitly validated disposable database.
        assert schema.startswith("audit_p0_") and schema[9:].isalnum()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def binding(**changes):
    args = dict(principal_id=71, company_id=9, user_id=3, tool_name="update_project",
                payload={"company_id": 9, "project_id": 31, "title": "approved"})
    args.update(changes)
    return ToolApprovalBinding.from_execution(**args)


def seed_approval(lab, approved_binding, **changes):
    now = datetime.utcnow()
    values = dict(type="workflow_approval_request", status="approved", company_id=9, user_id=3,
                  resolved_at=now, payload={
                      "created_via": "mcp_tool_approval", "approval_key": approved_binding.approval_key,
                      "principal_id": approved_binding.principal_id,
                      "action_key": "tool.update_project",
                      "approval_expires_at": (now + timedelta(minutes=5)).isoformat(),
                  })
    values.update(changes)
    row = lab.action(**values)
    lab.session.add(row)
    lab.session.commit()
    return row.id


def test_fresh_schema_upgrade_is_idempotent_and_writer_persists_v2(lab):
    lab.upgrade()
    lab.upgrade()
    indexes = {x["name"] for x in inspect(lab.engine).get_indexes("ai_mcp_audit_events")}
    assert set(lab.migration.INDEXES) <= indexes
    record = build_ai_execution_audit_record(
        event_type="mcp.tool_policy.allowed", runtime="mcp", status="allowed", company_id=9,
        principal_id=71, client_id="codex", auth_method="oauth", surface="admin",
        token_scopes=["mcp:access", "mcp:admin"], policy_allowed=True, policy_reason="ok",
        approval_request_id=321, payload_digest="a" * 64,
        metadata={"nested": [{"access_token": "NEVER_STORE_THIS"}]},
    )
    persist_ai_execution_audit_event(record)
    with lab.engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM ai_mcp_audit_events")).mappings().one()
    assert row["principal_id"] == 71 and row["policy_allowed"] is True
    assert row["token_scopes"] == ["mcp:access", "mcp:admin"]
    assert row["metadata_json"]["nested"][0]["access_token"] == "[REDACTED]"


def test_legacy_history_survives_upgrade_and_preserving_downgrade(lab):
    statements = []
    lab.migration.op = SimpleNamespace(execute=statements.append)
    lab.migration.upgrade()
    with lab.engine.begin() as conn:
        conn.execute(text(statements[0]))
        conn.execute(text("""INSERT INTO ai_mcp_audit_events
            (schema_version,event_type,runtime,status,company_id,metadata_json,occurred_at)
            VALUES ('legacy','test','mcp','allowed',9,CAST(:metadata AS JSONB),NOW())"""),
                     {"metadata": '{"kept":true}'})
    lab.upgrade()
    lab.migration.downgrade()
    with lab.engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM ai_mcp_audit_events")).mappings().one()
    assert row["schema_version"] == "legacy" and row["metadata_json"] == {"kept": True}
    assert row["principal_id"] is None and row["token_scopes"] == []


def test_concurrent_approval_consumption_allows_exactly_one_and_denies_replay(lab):
    approved = binding()
    action_id = seed_approval(lab, approved)
    barrier = Barrier(2)
    def consume():
        try:
            barrier.wait(timeout=10)
            return ToolApprovalService().authorize_and_consume(approved).allowed
        finally:
            lab.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(results) == [False, True]
    assert ToolApprovalService().authorize_and_consume(approved).allowed is False
    lab.session.expire_all()
    action = lab.session.get(lab.action, action_id)
    assert action.status == "executed" and action.executed_at is not None


@pytest.mark.parametrize("change", ["tenant", "user", "payload", "expiry"])
def test_approval_denies_cross_scope_changed_payload_and_expiry(lab, change):
    approved = binding()
    changes = {"company_id": 10} if change == "tenant" else {"user_id": 4} if change == "user" else {}
    action_id = seed_approval(lab, approved, **changes)
    if change == "expiry":
        action = lab.session.get(lab.action, action_id)
        action.payload = {**action.payload, "approval_expires_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat()}
        lab.session.commit()
    requested = binding(payload={"company_id": 9, "project_id": 31, "title": "tampered"}) if change == "payload" else approved
    assert ToolApprovalService().authorize_and_consume(requested).allowed is False
    assert lab.session.get(lab.action, action_id).status == "approved"


def test_audit_transaction_does_not_commit_operational_session(lab):
    lab.upgrade()
    lab.session.add(lab.action(type="technical_fix", status="pending", company_id=9, user_id=3))
    record = build_ai_execution_audit_record(event_type="mcp.test", runtime="mcp", status="allowed", company_id=9)
    persist_ai_execution_audit_event(record)
    lab.session.rollback()
    with lab.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_actions")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM ai_mcp_audit_events")).scalar_one() == 1


def test_exact_approval_is_not_hidden_by_twenty_newer_unrelated_requests(lab):
    approved = binding()
    seed_approval(lab, approved)
    for i in range(21):
        unrelated = binding(payload={"project_id": i, "title": "unrelated"})
        seed_approval(lab, unrelated)
    assert ToolApprovalService().authorize_and_consume(approved).allowed is True


def _oauth_lab_service(lab):
    def principal_lookup(principal_id):
        with lab.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM identity_principals WHERE id=:id"), {"id": principal_id}
            ).mappings().first()
        if row is None:
            return None
        return SimpleNamespace(
            id=row["id"], user_id=row["user_id"], subject_type=row["subject_type"],
            is_active=row["status"] == "active" and row["revoked_at"] is None,
        )

    def external_lookup(issuer, subject):
        with lab.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM external_identities WHERE issuer=:issuer AND subject=:subject"),
                {"issuer": issuer, "subject": subject},
            ).mappings().first()
        return SimpleNamespace(**row) if row else None

    def grant_lookup(principal_id, company_id):
        with lab.engine.connect() as conn:
            row = conn.execute(
                text("""SELECT * FROM principal_company_grants
                        WHERE principal_id=:principal_id AND company_id=:company_id"""),
                {"principal_id": principal_id, "company_id": company_id},
            ).mappings().first()
        if row is None:
            return None

        def inactive_reason_at(now):
            if row["status"] != "active" or row["revoked_at"] is not None:
                return "inactive"
            if row["expires_at"] is not None and row["expires_at"] < now:
                return "expired"
            return None

        return SimpleNamespace(
            id=row["id"], principal_id=row["principal_id"], company_id=row["company_id"],
            role=row["role"], inactive_reason_at=inactive_reason_at,
        )

    return PrincipalAuthorizationService(
        principal_lookup=principal_lookup,
        grant_lookup=grant_lookup,
        external_identity_lookup=external_lookup,
    )


def _seed_oauth_lab(lab):
    with lab.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE identity_principals (
                id INTEGER PRIMARY KEY, subject_type VARCHAR(16) NOT NULL,
                user_id INTEGER, status VARCHAR(16) NOT NULL, revoked_at TIMESTAMP
            );
            CREATE TABLE external_identities (
                id INTEGER PRIMARY KEY, principal_id INTEGER NOT NULL,
                issuer VARCHAR(512) NOT NULL, subject VARCHAR(512) NOT NULL,
                UNIQUE (issuer, subject)
            );
            CREATE TABLE principal_company_grants (
                id INTEGER PRIMARY KEY, principal_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL, role VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL, expires_at TIMESTAMP, revoked_at TIMESTAMP,
                UNIQUE (principal_id, company_id)
            );
            INSERT INTO identity_principals VALUES (71, 'SERVICE', NULL, 'active', NULL);
            INSERT INTO external_identities VALUES
                (1, 71, 'https://idp.audit.local/realms/app32', 'service:audit-smoke');
            INSERT INTO principal_company_grants VALUES
                (1, 71, 9, 'auditor', 'active', NULL, NULL);
        """))


def _signed_oauth_token(*, audience="app32-mcp", expires_delta=300):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.utcnow()
    token = jwt.encode(
        {
            "iss": "https://idp.audit.local/realms/app32",
            "sub": "service:audit-smoke",
            "aud": audience,
            "azp": "codex-audit-lab",
            "scope": "mcp:access mcp:user",
            "iat": now,
            "exp": now + timedelta(seconds=expires_delta),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "audit-p0-key"},
    )
    settings = OAuthTokenVerifierSettings(
        issuer="https://idp.audit.local/realms/app32",
        audience="app32-mcp",
        jwks_url="https://idp.audit.local/realms/app32/protocol/openid-connect/certs",
        allowed_client_ids=("codex-audit-lab",),
        required_scopes=("mcp:access",),
    )
    resolver = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private_key.public_key())
    )
    return token, OAuthAccessTokenVerifier(settings, signing_key_resolver=resolver)


def test_real_oauth_token_grant_tenant_and_audit_event(lab, monkeypatch):
    import src.core.mcp_http_auth as auth
    import services.principal_authorization_service as principal_module

    lab.upgrade()
    _seed_oauth_lab(lab)
    service = _oauth_lab_service(lab)
    token, verifier = _signed_oauth_token()
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(auth, "load_oauth_access_token_verifier", lambda: verifier)
    monkeypatch.setattr(principal_module, "principal_authorization_service", service)

    resolution = auth._resolve_oauth_identity(token=token, surface="user")
    assert resolution.status_code == 200 and resolution.identity.principal_id == 71
    identity = resolution.identity
    payload = auth._build_identity_context_payload(identity, surface="user")
    tokens = set_http_request_context(identity, payload)
    try:
        context = resolve_mcp_execution_context({"company_id": 9})
        assert context.company_id == 9
        assert context.principal_id == 71
        assert context.role == "auditor"
        assert context.metadata["principal_grant_enforced"] is True

        policy_source = {
            "principal_id": context.principal_id,
            "subject_type": context.subject_type,
            "client_id": context.client_id,
            "auth_method": context.auth_method,
            "token_scopes": context.token_scopes,
            "user_id": context.user_id,
            "correlation_id": "audit-p0-oauth-smoke",
        }
        request = ToolPolicyRequest(
            tool_name="list_audit_points", surface="user", domain="auditoria",
            action="read", risk="low", requested_company_id=9,
            accessible_company_ids=(9,),
        )
        with Flask(__name__).app_context():
            _emit_mcp_policy_audit(
                policy_source, request, {"company_id": 9}, allowed=True, reason="ok"
            )
    finally:
        reset_http_request_context(tokens)

    with lab.engine.connect() as conn:
        event = conn.execute(text("SELECT * FROM ai_mcp_audit_events")).mappings().one()
    assert event["company_id"] == 9
    assert event["principal_id"] == 71
    assert event["client_id"] == "codex-audit-lab"
    assert event["auth_method"] == "oauth_oidc_bearer"
    assert event["policy_allowed"] is True

    # O mesmo principal nunca herda outro tenant sem grant explícito.
    tokens = set_http_request_context(identity, payload)
    try:
        with pytest.raises(PermissionError, match="grant do principal"):
            resolve_mcp_execution_context({"company_id": 10})
    finally:
        reset_http_request_context(tokens)


def test_real_oauth_rejects_bad_audience_and_revoked_principal(lab, monkeypatch):
    import src.core.mcp_http_auth as auth
    import services.principal_authorization_service as principal_module

    _seed_oauth_lab(lab)
    service = _oauth_lab_service(lab)
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(principal_module, "principal_authorization_service", service)

    bad_token, bad_verifier = _signed_oauth_token(audience="another-resource")
    monkeypatch.setattr(auth, "load_oauth_access_token_verifier", lambda: bad_verifier)
    rejected = auth._resolve_oauth_identity(token=bad_token, surface="user")
    assert rejected.status_code == 401 and rejected.error == "invalid_token"

    valid_token, valid_verifier = _signed_oauth_token()
    monkeypatch.setattr(auth, "load_oauth_access_token_verifier", lambda: valid_verifier)
    with lab.engine.begin() as conn:
        conn.execute(text("UPDATE identity_principals SET status='revoked', revoked_at=NOW() WHERE id=71"))
    revoked = auth._resolve_oauth_identity(token=valid_token, surface="user")
    assert revoked.status_code == 401 and revoked.error == "invalid_token"
