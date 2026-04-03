"""create routine journey bindings

Revision ID: 20260403_1800
Revises: 20260403_1600
Create Date: 2026-04-03 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '20260403_1800'
down_revision = '20260403_1600'
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get('name') == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(inspector, index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(inspector, table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, 'routine_journey_bindings'):
        op.create_table(
            'routine_journey_bindings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('routine_id', sa.Integer(), nullable=False),
            sa.Column('employee_id', sa.Integer(), nullable=False),
            sa.Column('block_id', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['block_id'], ['work_journey_blocks.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['routine_id'], ['routines.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id', 'routine_id', 'employee_id', name='uq_routine_journey_binding'),
        )
        inspector = sa.inspect(bind)

    _create_index_if_missing(inspector, 'ix_routine_journey_bindings_company_id', 'routine_journey_bindings', ['company_id'])
    _create_index_if_missing(inspector, 'ix_routine_journey_bindings_routine_id', 'routine_journey_bindings', ['routine_id'])
    _create_index_if_missing(inspector, 'ix_routine_journey_bindings_employee_id', 'routine_journey_bindings', ['employee_id'])
    _create_index_if_missing(inspector, 'ix_routine_journey_bindings_block_id', 'routine_journey_bindings', ['block_id'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, 'routine_journey_bindings'):
        return

    table_indexes = {index.get('name') for index in inspector.get_indexes('routine_journey_bindings')}
    for index_name in [
        'ix_routine_journey_bindings_block_id',
        'ix_routine_journey_bindings_employee_id',
        'ix_routine_journey_bindings_routine_id',
        'ix_routine_journey_bindings_company_id',
    ]:
        if index_name in table_indexes:
            op.drop_index(index_name, table_name='routine_journey_bindings')
    op.drop_table('routine_journey_bindings')
