"""add budget cycle hierarchy and hierarchical budget codes

Revision ID: 20260327_1400
Revises: 20260327_1300
Create Date: 2026-03-27 14:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260327_1400"
down_revision = "20260327_1300"
branch_labels = None
depends_on = None


BUDGET_CYCLE_STATUS_VALUES = ("draft", "active", "archived")
BUDGET_CATEGORY_VALUES = ("general", "capex", "opex", "capex_extra", "custom")


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _unique_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(constraint.get("name") == constraint_name for constraint in inspector.get_unique_constraints(table_name))


def _check_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(constraint.get("name") == constraint_name for constraint in inspector.get_check_constraints(table_name))


def _fk_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(constraint.get("name") == constraint_name for constraint in inspector.get_foreign_keys(table_name))


def _company_code_expr(alias: str = "company") -> str:
    return (
        f"COALESCE(NULLIF({alias}.client_code, ''), "
        f"NULLIF(UPPER(LEFT(REGEXP_REPLACE({alias}.name, '[^A-Za-z0-9]', '', 'g'), 2)), ''), "
        f"'CP')"
    )


def _budget_category_expr(alias: str = "v") -> str:
    return (
        "CASE "
        f"WHEN LOWER(COALESCE({alias}.code, '') || ' ' || COALESCE({alias}.name, '')) LIKE '%capex extra%' THEN 'capex_extra' "
        f"WHEN LOWER(COALESCE({alias}.code, '') || ' ' || COALESCE({alias}.name, '')) LIKE '%capex_extra%' THEN 'capex_extra' "
        f"WHEN LOWER(COALESCE({alias}.code, '') || ' ' || COALESCE({alias}.name, '')) LIKE '%opex%' THEN 'opex' "
        f"WHEN LOWER(COALESCE({alias}.code, '') || ' ' || COALESCE({alias}.name, '')) LIKE '%capex%' THEN 'capex' "
        "ELSE 'general' END"
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("financial_budget_cycles"):
        op.create_table(
            "financial_budget_cycles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("company_code_snapshot", sa.String(length=20), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "year", name="uq_financial_budget_cycles_company_year"),
            sa.UniqueConstraint("company_id", "code", name="uq_financial_budget_cycles_company_code"),
            sa.CheckConstraint(
                f"status IN {BUDGET_CYCLE_STATUS_VALUES}",
                name="ck_financial_budget_cycles_status",
            ),
            sa.CheckConstraint("year >= 2000", name="ck_financial_budget_cycles_year"),
        )
        inspector = sa.inspect(bind)

    version_columns = [
        ("budget_cycle_id", sa.Integer()),
        ("budget_category", sa.String(length=24)),
        ("budget_seq", sa.Integer()),
        ("full_code", sa.String(length=200)),
        ("company_code_snapshot", sa.String(length=20)),
    ]
    for column_name, column_type in version_columns:
        if _has_table("financial_budget_versions") and not _has_column("financial_budget_versions", column_name):
            op.add_column("financial_budget_versions", sa.Column(column_name, column_type, nullable=True))

    if _has_table("financial_budget_versions") and not _fk_exists(
        "financial_budget_versions", "fk_financial_budget_versions_budget_cycle_id"
    ) and _has_column("financial_budget_versions", "budget_cycle_id"):
        op.create_foreign_key(
            "fk_financial_budget_versions_budget_cycle_id",
            "financial_budget_versions",
            "financial_budget_cycles",
            ["budget_cycle_id"],
            ["id"],
        )

    if _has_table("financial_budget_lines"):
        if not _has_column("financial_budget_lines", "line_seq"):
            op.add_column("financial_budget_lines", sa.Column("line_seq", sa.Integer(), nullable=True))
        if not _has_column("financial_budget_lines", "full_code"):
            op.add_column("financial_budget_lines", sa.Column("full_code", sa.String(length=200), nullable=True))
        if not _has_column("financial_budget_lines", "company_code_snapshot"):
            op.add_column("financial_budget_lines", sa.Column("company_code_snapshot", sa.String(length=20), nullable=True))

    if _has_table("financial_budget_contracts"):
        if not _has_column("financial_budget_contracts", "contract_seq"):
            op.add_column("financial_budget_contracts", sa.Column("contract_seq", sa.Integer(), nullable=True))
        if not _has_column("financial_budget_contracts", "full_code"):
            op.add_column("financial_budget_contracts", sa.Column("full_code", sa.String(length=200), nullable=True))
        if not _has_column("financial_budget_contracts", "company_code_snapshot"):
            op.add_column("financial_budget_contracts", sa.Column("company_code_snapshot", sa.String(length=20), nullable=True))

    if _has_table("financial_budget_documents"):
        if not _has_column("financial_budget_documents", "document_seq"):
            op.add_column("financial_budget_documents", sa.Column("document_seq", sa.Integer(), nullable=True))
        if not _has_column("financial_budget_documents", "full_code"):
            op.add_column("financial_budget_documents", sa.Column("full_code", sa.String(length=200), nullable=True))
        if not _has_column("financial_budget_documents", "company_code_snapshot"):
            op.add_column("financial_budget_documents", sa.Column("company_code_snapshot", sa.String(length=20), nullable=True))

    inspector = sa.inspect(bind)
    if inspector.has_table("financial_budget_versions"):
        if not _check_exists("financial_budget_versions", "ck_financial_budget_versions_budget_category"):
            op.create_check_constraint(
                "ck_financial_budget_versions_budget_category",
                "financial_budget_versions",
                f"budget_category IN {BUDGET_CATEGORY_VALUES}",
            )
        if not _check_exists("financial_budget_versions", "ck_financial_budget_versions_budget_seq"):
            op.create_check_constraint(
                "ck_financial_budget_versions_budget_seq",
                "financial_budget_versions",
                "budget_seq IS NULL OR budget_seq >= 1",
            )
        if not _unique_exists("financial_budget_versions", "uq_financial_budget_versions_company_cycle_category_seq"):
            op.create_unique_constraint(
                "uq_financial_budget_versions_company_cycle_category_seq",
                "financial_budget_versions",
                ["company_id", "budget_cycle_id", "budget_category", "budget_seq"],
            )
        if not _unique_exists("financial_budget_versions", "uq_financial_budget_versions_company_full_code"):
            op.create_unique_constraint(
                "uq_financial_budget_versions_company_full_code",
                "financial_budget_versions",
                ["company_id", "full_code"],
            )

    if inspector.has_table("financial_budget_lines"):
        if not _check_exists("financial_budget_lines", "ck_financial_budget_lines_line_seq"):
            op.create_check_constraint(
                "ck_financial_budget_lines_line_seq",
                "financial_budget_lines",
                "line_seq IS NULL OR line_seq >= 1",
            )
        if not _unique_exists("financial_budget_lines", "uq_financial_budget_lines_company_version_seq"):
            op.create_unique_constraint(
                "uq_financial_budget_lines_company_version_seq",
                "financial_budget_lines",
                ["company_id", "budget_version_id", "line_seq"],
            )
        if not _unique_exists("financial_budget_lines", "uq_financial_budget_lines_company_full_code"):
            op.create_unique_constraint(
                "uq_financial_budget_lines_company_full_code",
                "financial_budget_lines",
                ["company_id", "full_code"],
            )

    if inspector.has_table("financial_budget_contracts"):
        if not _check_exists("financial_budget_contracts", "ck_financial_budget_contracts_contract_seq"):
            op.create_check_constraint(
                "ck_financial_budget_contracts_contract_seq",
                "financial_budget_contracts",
                "contract_seq IS NULL OR contract_seq >= 1",
            )
        if not _unique_exists("financial_budget_contracts", "uq_financial_budget_contracts_company_line_seq"):
            op.create_unique_constraint(
                "uq_financial_budget_contracts_company_line_seq",
                "financial_budget_contracts",
                ["company_id", "budget_line_id", "contract_seq"],
            )
        if not _unique_exists("financial_budget_contracts", "uq_financial_budget_contracts_company_full_code"):
            op.create_unique_constraint(
                "uq_financial_budget_contracts_company_full_code",
                "financial_budget_contracts",
                ["company_id", "full_code"],
            )

    if inspector.has_table("financial_budget_documents"):
        if not _check_exists("financial_budget_documents", "ck_financial_budget_documents_document_seq"):
            op.create_check_constraint(
                "ck_financial_budget_documents_document_seq",
                "financial_budget_documents",
                "document_seq IS NULL OR document_seq >= 1",
            )
        if not _unique_exists("financial_budget_documents", "uq_financial_budget_documents_company_contract_seq"):
            op.create_unique_constraint(
                "uq_financial_budget_documents_company_contract_seq",
                "financial_budget_documents",
                ["company_id", "budget_contract_id", "document_seq"],
            )
        if not _unique_exists("financial_budget_documents", "uq_financial_budget_documents_company_full_code"):
            op.create_unique_constraint(
                "uq_financial_budget_documents_company_full_code",
                "financial_budget_documents",
                ["company_id", "full_code"],
            )

    if _has_table("financial_budget_versions"):
        op.execute(
            f"""
            INSERT INTO financial_budget_cycles (
                company_id, code, name, year, status, metadata_json, company_code_snapshot, created_at, updated_at
            )
            SELECT
                grouped.company_id,
                (grouped.company_code_snapshot || '.CY.' || grouped.year::text) AS code,
                ('Ciclo Orçamentário ' || grouped.year::text) AS name,
                grouped.year,
                'active' AS status,
                '{{}}'::jsonb AS metadata_json,
                grouped.company_code_snapshot,
                NOW() AS created_at,
                NOW() AS updated_at
            FROM (
                SELECT DISTINCT
                    v.company_id,
                    COALESCE(EXTRACT(YEAR FROM v.period_start)::int, EXTRACT(YEAR FROM CURRENT_DATE)::int) AS year,
                    {_company_code_expr('company')} AS company_code_snapshot
                FROM financial_budget_versions v
                JOIN companies company
                  ON company.id = v.company_id
            ) grouped
            ON CONFLICT (company_id, year) DO NOTHING
            """
        )

        op.execute(
            f"""
            WITH ranked AS (
                SELECT
                    v.id,
                    c.id AS budget_cycle_id,
                    CASE
                        WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex extra%' THEN 'capex_extra'
                        WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex_extra%' THEN 'capex_extra'
                        WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%opex%' THEN 'opex'
                        WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex%' THEN 'capex'
                        ELSE 'general'
                    END AS budget_category,
                    ROW_NUMBER() OVER (
                        PARTITION BY v.company_id, c.id,
                            CASE
                                WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex extra%' THEN 'capex_extra'
                                WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex_extra%' THEN 'capex_extra'
                                WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%opex%' THEN 'opex'
                                WHEN LOWER(COALESCE(v.code, '') || ' ' || COALESCE(v.name, '')) LIKE '%capex%' THEN 'capex'
                                ELSE 'general'
                            END
                        ORDER BY COALESCE(v.period_start, CURRENT_DATE), v.created_at, v.id
                    ) AS budget_seq,
                    ({_company_code_expr('company')}) AS company_code_snapshot,
                    EXTRACT(YEAR FROM COALESCE(v.period_start, CURRENT_DATE))::int AS budget_year
                FROM financial_budget_versions v
                JOIN financial_budget_cycles c
                  ON c.company_id = v.company_id
                 AND c.year = COALESCE(EXTRACT(YEAR FROM v.period_start)::int, EXTRACT(YEAR FROM CURRENT_DATE)::int)
                JOIN companies company
                  ON company.id = v.company_id
            )
            UPDATE financial_budget_versions v
               SET budget_cycle_id = ranked.budget_cycle_id,
                   budget_category = ranked.budget_category,
                   budget_seq = ranked.budget_seq,
                   company_code_snapshot = COALESCE(v.company_code_snapshot, ranked.company_code_snapshot),
                   full_code = COALESCE(
                       v.full_code,
                       ranked.company_code_snapshot
                       || '.CY.'
                       || ranked.budget_year::text
                       || '.'
                       || UPPER(ranked.budget_category)
                       || '.'
                       || ranked.budget_seq::text
                   )
              FROM ranked
             WHERE v.id = ranked.id
            """
        )

        op.execute(
            """
            WITH ranked AS (
                SELECT
                    l.id,
                    v.company_code_snapshot,
                    ROW_NUMBER() OVER (
                        PARTITION BY l.budget_version_id
                        ORDER BY COALESCE(l.line_order, 100), l.created_at, l.id
                    ) AS line_seq,
                    v.full_code AS version_full_code
                FROM financial_budget_lines l
                JOIN financial_budget_versions v
                  ON v.id = l.budget_version_id
            )
            UPDATE financial_budget_lines l
               SET line_seq = ranked.line_seq,
                   company_code_snapshot = COALESCE(l.company_code_snapshot, ranked.company_code_snapshot),
                   full_code = COALESCE(
                       l.full_code,
                       ranked.version_full_code || '.' || ranked.line_seq::text
                   )
              FROM ranked
             WHERE l.id = ranked.id
            """
        )

        op.execute(
            """
            WITH ranked AS (
                SELECT
                    c.id,
                    l.company_code_snapshot,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.budget_line_id
                        ORDER BY COALESCE(c.created_at, CURRENT_TIMESTAMP), c.id
                    ) AS contract_seq,
                    l.full_code AS line_full_code
                FROM financial_budget_contracts c
                JOIN financial_budget_lines l
                  ON l.id = c.budget_line_id
            )
            UPDATE financial_budget_contracts c
               SET contract_seq = ranked.contract_seq,
                   company_code_snapshot = COALESCE(c.company_code_snapshot, ranked.company_code_snapshot),
                   full_code = COALESCE(
                       c.full_code,
                       ranked.line_full_code || '.' || ranked.contract_seq::text
                   )
              FROM ranked
             WHERE c.id = ranked.id
            """
        )

        op.execute(
            """
            WITH ranked AS (
                SELECT
                    d.id,
                    c.company_code_snapshot,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.budget_contract_id
                        ORDER BY COALESCE(d.created_at, CURRENT_TIMESTAMP), d.id
                    ) AS document_seq,
                    c.full_code AS contract_full_code
                FROM financial_budget_documents d
                JOIN financial_budget_contracts c
                  ON c.id = d.budget_contract_id
            )
            UPDATE financial_budget_documents d
               SET document_seq = ranked.document_seq,
                   company_code_snapshot = COALESCE(d.company_code_snapshot, ranked.company_code_snapshot),
                   full_code = COALESCE(
                       d.full_code,
                       ranked.contract_full_code || '.' || ranked.document_seq::text
                   )
              FROM ranked
             WHERE d.id = ranked.id
            """
        )

    indexes = [
        ("idx_financial_budget_cycles_company_year", "financial_budget_cycles", ["company_id", "year"]),
        ("idx_financial_budget_cycles_company_status", "financial_budget_cycles", ["company_id", "status"]),
        ("idx_financial_budget_versions_company_cycle", "financial_budget_versions", ["company_id", "budget_cycle_id"]),
        ("idx_financial_budget_versions_company_category", "financial_budget_versions", ["company_id", "budget_category"]),
        ("idx_financial_budget_versions_full_code", "financial_budget_versions", ["company_id", "full_code"]),
        ("idx_financial_budget_lines_company_seq", "financial_budget_lines", ["company_id", "budget_version_id", "line_seq"]),
        ("idx_financial_budget_lines_full_code", "financial_budget_lines", ["company_id", "full_code"]),
        ("idx_financial_budget_contracts_company_seq", "financial_budget_contracts", ["company_id", "budget_line_id", "contract_seq"]),
        ("idx_financial_budget_contracts_full_code", "financial_budget_contracts", ["company_id", "full_code"]),
        ("idx_financial_budget_documents_company_seq", "financial_budget_documents", ["company_id", "budget_contract_id", "document_seq"]),
        ("idx_financial_budget_documents_full_code", "financial_budget_documents", ["company_id", "full_code"]),
    ]
    for index_name, table_name, columns in indexes:
        if _has_table(table_name) and not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_budget_documents_full_code", "financial_budget_documents"),
        ("idx_financial_budget_documents_company_seq", "financial_budget_documents"),
        ("idx_financial_budget_contracts_full_code", "financial_budget_contracts"),
        ("idx_financial_budget_contracts_company_seq", "financial_budget_contracts"),
        ("idx_financial_budget_lines_full_code", "financial_budget_lines"),
        ("idx_financial_budget_lines_company_seq", "financial_budget_lines"),
        ("idx_financial_budget_versions_full_code", "financial_budget_versions"),
        ("idx_financial_budget_versions_company_category", "financial_budget_versions"),
        ("idx_financial_budget_versions_company_cycle", "financial_budget_versions"),
        ("idx_financial_budget_cycles_company_status", "financial_budget_cycles"),
        ("idx_financial_budget_cycles_company_year", "financial_budget_cycles"),
    ]:
        if inspector.has_table(table_name) and _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)

    if inspector.has_table("financial_budget_documents"):
        for constraint_name in [
            "uq_financial_budget_documents_company_full_code",
            "uq_financial_budget_documents_company_contract_seq",
            "ck_financial_budget_documents_document_seq",
        ]:
            try:
                op.drop_constraint(constraint_name, "financial_budget_documents", type_="unique" if constraint_name.startswith("uq_") else "check")
            except Exception:
                pass
        for column_name in ["company_code_snapshot", "full_code", "document_seq"]:
            if _has_column("financial_budget_documents", column_name):
                op.drop_column("financial_budget_documents", column_name)

    if inspector.has_table("financial_budget_contracts"):
        for constraint_name in [
            "uq_financial_budget_contracts_company_full_code",
            "uq_financial_budget_contracts_company_line_seq",
            "ck_financial_budget_contracts_contract_seq",
        ]:
            try:
                op.drop_constraint(constraint_name, "financial_budget_contracts", type_="unique" if constraint_name.startswith("uq_") else "check")
            except Exception:
                pass
        for column_name in ["company_code_snapshot", "full_code", "contract_seq"]:
            if _has_column("financial_budget_contracts", column_name):
                op.drop_column("financial_budget_contracts", column_name)

    if inspector.has_table("financial_budget_lines"):
        for constraint_name in [
            "uq_financial_budget_lines_company_full_code",
            "uq_financial_budget_lines_company_version_seq",
            "ck_financial_budget_lines_line_seq",
        ]:
            try:
                op.drop_constraint(constraint_name, "financial_budget_lines", type_="unique" if constraint_name.startswith("uq_") else "check")
            except Exception:
                pass
        for column_name in ["company_code_snapshot", "full_code", "line_seq"]:
            if _has_column("financial_budget_lines", column_name):
                op.drop_column("financial_budget_lines", column_name)

    if inspector.has_table("financial_budget_versions"):
        for constraint_name in [
            "uq_financial_budget_versions_company_full_code",
            "uq_financial_budget_versions_company_cycle_category_seq",
            "ck_financial_budget_versions_budget_seq",
            "ck_financial_budget_versions_budget_category",
        ]:
            try:
                op.drop_constraint(constraint_name, "financial_budget_versions", type_="unique" if constraint_name.startswith("uq_") else "check")
            except Exception:
                pass
        if _fk_exists("financial_budget_versions", "fk_financial_budget_versions_budget_cycle_id"):
            try:
                op.drop_constraint("fk_financial_budget_versions_budget_cycle_id", "financial_budget_versions", type_="foreignkey")
            except Exception:
                pass
        for column_name in ["company_code_snapshot", "full_code", "budget_seq", "budget_category", "budget_cycle_id"]:
            if _has_column("financial_budget_versions", column_name):
                op.drop_column("financial_budget_versions", column_name)

    if inspector.has_table("financial_budget_cycles"):
        try:
            op.drop_table("financial_budget_cycles")
        except Exception:
            pass
