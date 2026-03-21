"""create financial classification rules

Revision ID: 20260319_0015
Revises: 20260318_2355
Create Date: 2026-03-19 00:15:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0015"
down_revision = "20260318_2355"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if not _has_table("financial_classification_rules"):
        op.create_table(
            "financial_classification_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("source_type", sa.String(length=20), nullable=True),
            sa.Column("field_name", sa.String(length=50), nullable=False),
            sa.Column("operator", sa.String(length=20), nullable=False, server_default="contains"),
            sa.Column("match_value", sa.String(length=255), nullable=False),
            sa.Column("entry_type", sa.String(length=30), nullable=True),
            sa.Column("movement_nature", sa.String(length=10), nullable=True),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("process_instance_id", sa.Integer(), nullable=True),
            sa.Column("routine_id", sa.Integer(), nullable=True),
            sa.Column("counterparty_hint", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
            sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
            sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
            sa.CheckConstraint("operator IN ('contains', 'equals', 'starts_with')", name="ck_financial_classification_rules_operator"),
        )

    for index_name, table_name, columns in [
        ("idx_financial_classification_rules_company_active", "financial_classification_rules", ["company_id", "is_active"]),
        ("idx_financial_classification_rules_company_priority", "financial_classification_rules", ["company_id", "priority"]),
    ]:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_classification_rules_company_priority", "financial_classification_rules"),
        ("idx_financial_classification_rules_company_active", "financial_classification_rules"),
    ]:
        if inspector.has_table(table_name):
            indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name)

    if inspector.has_table("financial_classification_rules"):
        op.drop_table("financial_classification_rules")
