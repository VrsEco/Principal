"""reconcile_incentive_rules_schema

Revision ID: 20260316_1845
Revises: 20260316_1900
Create Date: 2026-03-16 18:45:00.000000

Descrição:
    Reconcilia colunas legadas da tabela incentive_rules para compatibilidade
    com o model atual de incentivos.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_1845"
down_revision = "20260316_1900"
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

    _add_column_if_missing(inspector, "incentive_rules", "impact_value", "impact_value NUMERIC(15, 4) DEFAULT 1.0")
    _add_column_if_missing(inspector, "incentive_rules", "weight", "weight NUMERIC(10, 4) DEFAULT 1.0")
    _add_column_if_missing(inspector, "incentive_rules", "use_indicator_goal", "use_indicator_goal BOOLEAN DEFAULT TRUE")
    _add_column_if_missing(inspector, "incentive_rules", "calculation_mode", "calculation_mode VARCHAR(30) DEFAULT 'ranges'")
    _add_column_if_missing(inspector, "incentive_rules", "ranges_config", "ranges_config JSON")
    _add_column_if_missing(inspector, "incentive_rules", "target_value", "target_value NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rules", "min_threshold", "min_threshold NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rules", "max_cap", "max_cap NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rules", "max_reduction", "max_reduction NUMERIC(15, 4)")
    _add_column_if_missing(inspector, "incentive_rules", "impact_type", "impact_type VARCHAR(20) DEFAULT 'multiplier'")
    _add_column_if_missing(inspector, "incentive_rules", "order_index", "order_index INTEGER DEFAULT 0")


def downgrade():
    pass
