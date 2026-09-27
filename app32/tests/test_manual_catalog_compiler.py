import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yaml

from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter
from services.knowledge.manual_catalog_compiler import ManualCatalogCompiler, ManualNavigationEntry
from services.mcp_feature_catalog_service import MCPFeatureCatalogService


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


def _reconciliation_entry(navigation_target: str = "/financial/reconciliation") -> ManualNavigationEntry:
    return ManualNavigationEntry(
        title="Conciliação Bancária",
        navigation_target=navigation_target,
        route_key="financial.reconciliation",
        module_key="finance",
        module_label="Gestão Financeira",
    )


def _feature_catalog_service_with_guide(tmp_path, *, rotas_app, guide_content):
    guides_root = tmp_path / "features"
    guides_root.mkdir()
    guide_path = guides_root / "financeiro_conciliacao_bancaria.md"
    guide_path.write_text(guide_content, encoding="utf-8")

    catalog_path = tmp_path / "catalogo_features.yaml"
    catalog_path.write_text(
        yaml.safe_dump(
            {
                "features": [
                    {
                        "id": "financeiro_conciliacao_bancaria",
                        "surfaces": ["user"],
                        "rotas_app": rotas_app,
                        "guia_ref": "features/financeiro_conciliacao_bancaria.md",
                    }
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return MCPFeatureCatalogService(catalog_path=catalog_path, guides_root=guides_root)


def test_curated_content_for_uses_cut_guide_when_route_matches_feature(tmp_path):
    guide_content = (
        "# Guia\n\n"
        "## Como orientar o usuário\n"
        "Passo curado real, com detalhes de UI.\n\n"
        "## Uso por IA / MCP\n"
        "Conteúdo técnico que não deve vazar para o Sapiens.\n"
    )
    service = _feature_catalog_service_with_guide(
        tmp_path,
        rotas_app=["/financial/reconciliation"],
        guide_content=guide_content,
    )
    compiler = ManualCatalogCompiler(tmp_path, feature_catalog_service=service)

    content = compiler._curated_content_for(_reconciliation_entry())

    assert "Passo curado real, com detalhes de UI." in content
    assert "Uso por IA / MCP" not in content
    assert "Conteúdo técnico que não deve vazar" not in content


def test_curated_content_for_falls_back_to_generic_when_no_feature_matches_route(tmp_path):
    service = _feature_catalog_service_with_guide(
        tmp_path,
        rotas_app=["/some-other-route"],
        guide_content="## Uso por IA / MCP\nconteudo tecnico irrelevante",
    )
    compiler = ManualCatalogCompiler(tmp_path, feature_catalog_service=service)
    entry = _reconciliation_entry()

    content = compiler._curated_content_for(entry)

    assert content == compiler._content(entry)
    assert "Como acessar Conciliação Bancária" in content


def test_curated_content_for_returns_full_guide_when_cutoff_heading_missing(tmp_path):
    guide_content = "# Guia\n\nConteúdo curado sem o heading de corte esperado.\n"
    service = _feature_catalog_service_with_guide(
        tmp_path,
        rotas_app=["/financial/reconciliation"],
        guide_content=guide_content,
    )
    compiler = ManualCatalogCompiler(tmp_path, feature_catalog_service=service)

    content = compiler._curated_content_for(_reconciliation_entry())

    assert content == guide_content
