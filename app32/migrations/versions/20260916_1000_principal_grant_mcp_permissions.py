"""Grant MCP granular por principal e empresa, sem herdar RBAC legado."""

from alembic import op
import sqlalchemy as sa


revision = "20260916_1000"
down_revision = ("20260910_1000", "20260911_1830")
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "principal_company_grants",
        sa.Column(
            "mcp_permissions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade():
    op.drop_column("principal_company_grants", "mcp_permissions")
