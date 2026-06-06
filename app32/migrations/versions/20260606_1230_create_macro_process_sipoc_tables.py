"""create macro process sipoc tables

Revision ID: 20260606_1230
Revises: 20260606_1100
Create Date: 2026-06-06 12:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260606_1230"
down_revision = "20260606_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "macro_process_sipoc_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("macro_process_id", sa.Integer(), sa.ForeignKey("macro_processes.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("start_boundary", sa.Text(), nullable=True),
        sa.Column("end_boundary", sa.Text(), nullable=True),
        sa.Column("trigger_event", sa.Text(), nullable=True),
        sa.Column("customer_requirements", sa.Text(), nullable=True),
        sa.Column("constraints_notes", sa.Text(), nullable=True),
        sa.Column("measures_notes", sa.Text(), nullable=True),
        sa.Column("risks_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("macro_process_id", "version", name="uq_macro_process_sipoc_snapshot_macro_version"),
    )
    op.create_index("ix_macro_process_sipoc_snapshots_company_id", "macro_process_sipoc_snapshots", ["company_id"])
    op.create_index("ix_macro_process_sipoc_snapshots_macro_process_id", "macro_process_sipoc_snapshots", ["macro_process_id"])

    op.create_table(
        "macro_process_sipoc_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("sipoc_snapshot_id", sa.Integer(), sa.ForeignKey("macro_process_sipoc_snapshots.id"), nullable=False),
        sa.Column("lane", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_type", sa.String(length=30), nullable=True),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_macro_process_sipoc_items_company_id", "macro_process_sipoc_items", ["company_id"])
    op.create_index("ix_macro_process_sipoc_items_sipoc_snapshot_id", "macro_process_sipoc_items", ["sipoc_snapshot_id"])

    op.create_table(
        "macro_process_sipoc_regulatory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("sipoc_snapshot_id", sa.Integer(), sa.ForeignKey("macro_process_sipoc_snapshots.id"), nullable=False),
        sa.Column("sipoc_item_id", sa.Integer(), sa.ForeignKey("macro_process_sipoc_items.id"), nullable=True),
        sa.Column("regulatory_domain", sa.String(length=120), nullable=False),
        sa.Column("regulatory_code", sa.String(length=120), nullable=True),
        sa.Column("regulatory_name", sa.String(length=255), nullable=False),
        sa.Column("regulator_entity", sa.String(length=255), nullable=True),
        sa.Column("requirement_summary", sa.Text(), nullable=True),
        sa.Column("affected_scope_type", sa.String(length=30), nullable=False, server_default="process"),
        sa.Column("control_requirements", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("evidence_requirements", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_macro_process_sipoc_regulatory_items_company_id", "macro_process_sipoc_regulatory_items", ["company_id"])
    op.create_index("ix_macro_process_sipoc_regulatory_items_sipoc_snapshot_id", "macro_process_sipoc_regulatory_items", ["sipoc_snapshot_id"])
    op.create_index("ix_macro_process_sipoc_regulatory_items_sipoc_item_id", "macro_process_sipoc_regulatory_items", ["sipoc_item_id"])


def downgrade():
    op.drop_index("ix_macro_process_sipoc_regulatory_items_sipoc_item_id", table_name="macro_process_sipoc_regulatory_items")
    op.drop_index("ix_macro_process_sipoc_regulatory_items_sipoc_snapshot_id", table_name="macro_process_sipoc_regulatory_items")
    op.drop_index("ix_macro_process_sipoc_regulatory_items_company_id", table_name="macro_process_sipoc_regulatory_items")
    op.drop_table("macro_process_sipoc_regulatory_items")

    op.drop_index("ix_macro_process_sipoc_items_sipoc_snapshot_id", table_name="macro_process_sipoc_items")
    op.drop_index("ix_macro_process_sipoc_items_company_id", table_name="macro_process_sipoc_items")
    op.drop_table("macro_process_sipoc_items")

    op.drop_index("ix_macro_process_sipoc_snapshots_macro_process_id", table_name="macro_process_sipoc_snapshots")
    op.drop_index("ix_macro_process_sipoc_snapshots_company_id", table_name="macro_process_sipoc_snapshots")
    op.drop_table("macro_process_sipoc_snapshots")
