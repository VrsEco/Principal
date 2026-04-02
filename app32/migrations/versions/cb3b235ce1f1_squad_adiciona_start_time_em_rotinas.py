"""SQUAD: Adiciona start_time em rotinas

Revision ID: cb3b235ce1f1
Revises: 20260329_2030
Create Date: 2026-03-31 17:23:54.546902

Esta revisão foi saneada para evitar operações destrutivas indevidas.
O objetivo funcional válido desta migration é garantir a coluna
``routines.start_time`` com valor padrão operacional.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "cb3b235ce1f1"
down_revision = "20260329_2030"
branch_labels = None
depends_on = None


TABLE_NAME = "routines"
COLUMN_NAME = "start_time"
DEFAULT_VALUE = "00:01"


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    """Garantir coluna start_time em routines sem destruir schema existente."""
    if not _table_exists(TABLE_NAME):
        return

    if not _column_exists(TABLE_NAME, COLUMN_NAME):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                COLUMN_NAME,
                sa.String(length=10),
                nullable=False,
                server_default=sa.text(f"'{DEFAULT_VALUE}'"),
            ),
        )

    op.execute(
        sa.text(f"UPDATE {TABLE_NAME} SET {COLUMN_NAME} = :default_value WHERE {COLUMN_NAME} IS NULL").bindparams(
            default_value=DEFAULT_VALUE
        )
    )

    op.alter_column(
        TABLE_NAME,
        COLUMN_NAME,
        existing_type=sa.String(length=10),
        nullable=False,
        server_default=sa.text(f"'{DEFAULT_VALUE}'"),
    )


def downgrade() -> None:
    """Reverter apenas a coluna adicionada quando presente."""
    if _column_exists(TABLE_NAME, COLUMN_NAME):
        op.drop_column(TABLE_NAME, COLUMN_NAME)
