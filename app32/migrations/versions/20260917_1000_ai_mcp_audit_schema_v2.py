"""Own IA/MCP audit schema in Alembic and add OAuth/policy fields.

Legacy rows and metadata are preserved. No parsing of untrusted legacy metadata.
"""
from alembic import op

revision = "20260917_1000"
down_revision = ("20260913_1500", "20260916_1000")
branch_labels = None
depends_on = None

NEW_COLUMNS = {
    "principal_id": "INTEGER",
    "auth_method": "VARCHAR(40)",
    "client_id": "VARCHAR(200)",
    "surface": "VARCHAR(40)",
    "token_scopes": "JSONB NOT NULL DEFAULT '[]'::jsonb",
    "policy_allowed": "BOOLEAN",
    "policy_reason": "VARCHAR(500)",
    "approval_request_id": "INTEGER",
    "payload_digest": "VARCHAR(64)",
}
INDEXES = {
    "ix_ai_mcp_audit_events_company_occurred_at": "company_id, occurred_at DESC",
    "ix_ai_mcp_audit_events_user_occurred_at": "user_id, occurred_at DESC",
    "ix_ai_mcp_audit_events_runtime_tool_occurred_at": "runtime, tool_name, occurred_at DESC",
    "ix_ai_mcp_audit_events_trace_id": "trace_id",
    "ix_ai_mcp_audit_events_company_principal_time": "company_id, principal_id, occurred_at DESC",
    "ix_ai_mcp_audit_events_company_policy_time": "company_id, policy_allowed, occurred_at DESC",
    "ix_ai_mcp_audit_events_company_approval": "company_id, approval_request_id",
}


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_mcp_audit_events (
            id BIGSERIAL PRIMARY KEY,
            schema_version VARCHAR(40) NOT NULL,
            event_type VARCHAR(80) NOT NULL,
            runtime VARCHAR(40) NOT NULL,
            status VARCHAR(40) NOT NULL,
            domain VARCHAR(80), operation VARCHAR(120), tool_name VARCHAR(120),
            scope VARCHAR(40), company_id INTEGER, user_id INTEGER,
            thread_id VARCHAR(120), execution_id VARCHAR(120),
            request_id VARCHAR(120), trace_id VARCHAR(120),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    for name, sql_type in NEW_COLUMNS.items():
        op.execute(f"ALTER TABLE ai_mcp_audit_events ADD COLUMN IF NOT EXISTS {name} {sql_type}")
    for name, columns in INDEXES.items():
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON ai_mcp_audit_events ({columns})")


def downgrade():
    # Retain audit evidence even when runtime is rolled back. Additive schema is
    # compatible with the legacy writer; removal requires a retention decision.
    pass
