"""Harness read-only para detectar drift entre Alembic e schema PostgreSQL.

Não executa ``stamp``, DDL, seed ou backfill. O objetivo é impedir que uma
migration seja marcada como aplicada apenas porque uma tabela homônima existe.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import psycopg2
from alembic.config import Config
from alembic.script import ScriptDirectory


@dataclass(frozen=True)
class TableFingerprint:
    name: str
    columns: tuple[str, ...] = ()
    indexes: tuple[str, ...] = ()
    index_alternatives: tuple[tuple[str, ...], ...] = ()
    constraints: tuple[str, ...] = ()
    constraint_fragments: tuple[tuple[str, str], ...] = ()
    column_default_fragments: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SchemaMarker:
    revision: str
    tables: tuple[TableFingerprint, ...]


@dataclass(frozen=True)
class ProtocolSeedMarker:
    revision: str
    protocol_version: str
    global_note: str
    tenant_note: str


@dataclass(frozen=True)
class PortfolioBackfillMarker:
    revision: str


@dataclass(frozen=True)
class ProcessArtifactBackfillMarker:
    revision: str


@dataclass(frozen=True)
class CapabilityRolloutMarker:
    revision: str
    capability_key: str
    company_id: int


@dataclass(frozen=True)
class CapabilityDimensionSeedMarker:
    revision: str
    dimension_names: tuple[str, ...]


@dataclass(frozen=True)
class IndicatorGoalNormalizationMarker:
    revision: str


@dataclass(frozen=True)
class IndicatorGoalRoutineBackfillMarker:
    revision: str


PORTFOLIO_BACKFILL_MARKERS = (PortfolioBackfillMarker(revision="20260723_1000"),)
PROCESS_ARTIFACT_BACKFILL_MARKERS = (ProcessArtifactBackfillMarker(revision="20260801_1500"),)
CAPABILITY_ROLLOUT_MARKERS = (
    CapabilityRolloutMarker("20260802_2100", "knowledge.strategic_tree", 9),
)
CAPABILITY_DIMENSION_SEED_MARKERS = (
    CapabilityDimensionSeedMarker(
        "20260821_1200",
        (
            "Ativos e Estrutura Física",
            "Pessoas, Papéis e Competências",
            "Tecnologia, Dados e Sistemas",
            "Documentos e Conhecimento",
            "Materiais, Insumos e Serviços",
        ),
    ),
)
INDICATOR_GOAL_NORMALIZATION_MARKERS = (IndicatorGoalNormalizationMarker("20260826_1800"),)
INDICATOR_GOAL_ROUTINE_BACKFILL_MARKERS = (IndicatorGoalRoutineBackfillMarker("20260826_2000"),)


PROTOCOL_SEED_MARKERS = (
    ProtocolSeedMarker(
        revision="20260727_1800",
        protocol_version="positioning-official-v1.0",
        global_note="seed:positioning-official-v1.0:global",
        tenant_note="seed:positioning-official-v1.0:tenant-aa",
    ),
    ProtocolSeedMarker(
        revision="20260727_2100",
        protocol_version="org-chart-official-v1.0",
        global_note="seed:org-chart-official-v1.0:global",
        tenant_note="seed:org-chart-official-v1.0:tenant-aa",
    ),
    ProtocolSeedMarker(
        revision="20260721_2130",
        protocol_version="vision-official-v1.0",
        global_note="seed:vision-official-v1.0:global",
        tenant_note="seed:vision-official-v1.0:tenant-aa",
    ),
    ProtocolSeedMarker(
        revision="20260721_2130",
        protocol_version="values-official-v1.0",
        global_note="seed:values-official-v1.0:global",
        tenant_note="seed:values-official-v1.0:tenant-aa",
    ),
    ProtocolSeedMarker(
        revision="20260721_0900",
        protocol_version="mission-official-v1.0",
        global_note="seed:mission-official-v1.0:global",
        tenant_note="seed:mission-official-v1.0:tenant-aa",
    ),
)


# Primeiro ponto conhecido de colisão no clone local. Novos pontos devem ser
# adicionados somente com fingerprint de colunas, índices, constraints e dados
# de seed revisados; presença de tabela nunca autoriza stamp.
MARKERS = (
    SchemaMarker(
        revision="20260909_1000",
        tables=(
            TableFingerprint(
                "identity_principals",
                columns=("id", "subject_type", "user_id", "responsible_user_id", "status", "label", "purpose", "created_at", "updated_at", "revoked_at"),
                indexes=("ix_identity_principals_user_id", "ix_identity_principals_responsible_user_id", "ix_identity_principals_status", "ix_identity_principal_type_status"),
                constraints=("ck_identity_principal_subject_type", "ck_identity_principal_status", "ck_identity_principal_subject_binding", "uq_identity_principal_user"),
            ),
            TableFingerprint(
                "external_identities",
                columns=("id", "principal_id", "issuer", "subject", "provider_alias", "linked_at", "last_seen_at"),
                indexes=("ix_external_identity_principal",),
                constraints=("uq_external_identity_issuer_subject",),
            ),
            TableFingerprint(
                "principal_company_grants",
                columns=("id", "principal_id", "company_id", "role", "status", "starts_at", "expires_at", "granted_by_user_id", "revoked_at", "created_at", "updated_at"),
                indexes=("ix_principal_company_grant_company_status", "ix_principal_company_grant_principal_status"),
                constraints=("ck_principal_company_grant_status", "ck_principal_company_grant_validity", "uq_principal_company_grant"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260907_1900",
        tables=(
            TableFingerprint(
                "usage_telemetry_hourly",
                columns=("id", "company_id", "user_id", "bucket_started_at", "channel", "usage_kind", "sessions_started", "active_seconds", "request_count", "ai_request_count", "mcp_request_count", "error_count", "latency_ms_total", "created_at", "updated_at"),
                indexes=("ix_usage_telemetry_company_bucket", "ix_usage_telemetry_user_bucket"),
                constraints=("uq_usage_telemetry_hourly_bucket", "ck_usage_telemetry_nonnegative"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260904_1800",
        tables=(
            TableFingerprint(
                "employee_qualification_evidences",
                columns=("id", "company_id", "employee_id", "qualification_name", "level", "evidence_source", "evidence_reference", "expires_on", "created_by_user_id", "created_at", "updated_at"),
                indexes=("ix_qualification_company_employee",),
                constraints=("fk_qualification_tenant_employee", "ck_qualification_source", "uq_employee_qualification"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260904_1600",
        tables=(
            TableFingerprint(
                "role_cost_profiles",
                columns=("id", "company_id", "role_id", "starts_on", "ends_on", "currency", "base_salary", "charges", "benefits", "other_costs", "created_by_user_id", "created_at"),
                constraints=("fk_role_cost_tenant_role", "ck_role_cost_dates", "ck_role_cost_currency", "ck_role_cost_base_salary", "ck_role_cost_charges", "ck_role_cost_benefits", "ck_role_cost_other_costs", "uq_role_cost_start"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260904_1500",
        tables=(
            TableFingerprint("roles", constraints=("uq_roles_company_id",)),
            TableFingerprint("employees", constraints=("uq_employees_company_id",)),
            TableFingerprint(
                "employee_role_occupancies",
                columns=("id", "company_id", "employee_id", "role_id", "starts_on", "ends_on", "weekly_hours", "created_by_user_id", "ended_by_user_id", "ended_at", "created_at", "updated_at"),
                indexes=("ix_occupancy_company_employee", "ix_occupancy_company_role"),
                constraints=("fk_occupancy_tenant_employee", "fk_occupancy_tenant_role", "ck_occupancy_dates", "ck_occupancy_hours", "uq_occupancy_start"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260904_1400",
        tables=(TableFingerprint("roles", columns=("qualification_requirements",)),),
    ),
    SchemaMarker(
        revision="20260903_1300",
        tables=(
            TableFingerprint(
                "user_presence_sessions",
                columns=("id", "company_id", "user_id", "session_hash", "login_at", "last_seen_at", "expires_at", "logout_at", "revoked_at", "device_type", "browser", "ip_hash", "created_at", "updated_at"),
                indexes=("ix_user_presence_company_last_seen", "ix_user_presence_user_company", "ix_user_presence_active_company"),
                constraints=("uq_user_presence_company_user_session",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260903_1200",
        tables=(
            TableFingerprint(
                "process_activity_artifact_definitions",
                columns=("execution_scope",),
                indexes=("ix_process_activity_artifact_definitions_execution_scope",),
                constraints=("ck_process_artifact_definition_execution_scope",),
            ),
            TableFingerprint(
                "process_activity_artifact_executions",
                columns=("scope_key",),
                indexes=("ix_process_activity_artifact_executions_scope_key",),
                constraints=("uq_process_artifact_execution_scope",),
            ),
            TableFingerprint(
                "process_activity_artifact_interactions",
                columns=("id", "company_id", "process_instance_id", "activity_execution_id", "artifact_execution_id", "phase_key", "action", "actor_user_id", "before_json", "after_json", "created_at"),
                indexes=("ix_process_artifact_interaction_company_execution", "ix_process_activity_artifact_interactions_company_id", "ix_process_activity_artifact_interactions_process_instance_id", "ix_process_activity_artifact_interactions_activity_execution_id", "ix_process_activity_artifact_interactions_artifact_execution_id", "ix_process_activity_artifact_interactions_phase_key", "ix_process_activity_artifact_interactions_actor_user_id"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260901_1900",
        tables=(
            TableFingerprint(
                "routines",
                columns=("execution_mode",),
                constraints=("ck_routines_execution_mode",),
            ),
            TableFingerprint(
                "routine_role_assignments",
                columns=("id", "company_id", "routine_id", "role_id", "assignment_type", "distribution_mode", "hours_used", "notes", "is_active", "created_at", "updated_at"),
                indexes=("ix_routine_role_assignments_company_id", "ix_routine_role_assignments_routine_id", "ix_routine_role_assignments_role_id", "uq_routine_single_responsible_role"),
                constraints=("uq_routine_role_assignment", "ck_routine_role_assignment_type", "ck_routine_role_distribution", "ck_routine_role_hours_nonnegative"),
            ),
            TableFingerprint(
                "routine_triggers",
                columns=("id", "company_id", "routine_id", "trigger_type", "trigger_code", "name", "activation_policy", "config_json", "is_active", "created_at", "updated_at"),
                indexes=("ix_routine_triggers_company_id", "ix_routine_triggers_routine_id", "ix_routine_triggers_code"),
                constraints=("uq_routine_trigger_code", "ck_routine_trigger_type", "ck_routine_trigger_activation"),
            ),
            TableFingerprint(
                "routine_trigger_events",
                columns=("id", "company_id", "routine_id", "trigger_id", "event_key", "payload_json", "status", "created_instances_json", "received_at", "processed_at"),
                indexes=("ix_routine_trigger_events_company_id", "ix_routine_trigger_events_routine_id", "ix_routine_trigger_events_trigger_id"),
                constraints=("uq_routine_trigger_event_key", "ck_routine_trigger_event_status"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260826_2000",
        tables=(
            TableFingerprint(
                "indicator_goal_routines",
                columns=("id", "company_id", "goal_id", "routine_id", "created_at"),
                indexes=("ix_indicator_goal_routines_company_id", "ix_indicator_goal_routines_goal_id", "ix_indicator_goal_routines_routine_id"),
                constraints=("uq_indicator_goal_routine",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260826_1800",
        tables=(
            TableFingerprint(
                "indicator_goals",
                columns=("name", "goal_kind", "goal_scope", "composition_mode"),
                indexes=("ix_indicator_goals_company_indicator_period", "ix_indicator_goals_company_responsible_period"),
                constraints=("ck_indicator_goals_kind", "ck_indicator_goals_scope", "ck_indicator_goals_composition", "ck_indicator_goals_scope_responsible", "ck_indicator_goals_period"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260821_1200",
        tables=(
            TableFingerprint(
                "capability_dimensions",
                columns=("id", "company_id", "name", "description", "order_index", "is_active", "created_at", "updated_at"),
                indexes=("uq_capability_dimensions_company_name", "ix_capability_dimensions_company_order"),
            ),
            TableFingerprint(
                "resource_catalog",
                columns=("id", "company_id", "dimension_id", "type", "subtype", "item_name", "unit_value", "quantity", "acquisition_total_amount", "installation_total_amount", "monthly_recurring_amount", "operational_capacity_value", "operational_capacity_unit", "operational_capacity_period", "max_recommended_utilization_pct", "estimated_useful_life", "notes", "is_active", "created_at", "updated_at"),
                indexes=("ix_resource_catalog_company_type", "ix_resource_catalog_company_subtype", "ix_resource_catalog_company_dimension"),
                constraints=("ck_resource_catalog_type", "ck_resource_catalog_capacity_unit", "ck_resource_catalog_capacity_period", "ck_resource_catalog_max_utilization", "ck_resource_catalog_unit_value_non_negative", "ck_resource_catalog_quantity_non_negative", "ck_resource_catalog_acquisition_non_negative", "ck_resource_catalog_installation_non_negative", "ck_resource_catalog_monthly_non_negative"),
            ),
            TableFingerprint(
                "process_resource_links",
                columns=("id", "company_id", "process_id", "process_routine_id", "bpmn_element_id", "resource_id", "used_quantity", "used_quantity_per_execution", "estimated_monthly_instances", "monthly_used_quantity", "usage_percentage", "allocated_monthly_cost", "estimated_cost_per_execution", "capacity_bottleneck_notes", "required_condition", "criticality", "gap_notes", "is_active", "created_at", "updated_at"),
                indexes=("ix_process_resource_links_company_process", "ix_process_resource_links_company_resource", "ix_process_resource_links_routine", "ix_process_resource_links_bpmn_element"),
                constraints=("ck_process_resource_links_usage_percentage_non_negative", "ck_process_resource_links_criticality", "ck_process_resource_links_allocated_monthly_non_negative", "ck_process_resource_links_execution_cost_non_negative", "ck_process_resource_links_used_quantity_non_negative", "ck_process_resource_links_used_per_execution_non_negative", "ck_process_resource_links_instances_non_negative", "ck_process_resource_links_monthly_used_non_negative"),
            ),
            TableFingerprint(
                "process_execution_plans",
                columns=("id", "company_id", "process_id", "frequency_count", "frequency_period", "working_days_per_month", "notes", "created_at", "updated_at"),
                indexes=("ix_process_execution_plans_company_process",),
                constraints=("uq_process_execution_plans_company_process",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260813_1200",
        tables=(
            TableFingerprint(
                "project_tasks",
                indexes=("ix_project_tasks_board_page",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260802_2100",
        tables=(
            TableFingerprint(
                "strategic_trees",
                columns=("id", "company_id", "title", "purpose", "status", "visibility_scope", "root_node_id", "created_by_user_id", "updated_by_user_id", "created_at", "updated_at", "archived_at"),
                indexes=("ix_strategic_trees_company_id", "ix_strategic_trees_status", "ix_strategic_trees_root_node_id", "ix_strategic_trees_company_status"),
                constraints=("fk_strategic_trees_root_node",),
            ),
            TableFingerprint(
                "strategic_tree_nodes",
                columns=("id", "company_id", "tree_id", "parent_node_id", "node_type", "title", "summary", "visible_status", "technical_status", "sensitivity_level", "visibility_scope", "sort_order", "owner_user_id", "created_by_user_id", "updated_by_user_id", "created_at", "updated_at", "closed_at", "archived_at"),
                indexes=("ix_strategic_tree_nodes_company_id", "ix_strategic_tree_nodes_tree_id", "ix_strategic_tree_nodes_parent_node_id", "ix_strategic_tree_nodes_visible_status", "ix_strategic_tree_nodes_technical_status", "ix_strategic_tree_nodes_company_tree", "ix_strategic_tree_nodes_tree_parent"),
                constraints=("ck_strategic_tree_nodes_type",),
            ),
            TableFingerprint(
                "strategic_tree_contributions",
                columns=("id", "company_id", "tree_id", "node_id", "contribution_type", "source_type", "source_ref", "attribution_mode", "author_user_id", "participant_ref", "raw_content", "sanitized_content", "classification_json", "confidence_state", "sensitivity_level", "visibility_scope", "status", "idempotency_key", "created_at", "updated_at", "deleted_at"),
                indexes=("ix_strategic_tree_contributions_company_id", "ix_strategic_tree_contributions_tree_id", "ix_strategic_tree_contributions_node_id", "ix_strategic_tree_contributions_contribution_type", "ix_strategic_tree_contributions_source_type", "ix_strategic_tree_contributions_author_user_id", "ix_strategic_tree_contributions_status", "ix_strategic_tree_contributions_created_at", "ix_strategic_tree_contributions_deleted_at", "ix_strategic_tree_contributions_company_node"),
                constraints=("uq_strategic_tree_contribution_idempotency", "ck_strategic_tree_contributions_attribution"),
            ),
            TableFingerprint(
                "strategic_tree_audit_events",
                columns=("id", "company_id", "tree_id", "node_id", "contribution_id", "event_type", "actor_user_id", "surface", "metadata_json", "created_at"),
                indexes=("ix_strategic_tree_audit_events_company_id", "ix_strategic_tree_audit_events_tree_id", "ix_strategic_tree_audit_events_node_id", "ix_strategic_tree_audit_events_contribution_id", "ix_strategic_tree_audit_events_event_type", "ix_strategic_tree_audit_events_actor_user_id", "ix_strategic_tree_audit_events_created_at", "ix_strategic_tree_audit_company_created"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260801_1530",
        tables=(
            TableFingerprint(
                "process_execution_assignments",
                columns=(
                    "id", "company_id", "activity_execution_id", "assignee_type", "employee_id",
                    "team_id", "role_key", "status", "source", "assigned_by_user_id", "assigned_at",
                    "claimed_at", "completed_at", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_process_execution_assignments_company_id",
                    "ix_process_execution_assignments_activity_execution_id",
                    "ix_process_execution_assignments_employee_id",
                    "ix_process_execution_assignments_team_id", "ix_process_execution_assignments_role_key",
                    "ix_process_execution_assignments_status",
                    "ix_process_execution_assignment_company_activity_status",
                    "ix_process_execution_assignment_company_employee_status",
                    "uq_process_execution_assignment_active",
                ),
                constraints=(
                    "ck_process_execution_assignment_type", "ck_process_execution_assignment_status",
                    "ck_process_execution_assignment_target",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260801_1500",
        tables=(
            TableFingerprint(
                "process_activity_artifact_definitions",
                columns=(
                    "id", "company_id", "process_id", "artifact_key", "artifact_type", "name",
                    "description", "version", "status", "configuration_json", "legacy_process_routine_id",
                    "created_by_user_id", "updated_by_user_id", "published_at", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_process_artifact_definition_company_process_type",
                    "ix_process_activity_artifact_definitions_company_id",
                    "ix_process_activity_artifact_definitions_process_id",
                    "ix_process_activity_artifact_definitions_artifact_type",
                    "ix_process_activity_artifact_definitions_status",
                    "ix_process_artifact_definition_legacy_pop",
                ),
                constraints=(
                    "ck_process_artifact_definition_type", "ck_process_artifact_definition_status",
                    "ck_process_artifact_definition_version_positive", "uq_process_artifact_definition_version",
                    "uq_process_artifact_definition_legacy_pop_version",
                ),
            ),
            TableFingerprint(
                "process_activity_artifact_links",
                columns=(
                    "id", "company_id", "process_id", "bpmn_element_id", "artifact_definition_id",
                    "display_order", "is_required", "completion_policy_json", "is_active", "created_at",
                    "updated_at",
                ),
                indexes=(
                    "ix_process_artifact_link_company_activity",
                    "ix_process_activity_artifact_links_company_id",
                    "ix_process_activity_artifact_links_process_id",
                    "ix_process_activity_artifact_links_bpmn_element_id",
                    "ix_process_activity_artifact_links_artifact_definition_id",
                ),
                constraints=(
                    "ck_process_artifact_link_order_non_negative",
                    "uq_process_artifact_link_activity_definition",
                ),
            ),
            TableFingerprint(
                "process_activity_artifact_executions",
                columns=(
                    "id", "company_id", "process_instance_id", "activity_execution_id", "artifact_definition_id",
                    "artifact_key", "artifact_type", "artifact_version", "definition_snapshot_json", "status",
                    "input_json", "output_json", "evidence_json", "error_json", "started_at", "completed_at",
                    "created_at", "updated_at",
                ),
                indexes=(
                    "ix_process_artifact_execution_company_instance_status",
                    "ix_process_activity_artifact_executions_company_id",
                    "ix_process_activity_artifact_executions_process_instance_id",
                    "ix_process_activity_artifact_executions_activity_execution_id",
                    "ix_process_activity_artifact_executions_artifact_definition_id",
                    "ix_process_activity_artifact_executions_artifact_type",
                    "ix_process_activity_artifact_executions_status",
                ),
                constraints=(
                    "ck_process_artifact_execution_type", "ck_process_artifact_execution_status",
                    "ck_process_artifact_execution_version_positive",
                    "uq_process_artifact_execution_activity_definition",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260801_0900",
        tables=(
            TableFingerprint(
                "knowledge_interactions",
                columns=(
                    "id", "interaction_uuid", "company_id", "user_id", "employee_id", "requested_scope",
                    "knowledge_scope", "question", "normalized_question", "answer_preview",
                    "understanding_json", "query_plan_json", "citations_json", "actions_json",
                    "warnings_json", "engine_version", "rating_status", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_knowledge_interactions_company_created",
                    "ix_knowledge_interactions_normalized_question", "ix_knowledge_interactions_rating_status",
                ),
                index_alternatives=(("uq_knowledge_interactions_uuid", "ix_knowledge_interactions_interaction_uuid"),),
                constraints=("ck_knowledge_interactions_rating_status",),
            ),
            TableFingerprint(
                "knowledge_feedback",
                columns=(
                    "id", "interaction_id", "company_id", "user_id", "rating", "reason", "comment",
                    "expected_answer", "metadata_json", "created_at",
                ),
                indexes=(
                    "ix_knowledge_feedback_interaction_id", "ix_knowledge_feedback_company_rating",
                    "ix_knowledge_feedback_reason",
                ),
                constraints=("ck_knowledge_feedback_rating", "ck_knowledge_feedback_reason"),
            ),
            TableFingerprint(
                "knowledge_training_proposals",
                columns=(
                    "id", "proposal_uuid", "company_id", "proposal_scope", "pattern", "suggested_intent",
                    "suggested_domain", "suggestion_type", "evidence_count", "evidence_json", "sources_json",
                    "recommendation_json", "status", "created_by", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_knowledge_training_company_status",
                ),
                index_alternatives=(
                    ("uq_knowledge_training_proposals_uuid", "ix_knowledge_training_proposals_proposal_uuid"),
                    ("ix_knowledge_training_pattern", "ix_knowledge_training_proposals_pattern"),
                ),
                constraints=("ck_knowledge_training_proposals_status",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260730_1800",
        tables=(
            TableFingerprint(
                "knowledge_source_grants",
                columns=(
                    "id", "knowledge_source_id", "company_id", "grant_scope", "user_id",
                    "employee_id", "metadata_json", "created_at",
                ),
                indexes=(
                    "ix_knowledge_source_grants_knowledge_source_id",
                    "ix_knowledge_source_grants_company_id",
                    "ix_knowledge_source_grants_grant_scope",
                    "ix_knowledge_source_grants_user_id",
                    "ix_knowledge_source_grants_employee_id",
                    "uq_knowledge_source_grants_company",
                    "uq_knowledge_source_grants_user",
                    "uq_knowledge_source_grants_employee",
                ),
                constraints=("ck_knowledge_source_grants_scope_target",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260720_0900",
        tables=(
            TableFingerprint(
                "consultive_assisted_analyses",
                columns=("analysis_type", "journey_eligible", "eligibility_reasons_json"),
                indexes=("ix_consultive_assisted_analyses_company_front_eligible",),
                constraints=("ck_consultive_assisted_analyses_analysis_type",),
                constraint_fragments=(
                    ("ck_consultive_assisted_analyses_analysis_type", "technical_test"),
                ),
                column_default_fragments=(
                    ("analysis_type", "technical_test"),
                    ("journey_eligible", "false"),
                    ("eligibility_reasons_json", "[]"),
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260719_1030",
        tables=(
            TableFingerprint(
                "audit_workpapers",
                columns=(
                    "id", "company_id", "execution_id", "execution_item_id", "audit_point_id",
                    "auditor_user_id", "comments", "conclusion", "alert_notes", "evidence_summary",
                    "metadata_json", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_audit_workpapers_company_id", "ix_audit_workpapers_company_execution",
                    "ix_audit_workpapers_company_item", "ix_audit_workpapers_company_point",
                    "ix_audit_workpapers_company_auditor",
                ),
            ),
            TableFingerprint(
                "audit_findings",
                columns=(
                    "id", "company_id", "audit_point_id", "execution_id", "execution_item_id", "title",
                    "condition_text", "criterion_text", "cause_text", "effect_text", "recommendation_text",
                    "severity", "status", "responsible_user_id", "due_date", "project_id", "task_id",
                    "alignment_meeting_id", "metadata_json", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_audit_findings_company_id", "ix_audit_findings_company_status",
                    "ix_audit_findings_company_severity", "ix_audit_findings_company_point",
                    "ix_audit_findings_company_project", "ix_audit_findings_company_task",
                ),
                constraints=("ck_audit_findings_severity", "ck_audit_findings_status"),
            ),
            TableFingerprint(
                "audit_evidence_links",
                columns=(
                    "id", "company_id", "workpaper_id", "finding_id", "evidence_type", "source_module",
                    "source_id", "file_path", "caption", "created_by_user_id", "created_at",
                ),
                indexes=(
                    "ix_audit_evidence_links_company_id", "ix_audit_evidence_links_company_workpaper",
                    "ix_audit_evidence_links_company_finding", "ix_audit_evidence_links_company_source",
                ),
                constraints=("ck_audit_evidence_links_type", "ck_audit_evidence_links_parent"),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260719_0900",
        tables=(
            TableFingerprint(
                "audit_points",
                columns=(
                    "id", "company_id", "title", "description", "origin_type", "source_module",
                    "subject_type", "subject_id", "severity", "status", "assigned_to_user_id",
                    "detected_at", "due_date", "metadata_json", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_audit_points_company_id", "ix_audit_points_company_status",
                    "ix_audit_points_company_severity", "ix_audit_points_company_due_date",
                ),
                constraints=(
                    "ck_audit_points_origin_type", "ck_audit_points_severity", "ck_audit_points_status",
                ),
            ),
            TableFingerprint(
                "audit_executions",
                columns=(
                    "id", "company_id", "checklist_id", "schedule_id", "area_id", "auditor_user_id",
                    "period_label", "planned_start_date", "planned_end_date", "started_at", "completed_at",
                    "status", "metadata_json", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_audit_executions_company_id", "ix_audit_executions_company_status",
                    "ix_audit_executions_company_checklist", "ix_audit_executions_company_schedule",
                ),
                constraints=("ck_audit_executions_status",),
            ),
            TableFingerprint(
                "audit_execution_items",
                columns=(
                    "id", "company_id", "execution_id", "checklist_item_id", "status", "justification",
                    "comments", "audit_point_id", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_audit_execution_items_company_id", "ix_audit_execution_items_company_execution",
                    "ix_audit_execution_items_company_status",
                ),
                constraints=(
                    "ck_audit_execution_items_status", "uq_audit_execution_items_execution_item",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260718_1200",
        tables=(
            TableFingerprint(
                "user_mcp_tokens",
                columns=("last_harness_key",),
                indexes=("ix_user_mcp_tokens_last_harness_key",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260702_1800",
        tables=(
            TableFingerprint(
                "consultive_assisted_analyses",
                constraints=("ck_consultive_assisted_analyses_status",),
                constraint_fragments=(
                    ("ck_consultive_assisted_analyses_status", "conversion_requested"),
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260701_1015",
        tables=(
            TableFingerprint(
                "consultive_assisted_analyses",
                columns=(
                    "id", "company_id", "front_key", "status", "ai_origin", "responsible",
                    "diagnosis", "benchmarks", "risks", "recommendations", "source_payload_json",
                    "created_by_user_id", "updated_by_user_id", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_consultive_assisted_analyses_company_front",
                    "ix_consultive_assisted_analyses_company_status",
                ),
                constraints=(
                    "ck_consultive_assisted_analyses_front_key",
                    "ck_consultive_assisted_analyses_status",
                ),
            ),
            TableFingerprint(
                "consultive_assisted_analysis_validations",
                columns=(
                    "id", "company_id", "analysis_id", "squad", "status", "notes",
                    "validated_by_user_id", "created_at", "updated_at",
                ),
                indexes=("ix_consultive_assisted_analysis_validations_company_analysis",),
                constraints=(
                    "ck_consultive_assisted_analysis_validations_squad",
                    "ck_consultive_assisted_analysis_validations_status",
                    "uq_consultive_assisted_analysis_validations_analysis_squad",
                ),
            ),
            TableFingerprint(
                "consultive_assisted_analysis_decisions",
                columns=(
                    "id", "company_id", "analysis_id", "decision", "conversion_target",
                    "decision_reason", "next_action", "governance_notes", "decided_by_user_id",
                    "created_at", "updated_at",
                ),
                indexes=("ix_consultive_assisted_analysis_decisions_company_analysis",),
                constraints=(
                    "ck_consultive_assisted_analysis_decisions_decision",
                    "ck_consultive_assisted_analysis_decisions_conversion_target",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260701_1030",
        tables=(
            TableFingerprint(
                "consultive_protocols",
                columns=(
                    "id", "company_id", "front_key", "subphase_key", "audience", "depth_level",
                    "status", "protocol_version", "title", "objective", "prompt_markdown",
                    "protocol_json", "notes", "approved_by_user_id", "created_by_user_id",
                    "updated_by_user_id", "approved_at", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_consultive_protocols_resolution",
                    "ix_consultive_protocols_global_resolution",
                ),
                constraints=(
                    "ck_consultive_protocols_status",
                    "ck_consultive_protocols_audience",
                    "ck_consultive_protocols_depth_level",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260701_1045",
        tables=(
            TableFingerprint(
                "consultive_assisted_analyses",
                columns=(
                    "protocol_id", "protocol_version", "protocol_source", "protocol_title",
                    "protocol_snapshot_json",
                ),
                indexes=(
                    "ix_consultive_assisted_analyses_company_protocol",
                    "ix_consultive_assisted_analyses_company_front_protocol_version",
                ),
                constraints=("fk_consultive_assisted_analyses_protocol_id",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260630_1845",
        tables=(
            TableFingerprint(
                "urgent_need_overlays",
                columns=(
                    "id", "company_id", "title", "description", "status", "urgency_level",
                    "criticality_level", "origin_channel", "origin_summary", "project_id",
                    "project_task_id", "process_id", "process_instance_id", "routine_id",
                    "indicator_id", "meeting_id", "occurrence_id", "financial_ref_id", "source_type",
                    "source_ref_id", "source_payload_json", "business_impact_summary",
                    "operational_impact_summary", "risk_summary", "decision_status", "decision_summary",
                    "responsible_employee_id", "created_by_user_id", "updated_by_user_id",
                    "closed_by_user_id", "created_at", "updated_at", "closed_at",
                ),
                indexes=(
                    "ix_urgent_need_overlays_company_status",
                    "ix_urgent_need_overlays_company_urgency",
                    "ix_urgent_need_overlays_company_project",
                    "ix_urgent_need_overlays_company_task",
                    "ix_urgent_need_overlays_company_process",
                    "ix_urgent_need_overlays_company_indicator",
                ),
                constraints=(
                    "ck_urgent_need_overlays_status",
                    "ck_urgent_need_overlays_urgency_level",
                    "ck_urgent_need_overlays_criticality_level",
                    "ck_urgent_need_overlays_has_canonical_link",
                ),
            ),
            TableFingerprint(
                "business_review_records",
                columns=(
                    "id", "company_id", "title", "review_type", "status", "urgent_need_id",
                    "project_id", "project_task_id", "process_id", "indicator_id", "meeting_id",
                    "cost_to_act", "cost_to_not_act", "required_investment", "expected_gain",
                    "expected_return", "risk_level", "risk_acceptance_decision", "risk_acceptance_reason",
                    "decision_summary", "structural_learning_summary", "next_action",
                    "responsible_employee_id", "reviewed_by_user_id", "created_by_user_id",
                    "updated_by_user_id", "reviewed_at", "created_at", "updated_at", "closed_at",
                ),
                indexes=(
                    "ix_business_review_records_company_status",
                    "ix_business_review_records_company_type",
                    "ix_business_review_records_company_urgent_need",
                    "ix_business_review_records_company_project",
                    "ix_business_review_records_company_process",
                ),
                constraints=(
                    "ck_business_review_records_review_type",
                    "ck_business_review_records_status",
                    "ck_business_review_records_risk_reason",
                ),
            ),
            TableFingerprint(
                "structural_learning_links",
                columns=(
                    "id", "company_id", "business_review_id", "urgent_need_id", "target_project_id",
                    "target_project_task_id", "target_process_id", "target_routine_id", "target_indicator_id",
                    "target_meeting_id", "learning_type", "action_decision", "accepted_risk_reason",
                    "recommended_change", "created_project_id", "created_task_id", "created_by_user_id",
                    "updated_by_user_id", "created_at", "updated_at",
                ),
                indexes=(
                    "ix_structural_learning_links_company_review",
                    "ix_structural_learning_links_company_urgent_need",
                    "ix_structural_learning_links_company_process",
                ),
                constraints=(
                    "ck_structural_learning_links_learning_type",
                    "ck_structural_learning_links_action_decision",
                    "ck_structural_learning_links_risk_reason",
                ),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260730_1600",
        tables=(
            TableFingerprint(
                "audit_reports",
                columns=(
                    "id",
                    "company_id",
                    "execution_id",
                    "version",
                    "supersedes_report_id",
                    "title",
                    "objective",
                    "scope_text",
                    "period_start",
                    "period_end",
                    "executive_summary",
                    "auditor_conclusion",
                    "opinion",
                    "status",
                    "snapshot_json",
                    "prepared_by_user_id",
                    "approved_by_user_id",
                    "approved_at",
                    "issued_at",
                    "created_at",
                    "updated_at",
                ),
                indexes=(
                    "ix_audit_reports_company_status",
                    "ix_audit_reports_company_execution",
                    "ix_audit_reports_company_issued",
                ),
                constraints=("ck_audit_reports_status", "uq_audit_reports_company_execution_version"),
            ),
            TableFingerprint(
                "audit_follow_ups",
                columns=(
                    "id",
                    "company_id",
                    "finding_id",
                    "previous_status",
                    "status",
                    "action_summary",
                    "auditor_notes",
                    "evidence_summary",
                    "due_date",
                    "next_review_date",
                    "performed_by_user_id",
                    "created_at",
                ),
                indexes=(
                    "ix_audit_follow_ups_company_finding",
                    "ix_audit_follow_ups_company_status",
                    "ix_audit_follow_ups_company_review",
                ),
                constraints=("ck_audit_follow_ups_status",),
            ),
        ),
    ),
    SchemaMarker(
        revision="20260730_1700",
        tables=(
            TableFingerprint(
                "knowledge_sources",
                columns=(
                    "id",
                    "company_id",
                    "knowledge_scope",
                    "source_type",
                    "source_ref",
                    "knowledge_kind",
                    "title",
                    "canonical_uri",
                    "status",
                    "authority_level",
                    "version",
                    "product_version",
                    "locale",
                    "route_key",
                    "module_key",
                    "audience_json",
                    "required_capabilities_json",
                    "help_kind",
                    "navigation_target",
                    "tour_definition_id",
                    "metadata_json",
                    "content_checksum",
                    "valid_from",
                    "valid_to",
                    "source_updated_at",
                    "indexed_at",
                    "deleted_at",
                    "created_at",
                    "updated_at",
                ),
                indexes=(
                    "ix_knowledge_sources_company_id",
                    "ix_knowledge_sources_knowledge_scope",
                    "ix_knowledge_sources_source_type",
                    "ix_knowledge_sources_source_ref",
                    "ix_knowledge_sources_knowledge_kind",
                    "ix_knowledge_sources_status",
                    "ix_knowledge_sources_product_version",
                    "ix_knowledge_sources_route_key",
                    "ix_knowledge_sources_module_key",
                    "ix_knowledge_sources_help_kind",
                    "ix_knowledge_sources_content_checksum",
                    "ix_knowledge_sources_indexed_at",
                    "ix_knowledge_sources_deleted_at",
                    "uq_knowledge_sources_product_ref",
                    "uq_knowledge_sources_company_ref",
                ),
                constraints=("ck_knowledge_sources_scope_company",),
            ),
            TableFingerprint(
                "knowledge_chunks",
                columns=(
                    "id",
                    "knowledge_source_id",
                    "company_id",
                    "knowledge_scope",
                    "section_key",
                    "content",
                    "metadata_json",
                    "chunk_order",
                    "token_count",
                    "content_checksum",
                    "parent_chunk_id",
                    "source_span",
                    "adapter_version",
                    "parser_version",
                    "chunking_policy",
                    "created_at",
                    "updated_at",
                ),
                indexes=(
                    "ix_knowledge_chunks_knowledge_source_id",
                    "ix_knowledge_chunks_company_id",
                    "ix_knowledge_chunks_knowledge_scope",
                    "ix_knowledge_chunks_content_checksum",
                    "ix_knowledge_chunks_parent_chunk_id",
                    "ix_knowledge_chunks_content_fts",
                ),
                constraints=("ck_knowledge_chunks_scope_company", "uq_knowledge_chunks_source_section"),
            ),
            TableFingerprint(
                "knowledge_index_runs",
                columns=(
                    "id",
                    "company_id",
                    "knowledge_scope",
                    "source_type",
                    "trigger_kind",
                    "status",
                    "discovered_count",
                    "created_count",
                    "updated_count",
                    "unchanged_count",
                    "deactivated_count",
                    "failed_count",
                    "error_message",
                    "metadata_json",
                    "started_at",
                    "completed_at",
                ),
                indexes=(
                    "ix_knowledge_index_runs_company_id",
                    "ix_knowledge_index_runs_knowledge_scope",
                    "ix_knowledge_index_runs_source_type",
                    "ix_knowledge_index_runs_trigger_kind",
                    "ix_knowledge_index_runs_status",
                    "ix_knowledge_index_runs_started_at",
                ),
            ),
        ),
    ),
)


def assess_marker(
    *,
    existing_tables: Iterable[str],
    actual_fingerprints: dict[str, dict[str, object]] | None = None,
    marker: SchemaMarker,
) -> dict[str, object]:
    existing = set(existing_tables)
    expected_names = {table.name for table in marker.tables}
    missing = sorted(expected_names - existing)
    present = sorted(expected_names & existing)
    actual_fingerprints = actual_fingerprints or {}
    mismatches: dict[str, dict[str, list[str]]] = {}
    for table in marker.tables:
        actual = actual_fingerprints.get(table.name, {})
        differences = {
            "columns_missing": sorted(set(table.columns) - actual.get("columns", set())),
            "indexes_missing": sorted(set(table.indexes) - actual.get("indexes", set())),
            "index_alternatives_missing": sorted(
                "|".join(alternatives)
                for alternatives in table.index_alternatives
                if not set(alternatives) & set(actual.get("indexes", set()))
            ),
            "constraints_missing": sorted(set(table.constraints) - actual.get("constraints", set())),
            "constraint_fragments_missing": sorted(
                constraint_name
                for constraint_name, expected_fragment in table.constraint_fragments
                if expected_fragment not in str(actual.get("constraint_definitions", {}).get(constraint_name, ""))
            ),
            "column_default_fragments_missing": sorted(
                column_name
                for column_name, expected_fragment in table.column_default_fragments
                if expected_fragment not in str(actual.get("column_defaults", {}).get(column_name, ""))
            ),
        }
        if any(differences.values()):
            mismatches[table.name] = differences
    return {
        "revision": marker.revision,
        "tables_present": present,
        "tables_missing": missing,
        "fingerprint_mismatches": mismatches,
        "physical_state": "complete_candidate" if not missing and not mismatches else "partial_or_absent",
        # Mesmo quando todos os objetos existem, ainda faltam fingerprint e
        # validação de dados/seed: nunca promover esta resposta a um stamp.
        "stamp_allowed": False,
    }


def assess_protocol_seed(
    *,
    marker: ProtocolSeedMarker,
    global_rows: int,
    tenant_rows: int,
    tenant_expected: bool,
) -> dict[str, object]:
    expected_rows = 1 + int(tenant_expected)
    matching_rows = global_rows + tenant_rows
    if matching_rows == 0:
        state = "absent_or_pending"
    elif global_rows == 1 and (not tenant_expected or tenant_rows == 1):
        state = "complete_candidate"
    else:
        state = "partial_or_divergent"
    return {
        "revision": marker.revision,
        "protocol_version": marker.protocol_version,
        "expected_rows": expected_rows,
        "matching_rows": matching_rows,
        "global_rows": global_rows,
        "tenant_rows": tenant_rows,
        "physical_state": state,
        "stamp_allowed": False,
    }


def assess_portfolio_backfill(
    *,
    marker: PortfolioBackfillMarker,
    eligible_projects_without_portfolio: int,
    generated_portfolios: int,
    linked_projects_to_generated_portfolio: int,
) -> dict[str, object]:
    if eligible_projects_without_portfolio and not generated_portfolios:
        state = "absent_or_pending"
    elif eligible_projects_without_portfolio:
        state = "partial_or_divergent"
    else:
        state = "complete_candidate"
    return {
        "revision": marker.revision,
        "eligible_projects_without_portfolio": eligible_projects_without_portfolio,
        "generated_portfolios": generated_portfolios,
        "linked_projects_to_generated_portfolio": linked_projects_to_generated_portfolio,
        "physical_state": state,
        "stamp_allowed": False,
    }


def assess_process_artifact_backfill(
    *,
    marker: ProcessArtifactBackfillMarker,
    eligible_definitions_missing: int,
    generated_definitions: int,
    generated_definitions_without_link: int,
) -> dict[str, object]:
    if eligible_definitions_missing and generated_definitions:
        state = "partial_or_divergent"
    elif eligible_definitions_missing:
        state = "absent_or_pending"
    elif generated_definitions_without_link:
        state = "partial_or_divergent"
    else:
        state = "complete_candidate"
    return {
        "revision": marker.revision,
        "eligible_definitions_missing": eligible_definitions_missing,
        "generated_definitions": generated_definitions,
        "generated_definitions_without_link": generated_definitions_without_link,
        "physical_state": state,
        "stamp_allowed": False,
    }


def assess_capability_rollout(*, marker: CapabilityRolloutMarker, capability_rows: int, enabled_settings: int) -> dict[str, object]:
    if not capability_rows and not enabled_settings:
        state = "absent_or_pending"
    elif capability_rows == 1 and enabled_settings == 1:
        state = "complete_candidate"
    else:
        state = "partial_or_divergent"
    return {
        "revision": marker.revision,
        "capability_key": marker.capability_key,
        "company_id": marker.company_id,
        "capability_rows": capability_rows,
        "enabled_settings": enabled_settings,
        "physical_state": state,
        "stamp_allowed": False,
    }


def assess_capability_dimension_seed(
    *, marker: CapabilityDimensionSeedMarker, company_count: int, missing_dimensions: int
) -> dict[str, object]:
    expected_dimensions = company_count * len(marker.dimension_names)
    if missing_dimensions == expected_dimensions:
        state = "absent_or_pending"
    elif missing_dimensions:
        state = "partial_or_divergent"
    else:
        state = "complete_candidate"
    return {
        "revision": marker.revision,
        "company_count": company_count,
        "expected_dimensions": expected_dimensions,
        "missing_dimensions": missing_dimensions,
        "physical_state": state,
        "stamp_allowed": False,
    }


def assess_indicator_goal_normalization(
    *,
    marker: IndicatorGoalNormalizationMarker,
    legacy_active_recurring_start_date: int,
    missing_period_end_candidate: int,
) -> dict[str, object]:
    remaining = legacy_active_recurring_start_date + missing_period_end_candidate
    return {
        "revision": marker.revision,
        "legacy_active_recurring_start_date": legacy_active_recurring_start_date,
        "missing_period_end_candidate": missing_period_end_candidate,
        "physical_state": "complete_candidate" if not remaining else "partial_or_divergent",
        "stamp_allowed": False,
    }


def assess_indicator_goal_routine_backfill(
    *, marker: IndicatorGoalRoutineBackfillMarker, eligible_missing_links: int, generated_links: int
) -> dict[str, object]:
    # O marcador só é avaliado junto ao schema da própria revision. Se a tabela
    # já existe e ainda há metas elegíveis sem vínculo, o INSERT histórico não
    # foi materializado integralmente, ainda que não tenha produzido nenhuma
    # linha até então.
    state = "partial_or_divergent" if eligible_missing_links else "complete_candidate"
    return {
        "revision": marker.revision,
        "eligible_missing_links": eligible_missing_links,
        "generated_links": generated_links,
        "physical_state": state,
        "stamp_allowed": False,
    }


def requires_reconciliation(findings: Iterable[dict[str, object]]) -> bool:
    """Indica drift físico que exige investigação antes de qualquer upgrade.

    A ausência total dos objetos de um marcador é compatível com uma revision
    ainda não aplicada. A presença de qualquer objeto, mesmo incompleto, não é:
    ela pode bloquear a migration histórica e exige reconciliação explícita.
    """

    return any(bool(finding["tables_present"]) for finding in findings)


def revision_evidence_flags(revision_path: str | Path) -> list[str]:
    """Classifica riscos estáticos do trecho ``upgrade`` de uma revision.

    A classificação não prova que houve mutation; ela obriga a coleta de
    evidência de schema ou dados antes de uma reconciliação de ledger.
    """

    source = Path(revision_path).read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(revision_path))
    upgrade_node = next(
        (
            node
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "upgrade"
        ),
        None,
    )
    if upgrade_node is None:
        return []
    upgrade_source = ast.get_source_segment(source, upgrade_node) or ""
    flags: list[str] = []
    if "CREATE TABLE IF NOT EXISTS" in upgrade_source:
        flags.append("idempotent_schema")
    if any(
        operation in upgrade_source
        for operation in (
            "op.create_table(",
            "op.add_column(",
            "op.drop_column(",
            "op.create_index(",
            "op.drop_index(",
            "op.create_unique_constraint(",
            "op.create_foreign_key(",
            "op.drop_constraint(",
            "op.alter_column(",
        )
    ):
        flags.append("non_idempotent_schema")
    if any(statement in upgrade_source for statement in ("INSERT INTO", "UPDATE ", "DELETE FROM")):
        flags.append("data_mutation")
    if "op.execute(" in upgrade_source:
        flags.append("raw_sql")
    return flags


def pending_revision_path(
    *,
    applied_revisions: Iterable[str],
    migrations_path: str | Path,
) -> dict[str, object]:
    """Retorna a cadeia pendente em ordem de aplicação, sem tocar no banco."""

    config = Config()
    config.set_main_option("script_location", str(migrations_path))
    script = ScriptDirectory.from_config(config)
    heads = sorted(script.get_heads())
    pending = list(script.iterate_revisions(tuple(heads), tuple(applied_revisions)))
    pending_in_application_order = list(reversed(pending))
    return {
        "alembic_heads": heads,
        "pending_revisions": [revision.revision for revision in pending_in_application_order],
        "revisions_requiring_evidence": [
            {"revision": revision.revision, "flags": revision_evidence_flags(revision.path)}
            for revision in pending_in_application_order
            if revision_evidence_flags(revision.path)
        ],
    }


def audit(database_url: str, *, migrations_path: str | Path | None = None) -> dict[str, object]:
    conn = psycopg2.connect(database_url, connect_timeout=5)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
            ledger = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            fingerprints: dict[str, dict[str, object]] = {}
            for table in tables:
                cursor.execute(
                    "SELECT column_name, column_default FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = %s",
                    (table,),
                )
                columns_and_defaults = cursor.fetchall()
                columns = {name for name, _ in columns_and_defaults}
                column_defaults = {name: default for name, default in columns_and_defaults}
                cursor.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = %s",
                    (table,),
                )
                indexes = {row[0] for row in cursor.fetchall()}
                cursor.execute(
                    "SELECT conname, pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conrelid = %s::regclass",
                    (table,),
                )
                constraint_definitions = {name: definition for name, definition in cursor.fetchall()}
                fingerprints[table] = {
                    "columns": columns,
                    "indexes": indexes,
                    "constraints": set(constraint_definitions),
                    "constraint_definitions": constraint_definitions,
                    "column_defaults": column_defaults,
                }
        findings = [
            assess_marker(existing_tables=tables, actual_fingerprints=fingerprints, marker=marker)
            for marker in sorted(MARKERS, key=lambda marker: marker.revision)
        ]
        seed_findings: list[dict[str, object]] = []
        with conn.cursor() as cursor:
            for marker in PROTOCOL_SEED_MARKERS:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM companies WHERE client_code = 'AA')")
                tenant_expected = bool(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM consultive_protocols "
                    "WHERE protocol_version = %s AND company_id IS NULL AND notes = %s",
                    (marker.protocol_version, marker.global_note),
                )
                global_rows = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM consultive_protocols "
                    "WHERE protocol_version = %s AND notes = %s",
                    (marker.protocol_version, marker.tenant_note),
                )
                tenant_rows = int(cursor.fetchone()[0])
                seed_findings.append(
                    assess_protocol_seed(
                        marker=marker,
                        global_rows=global_rows,
                        tenant_rows=tenant_rows,
                        tenant_expected=tenant_expected,
                    )
                )
        data_findings: list[dict[str, object]] = []
        with conn.cursor() as cursor:
            for marker in PORTFOLIO_BACKFILL_MARKERS:
                cursor.execute(
                    "SELECT COUNT(*) FROM projects AS project "
                    "WHERE project.plan_id IS NOT NULL AND project.portfolio_id IS NULL "
                    "AND COALESCE(project.is_deleted, FALSE) = FALSE"
                )
                eligible_projects_without_portfolio = int(cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM portfolios WHERE notes LIKE '[APP32_PLAN_PORTFOLIO]%'")
                generated_portfolios = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM projects AS project "
                    "JOIN portfolios AS portfolio ON portfolio.id = project.portfolio_id "
                    "WHERE portfolio.notes LIKE '[APP32_PLAN_PORTFOLIO]%'"
                )
                linked_projects_to_generated_portfolio = int(cursor.fetchone()[0])
                data_findings.append(
                    assess_portfolio_backfill(
                        marker=marker,
                        eligible_projects_without_portfolio=eligible_projects_without_portfolio,
                        generated_portfolios=generated_portfolios,
                        linked_projects_to_generated_portfolio=linked_projects_to_generated_portfolio,
                    )
                )
            for marker in CAPABILITY_ROLLOUT_MARKERS:
                cursor.execute("SELECT COUNT(*) FROM ai_capabilities WHERE key = %s", (marker.capability_key,))
                capability_rows = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM ai_capability_company_settings AS setting "
                    "JOIN ai_capabilities AS capability ON capability.id = setting.capability_id "
                    "WHERE capability.key = %s AND setting.company_id = %s AND setting.is_enabled = TRUE",
                    (marker.capability_key, marker.company_id),
                )
                enabled_settings = int(cursor.fetchone()[0])
                data_findings.append(
                    assess_capability_rollout(
                        marker=marker,
                        capability_rows=capability_rows,
                        enabled_settings=enabled_settings,
                    )
                )
            for marker in CAPABILITY_DIMENSION_SEED_MARKERS:
                cursor.execute("SELECT COUNT(*) FROM companies")
                company_count = int(cursor.fetchone()[0])
                if "capability_dimensions" in tables:
                    cursor.execute(
                        "SELECT COUNT(*) FROM companies AS company "
                        "CROSS JOIN unnest(%s::text[]) AS expected(name) "
                        "LEFT JOIN capability_dimensions AS dimension "
                        "ON dimension.company_id = company.id AND dimension.name = expected.name "
                        "WHERE dimension.id IS NULL",
                        (list(marker.dimension_names),),
                    )
                    missing_dimensions = int(cursor.fetchone()[0])
                else:
                    missing_dimensions = company_count * len(marker.dimension_names)
                data_findings.append(
                    assess_capability_dimension_seed(
                        marker=marker,
                        company_count=company_count,
                        missing_dimensions=missing_dimensions,
                    )
                )
            for marker in INDICATOR_GOAL_NORMALIZATION_MARKERS:
                cursor.execute(
                    "SELECT COUNT(*) FROM indicator_goals "
                    "WHERE status = 'active' AND COALESCE(goal_type, 'monthly') <> 'single' "
                    "AND goal_date = period_start"
                )
                legacy_active_recurring_start_date = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM indicator_goals "
                    "WHERE period_end IS NULL AND goal_date IS NOT NULL "
                    "AND goal_date > period_start"
                )
                missing_period_end_candidate = int(cursor.fetchone()[0])
                data_findings.append(
                    assess_indicator_goal_normalization(
                        marker=marker,
                        legacy_active_recurring_start_date=legacy_active_recurring_start_date,
                        missing_period_end_candidate=missing_period_end_candidate,
                    )
                )
            for marker in INDICATOR_GOAL_ROUTINE_BACKFILL_MARKERS:
                if "indicator_goal_routines" in tables:
                    cursor.execute(
                        "SELECT COUNT(*) FROM indicator_goals AS goal "
                        "JOIN routines AS routine ON routine.id = goal.routine_id "
                        "AND routine.company_id = goal.company_id "
                        "LEFT JOIN indicator_goal_routines AS link "
                        "ON link.company_id = goal.company_id AND link.goal_id = goal.id "
                        "AND link.routine_id = goal.routine_id "
                        "WHERE goal.routine_id IS NOT NULL AND link.id IS NULL"
                    )
                    eligible_missing_links = int(cursor.fetchone()[0])
                    cursor.execute("SELECT COUNT(*) FROM indicator_goal_routines")
                    generated_links = int(cursor.fetchone()[0])
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM indicator_goals AS goal "
                        "JOIN routines AS routine ON routine.id = goal.routine_id "
                        "AND routine.company_id = goal.company_id "
                        "WHERE goal.routine_id IS NOT NULL"
                    )
                    eligible_missing_links = int(cursor.fetchone()[0])
                    generated_links = 0
                data_findings.append(
                    assess_indicator_goal_routine_backfill(
                        marker=marker,
                        eligible_missing_links=eligible_missing_links,
                        generated_links=generated_links,
                    )
                )
            for marker in PROCESS_ARTIFACT_BACKFILL_MARKERS:
                cursor.execute(
                    "SELECT COUNT(*) FROM process_routines AS routine "
                    "LEFT JOIN process_activity_artifact_definitions AS definition "
                    "ON definition.company_id = routine.company_id "
                    "AND definition.process_id = routine.process_id "
                    "AND definition.legacy_process_routine_id = routine.id "
                    "AND definition.version = 1 "
                    "WHERE routine.bpmn_element_id IS NOT NULL "
                    "AND BTRIM(routine.bpmn_element_id) <> '' "
                    "AND COALESCE(routine.is_active, TRUE) = TRUE "
                    "AND definition.id IS NULL"
                )
                eligible_definitions_missing = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM process_activity_artifact_definitions "
                    "WHERE legacy_process_routine_id IS NOT NULL"
                )
                generated_definitions = int(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT COUNT(*) FROM process_activity_artifact_definitions AS definition "
                    "LEFT JOIN process_activity_artifact_links AS link "
                    "ON link.company_id = definition.company_id "
                    "AND link.process_id = definition.process_id "
                    "AND link.artifact_definition_id = definition.id "
                    "WHERE definition.legacy_process_routine_id IS NOT NULL "
                    "AND definition.version = 1 AND link.id IS NULL"
                )
                generated_definitions_without_link = int(cursor.fetchone()[0])
                data_findings.append(
                    assess_process_artifact_backfill(
                        marker=marker,
                        eligible_definitions_missing=eligible_definitions_missing,
                        generated_definitions=generated_definitions,
                        generated_definitions_without_link=generated_definitions_without_link,
                    )
                )
        migration_path = migrations_path or Path(__file__).resolve().parents[2] / "migrations"
        path = pending_revision_path(applied_revisions=ledger, migrations_path=migration_path)
        pending_revisions = set(path["pending_revisions"])
        schema_reconciliation_required = requires_reconciliation(
            finding for finding in findings if finding["revision"] in pending_revisions
        )
        seed_reconciliation_required = any(
            finding["revision"] in pending_revisions and finding["physical_state"] == "partial_or_divergent"
            for finding in seed_findings
        )
        data_reconciliation_required = any(
            finding["revision"] in pending_revisions and finding["physical_state"] == "partial_or_divergent"
            for finding in data_findings
        )
        return {
            "ledger_revisions": ledger,
            **path,
            "findings": findings,
            "seed_findings": seed_findings,
            "data_findings": data_findings,
            "schema_reconciliation_required": schema_reconciliation_required,
            "seed_reconciliation_required": seed_reconciliation_required,
            "data_reconciliation_required": data_reconciliation_required,
            "reconciliation_required": (
                schema_reconciliation_required
                or seed_reconciliation_required
                or data_reconciliation_required
            ),
            "mutation_performed": False,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument(
        "--migrations-path",
        default=str(Path(__file__).resolve().parents[2] / "migrations"),
        help="diretório Alembic do APP32; usado apenas para mapear revisions pendentes",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url ou DATABASE_URL é obrigatório")
    print(
        json.dumps(
            audit(args.database_url, migrations_path=args.migrations_path),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
