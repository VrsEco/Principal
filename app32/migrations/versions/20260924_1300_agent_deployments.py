"""Cria o ledger tenant-safe de deploys solicitados por agentes.

Revision ID: 20260924_1300
Revises: 20260923_1200
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_1300"
down_revision = "20260923_1200"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("agent_deployments"):
        return
    op.create_table(
        "agent_deployments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by_principal_id", sa.Integer(), sa.ForeignKey("identity_principals.id", ondelete="SET NULL")),
        sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_subject", sa.String(255), nullable=False),
        sa.Column("actor_client_id", sa.String(255), nullable=False),
        sa.Column("actor_kind", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("restart_mcp", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("target_sha", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="requested"),
        sa.Column("github_run_url", sa.String(512)),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("company_id", "correlation_id", name="uq_agent_deployment_company_correlation"),
    )
    op.create_index("ix_agent_deployment_company_status_created", "agent_deployments", ["company_id", "status", "created_at"])


def downgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("agent_deployments"):
        op.drop_table("agent_deployments")
