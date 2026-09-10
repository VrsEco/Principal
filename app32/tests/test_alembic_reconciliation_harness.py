from scripts.qa.audit_alembic_reconciliation import (
    MARKERS,
    PortfolioBackfillMarker,
    ProcessArtifactBackfillMarker,
    CapabilityRolloutMarker,
    CapabilityDimensionSeedMarker,
    IndicatorGoalNormalizationMarker,
    IndicatorGoalRoutineBackfillMarker,
    ProtocolSeedMarker,
    SchemaMarker,
    TableFingerprint,
    assess_marker,
    assess_portfolio_backfill,
    assess_process_artifact_backfill,
    assess_capability_rollout,
    assess_capability_dimension_seed,
    assess_indicator_goal_normalization,
    assess_indicator_goal_routine_backfill,
    assess_protocol_seed,
    pending_revision_path,
    revision_evidence_flags,
    requires_reconciliation,
)


def test_known_markers_cover_the_first_hidden_and_explicit_collisions() -> None:
    assert sorted(marker.revision for marker in MARKERS) == [
        "20260630_1845",
        "20260701_1015",
        "20260701_1030",
        "20260701_1045",
        "20260702_1800",
        "20260718_1200",
        "20260719_0900",
        "20260719_1030",
        "20260720_0900",
        "20260730_1600",
        "20260730_1700",
        "20260730_1800",
        "20260801_0900",
        "20260801_1500",
        "20260801_1530",
        "20260802_2100",
        "20260813_1200",
        "20260821_1200",
        "20260826_1800",
        "20260826_2000",
        "20260901_1900",
        "20260903_1200",
        "20260903_1300",
        "20260904_1400",
        "20260904_1500",
        "20260904_1600",
        "20260904_1800",
        "20260907_1900",
        "20260909_1000",
    ]


def test_marker_never_authorizes_stamp_from_table_presence_alone() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a"), TableFingerprint("b")))

    assessed = assess_marker(existing_tables=("a", "b", "other"), marker=marker)

    assert assessed["physical_state"] == "complete_candidate"
    assert assessed["tables_missing"] == []
    assert assessed["stamp_allowed"] is False


def test_protocol_seed_marker_distinguishes_absent_from_partial() -> None:
    marker = ProtocolSeedMarker("x", "v1", "global", "tenant")

    absent = assess_protocol_seed(marker=marker, global_rows=0, tenant_rows=0, tenant_expected=True)
    partial = assess_protocol_seed(marker=marker, global_rows=1, tenant_rows=0, tenant_expected=True)

    assert absent["physical_state"] == "absent_or_pending"
    assert partial["physical_state"] == "partial_or_divergent"
    assert absent["stamp_allowed"] is False


def test_protocol_seed_markers_allow_multiple_protocols_in_one_revision() -> None:
    from scripts.qa.audit_alembic_reconciliation import PROTOCOL_SEED_MARKERS

    versioned_markers = [marker.protocol_version for marker in PROTOCOL_SEED_MARKERS if marker.revision == "20260721_2130"]

    assert versioned_markers == ["vision-official-v1.0", "values-official-v1.0"]


def test_protocol_seed_markers_cover_following_single_protocol_revisions() -> None:
    from scripts.qa.audit_alembic_reconciliation import PROTOCOL_SEED_MARKERS

    revisions = {marker.revision: marker.protocol_version for marker in PROTOCOL_SEED_MARKERS}

    assert revisions["20260727_1800"] == "positioning-official-v1.0"
    assert revisions["20260727_2100"] == "org-chart-official-v1.0"


def test_portfolio_backfill_distinguishes_pending_from_partial() -> None:
    marker = PortfolioBackfillMarker("x")

    pending = assess_portfolio_backfill(
        marker=marker,
        eligible_projects_without_portfolio=1,
        generated_portfolios=0,
        linked_projects_to_generated_portfolio=0,
    )
    partial = assess_portfolio_backfill(
        marker=marker,
        eligible_projects_without_portfolio=1,
        generated_portfolios=1,
        linked_projects_to_generated_portfolio=1,
    )

    assert pending["physical_state"] == "absent_or_pending"
    assert partial["physical_state"] == "partial_or_divergent"


