"""create work journey agendas

Revision ID: 20260403_2010
Revises: 20260403_1910
Create Date: 2026-04-03 20:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260403_2010'
down_revision = '20260403_1910'
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _create_index_if_missing(inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    existing_indexes = {index['name'] for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        return
    op.create_index(index_name, table_name, columns)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, 'work_journey_agendas'):
        op.create_table(
            'work_journey_agendas',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
            sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
            sa.Column('anchor_date', sa.Date(), nullable=False),
            sa.Column('scope', sa.String(length=20), nullable=False, server_default='day'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='suggested'),
            sa.Column('engine_version', sa.String(length=30), nullable=False, server_default='agendas-v1'),
            sa.Column('summary_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column('generated_at', sa.DateTime(), nullable=True),
            sa.Column('locked_at', sa.DateTime(), nullable=True),
            sa.Column('locked_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.UniqueConstraint('company_id', 'employee_id', 'anchor_date', 'scope', name='uq_work_journey_agendas_scope'),
        )
    inspector = inspect(bind)
    _create_index_if_missing(inspector, 'work_journey_agendas', 'ix_work_journey_agendas_company_id', ['company_id'])
    _create_index_if_missing(inspector, 'work_journey_agendas', 'ix_work_journey_agendas_employee_id', ['employee_id'])
    _create_index_if_missing(inspector, 'work_journey_agendas', 'ix_work_journey_agendas_anchor_date', ['anchor_date'])
    _create_index_if_missing(inspector, 'work_journey_agendas', 'ix_work_journey_agendas_scope', ['scope'])
    _create_index_if_missing(inspector, 'work_journey_agendas', 'ix_work_journey_agendas_status', ['status'])

    if not _has_table(inspector, 'work_journey_agenda_items'):
        op.create_table(
            'work_journey_agenda_items',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('work_journey_agendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
            sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
            sa.Column('journey_item_id', sa.Integer(), sa.ForeignKey('work_journey_items.id', ondelete='SET NULL'), nullable=True),
            sa.Column('block_id', sa.Integer(), sa.ForeignKey('work_journey_blocks.id', ondelete='SET NULL'), nullable=True),
            sa.Column('planned_date', sa.Date(), nullable=False),
            sa.Column('position_index', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('allocated_minutes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('planned_start_minutes', sa.Integer(), nullable=True),
            sa.Column('planned_end_minutes', sa.Integer(), nullable=True),
            sa.Column('overflow_minutes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_fixed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('is_over_capacity', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('manual_override', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('metadata_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        )
    inspector = inspect(bind)
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_agenda_id', ['agenda_id'])
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_company_id', ['company_id'])
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_employee_id', ['employee_id'])
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_journey_item_id', ['journey_item_id'])
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_block_id', ['block_id'])
    _create_index_if_missing(inspector, 'work_journey_agenda_items', 'ix_work_journey_agenda_items_planned_date', ['planned_date'])
    _create_index_if_missing(
        inspector,
        'work_journey_agenda_items',
        'ix_work_journey_agenda_items_agenda_day_position',
        ['agenda_id', 'planned_date', 'position_index'],
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, 'work_journey_agenda_items'):
        op.drop_table('work_journey_agenda_items')
    inspector = inspect(bind)
    if _has_table(inspector, 'work_journey_agendas'):
        op.drop_table('work_journey_agendas')
