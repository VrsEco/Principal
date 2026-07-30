from __future__ import annotations

from services.knowledge.adapters.base import KnowledgeSourceAdapter
from services.knowledge.adapters.meeting import MeetingKnowledgeAdapter
from services.knowledge.adapters.process_publication import ProcessPublicationKnowledgeAdapter
from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter


class KnowledgeSourceRegistry:
    def __init__(self):
        self._adapters: dict[str, KnowledgeSourceAdapter] = {}

    def register(self, adapter: KnowledgeSourceAdapter) -> None:
        if adapter.source_type in self._adapters:
            raise ValueError(f"Adapter knowledge já registrado: {adapter.source_type}")
        self._adapters[adapter.source_type] = adapter

    def get(self, source_type: str) -> KnowledgeSourceAdapter:
        try:
            return self._adapters[source_type]
        except KeyError as exc:
            raise KeyError(f"Adapter knowledge não registrado: {source_type}") from exc

    def list_source_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


knowledge_source_registry = KnowledgeSourceRegistry()
knowledge_source_registry.register(ProductHelpKnowledgeAdapter())
knowledge_source_registry.register(ProcessPublicationKnowledgeAdapter())
knowledge_source_registry.register(MeetingKnowledgeAdapter())
