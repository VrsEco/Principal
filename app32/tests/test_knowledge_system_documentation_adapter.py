import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.adapters.system_documentation import (
    SystemDocumentationKnowledgeAdapter,
)


def test_system_documentation_adapter_indexes_papers_and_specs_with_authority(tmp_path):
    papers = tmp_path / "papers"
    specs = tmp_path / "spec"
    papers.mkdir()
    specs.mkdir()
    (papers / "paper_manual_v2.md").write_text(
        "# Paper — Manual v2\n\nStatus: em evolução\n\n## Uso\n\nOrientação conceitual.",
        encoding="utf-8",
    )
    (specs / "financeiro_v3.md").write_text(
        "# SPEC — Financeiro v3\n\n**Status:** canônico\n\n## Títulos\n\nVer títulos em aberto.",
        encoding="utf-8",
    )

    documents = SystemDocumentationKnowledgeAdapter(tmp_path).discover_documents()

    assert len(documents) == 2
    by_kind = {document.knowledge_kind: document for document in documents}
    assert by_kind["paper"].authority_level == "contextual"
    assert by_kind["spec"].authority_level == "official"
    assert by_kind["spec"].version == "v3"
    assert by_kind["spec"].canonical_uri.startswith("app-versus://docs/spec/")
    assert any("Ver títulos em aberto" in chunk.content for chunk in by_kind["spec"].chunks)


def test_system_documentation_adapter_is_global_and_checksum_is_stable(tmp_path):
    (tmp_path / "papers").mkdir()
    path = tmp_path / "papers" / "paper_a_v1.md"
    path.write_text("# Paper A v1\n\n## Tema\n\nConteúdo.", encoding="utf-8")
    adapter = SystemDocumentationKnowledgeAdapter(tmp_path)

    first = adapter.discover_documents()
    second = adapter.discover_documents()

    assert first[0].content_checksum == second[0].content_checksum
    with pytest.raises(ValueError, match="não aceita company_id"):
        adapter.discover_documents(company_id=7)


def test_system_documentation_adapter_splits_large_sections(tmp_path):
    (tmp_path / "spec").mkdir()
    paragraphs = "\n\n".join(["Regra operacional " + ("segura " * 90)] * 12)
    (tmp_path / "spec" / "grande_v1.md").write_text(
        f"# SPEC Grande v1\n\n## Regras\n\n{paragraphs}",
        encoding="utf-8",
    )

    document = SystemDocumentationKnowledgeAdapter(tmp_path).discover_documents()[0]

    assert len(document.chunks) > 1
    assert max(len(chunk.content) for chunk in document.chunks) < 4_000


def test_system_documentation_adapter_never_collides_natural_and_generated_suffixes(tmp_path):
    (tmp_path / "papers").mkdir()
    (tmp_path / "papers" / "colisoes_v1.md").write_text(
        "# Paper\n\n## Exemplo\n\nA.\n\n## Exemplo 2\n\nB.\n\n## Exemplo\n\nC.",
        encoding="utf-8",
    )

    document = SystemDocumentationKnowledgeAdapter(tmp_path).discover_documents()[0]
    keys = [chunk.section_key for chunk in document.chunks]

    assert len(keys) == len(set(keys))
    assert keys == ["exemplo", "exemplo-2", "exemplo-3"]