def test_process_artifact_backfill_detects_partial_materialization() -> None:
    assessed = assess_process_artifact_backfill(
        marker=ProcessArtifactBackfillMarker("x"),
        eligible_definitions_missing=17,
        generated_definitions=4,
        generated_definitions_without_link=0,
    )

    assert assessed["physical_state"] == "partial_or_divergent"


def test_capability_rollout_distinguishes_absent_from_partial() -> None:
    marker = CapabilityRolloutMarker("x", "capability.key", 9)

    absent = assess_capability_rollout(marker=marker, capability_rows=0, enabled_settings=0)
    partial = assess_capability_rollout(marker=marker, capability_rows=1, enabled_settings=0)

    assert absent["physical_state"] == "absent_or_pending"
    assert partial["physical_state"] == "partial_or_divergent"


def test_capability_dimension_seed_distinguishes_pending_from_partial() -> None:
    marker = CapabilityDimensionSeedMarker("x", ("a", "b"))

    pending = assess_capability_dimension_seed(marker=marker, company_count=3, missing_dimensions=6)
    partial = assess_capability_dimension_seed(marker=marker, company_count=3, missing_dimensions=2)

    assert pending["physical_state"] == "absent_or_pending"
    assert partial["physical_state"] == "partial_or_divergent"


def test_indicator_goal_normalization_detects_legacy_rows() -> None:
    marker = IndicatorGoalNormalizationMarker("x")

    complete = assess_indicator_goal_normalization(
        marker=marker, legacy_active_recurring_start_date=0, missing_period_end_candidate=0
    )
    partial = assess_indicator_goal_normalization(
        marker=marker, legacy_active_recurring_start_date=1, missing_period_end_candidate=0
    )

    assert complete["physical_state"] == "complete_candidate"
    assert partial["physical_state"] == "partial_or_divergent"


def test_indicator_goal_routine_backfill_detects_missing_links() -> None:
    marker = IndicatorGoalRoutineBackfillMarker("x")

    missing = assess_indicator_goal_routine_backfill(marker=marker, eligible_missing_links=2, generated_links=0)
    complete = assess_indicator_goal_routine_backfill(marker=marker, eligible_missing_links=0, generated_links=2)

    assert missing["physical_state"] == "partial_or_divergent"
    assert complete["physical_state"] == "complete_candidate"


def test_marker_reports_partial_schema_without_mutation() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a"), TableFingerprint("b")))

    assessed = assess_marker(existing_tables=("a",), marker=marker)

    assert assessed["physical_state"] == "partial_or_absent"
    assert assessed["tables_missing"] == ["b"]
    assert assessed["stamp_allowed"] is False


def test_marker_reports_missing_index_even_when_table_exists() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a", indexes=("ix_a",)),))

    assessed = assess_marker(existing_tables=("a",), actual_fingerprints={"a": {"indexes": set()}}, marker=marker)

    assert assessed["physical_state"] == "partial_or_absent"
    assert assessed["fingerprint_mismatches"]["a"]["indexes_missing"] == ["ix_a"]


def test_marker_accepts_index_alias_for_equivalent_legacy_contract() -> None:
    marker = SchemaMarker(
        revision="x",
        tables=(TableFingerprint("a", index_alternatives=(("ix_historical", "ix_equivalent"),)),),
    )

    assessed = assess_marker(
        existing_tables=("a",),
        actual_fingerprints={"a": {"indexes": {"ix_equivalent"}}},
        marker=marker,
    )

    assert assessed["physical_state"] == "complete_candidate"


def test_marker_reports_missing_column_even_when_table_exists() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a", columns=("company_id",)),))

    assessed = assess_marker(existing_tables=("a",), actual_fingerprints={"a": {"columns": set()}}, marker=marker)

    assert assessed["physical_state"] == "partial_or_absent"
    assert assessed["fingerprint_mismatches"]["a"]["columns_missing"] == ["company_id"]


