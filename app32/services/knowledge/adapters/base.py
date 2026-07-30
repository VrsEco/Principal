from __future__ import annotations

from abc import ABC, abstractmethod

from services.knowledge.contracts import SourceDocument


class KnowledgeSourceAdapter(ABC):
    source_type: str
    knowledge_scope: str
    adapter_version: str = "v1"

    @abstractmethod
    def discover_documents(self, *, company_id: int | None = None) -> tuple[SourceDocument, ...]:
        """Descobre e normaliza todas as fontes elegíveis do escopo."""

    def validate_scope(self, *, company_id: int | None) -> None:
        if self.knowledge_scope == "company" and company_id is None:
            raise ValueError(f"Adapter {self.source_type} exige company_id.")
        if self.knowledge_scope == "product" and company_id is not None:
            raise ValueError(f"Adapter {self.source_type} não aceita company_id.")
