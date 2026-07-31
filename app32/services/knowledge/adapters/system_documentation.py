from __future__ import annotations

import hashlib
import re
from pathlib import Path

from services.knowledge.adapters.base import KnowledgeSourceAdapter
from services.knowledge.contracts import SourceChunkDocument, SourceDocument


class SystemDocumentationKnowledgeAdapter(KnowledgeSourceAdapter):
    """Projeta Papers e SPECs canônicos como conhecimento global do produto."""

    source_type = "system_documentation"
    knowledge_scope = "product"
    adapter_version = "v1"
    parser_version = "markdown-system-doc-v1"
    chunking_policy = "heading-bounded-v1"
    DOCUMENT_CLASSES = {
        "papers": ("paper", "contextual"),
        "spec": ("spec", "official"),
    }
    MAX_CHUNK_CHARS = 3_600

    def __init__(self, docs_root: str | Path | None = None):
        app_root = Path(__file__).resolve().parents[3]
        self.docs_root = Path(docs_root or app_root / "docs")

    def discover_documents(self, *, company_id: int | None = None) -> tuple[SourceDocument, ...]:
        self.validate_scope(company_id=company_id)
        documents: list[SourceDocument] = []
        for directory, (document_class, authority_level) in self.DOCUMENT_CLASSES.items():
            root = self.docs_root / directory
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.md")):
                if path.name.lower() in {"readme.md", "index.md"}:
                    continue
                documents.append(
                    self._build_document(
                        path,
                        document_class=document_class,
                        authority_level=authority_level,
                    )
                )
        return tuple(documents)

    def _build_document(
        self,
        path: Path,
        *,
        document_class: str,
        authority_level: str,
    ) -> SourceDocument:
        try:
            content = path.read_text(encoding="utf-8-sig").strip()
        except OSError as exc:
            raise ValueError(f"Não foi possível ler {path}: {exc}") from exc
        if not content:
            raise ValueError(f"Documento sistêmico vazio: {path.name}")

        relative_path = path.relative_to(self.docs_root).as_posix()
        title = self._extract_title(content, fallback=path.stem.replace("_", " ").title())
        version = self._extract_version(content, path.name)
        chunks = self._build_chunks(content)
        checksum = self._checksum(content)
        return SourceDocument(
            knowledge_scope="product",
            source_type=self.source_type,
            source_ref=f"system_documentation:{relative_path}",
            knowledge_kind=document_class,
            title=title,
            canonical_uri=f"app-versus://docs/{relative_path}",
            status="published",
            authority_level=authority_level,
            version=version,
            content_checksum=checksum,
            product_version="3.2",
            locale="pt-BR",
            module_key="system_documentation",
            help_kind="concept",
            chunks=chunks,
            metadata={
                "document_class": document_class,
                "relative_path": relative_path,
                "declared_status": self._extract_declared_status(content),
            },
        )

    def _build_chunks(self, content: str) -> tuple[SourceChunkDocument, ...]:
        sections: list[tuple[str, str]] = []
        current_heading = "Visão geral"
        current_lines: list[str] = []

        def flush() -> None:
            body = "\n".join(current_lines).strip()
            if not body:
                return
            sections.extend(self._bounded_sections(current_heading, body))

        for line in content.splitlines():
            heading = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
            if heading:
                flush()
                current_heading = heading.group(1).strip()
                current_lines = []
                continue
            current_lines.append(line)
        flush()

        chunks: list[SourceChunkDocument] = []
        used_keys: set[str] = set()
        for order, (heading, body) in enumerate(sections):
            base_key = self._slugify(heading)
            section_key = base_key
            suffix = 2
            while section_key in used_keys:
                section_key = f"{base_key}-{suffix}"
                suffix += 1
            used_keys.add(section_key)
            normalized = f"{heading}\n\n{body}".strip()
            chunks.append(
                SourceChunkDocument(
                    section_key=section_key,
                    content=normalized,
                    chunk_order=order,
                    content_checksum=self._checksum(normalized),
                    token_count=len(normalized.split()),
                    source_span=heading,
                    metadata={"heading": heading},
                    adapter_version=self.adapter_version,
                    parser_version=self.parser_version,
                    chunking_policy=self.chunking_policy,
                )
            )
        if not chunks:
            raise ValueError("Documento sistêmico sem conteúdo indexável.")
        return tuple(chunks)

    def _bounded_sections(self, heading: str, body: str) -> list[tuple[str, str]]:
        if len(body) <= self.MAX_CHUNK_CHARS:
            return [(heading, body)]
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
        batches: list[str] = []
        current: list[str] = []
        current_size = 0
        for paragraph in paragraphs:
            if current and current_size + len(paragraph) + 2 > self.MAX_CHUNK_CHARS:
                batches.append("\n\n".join(current))
                current = []
                current_size = 0
            current.append(paragraph)
            current_size += len(paragraph) + 2
        if current:
            batches.append("\n\n".join(current))
        return [
            (heading if index == 1 else f"{heading} — parte {index}", batch)
            for index, batch in enumerate(batches, start=1)
        ]

    @staticmethod
    def _extract_title(content: str, *, fallback: str) -> str:
        match = re.search(r"^#\s+(.+?)\s*$", content, flags=re.MULTILINE)
        return match.group(1).strip() if match else fallback

    @staticmethod
    def _extract_version(content: str, filename: str) -> str:
        match = re.search(r"(?:^|[_\s-])v(\d+(?:\.\d+)*)\b", filename, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"\bv(\d+(?:\.\d+)*)\b", content[:500], flags=re.IGNORECASE)
        return f"v{match.group(1)}" if match else "v1"

    @staticmethod
    def _extract_declared_status(content: str) -> str | None:
        match = re.search(r"^\*{0,2}Status\*{0,2}\s*:\s*(.+?)\s*$", content, flags=re.I | re.M)
        return match.group(1).strip() if match else None

    @staticmethod
    def _checksum(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "secao"
