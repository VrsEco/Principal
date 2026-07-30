"""Camada de Conhecimento Corporativo do APP Versus."""

from .auto_update_service import KnowledgeAutoUpdateService
from .registry import knowledge_source_registry

__all__ = ["KnowledgeAutoUpdateService", "knowledge_source_registry"]
