from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from models import ProcessPortalPublication, ProcessPortalPublicationGrant
from services.knowledge.adapters.base import KnowledgeSourceAdapter
from services.knowledge.contracts import (
    SourceChunkDocument,
    SourceDocument,
    SourceGrantDocument,
)


class ProcessPublicationKnowledgeAdapter(KnowledgeSourceAdapter):
    source_type = "process_publication"
    knowledge_scope = "company"
    adapter_version = "v1"
    parser_version = "process-portal-snapshot-v1"
    chunking_policy = "snapshot-section-v1"

    _IGNORED_KEYS = {
        "bpmn_xml",
        "svg_snapshot",
        "png_snapshot",
        "image_path",
        "image_url",
        "video_path",
        "video_url",
    }

    def discover_documents(self, *, company_id: int | None = None) -> tuple[SourceDocument, ...]:
        self.validate_scope(company_id=company_id)
        publications = (
            ProcessPortalPublication.query.filter_by(
                company_id=company_id,
                status="published",
            )
            .order_by(
                ProcessPortalPublication.process_id.asc(),
                ProcessPortalPublication.publication_version.desc(),
                ProcessPortalPublication.id.desc(),
            )
            .all()
        )
        if not publications:
            return ()

        latest_by_process: dict[int, ProcessPortalPublication] = {}
        for publication in publications:
            latest_by_process.setdefault(publication.process_id, publication)

        publication_ids = [item.id for item in latest_by_process.values()]
        grant_rows = (
            ProcessPortalPublicationGrant.query.filter(
                ProcessPortalPublicationGrant.company_id == company_id,
                ProcessPortalPublicationGrant.publication_id.in_(publication_ids),
                ProcessPortalPublicationGrant.can_view.is_(True),
            )
            .all()
        )
        grants_by_publication: dict[int, list[ProcessPortalPublicationGrant]] = {}
        for grant in grant_rows:
            grants_by_publication.setdefault(grant.publication_id, []).append(grant)

        documents = [
            self._build_document(
                publication,
                grants_by_publication.get(publication.id, []),
            )
            for publication in latest_by_process.values()
        ]
        return tuple(documents)

    def _build_document(
        self,
        publication: ProcessPortalPublication,
        grant_rows: list[ProcessPortalPublicationGrant],
    ) -> SourceDocument:
        snapshot = (
            dict(publication.content_snapshot_json)
            if isinstance(publication.content_snapshot_json, dict)
            else {}
        )
        grants = self._build_grants(publication, grant_rows)
        chunks = self._build_chunks(publication, snapshot)
        checksum_payload = {
            "publication_id": publication.id,
            "version": publication.publication_version,
            "visibility_scope": publication.visibility_scope,
            "title": publication.title,
            "summary": publication.summary,
            "snapshot": snapshot,
            "grants": [
                {
                    "scope": grant.grant_scope,
                    "user_id": grant.user_id,
                    "employee_id": grant.employee_id,
                }
                for grant in grants
            ],
        }
        return SourceDocument(
            knowledge_scope="company",
            source_type=self.source_type,
            source_ref=f"process-publication:{publication.id}",
            knowledge_kind="procedure",
            title=publication.title,
            canonical_uri=(
                f"app-versus://companies/{publication.company_id}/"
                f"process-portal/processes/{publication.process_id}"
            ),
            status="published",
            authority_level="official",
            version=str(publication.publication_version),
            content_checksum=self._checksum(checksum_payload),
            chunks=chunks,
            route_key="processes.process_portal_process_page",
            module_key="processes",
            navigation_target="processes.process_portal_process_page",
            valid_from=publication.published_at,
            source_updated_at=publication.updated_at or publication.published_at,
            metadata={
                "publication_id": publication.id,
                "process_id": publication.process_id,
                "visibility_scope": publication.visibility_scope,
                "slug": publication.slug,
                "route_params": {
                    "company_id": publication.company_id,
                    "process_id": publication.process_id,
                },
                "unsupported_grants_ignored": sum(
                    1
                    for row in grant_rows
                    if row.grant_scope not in {"company", "user", "employee"}
                ),
            },
            grants=grants,
        )

    def _build_grants(
        self,
        publication: ProcessPortalPublication,
        rows: list[ProcessPortalPublicationGrant],
    ) -> tuple[SourceGrantDocument, ...]:
        grants: list[SourceGrantDocument] = []
        seen: set[tuple[str, int | None, int | None]] = set()

        if str(publication.visibility_scope or "").strip().lower() == "company":
            grants.append(SourceGrantDocument(grant_scope="company"))
            seen.add(("company", None, None))

        for row in rows:
            scope = str(row.grant_scope or "").strip().lower()
            user_id = row.user_id if scope == "user" else None
            employee_id = row.employee_id if scope == "employee" else None
            if scope == "company":
                user_id = None
                employee_id = None
            if scope not in {"company", "user", "employee"}:
                continue
            if scope == "user" and not user_id:
                continue
            if scope == "employee" and not employee_id:
                continue
            key = (scope, user_id, employee_id)
            if key in seen:
                continue
            seen.add(key)
            grants.append(
                SourceGrantDocument(
                    grant_scope=scope,
                    user_id=user_id,
                    employee_id=employee_id,
                    metadata={"origin": "process_portal_publication_grant"},
                )
            )
        return tuple(grants)

    def _build_chunks(
        self,
        publication: ProcessPortalPublication,
        snapshot: dict[str, Any],
    ) -> tuple[SourceChunkDocument, ...]:
        sections: list[tuple[str, str]] = []
        overview = self._join_lines(
            [
                publication.title,
                publication.summary,
                snapshot.get("name"),
                snapshot.get("description"),
                snapshot.get("objective"),
                snapshot.get("notes"),
            ]
        )
        if overview:
            sections.append(("visao-geral", overview))

        for key in sorted(snapshot):
            if key in self._IGNORED_KEYS or key in {
                "name",
                "description",
                "objective",
                "notes",
            }:
                continue
            lines = self._flatten_text(snapshot[key], path=key)
            content = "\n".join(lines).strip()
            if content:
                sections.append((self._slugify(key), content))

        if not sections:
            sections.append(("visao-geral", publication.title))
        return tuple(
            SourceChunkDocument(
                section_key=self._unique_section_key(key, index),
                content=content,
                chunk_order=index,
                token_count=len(content.split()),
                content_checksum=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                source_span=key,
                adapter_version=self.adapter_version,
                parser_version=self.parser_version,
                chunking_policy=self.chunking_policy,
            )
            for index, (key, content) in enumerate(sections)
        )

    def _flatten_text(self, value: Any, *, path: str, depth: int = 0) -> list[str]:
        if depth > 5 or value is None:
            return []
        if isinstance(value, str):
            normalized = " ".join(value.split())
            return [f"{self._label(path)}: {normalized}"] if normalized else []
        if isinstance(value, (int, float, bool)):
            return [f"{self._label(path)}: {value}"]
        if isinstance(value, list):
            lines: list[str] = []
            for index, item in enumerate(value, start=1):
                lines.extend(self._flatten_text(item, path=f"{path} {index}", depth=depth + 1))
            return lines
        if isinstance(value, dict):
            lines = []
            for key in sorted(value):
                if str(key).lower() in self._IGNORED_KEYS:
                    continue
                lines.extend(
                    self._flatten_text(
                        value[key],
                        path=f"{path} {key}",
                        depth=depth + 1,
                    )
                )
            return lines
        return []

    @staticmethod
    def _join_lines(values: list[Any]) -> str:
        lines = []
        for value in values:
            normalized = " ".join(str(value or "").split())
            if normalized and normalized not in lines:
                lines.append(normalized)
        return "\n".join(lines)

    @staticmethod
    def _checksum(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or "secao"

    @staticmethod
    def _label(value: str) -> str:
        return str(value).replace("_", " ").strip().capitalize()

    @staticmethod
    def _unique_section_key(key: str, index: int) -> str:
        return f"{key}-{index + 1}"


__all__ = ["ProcessPublicationKnowledgeAdapter"]
