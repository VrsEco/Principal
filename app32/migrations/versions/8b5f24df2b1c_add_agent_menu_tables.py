"""add_agent_menu_tables

Revision ID: 8b5f24df2b1c
Revises: 4a3df7ddf9ea
Create Date: 2026-03-03 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b5f24df2b1c"
down_revision = "4a3df7ddf9ea"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "agent_menu_options" not in existing_tables:
        op.create_table(
            "agent_menu_options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("action_key", sa.String(length=120), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("required_fields", sa.JSON(), nullable=True),
            sa.Column("keywords", sa.JSON(), nullable=True),
            sa.Column("confirmation_template", sa.Text(), nullable=True),
            sa.Column("execution_template", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["parent_id"], ["agent_menu_options.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "code", name="uq_agent_menu_options_company_code"),
        )

    # Atualiza tabela existente na mesma execução, caso tenha sido criada anteriormente sem constraint.
    inspector = sa.inspect(bind)
    constraints = {c.get("name") for c in inspector.get_unique_constraints("agent_menu_options")}
    if "uq_agent_menu_options_company_code" not in constraints:
        op.create_unique_constraint(
            "uq_agent_menu_options_company_code",
            "agent_menu_options",
            ["company_id", "code"],
        )

    if "agent_menu_sessions" not in set(inspector.get_table_names()):
        op.create_table(
            "agent_menu_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("channel", sa.String(length=40), nullable=False, server_default="web"),
            sa.Column("thread_id", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="idle"),
            sa.Column("selected_option_id", sa.Integer(), nullable=True),
            sa.Column("collected_data", sa.JSON(), nullable=True),
            sa.Column("missing_fields", sa.JSON(), nullable=True),
            sa.Column("last_user_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["selected_option_id"], ["agent_menu_options.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "company_id",
                "channel",
                "thread_id",
                name="uq_agent_menu_sessions_context",
            ),
        )

    inspector = sa.inspect(bind)
    constraints = {c.get("name") for c in inspector.get_unique_constraints("agent_menu_sessions")}
    if "uq_agent_menu_sessions_context" not in constraints:
        op.create_unique_constraint(
            "uq_agent_menu_sessions_context",
            "agent_menu_sessions",
            ["user_id", "company_id", "channel", "thread_id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "agent_menu_sessions" in existing_tables:
        op.drop_table("agent_menu_sessions")
    if "agent_menu_options" in existing_tables:
        op.drop_table("agent_menu_options")
