"""create process activity artifact foundation

Revision ID: 20260801_1500
Revises: 20260801_0900
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_1500"
down_revision = "20260801_0900"
branch_labels = None
depends_on = None


ARTIFACT_TYPE_CHECK = "artifact_type IN ('pop', 'form', 'check', 'ai', 'data_in', 'data_out')"


def upgrade():
    op.create_table(
        "process_activity_artifact_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_key", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("configuration_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "legacy_process_routine_id",
            sa.Integer(),
            sa.ForeignKey("process_routines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(ARTIFACT_TYPE_CHECK, name="ck_process_artifact_definition_type"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_process_artifact_definition_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_process_artifact_definition_version_positive"),
        sa.UniqueConstraint(
            "company_id",
            "process_id",
            "artifact_key",
            "version",
            name="uq_process_artifact_definition_version",
        ),
        sa.UniqueConstraint(
            "company_id",
            "legacy_process_routine_id",
            "version",
            name="uq_process_artifact_definition_legacy_pop_version",
        ),
    )
    op.create_index(
        "ix_process_artifact_definition_company_process_type",
        "process_activity_artifact_definitions",
        ["company_id", "process_id", "artifact_type"],
    )
    op.create_index(
        "ix_process_activity_artifact_definitions_company_id",
        "process_activity_artifact_definitions",
        ["company_id"],
    )
    op.create_index(
        "ix_process_activity_artifact_definitions_process_id",
        "process_activity_artifact_definitions",
        ["process_id"],
    )
    op.create_index(
        "ix_process_activity_artifact_definitions_artifact_type",
        "process_activity_artifact_definitions",
        ["artifact_type"],
    )
    op.create_index(
        "ix_process_activity_artifact_definitions_status",
        "process_activity_artifact_definitions",
        ["status"],
    )
    op.create_index(
        "ix_process_artifact_definition_legacy_pop",
        "process_activity_artifact_definitions",
        ["legacy_process_routine_id"],
    )

    op.create_table(
        "process_activity_artifact_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bpmn_element_id", sa.String(length=255), nullable=False),
        sa.Column(
            "artifact_definition_id",
            sa.Integer(),
            sa.ForeignKey("process_activity_artifact_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completion_policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("display_order >= 0", name="ck_process_artifact_link_order_non_negative"),
        sa.UniqueConstraint(
            "company_id",
            "process_id",
            "bpmn_element_id",
            "artifact_definition_id",
            name="uq_process_artifact_link_activity_definition",
        ),
    )
    op.create_index(
        "ix_process_artifact_link_company_activity",
        "process_activity_artifact_links",
        ["company_id", "process_id", "bpmn_element_id"],
    )
    for column in ("company_id", "process_id", "bpmn_element_id", "artifact_definition_id"):
        op.create_index(
            f"ix_process_activity_artifact_links_{column}",
            "process_activity_artifact_links",
            [column],
        )

    op.create_table(
        "process_activity_artifact_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "process_instance_id",
            sa.Integer(),
            sa.ForeignKey("process_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "activity_execution_id",
            sa.Integer(),
            sa.ForeignKey("process_instance_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_definition_id",
            sa.Integer(),
            sa.ForeignKey("process_activity_artifact_definitions.id"),
            nullable=False,
        ),
        sa.Column("artifact_key", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=30), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("definition_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("input_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("error_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(ARTIFACT_TYPE_CHECK, name="ck_process_artifact_execution_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'waiting_external', 'waiting_human', 'completed', 'failed', 'skipped')",
            name="ck_process_artifact_execution_status",
        ),
        sa.CheckConstraint("artifact_version > 0", name="ck_process_artifact_execution_version_positive"),
        sa.UniqueConstraint(
            "company_id",
            "activity_execution_id",
            "artifact_definition_id",
            name="uq_process_artifact_execution_activity_definition",
        ),
    )
    op.create_index(
        "ix_process_artifact_execution_company_instance_status",
        "process_activity_artifact_executions",
        ["company_id", "process_instance_id", "status"],
    )
    for column in (
        "company_id",
        "process_instance_id",
        "activity_execution_id",
        "artifact_definition_id",
        "artifact_type",
        "status",
    ):
        op.create_index(
            f"ix_process_activity_artifact_executions_{column}",
            "process_activity_artifact_executions",
            [column],
        )

    # Compatibilidade imediata: cada POP ativo já vinculado ao BPMN passa a ter
    # uma definição publicada e um vínculo externo, sem alterar ProcessRoutine.
    op.execute(
        sa.text(
            """
            INSERT INTO process_activity_artifact_definitions (
                company_id,
                process_id,
                artifact_key,
                artifact_type,
                name,
                description,
                version,
                status,
                configuration_json,
                legacy_process_routine_id,
                published_at,
                created_at,
                updated_at
            )
            SELECT
                routine.company_id,
                routine.process_id,
                'legacy-pop-' || routine.id::text,
                'pop',
                routine.name,
                routine.description,
                1,
                'published',
                json_build_object(
                    'adapter', 'process_routine',
                    'process_routine_id', routine.id,
                    'code', routine.code,
                    'bpmn_element_type', routine.bpmn_element_type
                ),
                routine.id,
                COALESCE(routine.created_at, NOW()),
                COALESCE(routine.created_at, NOW()),
                NOW()
            FROM process_routines AS routine
            WHERE routine.bpmn_element_id IS NOT NULL
              AND BTRIM(routine.bpmn_element_id) <> ''
              AND COALESCE(routine.is_active, TRUE) = TRUE
            ON CONFLICT ON CONSTRAINT uq_process_artifact_definition_legacy_pop_version DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO process_activity_artifact_links (
                company_id,
                process_id,
                bpmn_element_id,
                artifact_definition_id,
                display_order,
                is_required,
                completion_policy_json,
                is_active,
                created_at,
                updated_at
            )
            SELECT
                routine.company_id,
                routine.process_id,
                routine.bpmn_element_id,
                definition.id,
                COALESCE(routine.order_index, 0),
                FALSE,
                json_build_object('mode', 'available', 'acknowledgement_required', false),
                TRUE,
                NOW(),
                NOW()
            FROM process_routines AS routine
            JOIN process_activity_artifact_definitions AS definition
              ON definition.company_id = routine.company_id
             AND definition.process_id = routine.process_id
             AND definition.legacy_process_routine_id = routine.id
             AND definition.version = 1
            WHERE routine.bpmn_element_id IS NOT NULL
              AND BTRIM(routine.bpmn_element_id) <> ''
              AND COALESCE(routine.is_active, TRUE) = TRUE
            ON CONFLICT ON CONSTRAINT uq_process_artifact_link_activity_definition DO NOTHING
            """
        )
    )


def downgrade():
    op.drop_table("process_activity_artifact_executions")
    op.drop_table("process_activity_artifact_links")
    op.drop_table("process_activity_artifact_definitions")
