"""global_schema_reconciliation

Revision ID: 20260316_1900
Revises: 5db8307519c3
Create Date: 2026-03-16 19:00:00.000000

Descrição:
    Formaliza em Alembic a reconciliação de schema hoje aplicada
    defensivamente no startup da aplicação. Foco em compatibilidade
    com bancos legados já existentes em produção.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_1900"
down_revision = "5db8307519c3"
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


def _rename_column_if_needed(inspector, table_name: str, old_name: str, new_name: str):
    columns = _table_columns(inspector, table_name)
    if not columns:
        return
    if old_name in columns and new_name not in columns:
        op.execute(sa.text(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # users
    _add_column_if_missing(inspector, "users", "instagram", "instagram VARCHAR(100)")
    _add_column_if_missing(
        inspector,
        "users",
        "summary_delivery_channels",
        "summary_delivery_channels VARCHAR(100) NOT NULL DEFAULT 'telegram'",
    )

    # indicators
    _add_column_if_missing(inspector, "indicators", "indicator_type", "indicator_type VARCHAR(50) NOT NULL DEFAULT 'result'")
    _add_column_if_missing(inspector, "indicators", "source_module", "source_module VARCHAR(50) NOT NULL DEFAULT 'manual'")
    _add_column_if_missing(inspector, "indicators", "source_id", "source_id INTEGER")
    _add_column_if_missing(inspector, "indicators", "source_scope", "source_scope VARCHAR(50) NOT NULL DEFAULT 'company'")
    _add_column_if_missing(inspector, "indicators", "source_config", "source_config JSON")
    _add_column_if_missing(inspector, "indicators", "collection_mode", "collection_mode VARCHAR(30) NOT NULL DEFAULT 'manual'")
    _add_column_if_missing(inspector, "indicators", "aggregation_function", "aggregation_function VARCHAR(30) NOT NULL DEFAULT 'sum'")
    _add_column_if_missing(inspector, "indicators", "unit", "unit VARCHAR(50) DEFAULT 'pts'")
    _add_column_if_missing(inspector, "indicators", "polarity", "polarity VARCHAR(20) DEFAULT 'positive'")
    _add_column_if_missing(inspector, "indicators", "measurement_frequency", "measurement_frequency VARCHAR(30) DEFAULT 'monthly'")
    _add_column_if_missing(inspector, "indicators", "formula", "formula TEXT")
    _add_column_if_missing(inspector, "indicators", "process_id", "process_id INTEGER REFERENCES processes(id)")
    _add_column_if_missing(inspector, "indicators", "project_id", "project_id INTEGER REFERENCES projects(id)")
    _add_column_if_missing(inspector, "indicators", "responsible_id", "responsible_id INTEGER REFERENCES employees(id)")
    _add_column_if_missing(inspector, "indicators", "collaborators", "collaborators JSON")
    _add_column_if_missing(inspector, "indicators", "data_source", "data_source TEXT")
    _add_column_if_missing(inspector, "indicators", "notes", "notes TEXT")
    _add_column_if_missing(inspector, "indicators", "okr_reference", "okr_reference VARCHAR(255)")
    _add_column_if_missing(inspector, "indicators", "okr_level", "okr_level VARCHAR(50)")
    _add_column_if_missing(inspector, "indicators", "is_active", "is_active BOOLEAN DEFAULT TRUE")
    _add_column_if_missing(inspector, "indicators", "routine_id", "routine_id INTEGER REFERENCES routines(id)")

    # indicator_goals
    _add_column_if_missing(inspector, "indicator_goals", "performance_ranges", "performance_ranges JSON")
    _add_column_if_missing(inspector, "indicator_goals", "routine_id", "routine_id INTEGER REFERENCES routines(id)")
    _add_column_if_missing(inspector, "indicator_goals", "collection_method", "collection_method VARCHAR(50) DEFAULT 'manual'")

    # indicator_data
    _add_column_if_missing(inspector, "indicator_data", "indicator_id", "indicator_id INTEGER")
    if inspector.has_table("indicator_data") and inspector.has_table("indicator_goals"):
        op.execute(
            sa.text(
                """
                UPDATE indicator_data
                SET indicator_id = indicator_goals.indicator_id
                FROM indicator_goals
                WHERE indicator_data.goal_id = indicator_goals.id
                  AND indicator_data.indicator_id IS NULL
                """
            )
        )
    _rename_column_if_needed(inspector, "indicator_data", "record_date", "measured_date")
    inspector = sa.inspect(bind)
    _rename_column_if_needed(inspector, "indicator_data", "value", "measured_value")
    inspector = sa.inspect(bind)
    if inspector.has_table("indicator_data") and "measured_value" in _table_columns(inspector, "indicator_data"):
        op.execute(
            sa.text(
                """
                ALTER TABLE indicator_data
                ALTER COLUMN measured_value TYPE NUMERIC(15, 4)
                USING measured_value::numeric
                """
            )
        )
    _add_column_if_missing(inspector, "indicator_data", "period_start", "period_start DATE")
    _add_column_if_missing(inspector, "indicator_data", "period_end", "period_end DATE")
    _add_column_if_missing(inspector, "indicator_data", "employee_id", "employee_id INTEGER REFERENCES employees(id)")
    _add_column_if_missing(inspector, "indicator_data", "collaborator_id", "collaborator_id INTEGER REFERENCES employees(id)")
    _add_column_if_missing(inspector, "indicator_data", "source_ref", "source_ref VARCHAR(255)")
    _add_column_if_missing(inspector, "indicator_data", "evidence_payload", "evidence_payload JSON")
    _add_column_if_missing(inspector, "indicator_data", "routine_id", "routine_id INTEGER REFERENCES routines(id)")
    _add_column_if_missing(
        inspector,
        "indicator_data",
        "process_instance_id",
        "process_instance_id INTEGER REFERENCES process_instances(id)",
    )
    _add_column_if_missing(inspector, "indicator_data", "status", "status VARCHAR(30) DEFAULT 'draft'")
    _add_column_if_missing(inspector, "indicator_data", "is_manual", "is_manual BOOLEAN DEFAULT FALSE")


def downgrade():
    # Migração de reconciliação/compatibilidade. Downgrade deliberadamente no-op.
    pass
