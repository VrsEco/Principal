"""Eventos de uso da Agenda (sem conteúdo dos itens), para medir adoção.

Revision ID: 20261003_1100
Revises: 20261002_1000
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261003_1100"
down_revision = "20261002_1000"
branch_labels = None
depends_on = None

TABLE = "agenda_ui_events"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABLE):
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("detail", sa.String(40)),
        sa.Column("device", sa.String(10)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_agenda_ui_events_company_created", TABLE, ["company_id", "created_at"])
    op.create_index("ix_agenda_ui_events_event_created", TABLE, ["event", "created_at"])


def downgrade() -> None:
    op.drop_table(TABLE)
