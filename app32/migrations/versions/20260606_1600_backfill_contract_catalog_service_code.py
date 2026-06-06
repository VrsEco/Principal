"""backfill contract catalog service code for nfse integration

Revision ID: 20260606_1600
Revises: 20260606_1230
Create Date: 2026-06-06 16:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260606_1600"
down_revision = "20260606_1230"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE contract_catalog_items
           SET metadata_json = jsonb_set(
               COALESCE(metadata_json, '{}'::jsonb),
               '{service_code}',
               to_jsonb('0710002'::text),
               true
           )
         WHERE deleted_at IS NULL
        """
    )


def downgrade():
    # Data backfill requested as an operational correction; do not remove values
    # on downgrade to avoid deleting service codes later edited by users.
    pass
