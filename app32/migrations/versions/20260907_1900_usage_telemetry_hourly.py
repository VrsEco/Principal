"""Buckets horários de uso, sem dados sensíveis."""
from alembic import op
import sqlalchemy as sa

revision = '20260907_1900'
down_revision = '20260904_1800'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('usage_telemetry_hourly',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('bucket_started_at', sa.DateTime(), nullable=False), sa.Column('channel', sa.String(24), nullable=False, server_default='web'), sa.Column('usage_kind', sa.String(24), nullable=False, server_default='standard'),
        sa.Column('sessions_started', sa.Integer(), nullable=False, server_default='0'), sa.Column('active_seconds', sa.Integer(), nullable=False, server_default='0'), sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'), sa.Column('ai_request_count', sa.Integer(), nullable=False, server_default='0'), sa.Column('mcp_request_count', sa.Integer(), nullable=False, server_default='0'), sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'), sa.Column('latency_ms_total', sa.BigInteger(), nullable=False, server_default='0'), sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')), sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('company_id','user_id','bucket_started_at','channel','usage_kind', name='uq_usage_telemetry_hourly_bucket'), sa.CheckConstraint('sessions_started >= 0 AND active_seconds >= 0 AND request_count >= 0 AND ai_request_count >= 0 AND mcp_request_count >= 0 AND error_count >= 0 AND latency_ms_total >= 0', name='ck_usage_telemetry_nonnegative'))
    op.create_index('ix_usage_telemetry_company_bucket','usage_telemetry_hourly',['company_id','bucket_started_at'])
    op.create_index('ix_usage_telemetry_user_bucket','usage_telemetry_hourly',['user_id','bucket_started_at'])

def downgrade():
    op.drop_table('usage_telemetry_hourly')
