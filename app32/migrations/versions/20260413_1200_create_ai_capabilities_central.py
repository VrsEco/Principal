"""create ai capabilities central tables

Revision ID: 20260413_1200
Revises: 20260405_1830
Create Date: 2026-04-13 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_1200"
down_revision = "20260405_1830"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(inspector, index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(inspector, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "ai_capabilities"):
        op.create_table(
            "ai_capabilities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(length=160), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("domain", sa.String(length=80), nullable=False),
            sa.Column("capability_type", sa.String(length=40), nullable=False, server_default="feature"),
            sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("rollout_status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("origin", sa.String(length=30), nullable=False, server_default="system"),
            sa.Column("source_ref", sa.String(length=180), nullable=True),
            sa.Column("requires_human_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_active_company", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("requires_user_binding", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("technical_binding_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("supported_channels_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("supported_surfaces_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("default_settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("key", name="uq_ai_capabilities_key"),
        )
        inspector = sa.inspect(bind)

    for idx, cols in {
        "ix_ai_capabilities_key": ["key"],
        "ix_ai_capabilities_domain": ["domain"],
        "ix_ai_capabilities_type": ["capability_type"],
        "ix_ai_capabilities_status": ["status"],
        "ix_ai_capabilities_rollout": ["rollout_status"],
        "ix_ai_capabilities_origin": ["origin"],
    }.items():
        _create_index_if_missing(inspector, idx, "ai_capabilities", cols)

    if not _has_table(inspector, "ai_capability_grants"):
        op.create_table(
            "ai_capability_grants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capability_id", sa.Integer(), nullable=False),
            sa.Column("scope_type", sa.String(length=20), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("role_id", sa.Integer(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("channels_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("valid_from", sa.DateTime(), nullable=True),
            sa.Column("valid_until", sa.DateTime(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["capability_id"], ["ai_capabilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("capability_id", "scope_type", "company_id", "user_id", "role_id", name="uq_ai_capability_grants_scope"),
        )
        inspector = sa.inspect(bind)

    for idx, cols in {
        "ix_ai_capability_grants_capability": ["capability_id"],
        "ix_ai_capability_grants_scope": ["scope_type"],
        "ix_ai_capability_grants_company": ["company_id"],
        "ix_ai_capability_grants_user": ["user_id"],
        "ix_ai_capability_grants_role": ["role_id"],
        "ix_ai_capability_grants_enabled": ["is_enabled"],
    }.items():
        _create_index_if_missing(inspector, idx, "ai_capability_grants", cols)

    if not _has_table(inspector, "ai_capability_company_settings"):
        op.create_table(
            "ai_capability_company_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capability_id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["capability_id"], ["ai_capabilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("capability_id", "company_id", name="uq_ai_capability_company_settings"),
        )
        inspector = sa.inspect(bind)

    for idx, cols in {
        "ix_ai_capability_company_settings_capability": ["capability_id"],
        "ix_ai_capability_company_settings_company": ["company_id"],
        "ix_ai_capability_company_settings_enabled": ["is_enabled"],
    }.items():
        _create_index_if_missing(inspector, idx, "ai_capability_company_settings", cols)

    if not _has_table(inspector, "ai_capability_audit_logs"):
        op.create_table(
            "ai_capability_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capability_id", sa.Integer(), nullable=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=60), nullable=False),
            sa.Column("result", sa.String(length=20), nullable=False, server_default="success"),
            sa.Column("channel", sa.String(length=50), nullable=True),
            sa.Column("surface", sa.String(length=40), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["capability_id"], ["ai_capabilities.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        inspector = sa.inspect(bind)

    for idx, cols in {
        "ix_ai_capability_audit_logs_capability": ["capability_id"],
        "ix_ai_capability_audit_logs_company": ["company_id"],
        "ix_ai_capability_audit_logs_user": ["user_id"],
        "ix_ai_capability_audit_logs_actor": ["actor_user_id"],
        "ix_ai_capability_audit_logs_event": ["event_type"],
        "ix_ai_capability_audit_logs_result": ["result"],
        "ix_ai_capability_audit_logs_created_at": ["created_at"],
    }.items():
        _create_index_if_missing(inspector, idx, "ai_capability_audit_logs", cols)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in [
        "ai_capability_audit_logs",
        "ai_capability_company_settings",
        "ai_capability_grants",
        "ai_capabilities",
    ]:
        if _has_table(inspector, table_name):
            op.drop_table(table_name)
            inspector = sa.inspect(bind)
