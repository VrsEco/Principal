"""create work journey core tables

Revision ID: 20260403_1600
Revises: 20260402_1200
Create Date: 2026-04-03 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '20260403_1600'
down_revision = '20260402_1200'
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

    if not _has_table(inspector, 'work_journey_blocks'):
        op.create_table(
            'work_journey_blocks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('employee_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=160), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('start_time', sa.Time(), nullable=False),
            sa.Column('end_time', sa.Time(), nullable=False),
            sa.Column('weekdays_json', sa.JSON(), nullable=False),
            sa.Column('accepted_item_types', sa.JSON(), nullable=False),
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, 'ix_work_journey_blocks_company_id', 'work_journey_blocks', ['company_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_blocks_employee_id', 'work_journey_blocks', ['employee_id'])

    if not _has_table(inspector, 'work_journey_rules'):
        op.create_table(
            'work_journey_rules',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('employee_id', sa.Integer(), nullable=False),
            sa.Column('preferred_block_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=180), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('item_type', sa.String(length=40), nullable=False, server_default='manual'),
            sa.Column('recurrence_type', sa.String(length=40), nullable=False, server_default='daily'),
            sa.Column('recurrence_config', sa.JSON(), nullable=False),
            sa.Column('estimated_minutes', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['preferred_block_id'], ['work_journey_blocks.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, 'ix_work_journey_rules_company_id', 'work_journey_rules', ['company_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_rules_employee_id', 'work_journey_rules', ['employee_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_rules_preferred_block_id', 'work_journey_rules', ['preferred_block_id'])

    if not _has_table(inspector, 'work_journey_items'):
        op.create_table(
            'work_journey_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('employee_id', sa.Integer(), nullable=False),
            sa.Column('block_id', sa.Integer(), nullable=True),
            sa.Column('rule_id', sa.Integer(), nullable=True),
            sa.Column('item_type', sa.String(length=40), nullable=False, server_default='manual'),
            sa.Column('source_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('recurrence_type', sa.String(length=40), nullable=True),
            sa.Column('occurrence_date', sa.Date(), nullable=True),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('estimated_minutes', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('worked_minutes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
            sa.Column('metadata_json', sa.JSON(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('last_synced_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['block_id'], ['work_journey_blocks.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['rule_id'], ['work_journey_rules.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id', 'item_type', 'source_id', name='uq_work_journey_items_source'),
            sa.UniqueConstraint('company_id', 'rule_id', 'occurrence_date', name='uq_work_journey_items_rule_occurrence'),
        )
        inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, 'ix_work_journey_items_company_id', 'work_journey_items', ['company_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_employee_id', 'work_journey_items', ['employee_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_block_id', 'work_journey_items', ['block_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_rule_id', 'work_journey_items', ['rule_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_item_type', 'work_journey_items', ['item_type'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_source_id', 'work_journey_items', ['source_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_occurrence_date', 'work_journey_items', ['occurrence_date'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_due_date', 'work_journey_items', ['due_date'])
    _create_index_if_missing(inspector, 'ix_work_journey_items_status', 'work_journey_items', ['status'])

    if not _has_table(inspector, 'work_journey_absence_requests'):
        op.create_table(
            'work_journey_absence_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('employee_id', sa.Integer(), nullable=False),
            sa.Column('requested_by_user_id', sa.Integer(), nullable=True),
            sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
            sa.Column('absence_type', sa.String(length=40), nullable=False, server_default='vacation'),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
            sa.Column('cleanup_notes', sa.Text(), nullable=True),
            sa.Column('metadata_json', sa.JSON(), nullable=False),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, 'ix_work_journey_absence_requests_company_id', 'work_journey_absence_requests', ['company_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_absence_requests_employee_id', 'work_journey_absence_requests', ['employee_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_absence_requests_start_date', 'work_journey_absence_requests', ['start_date'])
    _create_index_if_missing(inspector, 'ix_work_journey_absence_requests_end_date', 'work_journey_absence_requests', ['end_date'])
    _create_index_if_missing(inspector, 'ix_work_journey_absence_requests_status', 'work_journey_absence_requests', ['status'])

    if not _has_table(inspector, 'work_journey_transfer_requests'):
        op.create_table(
            'work_journey_transfer_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=False),
            sa.Column('from_employee_id', sa.Integer(), nullable=False),
            sa.Column('to_employee_id', sa.Integer(), nullable=False),
            sa.Column('requested_by_user_id', sa.Integer(), nullable=True),
            sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
            sa.Column('resolution_notes', sa.Text(), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['from_employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['item_id'], ['work_journey_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['to_employee_id'], ['employees.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, 'ix_work_journey_transfer_requests_company_id', 'work_journey_transfer_requests', ['company_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_transfer_requests_item_id', 'work_journey_transfer_requests', ['item_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_transfer_requests_from_employee_id', 'work_journey_transfer_requests', ['from_employee_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_transfer_requests_to_employee_id', 'work_journey_transfer_requests', ['to_employee_id'])
    _create_index_if_missing(inspector, 'ix_work_journey_transfer_requests_status', 'work_journey_transfer_requests', ['status'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in [
        ('work_journey_transfer_requests', [
            'ix_work_journey_transfer_requests_status',
            'ix_work_journey_transfer_requests_to_employee_id',
            'ix_work_journey_transfer_requests_from_employee_id',
            'ix_work_journey_transfer_requests_item_id',
            'ix_work_journey_transfer_requests_company_id',
        ]),
        ('work_journey_absence_requests', [
            'ix_work_journey_absence_requests_status',
            'ix_work_journey_absence_requests_end_date',
            'ix_work_journey_absence_requests_start_date',
            'ix_work_journey_absence_requests_employee_id',
            'ix_work_journey_absence_requests_company_id',
        ]),
        ('work_journey_items', [
            'ix_work_journey_items_status',
            'ix_work_journey_items_due_date',
            'ix_work_journey_items_occurrence_date',
            'ix_work_journey_items_source_id',
            'ix_work_journey_items_item_type',
            'ix_work_journey_items_rule_id',
            'ix_work_journey_items_block_id',
            'ix_work_journey_items_employee_id',
            'ix_work_journey_items_company_id',
        ]),
        ('work_journey_rules', [
            'ix_work_journey_rules_preferred_block_id',
            'ix_work_journey_rules_employee_id',
            'ix_work_journey_rules_company_id',
        ]),
        ('work_journey_blocks', [
            'ix_work_journey_blocks_employee_id',
            'ix_work_journey_blocks_company_id',
        ]),
    ]:
        if not _has_table(inspector, table_name):
            continue
        table_indexes = {index.get('name') for index in inspector.get_indexes(table_name)}
        for index_name in indexes:
            if index_name in table_indexes:
                op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
        inspector = sa.inspect(bind)
