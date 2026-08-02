"""Create the tenant-safe Strategic Tree P0 foundation.

Revision ID: 20260802_2100
Revises: 20260801_1530
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260802_2100"
down_revision = "20260801_1530"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategic_trees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("visibility_scope", sa.String(length=40), nullable=False, server_default="company_authorized"),
        sa.Column("root_node_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_strategic_trees_company_id", "strategic_trees", ["company_id"])
    op.create_index("ix_strategic_trees_status", "strategic_trees", ["status"])
    op.create_index("ix_strategic_trees_root_node_id", "strategic_trees", ["root_node_id"])
    op.create_index("ix_strategic_trees_company_status", "strategic_trees", ["company_id", "status"])

    op.create_table(
        "strategic_tree_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tree_id", sa.Integer(), sa.ForeignKey("strategic_trees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_node_id", sa.Integer(), sa.ForeignKey("strategic_tree_nodes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("node_type", sa.String(length=30), nullable=False, server_default="theme"),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("visible_status", sa.String(length=30), nullable=False, server_default="collecting"),
        sa.Column("technical_status", sa.String(length=30), nullable=False, server_default="captured"),
        sa.Column("sensitivity_level", sa.String(length=20), nullable=False, server_default="internal"),
        sa.Column("visibility_scope", sa.String(length=40), nullable=False, server_default="company_authorized"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "node_type IN ('root','theme','subtheme','investigation','decision','unfolding','parked')",
            name="ck_strategic_tree_nodes_type",
        ),
    )
    for column in ("company_id", "tree_id", "parent_node_id", "visible_status", "technical_status"):
        op.create_index(f"ix_strategic_tree_nodes_{column}", "strategic_tree_nodes", [column])
    op.create_index("ix_strategic_tree_nodes_company_tree", "strategic_tree_nodes", ["company_id", "tree_id"])
    op.create_index("ix_strategic_tree_nodes_tree_parent", "strategic_tree_nodes", ["tree_id", "parent_node_id"])
    op.create_foreign_key(
        "fk_strategic_trees_root_node",
        "strategic_trees",
        "strategic_tree_nodes",
        ["root_node_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "strategic_tree_contributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tree_id", sa.Integer(), sa.ForeignKey("strategic_trees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("strategic_tree_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contribution_type", sa.String(length=40), nullable=False, server_default="human_statement"),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="app32"),
        sa.Column("source_ref", sa.String(length=240), nullable=True),
        sa.Column("attribution_mode", sa.String(length=30), nullable=False, server_default="identified"),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("participant_ref", sa.String(length=180), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("sanitized_content", sa.Text(), nullable=True),
        sa.Column("classification_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence_state", sa.String(length=30), nullable=False, server_default="unverified"),
        sa.Column("sensitivity_level", sa.String(length=20), nullable=False, server_default="internal"),
        sa.Column("visibility_scope", sa.String(length=40), nullable=False, server_default="company_authorized"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("company_id", "idempotency_key", name="uq_strategic_tree_contribution_idempotency"),
        sa.CheckConstraint(
            "attribution_mode IN ('identified','confidential','pseudonymized')",
            name="ck_strategic_tree_contributions_attribution",
        ),
    )
    for column in ("company_id", "tree_id", "node_id", "contribution_type", "source_type", "author_user_id", "status", "created_at", "deleted_at"):
        op.create_index(f"ix_strategic_tree_contributions_{column}", "strategic_tree_contributions", [column])
    op.create_index("ix_strategic_tree_contributions_company_node", "strategic_tree_contributions", ["company_id", "node_id"])

    op.create_table(
        "strategic_tree_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tree_id", sa.Integer(), sa.ForeignKey("strategic_trees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("strategic_tree_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("contribution_id", sa.Integer(), sa.ForeignKey("strategic_tree_contributions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("surface", sa.String(length=30), nullable=False, server_default="app32"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("company_id", "tree_id", "node_id", "contribution_id", "event_type", "actor_user_id", "created_at"):
        op.create_index(f"ix_strategic_tree_audit_events_{column}", "strategic_tree_audit_events", [column])
    op.create_index("ix_strategic_tree_audit_company_created", "strategic_tree_audit_events", ["company_id", "created_at"])

    # Capability única e rollout inicial somente na Versus (company_id 9).
    op.execute(
        sa.text(
            """
            INSERT INTO ai_capabilities
                (key, name, description, domain, capability_type, risk_level, status,
                 rollout_status, origin, source_ref, requires_human_gate,
                 requires_active_company, requires_user_binding,
                 technical_binding_json, supported_channels_json,
                 supported_surfaces_json, default_settings_json, metadata_json,
                 created_at, updated_at)
            VALUES
                ('knowledge.strategic_tree', 'Árvore Estratégica',
                 'Registro e maturação tenant-safe de conhecimento consultivo no Sapiens.',
                 'knowledge', 'feature', 'medium', 'active', 'pilot', 'system',
                 'SPEC:arvore_estrategica_sapiens_conhecimento_consultivo_v1', false,
                 true, true, json_build_object('feature_flag', 'knowledge.strategic_tree'),
                 json_build_array('app32', 'mcp'),
                 json_build_array('sapiens', 'mcp_user', 'mcp_admin'),
                 json_build_object('enabled', false),
                 json_build_object('menu_code', '41', 'capability', 'strategic_tree'),
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO ai_capability_company_settings
                (capability_id, company_id, settings_json, is_enabled, created_at, updated_at)
            SELECT id, 9, json_build_object('pilot', true), true,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM ai_capabilities
            WHERE key = 'knowledge.strategic_tree'
              AND EXISTS (SELECT 1 FROM companies WHERE id = 9)
            ON CONFLICT (capability_id, company_id) DO UPDATE
                SET is_enabled = true, updated_at = CURRENT_TIMESTAMP
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM ai_capability_company_settings WHERE capability_id IN "
            "(SELECT id FROM ai_capabilities WHERE key = 'knowledge.strategic_tree')"
        )
    )
    op.execute(sa.text("DELETE FROM ai_capabilities WHERE key = 'knowledge.strategic_tree'"))
    op.drop_constraint("fk_strategic_trees_root_node", "strategic_trees", type_="foreignkey")
    op.drop_table("strategic_tree_audit_events")
    op.drop_table("strategic_tree_contributions")
    op.drop_table("strategic_tree_nodes")
    op.drop_table("strategic_trees")
