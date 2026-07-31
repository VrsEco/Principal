from __future__ import annotations

import logging
from typing import Any

from services.knowledge.registry import KnowledgeSourceRegistry, knowledge_source_registry
from services.knowledge.repository import KnowledgeRepository
from services.knowledge.manual_catalog_compiler import ManualCatalogCompiler


logger = logging.getLogger(__name__)


class KnowledgeAutoUpdateService:
    """Sincroniza fontes por adapter com checksum, deativação e ledger auditável."""

    TENANT_SOURCE_TYPES = ("process_publication", "meeting")
    PRODUCT_SOURCE_TYPES = ("product_help", "system_documentation")

    def __init__(
        self,
        *,
        repository: KnowledgeRepository | None = None,
        registry: KnowledgeSourceRegistry | None = None,
    ):
        self.repository = repository or KnowledgeRepository()
        self.registry = registry or knowledge_source_registry

    def sync_source(
        self,
        source_type: str,
        *,
        company_id: int | None = None,
        trigger_kind: str = "scheduled",
    ) -> dict[str, Any]:
        adapter = self.registry.get(source_type)
        adapter.validate_scope(company_id=company_id)
        run = self.repository.start_run(
            knowledge_scope=adapter.knowledge_scope,
            source_type=adapter.source_type,
            company_id=company_id,
            trigger_kind=trigger_kind,
            metadata={"adapter_version": adapter.adapter_version},
        )
        try:
            documents = adapter.discover_documents(company_id=company_id)
            counts = self.repository.sync_documents(
                documents=documents,
                knowledge_scope=adapter.knowledge_scope,
                source_type=adapter.source_type,
                company_id=company_id,
            )
            completed = self.repository.complete_run(
                run.id,
                status="completed",
                counts=counts,
            )
            payload = {"ok": True, "run": completed.to_dict(), "counts": counts}
            logger.info(
                "Knowledge sync concluído source_type=%s scope=%s counts=%s",
                source_type,
                adapter.knowledge_scope,
                counts,
            )
            return payload
        except Exception as exc:
            self.repository.rollback()
            failed = self.repository.complete_run(
                run.id,
                status="failed",
                error_message=str(exc)[:4000],
            )
            logger.exception(
                "Knowledge sync falhou source_type=%s scope=%s",
                source_type,
                adapter.knowledge_scope,
            )
            return {"ok": False, "run": failed.to_dict(), "error": str(exc)}

    def sync_product_help(self, *, trigger_kind: str = "scheduled") -> dict[str, Any]:
        return self.sync_source(
            "product_help",
            company_id=None,
            trigger_kind=trigger_kind,
        )

    def sync_product_sources(self, *, trigger_kind: str = "scheduled") -> dict[str, Any]:
        results = {
            source_type: self.sync_source(
                source_type,
                company_id=None,
                trigger_kind=trigger_kind,
            )
            for source_type in self.PRODUCT_SOURCE_TYPES
        }
        audit = self.audit_product_manual()
        return {
            "ok": all(item.get("ok") for item in results.values()) and audit["ok"],
            "sources": results,
            "manual_catalog_audit": audit,
        }

    def audit_product_manual(self) -> dict[str, Any]:
        adapter = self.registry.get("product_help")
        documents = adapter.discover_documents(company_id=None)
        return ManualCatalogCompiler().audit_documents(documents)

    def sync_company_sources(
        self,
        company_id: int,
        *,
        trigger_kind: str = "scheduled",
    ) -> dict[str, Any]:
        if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
            raise ValueError("company_id deve ser inteiro positivo.")
        results = {
            source_type: self.sync_source(
                source_type,
                company_id=company_id,
                trigger_kind=trigger_kind,
            )
            for source_type in self.TENANT_SOURCE_TYPES
        }
        return {
            "ok": all(item.get("ok") for item in results.values()),
            "company_id": company_id,
            "sources": results,
        }

    def sync_all_tenant_sources(
        self,
        *,
        trigger_kind: str = "scheduled",
    ) -> dict[str, Any]:
        from models import Company

        company_ids = [
            int(row[0])
            for row in (
                Company.query.with_entities(Company.id)
                .filter(Company.is_active.is_(True))
                .order_by(Company.id.asc())
                .all()
            )
        ]
        results = [
            self.sync_company_sources(
                company_id,
                trigger_kind=trigger_kind,
            )
            for company_id in company_ids
        ]
        return {
            "ok": all(item.get("ok") for item in results),
            "companies_discovered": len(company_ids),
            "companies": results,
        }
