import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter
from services.knowledge.manual_catalog_compiler import ManualCatalogCompiler


def test_manual_catalog_compiler_covers_literal_and_dynamic_sidebar_entries():
    entries = ManualCatalogCompiler().discover_entries()
    targets = {entry.navigation_target for entry in entries}

    assert len(entries) >= 90
    assert "/financial/schedules" in targets
    assert "/financial/reconciliation" in targets
    assert "/process-instances" in targets
    assert "/projects" in targets
    assert "/plans" in targets
    assert "/meetings" in targets


def test_default_product_help_catalog_combines_curated_and_compiled_articles():
    documents = ProductHelpKnowledgeAdapter().discover_documents()
    targets = {document.navigation_target for document in documents}

    assert len(documents) >= 90
    assert len(targets) == len(documents)
    assert "/process-portal" in targets
    assert sum(document.navigation_target == "/process-portal" for document in documents) == 1
    assert all(document.source_type == "product_help" for document in documents)

    audit = ManualCatalogCompiler().audit_documents(documents)
    assert audit["ok"] is True
    assert audit["coverage_percent"] == 100.0
    assert audit["missing_targets"] == []
    assert audit["duplicate_targets"] == []
