from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_migration_has_scope_constraints_fts_and_run_ledger():
    migration = (
        ROOT
        / "migrations"
        / "versions"
        / "20260730_1700_create_knowledge_foundation.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260730_1700"' in migration
    assert 'down_revision = "20260730_1600"' in migration
    assert '"knowledge_sources"' in migration
    assert '"knowledge_chunks"' in migration
    assert '"knowledge_index_runs"' in migration
    assert "ck_knowledge_sources_scope_company" in migration
    assert "uq_knowledge_sources_company_ref" in migration
    assert "to_tsvector('portuguese', content)" in migration


def test_knowledge_models_export_foundation_entities():
    models_init = (ROOT / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "KnowledgeSource" in models_init
    assert "KnowledgeChunk" in models_init
    assert "KnowledgeIndexRun" in models_init
    assert "KnowledgeSourceGrant" in models_init
    assert "KnowledgeInteraction" in models_init
    assert "KnowledgeFeedback" in models_init
    assert "KnowledgeTrainingProposal" in models_init


def test_knowledge_grants_migration_extends_foundation_chain():
    migration = (
        ROOT
        / "migrations"
        / "versions"
        / "20260730_1800_create_knowledge_source_grants.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260730_1800"' in migration
    assert 'down_revision = "20260730_1700"' in migration
    assert '"knowledge_source_grants"' in migration
    assert "ck_knowledge_source_grants_scope_target" in migration
    assert "uq_knowledge_source_grants_company" in migration
    assert "uq_knowledge_source_grants_user" in migration
    assert "uq_knowledge_source_grants_employee" in migration
    assert "postgresql_where" in migration


def test_knowledge_feedback_migration_adds_training_loop_tables():
    migration = (
        ROOT
        / "migrations"
        / "versions"
        / "20260801_0900_create_knowledge_feedback_training.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260801_0900"' in migration
    assert 'down_revision = "20260730_1800"' in migration
    assert '"knowledge_interactions"' in migration
    assert '"knowledge_feedback"' in migration
    assert '"knowledge_training_proposals"' in migration
    assert "ck_knowledge_feedback_rating" in migration
    assert "ck_knowledge_feedback_reason" in migration
    assert "pending_review" in migration
