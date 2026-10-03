"""Blocos de jornada da pessoa (Fase 3 da agenda unificada).

Tabela `person_work_blocks` por usuario (sem company_id, decisao D3 da SPEC) e colunas
`person_block_id` nulas e retrocompativeis. Nada historico e reescrito; os `block_id`
legados continuam validos.

Revision ID: 20261004_1000
Revises: 20261003_1100
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20261004_1000"
down_revision = "20261003_1100"
branch_labels = None
depends_on = None

TABLE = "person_work_blocks"
LINKED_TABLES = ("work_journey_agenda_items", "routine_journey_bindings", "work_calendar_events")


def _has_column(inspector, table, column) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("block_mode", sa.String(30), nullable=False, server_default="operational"),
            sa.Column("weekdays_json", sa.JSON(), nullable=False),
            sa.Column("preferred_item_types", sa.JSON(), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("end_time > start_time", name="ck_person_work_blocks_time_order"),
        )
        op.create_index("ix_person_work_blocks_user_active", TABLE, ["user_id", "is_active"])

    inspector = sa.inspect(bind)
    for table in LINKED_TABLES:
        if inspector.has_table(table) and not _has_column(inspector, table, "person_block_id"):
            op.add_column(
                table,
                sa.Column("person_block_id", sa.Integer(), sa.ForeignKey(f"{TABLE}.id", ondelete="SET NULL"), nullable=True),
            )
            op.create_index(f"ix_{table}_person_block_id", table, ["person_block_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in LINKED_TABLES:
        if inspector.has_table(table) and _has_column(inspector, table, "person_block_id"):
            op.drop_index(f"ix_{table}_person_block_id", table_name=table)
            op.drop_column(table, "person_block_id")
    if inspector.has_table(TABLE):
        op.drop_table(TABLE)
