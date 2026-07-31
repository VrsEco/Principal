import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter


def _payload(**overrides):
    payload = {
        "source_ref": "processes.publish",
        "title": "Publicar processo",
        "version": "v1",
        "product_version": "3.2",
        "locale": "pt-BR",
        "status": "published",
        "authority_level": "official",
        "route_key": "processes.detail",
        "module_key": "processes",
        "help_kind": "guided_tour",
        "canonical_uri": "app-versus://help/processes/publish",
        "navigation_target": "/process-portal",
        "audience": ["administrator"],
        "required_capabilities": ["processes.view"],
        "content": "# Antes\n\nValide o POP.\n\n# Passos\n\n1. Abra Fluxo / POP.",
    }
    payload.update(overrides)
    return payload


def _write(path: Path, name: str, payload: dict):
    (path / name).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_product_help_adapter_discovers_versioned_chunks_and_checksum(tmp_path):
    _write(tmp_path, "publish.json", _payload())
    adapter = ProductHelpKnowledgeAdapter(tmp_path)

    first = adapter.discover_documents()
    second = adapter.discover_documents()

    assert len(first) == 1
    document = first[0]
    assert document.knowledge_scope == "product"
    assert document.source_type == "product_help"
    assert document.product_version == "3.2"
    assert document.required_capabilities == ("processes.view",)
    assert document.navigation_target == "/process-portal"
    assert [chunk.section_key for chunk in document.chunks] == ["antes", "passos"]
    assert document.content_checksum == second[0].content_checksum


def test_product_help_adapter_checksum_changes_with_content(tmp_path):
    path = tmp_path / "publish.json"
    _write(tmp_path, path.name, _payload())
    adapter = ProductHelpKnowledgeAdapter(tmp_path)
    first_checksum = adapter.discover_documents()[0].content_checksum

    _write(tmp_path, path.name, _payload(content="# Passos\n\nConteúdo alterado."))

    assert adapter.discover_documents()[0].content_checksum != first_checksum


def test_product_help_adapter_exposes_safe_navigation_actions(tmp_path):
    _write(
        tmp_path,
        "publish.json",
        _payload(
            navigation_actions=[
                {"label": "Abrir títulos", "target": "/financial/schedules"},
                {"label": "Abrir relatório", "target": "/financial/reports/agendamento"},
            ]
        ),
    )

    document = ProductHelpKnowledgeAdapter(tmp_path).discover_documents()[0]

    assert document.metadata["navigation_actions"] == [
        {"label": "Abrir títulos", "target": "/financial/schedules"},
        {"label": "Abrir relatório", "target": "/financial/reports/agendamento"},
    ]


def test_product_help_adapter_rejects_company_scope_and_invalid_catalog(tmp_path):
    adapter = ProductHelpKnowledgeAdapter(tmp_path)
    with pytest.raises(ValueError, match="não aceita company_id"):
        adapter.discover_documents(company_id=9)

    _write(tmp_path, "invalid.json", _payload(status="draft"))
    with pytest.raises(ValueError, match="Somente product_help publicado"):
        adapter.discover_documents()


def test_product_help_adapter_rejects_duplicate_source_ref(tmp_path):
    _write(tmp_path, "a.json", _payload())
    _write(tmp_path, "b.json", _payload(title="Outro título"))

    with pytest.raises(ValueError, match="source_ref duplicado"):
        ProductHelpKnowledgeAdapter(tmp_path).discover_documents()


@pytest.mark.parametrize(
    "navigation_target",
    ["processes.detail", "//external.example/process", r"/process-portal\\escape"],
)
def test_product_help_adapter_rejects_unsafe_or_unresolvable_navigation_target(
    tmp_path,
    navigation_target,
):
    _write(tmp_path, "invalid-target.json", _payload(navigation_target=navigation_target))

    with pytest.raises(ValueError, match="rota interna absoluta"):
        ProductHelpKnowledgeAdapter(tmp_path).discover_documents()


def test_product_help_adapter_rejects_unsafe_navigation_action(tmp_path):
    _write(
        tmp_path,
        "invalid-action.json",
        _payload(
            navigation_actions=[
                {"label": "Site externo", "target": "//external.example/process"},
            ]
        ),
    )

    with pytest.raises(ValueError, match="rota interna absoluta"):
        ProductHelpKnowledgeAdapter(tmp_path).discover_documents()


def test_product_help_adapter_requires_navigation_action_target(tmp_path):
    _write(
        tmp_path,
        "missing-action-target.json",
        _payload(navigation_actions=[{"label": "Abrir relatório"}]),
    )

    with pytest.raises(ValueError, match="target é obrigatório"):
        ProductHelpKnowledgeAdapter(tmp_path).discover_documents()
