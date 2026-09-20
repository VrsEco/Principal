import importlib.util
from pathlib import Path
from types import SimpleNamespace

from src.intelligence.audit import (
    build_ai_execution_audit_record, build_persistable_ai_execution_audit_payload,
    build_ai_execution_audit_persistence_plan, persist_ai_execution_audit_event,
)


def test_migration_matches_contract_and_preserves_legacy(monkeypatch):
    path = Path(__file__).parents[1] / "migrations/versions/20260916_1000_ai_mcp_audit_schema_v2.py"
    spec = importlib.util.spec_from_file_location("audit_v2_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements = []
    monkeypatch.setattr(migration, "op", SimpleNamespace(execute=statements.append))
    migration.upgrade()
    assert migration.down_revision == "20260913_1500"
    assert set(migration.INDEXES) == set(build_ai_execution_audit_persistence_plan().required_indexes)
    assert set(migration.NEW_COLUMNS) <= set(build_ai_execution_audit_persistence_plan().required_columns)
    assert "CREATE TABLE IF NOT EXISTS" in statements[0]
    assert all("ADD COLUMN IF NOT EXISTS" in sql for sql in statements[1:10])
    assert not any("UPDATE " in sql or "DELETE " in sql or "DROP " in sql for sql in statements)
    before = list(statements)
    migration.downgrade()
    assert statements == before


def test_structured_oauth_policy_payload():
    record = build_ai_execution_audit_record(
        event_type="mcp.tool_policy.allowed", runtime="mcp", status="allowed",
        company_id=9, principal_id=71, auth_method="oauth", client_id="codex",
        surface="admin", token_scopes=["mcp:access", "mcp:admin"],
        policy_allowed=True, policy_reason="ok", approval_request_id=321,
        payload_digest="a" * 64,
    )
    payload = build_persistable_ai_execution_audit_payload(record)
    assert payload["principal_id"] == 71
    assert payload["policy_allowed"] is True
    assert payload["approval_request_id"] == 321
    assert payload["token_scopes"] == ["mcp:access", "mcp:admin"]


def test_persistence_uses_own_transaction_without_runtime_ddl(monkeypatch):
    import sys
    from contextlib import contextmanager
    captured = []
    @contextmanager
    def begin():
        yield SimpleNamespace(execute=lambda sql, params: captured.append((str(sql), params)))
    monkeypatch.setitem(sys.modules, "models", SimpleNamespace(
        db=SimpleNamespace(engine=SimpleNamespace(begin=begin)),
    ))
    record = build_ai_execution_audit_record(event_type="mcp.read", runtime="mcp", status="allowed", company_id=9)
    persist_ai_execution_audit_event(record)
    assert len(captured) == 1
    sql, params = captured[0]
    assert sql.startswith("INSERT INTO")
    assert "CREATE" not in sql and "ALTER" not in sql
    assert params["token_scopes"] == "[]"
    assert params["company_id"] == 9
