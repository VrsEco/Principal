"""Cria o ledger tenant-safe de deploys do Squad Engenharia e seus eventos append-only.

Revision ID: 20260924_1300
Revises: 20260923_1200
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_1300"
down_revision = "20260923_1200"
branch_labels = None
depends_on = None

_APPEND_ONLY_FN = "agent_deployment_events_append_only"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("agent_deployments"):
        op.create_table(
            "agent_deployments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("requested_by_principal_id", sa.Integer(), sa.ForeignKey("identity_principals.id", ondelete="SET NULL")),
            sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("actor_subject", sa.String(255), nullable=False),
            sa.Column("actor_client_id", sa.String(255), nullable=False),
            sa.Column("actor_kind", sa.String(16), nullable=False),
            sa.Column("mode", sa.String(16), nullable=False),
            sa.Column("restart_mcp", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("target_sha", sa.String(40), nullable=False),
            sa.Column("correlation_id", sa.String(64), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="pending_approval"),
            sa.Column("approved_by_principal_id", sa.Integer(), sa.ForeignKey("identity_principals.id", ondelete="SET NULL")),
            sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("approved_by_subject", sa.String(255)),
            sa.Column("approved_at", sa.DateTime()),
            sa.Column("github_run_id", sa.BigInteger()),
            sa.Column("github_run_attempt", sa.Integer()),
            sa.Column("github_actor", sa.String(255)),
            sa.Column("github_triggering_actor", sa.String(255)),
            sa.Column("github_workflow_ref", sa.String(512)),
            sa.Column("github_sha", sa.String(40)),
            sa.Column("github_run_url", sa.String(512)),
            sa.Column("failure_reason", sa.String(255)),
            sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("finished_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("correlation_id", name="uq_agent_deployment_correlation"),
        )
        op.create_index("ix_agent_deployment_company_status_created", "agent_deployments", ["company_id", "status", "created_at"])
        op.create_index("ix_agent_deployments_company_id", "agent_deployments", ["company_id"])

    if not inspector.has_table("agent_deployment_events"):
        op.create_table(
            "agent_deployment_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deployment_id", sa.Integer(), sa.ForeignKey("agent_deployments.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("event_type", sa.String(32), nullable=False),
            sa.Column("from_status", sa.String(24)),
            sa.Column("to_status", sa.String(24)),
            sa.Column("source", sa.String(16), nullable=False),
            sa.Column("actor_ref", sa.String(255)),
            sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_agent_deployment_event_deployment", "agent_deployment_events", ["deployment_id", "id"])
        op.create_index("ix_agent_deployment_events_company_id", "agent_deployment_events", ["company_id"])

    if bind.dialect.name == "postgresql":
        # Defesa em profundidade: mesmo com SQL direto, eventos não são reescritos.
        op.execute(
            f"""
            CREATE OR REPLACE FUNCTION {_APPEND_ONLY_FN}() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'agent_deployment_events é append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_APPEND_ONLY_FN} ON agent_deployment_events")
        op.execute(
            f"CREATE TRIGGER trg_{_APPEND_ONLY_FN} BEFORE UPDATE OR DELETE ON agent_deployment_events "
            f"FOR EACH ROW EXECUTE FUNCTION {_APPEND_ONLY_FN}()"
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("agent_deployment_events"):
        if bind.dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER IF EXISTS trg_{_APPEND_ONLY_FN} ON agent_deployment_events")
        op.drop_table("agent_deployment_events")
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP FUNCTION IF EXISTS {_APPEND_ONLY_FN}()")
    if inspector.has_table("agent_deployments"):
        op.drop_table("agent_deployments")
