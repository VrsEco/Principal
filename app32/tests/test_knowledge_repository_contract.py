import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.knowledge import KnowledgeSource
from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter
from services.knowledge.contracts import (
    SourceChunkDocument,
    SourceDocument,
    SourceGrantDocument,
)
from services.knowledge.repository import KnowledgeRepository


def test_repository_projects_product_help_without_company_id(tmp_path):
    payload = {
        "source_ref": "processes.publish",
        "title": "Publicar processo",
        "version": "v1",
        "product_version": "3.2",
        "status": "published",
        "route_key": "processes.detail",
        "module_key": "processes",
        "help_kind": "how_to",
        "canonical_uri": "app-versus://help/processes/publish",
        "content": "# Passos\n\n1. Abra Fluxo / POP.",
    }
    (tmp_path / "publish.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    document = ProductHelpKnowledgeAdapter(tmp_path).discover_documents()[0]
    source = KnowledgeSource(
        knowledge_scope="product",
        source_type="product_help",
        source_ref=document.source_ref,
        knowledge_kind="product_help",
        title=document.title,
        canonical_uri=document.canonical_uri,
        content_checksum="old",
    )

    KnowledgeRepository._apply_document(
        source,
        document,
        company_id=None,
        now=datetime(2026, 7, 30, 12, 0, 0),
    )

    assert source.company_id is None
    assert source.knowledge_scope == "product"
    assert source.product_version == "3.2"
    assert source.content_checksum == document.content_checksum
    assert len(source.chunks) == 1
    assert source.chunks[0].company_id is None
    assert source.chunks[0].knowledge_scope == "product"


def test_repository_projects_tenant_grants_with_company_scope():
    content = "A manutenção preventiva é responsabilidade da equipe predial."
    document = SourceDocument(
        knowledge_scope="company",
        source_type="meeting",
        source_ref="meeting:91",
        knowledge_kind="decision_record",
        title="Reunião de infraestrutura",
        canonical_uri="app-versus://meetings/company/7/meeting/91/report",
        status="published",
        authority_level="internal",
        version="v1",
        content_checksum="a" * 64,
        chunks=(
            SourceChunkDocument(
                section_key="ata-1",
                content=content,
                chunk_order=0,
                content_checksum="b" * 64,
                token_count=len(content.split()),
            ),
        ),
        grants=(
            SourceGrantDocument(grant_scope="employee", employee_id=101),
        ),
    )
    source = KnowledgeSource(
        knowledge_scope="company",
        company_id=7,
        source_type="meeting",
        source_ref=document.source_ref,
        knowledge_kind=document.knowledge_kind,
        title=document.title,
        canonical_uri=document.canonical_uri,
        content_checksum="old",
    )

    KnowledgeRepository._apply_document(
        source,
        document,
        company_id=7,
        now=datetime(2026, 7, 30, 12, 0, 0),
    )

    assert len(source.grants) == 1
    assert source.grants[0].company_id == 7
    assert source.grants[0].grant_scope == "employee"
    assert source.grants[0].employee_id == 101
