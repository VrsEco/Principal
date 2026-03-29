"""add budget links to financial schedules and entries

Revision ID: 20260327_1300
Revises: 20260327_1200
Create Date: 2026-03-27 13:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_1300"
down_revision = "20260327_1200"
branch_labels = None
depends_on = None


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


def upgrade():
    if _has_table("financial_schedules") and not _has_column("financial_schedules", "budget_line_id"):
        op.add_column("financial_schedules", sa.Column("budget_line_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_schedules_budget_line_id",
            "financial_schedules",
            "financial_budget_lines",
            ["budget_line_id"],
            ["id"],
        )

    if _has_table("financial_schedules") and not _has_column("financial_schedules", "budget_contract_id"):
        op.add_column("financial_schedules", sa.Column("budget_contract_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_schedules_budget_contract_id",
            "financial_schedules",
            "financial_budget_contracts",
            ["budget_contract_id"],
            ["id"],
        )

    if _has_table("financial_entries") and not _has_column("financial_entries", "budget_line_id"):
        op.add_column("financial_entries", sa.Column("budget_line_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_entries_budget_line_id",
            "financial_entries",
            "financial_budget_lines",
            ["budget_line_id"],
            ["id"],
        )

    if _has_table("financial_entries") and not _has_column("financial_entries", "budget_contract_id"):
        op.add_column("financial_entries", sa.Column("budget_contract_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_entries_budget_contract_id",
            "financial_entries",
            "financial_budget_contracts",
            ["budget_contract_id"],
            ["id"],
        )

    if _has_table("financial_entries") and not _has_column("financial_entries", "budget_document_id"):
        op.add_column("financial_entries", sa.Column("budget_document_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_entries_budget_document_id",
            "financial_entries",
            "financial_budget_documents",
            ["budget_document_id"],
            ["id"],
        )

    if _has_table("financial_schedules"):
        if _has_column("financial_schedules", "budget_document_id") and _has_column("financial_schedules", "budget_contract_id"):
            op.execute(
                """
                UPDATE financial_schedules schedule
                   SET budget_contract_id = COALESCE(schedule.budget_contract_id, document.budget_contract_id),
                       budget_line_id = COALESCE(schedule.budget_line_id, contract.budget_line_id)
                  FROM financial_budget_documents document
                  JOIN financial_budget_contracts contract
                    ON contract.id = document.budget_contract_id
                 WHERE schedule.budget_document_id = document.id
                """
            )

        if _has_column("financial_schedules", "metadata_json"):
            op.execute(
                """
                UPDATE financial_schedules
                   SET budget_line_id = COALESCE(
                           budget_line_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_line_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_line_id')::integer
                           END
                       ),
                       budget_contract_id = COALESCE(
                           budget_contract_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_contract_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_contract_id')::integer
                           END
                       ),
                       budget_document_id = COALESCE(
                           budget_document_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_document_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_document_id')::integer
                           END
                       )
                """
            )

    if _has_table("financial_entries"):
        if _has_table("financial_schedules"):
            op.execute(
                """
                UPDATE financial_entries entry
                   SET budget_line_id = COALESCE(entry.budget_line_id, schedule.budget_line_id),
                       budget_contract_id = COALESCE(entry.budget_contract_id, schedule.budget_contract_id),
                       budget_document_id = COALESCE(entry.budget_document_id, schedule.budget_document_id)
                  FROM financial_schedules schedule
                 WHERE entry.external_reference = ('financial_schedule:' || schedule.id::text)
                """
            )
            op.execute(
                """
                UPDATE financial_entries entry
                   SET budget_line_id = COALESCE(entry.budget_line_id, schedule.budget_line_id),
                       budget_contract_id = COALESCE(entry.budget_contract_id, schedule.budget_contract_id),
                       budget_document_id = COALESCE(entry.budget_document_id, schedule.budget_document_id)
                  FROM financial_schedules schedule
                 WHERE (entry.metadata_json ->> 'financial_schedule_id') ~ '^[0-9]+$'
                   AND (entry.metadata_json ->> 'financial_schedule_id')::integer = schedule.id
                """
            )

        if _has_column("financial_entries", "metadata_json"):
            op.execute(
                """
                UPDATE financial_entries
                   SET budget_line_id = COALESCE(
                           budget_line_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_line_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_line_id')::integer
                           END
                       ),
                       budget_contract_id = COALESCE(
                           budget_contract_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_contract_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_contract_id')::integer
                           END
                       ),
                       budget_document_id = COALESCE(
                           budget_document_id,
                           CASE
                               WHEN (metadata_json ->> 'budget_document_id') ~ '^[0-9]+$'
                               THEN (metadata_json ->> 'budget_document_id')::integer
                           END
                       )
                """
            )

    indexes = [
        ("idx_financial_schedules_company_budget_line", "financial_schedules", ["company_id", "budget_line_id"]),
        ("idx_financial_schedules_company_budget_contract", "financial_schedules", ["company_id", "budget_contract_id"]),
        ("idx_financial_entries_company_budget_line", "financial_entries", ["company_id", "budget_line_id"]),
        ("idx_financial_entries_company_budget_contract", "financial_entries", ["company_id", "budget_contract_id"]),
        ("idx_financial_entries_company_budget_document", "financial_entries", ["company_id", "budget_document_id"]),
    ]
    for index_name, table_name, columns in indexes:
        if _has_table(table_name) and not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_entries_company_budget_document", "financial_entries"),
        ("idx_financial_entries_company_budget_contract", "financial_entries"),
        ("idx_financial_entries_company_budget_line", "financial_entries"),
        ("idx_financial_schedules_company_budget_contract", "financial_schedules"),
        ("idx_financial_schedules_company_budget_line", "financial_schedules"),
    ]:
        if inspector.has_table(table_name) and _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)

    if inspector.has_table("financial_entries") and _has_column("financial_entries", "budget_document_id"):
        try:
            op.drop_constraint("fk_financial_entries_budget_document_id", "financial_entries", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_entries", "budget_document_id")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_entries") and _has_column("financial_entries", "budget_contract_id"):
        try:
            op.drop_constraint("fk_financial_entries_budget_contract_id", "financial_entries", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_entries", "budget_contract_id")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_entries") and _has_column("financial_entries", "budget_line_id"):
        try:
            op.drop_constraint("fk_financial_entries_budget_line_id", "financial_entries", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_entries", "budget_line_id")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_schedules") and _has_column("financial_schedules", "budget_contract_id"):
        try:
            op.drop_constraint("fk_financial_schedules_budget_contract_id", "financial_schedules", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_schedules", "budget_contract_id")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_schedules") and _has_column("financial_schedules", "budget_line_id"):
        try:
            op.drop_constraint("fk_financial_schedules_budget_line_id", "financial_schedules", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_schedules", "budget_line_id")
