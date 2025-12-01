"""add app compliance report tables

Revision ID: 20251201_1700
Revises: 20251201_add_cadastro_sessions
Create Date: 2025-12-01 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251201_1700"
down_revision = "20251201_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_compliance_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("requested_code", sa.String(length=16), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ok_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("overview", sa.JSON(), nullable=True),
    )

    op.create_table(
        "app_compliance_report_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("app_compliance_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_code", sa.String(length=16), nullable=True),
        sa.Column("page_name", sa.String(length=256), nullable=True),
        sa.Column("page_route", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("primary_issue", sa.String(length=512), nullable=True),
        sa.Column("checks", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_table("app_compliance_report_items")
    op.drop_table("app_compliance_reports")
