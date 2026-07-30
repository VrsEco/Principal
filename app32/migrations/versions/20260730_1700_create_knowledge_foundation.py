"""Create the knowledge foundation and automatic index run ledger.

Revision ID: 20260730_1700
Revises: 20260730_1600
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_1700"
down_revision = "20260730_1600"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("knowledge_scope", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=180), nullable=False),
        sa.Column("knowledge_kind", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("canonical_uri", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("authority_level", sa.String(length=30), nullable=False, server_default="internal"),
        sa.Column("version", sa.String(length=60), nullable=False, server_default="v1"),
        sa.Column("product_version", sa.String(length=60), nullable=True),
        sa.Column("locale", sa.String(length=20), nullable=False, server_default="pt-BR"),
        sa.Column("route_key", sa.String(length=160), nullable=True),
        sa.Column("module_key", sa.String(length=120), nullable=True),
        sa.Column("audience_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "required_capabilities_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("help_kind", sa.String(length=40), nullable=True),
        sa.Column("navigation_target", sa.String(length=240), nullable=True),
        sa.Column("tour_definition_id", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(knowledge_scope = 'company' AND company_id IS NOT NULL) OR "
            "(knowledge_scope = 'product' AND company_id IS NULL)",
            name="ck_knowledge_sources_scope_company",
        ),
    )
    for column in (
        "company_id",
        "knowledge_scope",
        "source_type",
        "source_ref",
        "knowledge_kind",
        "status",
        "product_version",
        "route_key",
        "module_key",
        "help_kind",
        "content_checksum",
        "indexed_at",
        "deleted_at",
    ):
        op.create_index(f"ix_knowledge_sources_{column}", "knowledge_sources", [column])
    op.create_index(
        "uq_knowledge_sources_product_ref",
        "knowledge_sources",
        ["source_type", "source_ref"],
        unique=True,
        postgresql_where=sa.text("company_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_knowledge_sources_company_ref",
        "knowledge_sources",
        ["company_id", "source_type", "source_ref"],
        unique=True,
        postgresql_where=sa.text("company_id IS NOT NULL AND deleted_at IS NULL"),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "knowledge_source_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("knowledge_scope", sa.String(length=20), nullable=False),
        sa.Column("section_key", sa.String(length=180), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("chunk_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "parent_chunk_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_span", sa.String(length=240), nullable=True),
        sa.Column("adapter_version", sa.String(length=40), nullable=False, server_default="v1"),
        sa.Column("parser_version", sa.String(length=40), nullable=False, server_default="v1"),
        sa.Column(
            "chunking_policy",
            sa.String(length=80),
            nullable=False,
            server_default="heading-v1",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(knowledge_scope = 'company' AND company_id IS NOT NULL) OR "
            "(knowledge_scope = 'product' AND company_id IS NULL)",
            name="ck_knowledge_chunks_scope_company",
        ),
        sa.UniqueConstraint(
            "knowledge_source_id",
            "section_key",
            name="uq_knowledge_chunks_source_section",
        ),
    )
    for column in (
        "knowledge_source_id",
        "company_id",
        "knowledge_scope",
        "content_checksum",
        "parent_chunk_id",
    ):
        op.create_index(f"ix_knowledge_chunks_{column}", "knowledge_chunks", [column])
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_content_fts "
        "ON knowledge_chunks USING gin (to_tsvector('portuguese', content))"
    )

    op.create_table(
        "knowledge_index_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("knowledge_scope", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("trigger_kind", sa.String(length=30), nullable=False, server_default="scheduled"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="running"),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deactivated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    for column in (
        "company_id",
        "knowledge_scope",
        "source_type",
        "trigger_kind",
        "status",
        "started_at",
    ):
        op.create_index(f"ix_knowledge_index_runs_{column}", "knowledge_index_runs", [column])


def downgrade() -> None:
    op.drop_table("knowledge_index_runs")
    op.drop_index("ix_knowledge_chunks_content_fts", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
