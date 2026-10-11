import inspect
from datetime import timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from models import db
from models.mcp_idempotency import McpIdempotencyKey
from services import mcp_idempotency_service as svc
from src.core import mcp_idempotency_policy as policy
from src.core.mcp_param_hiding import adapt_for_mcp
from src.core.mcp_runtime import _idempotency_claim, _idempotency_finish, _idempotency_precheck


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[McpIdempotencyKey.__table__])
        yield app
        db.session.remove()


SCOPE = dict(company_id=1, principal_id="p1", tool_name="create_financial_entry", key="k1")


def _claim(digest="d1", **over):
    return svc.claim(**{**SCOPE, **over}, payload_digest=digest)


def test_policy_modes_cover_exactly_the_thirty_financial_tools():
    assert not policy.REQUIRED_TOOLS & policy.OPTIONAL_TOOLS
    assert len(policy.REQUIRED_TOOLS | policy.OPTIONAL_TOOLS) == 30
    assert policy.idempotency_mode("create_financial_entry") == "required"
    assert policy.idempotency_mode("upsert_financial_budget_matrix") == "optional"
    assert policy.idempotency_mode("list_financial_entries") is None
    for name in policy.REQUIRED_TOOLS:
        assert name.split("_")[0] in {"create", "generate", "import", "reconcile", "match"}, name


def test_adapter_adds_the_param_and_the_tool_never_receives_it():
    seen = {}

    def create_financial_entry(company_id: int, payload: dict):
        seen.update(company_id=company_id, payload=payload)
        return {"success": True}

    adapted = adapt_for_mcp("create_financial_entry", create_financial_entry)
    assert "idempotency_key" in inspect.signature(adapted).parameters
    assert adapted(1, {"a": 1}, idempotency_key="abc") == {"success": True}
    assert seen == {"company_id": 1, "payload": {"a": 1}}
    other = lambda x: x  # noqa: E731
    assert adapt_for_mcp("list_financial_entries", other) is other


def test_first_call_replay_conflict_and_in_progress(app):
    first = _claim()
    assert first.action == "proceed"
    assert _claim().action == "in_progress"  # corrida: ainda executando
    assert svc.lookup(**SCOPE, payload_digest="d1").action == "in_progress"
    svc.complete(first.row_id, {"success": True, "item": {"id": 9}})
    replay = svc.lookup(**SCOPE, payload_digest="d1")
    assert replay.action == "replay" and replay.result["item"]["id"] == 9
    assert _claim().action == "replay"
    assert svc.lookup(**SCOPE, payload_digest="outro").action == "conflict"
    assert _claim(digest="outro").action == "conflict"


def test_scope_isolates_company_principal_and_tool(app):
    assert _claim().action == "proceed"
    assert _claim(company_id=2).action == "proceed"
    assert _claim(principal_id="p2").action == "proceed"
    assert _claim(tool_name="create_financial_settlement").action == "proceed"


def test_failure_releases_the_key_for_the_same_payload(app):
    row = _claim()
    svc.fail(row.row_id)
    again = _claim()
    assert again.action == "proceed" and again.row_id == row.row_id
    business_failure = _claim(key="k2")
    svc.complete(business_failure.row_id, {"success": False, "error": "x"})
    assert _claim(key="k2").action == "proceed"


def test_expired_and_stale_reservations_are_retaken(app):
    row = _claim()
    svc.complete(row.row_id, {"success": True})
    stored = db.session.get(McpIdempotencyKey, row.row_id)
    stored.expires_at = svc._now() - timedelta(seconds=1)
    db.session.commit()
    assert svc.lookup(**SCOPE, payload_digest="novo").action == "proceed"
    assert _claim(digest="novo").action == "proceed"
    stale = db.session.get(McpIdempotencyKey, row.row_id)
    stale.updated_at = svc._now() - svc.STALE_IN_PROGRESS - timedelta(seconds=1)
    db.session.commit()
    assert _claim(digest="novo").action == "proceed"
    assert svc.purge_expired() == 0


def test_purge_removes_only_expired(app):
    row = _claim()
    stored = db.session.get(McpIdempotencyKey, row.row_id)
    stored.expires_at = svc._now() - timedelta(seconds=1)
    _claim(key="vivo")
    db.session.commit()
    assert svc.purge_expired() == 1
    assert McpIdempotencyKey.query.count() == 1


def test_large_results_are_not_stored_whole(app):
    row = _claim()
    svc.complete(row.row_id, {"success": True, "blob": "x" * (svc.MAX_STORED_RESULT_BYTES + 10)})
    assert svc.lookup(**SCOPE, payload_digest="d1").result["replay_truncated"] is True


CONTEXT = SimpleNamespace(company_id=1, principal_id="p1", user_id=7)
ALLOWED = SimpleNamespace(allowed=True)


def test_runtime_requires_the_key_on_creation_tools_and_not_on_optional_ones(app):
    state = _idempotency_precheck("create_financial_entry", {"company_id": 1, "payload": {}}, CONTEXT, ALLOWED)
    assert state.envelope["success"] is False and "idempotency_key obrigatória" in state.envelope["error"]
    assert _idempotency_precheck("upsert_financial_budget_matrix", {"company_id": 1}, CONTEXT, ALLOWED).envelope is None
    assert _idempotency_precheck("list_financial_entries", {"company_id": 1}, CONTEXT, ALLOWED).envelope is None
    denied = _idempotency_precheck("create_financial_entry", {}, CONTEXT, SimpleNamespace(allowed=False))
    assert denied.envelope is None  # a recusa de permissão segue o fluxo normal
    too_long = _idempotency_precheck("create_financial_entry", {"idempotency_key": "x" * 129}, CONTEXT, ALLOWED)
    assert "128" in too_long.envelope["error"]


def test_runtime_end_to_end_replays_without_executing_twice(app):
    payload = {"company_id": 1, "payload": {"amount": 10}, "idempotency_key": "lancamento-1"}
    state = _idempotency_precheck("create_financial_entry", payload, CONTEXT, ALLOWED)
    assert state.envelope is None
    row_id, refusal = _idempotency_claim(state, "create_financial_entry", CONTEXT)
    assert refusal is None and row_id
    _idempotency_finish(row_id, {"success": True, "item": {"id": 5}}, failed=False)

    again = _idempotency_precheck("create_financial_entry", dict(payload), CONTEXT, ALLOWED)
    assert again.envelope == {"success": True, "item": {"id": 5}, "replayed": True}
    changed = _idempotency_precheck(
        "create_financial_entry", {**payload, "payload": {"amount": 99}}, CONTEXT, ALLOWED
    )
    assert "idempotency_key_reuse" in changed.envelope["error"]


def test_runtime_is_fail_closed_when_the_table_is_unavailable():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    with app.app_context():
        with pytest.raises(PermissionError):
            _idempotency_precheck("create_financial_entry", {"idempotency_key": "k"}, CONTEXT, ALLOWED)
