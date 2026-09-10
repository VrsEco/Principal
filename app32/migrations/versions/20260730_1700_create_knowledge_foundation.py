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


def _assert_existing_table_contract(
    inspector: sa.Inspector,
    table_name: str,
    required_columns: tuple[str, ...],
    required_constraints: tuple[str, ...] = (),
) -> None:
    """Recusa marcar como aplicada uma tabela homônima, porém incompleta."""

    actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
    missing_columns = sorted(set(required_columns) - actual_columns)
    actual_constraints = {
        constraint["name"]
        for constraint in (*inspector.get_check_constraints(table_name), *inspector.get_unique_constraints(table_name))
        if constraint.get("name")
    }
    missing_constraints = sorted(set(required_constraints) - actual_constraints)
    if missing_columns or missing_constraints:
        raise RuntimeError(
            f"{table_name} já existe, mas não atende ao contrato da revision "
            f"20260730_1700; colunas ausentes={missing_columns}, "
            f"constraints ausentes={missing_constraints}."
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_contracts = (
        (
            "knowledge_sources",
            (
                "id", "company_id", "knowledge_scope", "source_type", "source_ref", "knowledge_kind",
                "title", "canonical_uri", "status", "authority_level", "version", "product_version",
                "locale", "route_key", "module_key", "audience_json", "required_capabilities_json",
                "help_kind", "navigation_target", "tour_definition_id", "metadata_json", "content_checksum",
                "valid_from", "valid_to", "source_updated_at", "indexed_at", "deleted_at", "created_at", "updated_at",
            ),
            ("ck_knowledge_sources_scope_company",),
        ),
        (
            "knowledge_chunks",
            (
                "id", "knowledge_source_id", "company_id", "knowledge_scope", "section_key", "content",
                "metadata_json", "chunk_order", "token_count", "content_checksum", "parent_chunk_id",
                "source_span", "adapter_version", "parser_version", "chunking_policy", "created_at", "updated_at",
            ),
            ("ck_knowledge_chunks_scope_company", "uq_knowledge_chunks_source_section"),
        ),
        (
            "knowledge_index_runs",
            (
                "id", "company_id", "knowledge_scope", "source_type", "trigger_kind", "status",
                "discovered_count", "created_count", "updated_count", "unchanged_count", "deactivated_count",
                "failed_count", "error_message", "metadata_json", "started_at", "completed_at",
            ),
            (),
        ),
    )
    for table_name, required_columns, required_constraints in existing_contracts:
        if inspector.has_table(table_name):
            _assert_existing_table_contract(inspector, table_name, required_columns, required_constraints)

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
        if_not_exists=True,
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
        op.create_index(f"ix_knowledge_sources_{column}", "knowledge_sources", [column], if_not_exists=True)
    op.create_index(
        "uq_knowledge_sources_product_ref",
        "knowledge_sources",
        ["source_type", "source_ref"],
        unique=True,
        postgresql_where=sa.text("company_id IS NULL AND deleted_at IS NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_knowledge_sources_company_ref",
        "knowledge_sources",
        ["company_id", "source_type", "source_ref"],
        unique=True,
        postgresql_where=sa.text("company_id IS NOT NULL AND deleted_at IS NULL"),
        if_not_exists=True,
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
        if_not_exists=True,
    )
    for column in (
        "knowledge_source_id",
        "company_id",
        "knowledge_scope",
        "content_checksum",
        "parent_chunk_id",
    ):
        op.create_index(f"ix_knowledge_chunks_{column}", "knowledge_chunks", [column], if_not_exists=True)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_fts "
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
        if_not_exists=True,
    )
    for column in (
        "company_id",
        "knowledge_scope",
        "source_type",
        "trigger_kind",
        "status",
        "started_at",
    ):
        op.create_index(f"ix_knowledge_index_runs_{column}", "knowledge_index_runs", [column], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("knowledge_index_runs")
    op.drop_index("ix_knowledge_chunks_content_fts", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
