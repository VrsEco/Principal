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


SHARED_GUIDE = """# Guia da Feature: Relatórios

## Metadados
- `feature_id`: `financeiro_relatorios`
- `company_id_obrigatorio`: `sim`

## Objetivo
Consultar relatórios financeiros: razão e demonstrativo de resultados.

## Quando usar
- explicar como ler o razão por conta contábil
- orientar qual relatório usar

## Entradas esperadas
- `company_id`: escopo do tenant

## Como orientar o usuário
1. Acessar **Gestão Financeira > Relatórios** no menu.
2. Escolher o relatório:
   - **Razão**: histórico de lançamentos por conta contábil.
   - **Demonstrativo de Resultados**: DRE do período.
3. Aplicar os filtros — a surface MCP decide o que a IA pode ver.

## Uso por IA / MCP
Chamar a tool interna.
"""


def _shared_guide_compiler(tmp_path):
    service = _feature_catalog_service_with_guide(
        tmp_path,
        rotas_app=["/financial/reports/razao", "/financial/reports/dre"],
        guide_content=SHARED_GUIDE,
    )
    return ManualCatalogCompiler(tmp_path, feature_catalog_service=service)


def _entry(title, target):
    return ManualNavigationEntry(
        title=title, navigation_target=target, route_key=target, module_key="finance", module_label="Gestão Financeira"
    )


def test_shared_guide_gives_each_screen_its_own_item_and_only_user_sections(tmp_path):
    compiler = _shared_guide_compiler(tmp_path)
    razao = compiler._curated_content_for(
        _entry("Razão", "/financial/reports/razao"), sibling_titles=("Demonstrativo de Resultados",)
    )
    dre = compiler._curated_content_for(
        _entry("Demonstrativo de Resultados", "/financial/reports/dre"), sibling_titles=("Razão",)
    )

    assert razao != dre
    assert razao.startswith("Como acessar Razão\n\nOnde fica: Gestão Financeira > Razão.")
    assert "histórico de lançamentos por conta contábil" in razao and "DRE do período" not in razao
    assert "DRE do período" in dre and "histórico de lançamentos" not in dre
    for content in (razao, dre):
        assert "Consultar relatórios financeiros" in content  # objetivo vale para todas as telas
        assert "- Qual relatório usar" in content  # "orientar qual..." (instrução p/ IA) vira texto p/ pessoa
        assert "Aplicar os filtros." in content  # trecho técnico depois do travessão sai
        for leaked in ("feature_id", "company_id", "surface", "tool", "Uso por IA"):
            assert leaked not in content
    assert "- Como ler o razão por conta contábil" in razao
    assert "ler o razão" not in dre  # item de "Quando usar" que fala só da tela irmã


def test_compile_documents_never_gives_two_screens_the_same_text():
    documents = ManualCatalogCompiler().compile_documents()
    by_content = {}
    for document in documents:
        by_content.setdefault(document.chunks[0].content, set()).add(document.title)

    assert all(len(titles) == 1 for titles in by_content.values())
    dre = next(d for d in documents if d.navigation_target == "/financial/reports/demonstrativo-resultados")
    razao = next(d for d in documents if d.navigation_target == "/financial/reports/razao")
    assert "DRE" in dre.chunks[0].content and "DRE" not in razao.chunks[0].content


def test_compiler_reads_every_sidebar_partial():
    targets = {entry.navigation_target for entry in ManualCatalogCompiler().discover_entries()}
    assert {"/indicators", "/internal-audit", "/plans", "/financial/reconciliation"} <= targets
