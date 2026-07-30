from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SourceChunkDocument:
    section_key: str
    content: str
    chunk_order: int
    content_checksum: str
    token_count: int
    source_span: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    adapter_version: str = "v1"
    parser_version: str = "v1"
    chunking_policy: str = "heading-v1"


@dataclass(frozen=True)
class SourceGrantDocument:
    grant_scope: str
    user_id: int | None = None
    employee_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceDocument:
    knowledge_scope: str
    source_type: str
    source_ref: str
    knowledge_kind: str
    title: str
    canonical_uri: str
    status: str
    authority_level: str
    version: str
    content_checksum: str
    chunks: tuple[SourceChunkDocument, ...]
    product_version: str | None = None
    locale: str = "pt-BR"
    route_key: str | None = None
    module_key: str | None = None
    audience: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    help_kind: str | None = None
    navigation_target: str | None = None
    tour_definition_id: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    grants: tuple[SourceGrantDocument, ...] = ()
