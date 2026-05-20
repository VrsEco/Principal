"""create company role permission presets

Revision ID: 20260519_1200
Revises: 20260517_1600
Create Date: 2026-05-19 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260519_1200"
down_revision = "20260517_1600"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "company_role_permission_presets" not in existing_tables:
        op.create_table(
            "company_role_permission_presets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("preset_key", sa.String(length=140), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint(
                "company_id",
                "preset_key",
                name="uq_company_role_permission_presets_company_key",
            ),
        )
        op.create_index(
            "ix_company_role_permission_presets_company_id",
            "company_role_permission_presets",
            ["company_id"],
            unique=False,
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "company_role_permission_presets" in existing_tables:
        indexes = {
            index["name"]
            for index in inspector.get_indexes("company_role_permission_presets")
        }
        if "ix_company_role_permission_presets_company_id" in indexes:
            op.drop_index(
                "ix_company_role_permission_presets_company_id",
                table_name="company_role_permission_presets",
            )
        op.drop_table("company_role_permission_presets")
