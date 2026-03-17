"""reconcile_incentive_calculations_schema

Revision ID: 20260317_0905
Revises: 20260316_1845
Create Date: 2026-03-17 09:05:00.000000

Descrição:
    Reconcilia colunas opcionais das tabelas centrais do módulo de
    incentivos para compatibilidade com o model atual.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_0905"
down_revision = "20260316_1845"
branch_labels = None
depends_on = None


def _table_columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _add_column_if_missing(inspector, table_name: str, column_name: str, ddl: str):
    if not inspector.has_table(table_name):
        return
    if column_name in _table_columns(inspector, table_name):
        return
    op.execute(sa.text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _add_column_if_missing(inspector, "incentive_rule_sets", "description", "description TEXT")
    _add_column_if_missing(inspector, "incentive_rule_sets", "version", "version INTEGER DEFAULT 1")
    _add_column_if_missing(inspector, "incentive_rule_sets", "is_active", "is_active BOOLEAN DEFAULT TRUE")
    _add_column_if_missing(inspector, "incentive_rule_sets", "valid_from", "valid_from DATE")
    _add_column_if_missing(inspector, "incentive_rule_sets", "valid_to", "valid_to DATE")
    _add_column_if_missing(inspector, "incentive_rule_sets", "max_red_total", "max_red_total NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rule_sets", "max_mult_total", "max_mult_total NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rule_sets", "created_at", "created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()")
    _add_column_if_missing(inspector, "incentive_rule_sets", "updated_at", "updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()")

    _add_column_if_missing(inspector, "incentive_calculations", "status", "status VARCHAR(20) DEFAULT 'preview'")
    _add_column_if_missing(inspector, "incentive_calculations", "total_distributed", "total_distributed NUMERIC(15, 2)")
    _add_column_if_missing(inspector, "incentive_calculations", "participants_count", "participants_count INTEGER")
    _add_column_if_missing(inspector, "incentive_calculations", "results_payload", "results_payload JSON")
    _add_column_if_missing(inspector, "incentive_calculations", "created_at", "created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()")


def downgrade():
    pass
