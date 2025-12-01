"""add_missing_columns_to_projects

Revision ID: 20251130_1131
Revises: 
Create Date: 2025-11-30 11:31:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251130_1131'
down_revision = '20231123_0001_add_notes'  # Última migration válida
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to projects table"""
    
    # Check if columns already exist before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('projects')]
    
    # Add title column if it doesn't exist
    if 'title' not in existing_columns:
        op.add_column('projects', sa.Column('title', sa.String(length=255), nullable=False, server_default=''))
        # Remove server_default after adding
        op.alter_column('projects', 'title', server_default=None)
    
    # Add description column if it doesn't exist
    if 'description' not in existing_columns:
        op.add_column('projects', sa.Column('description', sa.Text(), nullable=True))
    
    # Add status column if it doesn't exist
    if 'status' not in existing_columns:
        op.add_column('projects', sa.Column('status', sa.String(length=50), nullable=True, server_default='planned'))
    
    # Add priority column if it doesn't exist
    if 'priority' not in existing_columns:
        op.add_column('projects', sa.Column('priority', sa.String(length=50), nullable=True))
    
    # Add owner column if it doesn't exist
    if 'owner' not in existing_columns:
        op.add_column('projects', sa.Column('owner', sa.String(length=255), nullable=True))
    
    # Add start_date column if it doesn't exist
    if 'start_date' not in existing_columns:
        op.add_column('projects', sa.Column('start_date', sa.Date(), nullable=True))
    
    # Add end_date column if it doesn't exist
    if 'end_date' not in existing_columns:
        op.add_column('projects', sa.Column('end_date', sa.Date(), nullable=True))
    
    # Add created_at column if it doesn't exist
    if 'created_at' not in existing_columns:
        op.add_column('projects', sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Add updated_at column if it doesn't exist
    if 'updated_at' not in existing_columns:
        op.add_column('projects', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade():
    """Remove the added columns"""
    
    # Check if columns exist before removing
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('projects')]
    
    if 'updated_at' in existing_columns:
        op.drop_column('projects', 'updated_at')
    
    if 'created_at' in existing_columns:
        op.drop_column('projects', 'created_at')
    
    if 'end_date' in existing_columns:
        op.drop_column('projects', 'end_date')
    
    if 'start_date' in existing_columns:
        op.drop_column('projects', 'start_date')
    
    if 'owner' in existing_columns:
        op.drop_column('projects', 'owner')
    
    if 'priority' in existing_columns:
        op.drop_column('projects', 'priority')
    
    if 'status' in existing_columns:
        op.drop_column('projects', 'status')
    
    if 'description' in existing_columns:
        op.drop_column('projects', 'description')
    
    if 'title' in existing_columns:
        op.drop_column('projects', 'title')
