"""create site_leads for public lead capture

Revision ID: 20261015_1000
Revises: 20260606_1600
Create Date: 2026-10-15 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20261015_1000"
down_revision = "20260606_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_leads",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="novo"),
        sa.Column("nome", sa.String(80)),
        sa.Column("assunto", sa.String(60), nullable=False),
        sa.Column("relato", sa.String(600)),
        sa.Column("utm_source", sa.String(120)),
        sa.Column("utm_medium", sa.String(120)),
        sa.Column("utm_campaign", sa.String(120)),
        sa.Column("utm_content", sa.String(120)),
        sa.Column("utm_term", sa.String(120)),
        sa.Column("referrer_host", sa.String(255)),
        sa.Column("landing", sa.String(300)),
        sa.Column("page", sa.String(300)),
        sa.Column("client_ts", sa.DateTime),
        sa.Column("consent_at", sa.DateTime, nullable=False),
        sa.Column("privacy_policy_version", sa.String(40), nullable=False),
        sa.Column("ip_hash", sa.String(64)),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("project_task_id", sa.Integer, sa.ForeignKey("project_tasks.id")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("erased_at", sa.DateTime),
    )
    op.create_index("ix_site_leads_company_created", "site_leads", ["company_id", "created_at"])
    op.create_index(
        "ix_site_leads_company_channel", "site_leads", ["company_id", "utm_source", "utm_medium", "utm_campaign"]
    )
    op.create_index("ix_site_leads_dedupe", "site_leads", ["company_id", "dedupe_hash", "created_at"])


def downgrade():
    op.drop_table("site_leads")
