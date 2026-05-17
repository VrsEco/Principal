"""add project soft delete columns

Revision ID: 20260517_1600
Revises: 20260517_1200
Create Date: 2026-05-17 16:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260517_1600"
down_revision = "20260517_1200"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("projects")}

    with op.batch_alter_table("projects") as batch_op:
        if "description" not in existing_columns:
            batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        if "start_date" not in existing_columns:
            batch_op.add_column(sa.Column("start_date", sa.Date(), nullable=True))
        if "end_date" not in existing_columns:
            batch_op.add_column(sa.Column("end_date", sa.Date(), nullable=True))
        if "is_deleted" not in existing_columns:
            batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        if "deleted_at" not in existing_columns:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        if "deleted_by_user_id" not in existing_columns:
            batch_op.add_column(sa.Column("deleted_by_user_id", sa.Integer(), nullable=True))
        if "delete_reason" not in existing_columns:
            batch_op.add_column(sa.Column("delete_reason", sa.Text(), nullable=True))

    if "deleted_by_user_id" not in existing_columns:
        op.create_foreign_key(
            "fk_projects_deleted_by_user_id",
            "projects",
            "users",
            ["deleted_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("projects")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("projects")}

    if "fk_projects_deleted_by_user_id" in foreign_keys:
        op.drop_constraint("fk_projects_deleted_by_user_id", "projects", type_="foreignkey")

    with op.batch_alter_table("projects") as batch_op:
        for column_name in ("delete_reason", "deleted_by_user_id", "deleted_at", "is_deleted"):
            if column_name in existing_columns:
                batch_op.drop_column(column_name)