def test_marker_reports_constraint_definition_fragment_mismatch() -> None:
    marker = SchemaMarker(
        revision="x",
        tables=(TableFingerprint("a", constraint_fragments=(("ck_a", "expected_value"),)),),
    )

    assessed = assess_marker(
        existing_tables=("a",),
        actual_fingerprints={"a": {"constraint_definitions": {"ck_a": "CHECK (other_value)"}}},
        marker=marker,
    )

    assert assessed["physical_state"] == "partial_or_absent"
    assert assessed["fingerprint_mismatches"]["a"]["constraint_fragments_missing"] == ["ck_a"]


def test_marker_reports_column_default_fragment_mismatch() -> None:
    marker = SchemaMarker(
        revision="x",
        tables=(TableFingerprint("a", column_default_fragments=(("status", "expected_value"),)),),
    )

    assessed = assess_marker(
        existing_tables=("a",),
        actual_fingerprints={"a": {"column_defaults": {"status": "'other_value'::text"}}},
        marker=marker,
    )

    assert assessed["physical_state"] == "partial_or_absent"
    assert assessed["fingerprint_mismatches"]["a"]["column_default_fragments_missing"] == ["status"]


def test_physical_partial_marker_requires_reconciliation() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a", indexes=("ix_a",)),))
    assessed = assess_marker(existing_tables=("a",), actual_fingerprints={"a": {"indexes": set()}}, marker=marker)

    assert requires_reconciliation((assessed,)) is True


def test_absent_marker_does_not_require_reconciliation() -> None:
    marker = SchemaMarker(revision="x", tables=(TableFingerprint("a"),))
    assessed = assess_marker(existing_tables=(), marker=marker)

    assert requires_reconciliation((assessed,)) is False


def test_pending_revision_path_is_in_application_order(tmp_path) -> None:
    migrations = tmp_path / "migrations"
    versions = migrations / "versions"
    versions.mkdir(parents=True)
    (migrations / "env.py").write_text("", encoding="utf-8")
    (versions / "a.py").write_text("revision = 'a'\ndown_revision = None\n", encoding="utf-8")
    (versions / "b.py").write_text(
        "revision = 'b'\ndown_revision = 'a'\ndef upgrade():\n    op.execute('CREATE TABLE IF NOT EXISTS b (id integer)')\n",
        encoding="utf-8",
    )
    (versions / "c.py").write_text(
        "revision = 'c'\ndown_revision = 'b'\ndef upgrade():\n    op.create_table('c')\n    bind.execute(sa.text('INSERT INTO c VALUES (1)'))\n",
        encoding="utf-8",
    )

    path = pending_revision_path(applied_revisions=("a",), migrations_path=migrations)

    assert path == {
        "alembic_heads": ["c"],
        "pending_revisions": ["b", "c"],
        "revisions_requiring_evidence": [
            {"revision": "b", "flags": ["idempotent_schema", "raw_sql"]},
            {"revision": "c", "flags": ["non_idempotent_schema", "data_mutation"]},
        ],
    }


def test_revision_evidence_flags_ignores_downgrade_only_operations(tmp_path) -> None:
    revision = tmp_path / "revision.py"
    revision.write_text(
        "def upgrade():\n    pass\n\ndef downgrade():\n    op.execute('DELETE FROM t')\n",
        encoding="utf-8",
    )

    assert revision_evidence_flags(revision) == []


def test_revision_evidence_flags_ignores_annotated_downgrade_operations(tmp_path) -> None:
    revision = tmp_path / "revision.py"
    revision.write_text(
        "def upgrade() -> None:\n    pass\n\ndef downgrade() -> None:\n    op.execute('UPDATE t SET x = 1')\n",
        encoding="utf-8",
    )

    assert revision_evidence_flags(revision) == []


def test_revision_evidence_flags_detects_alembic_schema_operations(tmp_path) -> None:
    revision = tmp_path / "revision.py"
    revision.write_text(
        "def upgrade() -> None:\n    op.add_column('t', sa.Column('x'))\n    op.create_index('ix_t_x', 't', ['x'])\n",
        encoding="utf-8",
    )

    assert revision_evidence_flags(revision) == ["non_idempotent_schema"]
