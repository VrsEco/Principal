from __future__ import annotations

from datetime import datetime

from models import db
from models.knowledge import (
    KnowledgeChunk,
    KnowledgeIndexRun,
    KnowledgeSource,
    KnowledgeSourceGrant,
)
from services.knowledge.contracts import SourceDocument


class KnowledgeRepository:
    def start_run(
        self,
        *,
        knowledge_scope: str,
        source_type: str,
        company_id: int | None,
        trigger_kind: str,
        metadata: dict | None = None,
    ) -> KnowledgeIndexRun:
        run = KnowledgeIndexRun(
            company_id=company_id,
            knowledge_scope=knowledge_scope,
            source_type=source_type,
            trigger_kind=trigger_kind,
            status="running",
            metadata_json=dict(metadata or {}),
        )
        db.session.add(run)
        db.session.commit()
        return run

    def sync_documents(
        self,
        *,
        documents: tuple[SourceDocument, ...],
        knowledge_scope: str,
        source_type: str,
        company_id: int | None,
    ) -> dict[str, int]:
        now = datetime.utcnow()
        existing = (
            KnowledgeSource.query.filter(
                KnowledgeSource.knowledge_scope == knowledge_scope,
                KnowledgeSource.source_type == source_type,
                KnowledgeSource.company_id.is_(None)
                if company_id is None
                else KnowledgeSource.company_id == company_id,
                KnowledgeSource.deleted_at.is_(None),
            )
            .all()
        )
        by_ref = {source.source_ref: source for source in existing}
        discovered_refs = {document.source_ref for document in documents}
        counts = {
            "discovered": len(documents),
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "deactivated": 0,
        }

        for document in documents:
            source = by_ref.get(document.source_ref)
            if source is None:
                source = KnowledgeSource(
                    company_id=company_id,
                    knowledge_scope=knowledge_scope,
                    source_type=source_type,
                    source_ref=document.source_ref,
                    knowledge_kind=document.knowledge_kind,
                    title=document.title,
                    canonical_uri=document.canonical_uri,
                    status=document.status,
                    authority_level=document.authority_level,
                    version=document.version,
                    content_checksum=document.content_checksum,
                )
                db.session.add(source)
                self._apply_document(source, document, company_id=company_id, now=now)
                counts["created"] += 1
                continue

            if source.content_checksum == document.content_checksum:
                counts["unchanged"] += 1
                continue

            self._apply_document(source, document, company_id=company_id, now=now)
            counts["updated"] += 1

        for source in existing:
            if source.source_ref in discovered_refs:
                continue
            source.status = "inactive"
            source.deleted_at = now
            source.updated_at = now
            counts["deactivated"] += 1

        db.session.commit()
        return counts

    def complete_run(
        self,
        run_id: int,
        *,
        status: str,
        counts: dict[str, int] | None = None,
        error_message: str | None = None,
    ) -> KnowledgeIndexRun:
        run = db.session.get(KnowledgeIndexRun, run_id)
        if run is None:
            raise RuntimeError(f"KnowledgeIndexRun não encontrado: {run_id}")
        counts = counts or {}
        run.status = status
        run.discovered_count = int(counts.get("discovered", 0))
        run.created_count = int(counts.get("created", 0))
        run.updated_count = int(counts.get("updated", 0))
        run.unchanged_count = int(counts.get("unchanged", 0))
        run.deactivated_count = int(counts.get("deactivated", 0))
        run.failed_count = 1 if status == "failed" else 0
        run.error_message = error_message
        run.completed_at = datetime.utcnow()
        db.session.commit()
        return run

    @staticmethod
    def rollback() -> None:
        db.session.rollback()

    @staticmethod
    def _apply_document(
        source: KnowledgeSource,
        document: SourceDocument,
        *,
        company_id: int | None,
        now: datetime,
    ) -> None:
        source.company_id = company_id
        source.knowledge_scope = document.knowledge_scope
        source.source_type = document.source_type
        source.source_ref = document.source_ref
        source.knowledge_kind = document.knowledge_kind
        source.title = document.title
        source.canonical_uri = document.canonical_uri
        source.status = document.status
        source.authority_level = document.authority_level
        source.version = document.version
        source.product_version = document.product_version
        source.locale = document.locale
        source.route_key = document.route_key
        source.module_key = document.module_key
        source.audience_json = list(document.audience)
        source.required_capabilities_json = list(document.required_capabilities)
        source.help_kind = document.help_kind
        source.navigation_target = document.navigation_target
        source.tour_definition_id = document.tour_definition_id
        source.metadata_json = dict(document.metadata)
        source.content_checksum = document.content_checksum
        source.valid_from = document.valid_from
        source.valid_to = document.valid_to
        source.source_updated_at = document.source_updated_at
        source.indexed_at = now
        source.deleted_at = None
        source.updated_at = now
        source.chunks.clear()
        source.grants.clear()
        for chunk in document.chunks:
            source.chunks.append(
                KnowledgeChunk(
                    company_id=company_id,
                    knowledge_scope=document.knowledge_scope,
                    section_key=chunk.section_key,
                    content=chunk.content,
                    metadata_json=dict(chunk.metadata),
                    chunk_order=chunk.chunk_order,
                    token_count=chunk.token_count,
                    content_checksum=chunk.content_checksum,
                    source_span=chunk.source_span,
                    adapter_version=chunk.adapter_version,
                    parser_version=chunk.parser_version,
                    chunking_policy=chunk.chunking_policy,
                )
            )
        for grant in document.grants:
            source.grants.append(
                KnowledgeSourceGrant(
                    company_id=company_id,
                    grant_scope=grant.grant_scope,
                    user_id=grant.user_id,
                    employee_id=grant.employee_id,
                    metadata_json=dict(grant.metadata),
                )
            )
