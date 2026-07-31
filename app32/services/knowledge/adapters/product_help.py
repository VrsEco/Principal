from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from services.knowledge.adapters.base import KnowledgeSourceAdapter
from services.knowledge.contracts import SourceChunkDocument, SourceDocument


class ProductHelpKnowledgeAdapter(KnowledgeSourceAdapter):
    source_type = "product_help"
    knowledge_scope = "product"
    adapter_version = "v1"
    parser_version = "json-markdown-v1"
    chunking_policy = "markdown-heading-v1"

    REQUIRED_FIELDS = {
        "source_ref",
        "title",
        "version",
        "product_version",
        "route_key",
        "module_key",
        "help_kind",
        "canonical_uri",
        "content",
    }
    ALLOWED_HELP_KINDS = {
        "concept",
        "how_to",
        "navigation",
        "permission_explanation",
        "troubleshooting",
        "guided_tour",
        "release_change",
    }

    def __init__(self, catalog_dir: str | Path | None = None):
        app_root = Path(__file__).resolve().parents[3]
        self.catalog_dir = Path(catalog_dir or app_root / "knowledge" / "product_help")

    def discover_documents(self, *, company_id: int | None = None) -> tuple[SourceDocument, ...]:
        self.validate_scope(company_id=company_id)
        if not self.catalog_dir.exists():
            return ()

        documents: list[SourceDocument] = []
        seen_refs: set[str] = set()
        for path in sorted(self.catalog_dir.glob("*.json")):
            payload = self._load_payload(path)
            document = self._build_document(payload, path=path)
            if document.source_ref in seen_refs:
                raise ValueError(f"source_ref duplicado em product_help: {document.source_ref}")
            seen_refs.add(document.source_ref)
            documents.append(document)
        return tuple(documents)

    def _load_payload(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Catálogo product_help inválido em {path.name}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Catálogo product_help deve ser objeto JSON: {path.name}")
        missing = sorted(self.REQUIRED_FIELDS - set(payload))
        if missing:
            raise ValueError(f"Campos obrigatórios ausentes em {path.name}: {', '.join(missing)}")
        return payload

    def _build_document(self, payload: dict[str, Any], *, path: Path) -> SourceDocument:
        source_ref = self._required_text(payload, "source_ref", path)
        help_kind = self._required_text(payload, "help_kind", path)
        if help_kind not in self.ALLOWED_HELP_KINDS:
            raise ValueError(f"help_kind inválido em {path.name}: {help_kind}")

        content = self._required_text(payload, "content", path)
        navigation_target = str(payload.get("navigation_target") or "").strip() or None
        if navigation_target and (
            not navigation_target.startswith("/")
            or navigation_target.startswith("//")
            or "\\" in navigation_target
        ):
            raise ValueError(
                f"navigation_target deve ser uma rota interna absoluta em {path.name}"
            )
        status = str(payload.get("status") or "published").strip().lower()
        if status != "published":
            raise ValueError(f"Somente product_help publicado é elegível: {path.name}")

        normalized = {
            **payload,
            "source_ref": source_ref,
            "help_kind": help_kind,
            "content": content,
        }
        content_checksum = self._checksum(
            json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        chunks = self._build_chunks(content)
        if not chunks:
            raise ValueError(f"Conteúdo product_help vazio após parsing: {path.name}")

        return SourceDocument(
            knowledge_scope="product",
            source_type=self.source_type,
            source_ref=source_ref,
            knowledge_kind="product_help",
            title=self._required_text(payload, "title", path),
            canonical_uri=self._required_text(payload, "canonical_uri", path),
            status="published",
            authority_level=str(payload.get("authority_level") or "official"),
            version=self._required_text(payload, "version", path),
            product_version=self._required_text(payload, "product_version", path),
            locale=str(payload.get("locale") or "pt-BR"),
            route_key=self._required_text(payload, "route_key", path),
            module_key=self._required_text(payload, "module_key", path),
            audience=tuple(self._string_list(payload.get("audience"), "audience", path)),
            required_capabilities=tuple(
                self._string_list(
                    payload.get("required_capabilities"),
                    "required_capabilities",
                    path,
                )
            ),
            help_kind=help_kind,
            navigation_target=navigation_target,
            tour_definition_id=str(payload.get("tour_definition_id") or "").strip() or None,
            content_checksum=content_checksum,
            valid_from=self._parse_datetime(payload.get("valid_from"), "valid_from", path),
            valid_to=self._parse_datetime(payload.get("valid_to"), "valid_to", path),
            source_updated_at=self._parse_datetime(
                payload.get("source_updated_at"),
                "source_updated_at",
                path,
            ),
            chunks=chunks,
            metadata={
                "catalog_file": path.name,
                "tour_steps": list(payload.get("tour_steps") or []),
                "suggested_questions": list(payload.get("suggested_questions") or []),
            },
        )

    def _build_chunks(self, content: str) -> tuple[SourceChunkDocument, ...]:
        sections: list[tuple[str, str]] = []
        current_title = "visao-geral"
        current_lines: list[str] = []

        def flush() -> None:
            text = "\n".join(current_lines).strip()
            if text:
                sections.append((current_title, text))

        for line in content.splitlines():
            heading = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
            if heading:
                flush()
                current_lines = []
                current_title = self._slugify(heading.group(1))
                continue
            current_lines.append(line)
        flush()

        chunks: list[SourceChunkDocument] = []
        used_keys: dict[str, int] = {}
        for index, (section_key, section_content) in enumerate(sections):
            count = used_keys.get(section_key, 0) + 1
            used_keys[section_key] = count
            unique_key = section_key if count == 1 else f"{section_key}-{count}"
            chunks.append(
                SourceChunkDocument(
                    section_key=unique_key,
                    content=section_content,
                    chunk_order=index,
                    token_count=len(section_content.split()),
                    content_checksum=self._checksum(section_content),
                    source_span=unique_key,
                    adapter_version=self.adapter_version,
                    parser_version=self.parser_version,
                    chunking_policy=self.chunking_policy,
                )
            )
        return tuple(chunks)

    @staticmethod
    def _required_text(payload: dict[str, Any], field: str, path: Path) -> str:
        value = str(payload.get(field) or "").strip()
        if not value:
            raise ValueError(f"Campo {field} vazio em {path.name}")
        return value

    @staticmethod
    def _string_list(value: Any, field: str, path: Path) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"Campo {field} deve ser lista de strings em {path.name}")
        return [item.strip() for item in value if item.strip()]

    @staticmethod
    def _parse_datetime(value: Any, field: str, path: Path) -> datetime | None:
        if value in (None, ""):
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as exc:
            raise ValueError(f"Campo {field} inválido em {path.name}") from exc

    @staticmethod
    def _checksum(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "secao"
