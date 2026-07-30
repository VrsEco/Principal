from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, time
from typing import Any

from sqlalchemy import func

from models import Employee, Meeting
from services.knowledge.adapters.base import KnowledgeSourceAdapter
from services.knowledge.contracts import (
    SourceChunkDocument,
    SourceDocument,
    SourceGrantDocument,
)


class MeetingKnowledgeAdapter(KnowledgeSourceAdapter):
    source_type = "meeting"
    knowledge_scope = "company"
    adapter_version = "v1"
    parser_version = "meeting-json-v1"
    chunking_policy = "meeting-section-v1"
    ELIGIBLE_STATUSES = {"completed", "done"}

    def discover_documents(self, *, company_id: int | None = None) -> tuple[SourceDocument, ...]:
        self.validate_scope(company_id=company_id)
        employees = (
            Employee.query.filter(
                Employee.company_id == company_id,
                Employee.status == "active",
            )
            .order_by(Employee.id.asc())
            .all()
        )
        employees_by_id = {int(employee.id): employee for employee in employees}
        employees_by_name: dict[str, list[Employee]] = {}
        for employee in employees:
            normalized_name = self._normalize_name(employee.name)
            if normalized_name:
                employees_by_name.setdefault(normalized_name, []).append(employee)
        meetings = (
            Meeting.query.filter(
                Meeting.company_id == company_id,
                func.lower(Meeting.status).in_(tuple(sorted(self.ELIGIBLE_STATUSES))),
            )
            .order_by(Meeting.actual_date.desc(), Meeting.updated_at.desc(), Meeting.id.desc())
            .all()
        )
        return tuple(
            self._build_document(
                meeting,
                employees_by_id=employees_by_id,
                employees_by_name=employees_by_name,
            )
            for meeting in meetings
        )

    def _build_document(
        self,
        meeting: Meeting,
        *,
        employees_by_id: dict[int, Employee] | None = None,
        employees_by_name: dict[str, list[Employee]] | None = None,
    ) -> SourceDocument:
        agenda = self._safe_json(meeting.agenda_json)
        discussions = self._safe_json(meeting.discussions_json)
        activities = self._safe_json(meeting.activities_json)
        participants = self._safe_json(meeting.participants_json)
        guests = self._safe_json(meeting.guests_json)
        grants = self._participant_grants(
            participants,
            guests,
            employees_by_id=employees_by_id or {},
            employees_by_name=employees_by_name or {},
        )
        chunks = self._build_chunks(
            meeting,
            agenda=agenda,
            discussions=discussions,
            activities=activities,
        )
        checksum_payload = {
            "id": meeting.id,
            "title": meeting.title,
            "status": meeting.status,
            "meeting_notes": meeting.meeting_notes,
            "agenda": agenda,
            "discussions": discussions,
            "activities": activities,
            "participants": participants,
            "guests": guests,
            "grants": [
                {"scope": item.grant_scope, "employee_id": item.employee_id}
                for item in grants
            ],
        }
        occurred_at = self._occurred_at(meeting)
        return SourceDocument(
            knowledge_scope="company",
            source_type=self.source_type,
            source_ref=f"meeting:{meeting.id}",
            knowledge_kind="decision_record",
            title=meeting.title,
            canonical_uri=(
                f"app-versus://meetings/company/{meeting.company_id}/"
                f"meeting/{meeting.id}/report"
            ),
            status="published",
            authority_level="internal",
            version=(meeting.updated_at or meeting.created_at or datetime.utcnow()).isoformat(),
            content_checksum=self._checksum(checksum_payload),
            chunks=chunks,
            route_key="meetings.meeting_report",
            module_key="meetings",
            navigation_target="meetings.meeting_report",
            valid_from=occurred_at,
            source_updated_at=meeting.updated_at or meeting.created_at,
            metadata={
                "meeting_id": meeting.id,
                "project_id": meeting.project_id,
                "status": meeting.status,
                "route_params": {
                    "company_id": meeting.company_id,
                    "meeting_id": meeting.id,
                },
                "grant_resolution": "resolved" if grants else "unresolved_fail_closed",
            },
            grants=grants,
        )

    def _build_chunks(
        self,
        meeting: Meeting,
        *,
        agenda: Any,
        discussions: Any,
        activities: Any,
    ) -> tuple[SourceChunkDocument, ...]:
        sections: list[tuple[str, str]] = []
        overview = "\n".join(
            item
            for item in (
                meeting.title,
                " ".join(str(meeting.meeting_notes or "").split()),
            )
            if item
        )
        if overview:
            sections.append(("ata", overview))
        sections.extend(self._item_sections("discussao", discussions))
        sections.extend(self._item_sections("atividade", activities))
        sections.extend(self._item_sections("pauta", agenda))
        if not sections:
            sections.append(("ata", meeting.title))

        return tuple(
            SourceChunkDocument(
                section_key=f"{key}-{index + 1}",
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

    def _item_sections(self, prefix: str, payload: Any) -> list[tuple[str, str]]:
        items = payload if isinstance(payload, list) else [payload] if payload else []
        sections = []
        for index, item in enumerate(items, start=1):
            content = self._human_text(item)
            if content:
                sections.append((f"{prefix}-{index}", content))
        return sections

    def _human_text(self, value: Any) -> str:
        if isinstance(value, str):
            return " ".join(value.split())
        if isinstance(value, dict):
            lines = []
            for key, item in value.items():
                if item in (None, "", [], {}):
                    continue
                rendered = self._human_text(item)
                if rendered:
                    label = str(key).replace("_", " ").strip().capitalize()
                    lines.append(f"{label}: {rendered}")
            return "\n".join(lines)
        if isinstance(value, list):
            return "; ".join(filter(None, (self._human_text(item) for item in value)))
        if isinstance(value, (int, float, bool)):
            return str(value)
        return ""

    def _participant_grants(
        self,
        *payloads: Any,
        employees_by_id: dict[int, Employee],
        employees_by_name: dict[str, list[Employee]],
    ) -> tuple[SourceGrantDocument, ...]:
        employee_ids: set[int] = set()
        for payload in payloads:
            candidates = []
            if isinstance(payload, dict):
                candidates.extend(payload.get("internal") or [])
            elif isinstance(payload, list):
                candidates.extend(payload)
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                raw_id = candidate.get("employee_id") or candidate.get("id")
                try:
                    employee_id = int(raw_id)
                except (TypeError, ValueError):
                    employee_id = 0
                if employee_id > 0 and employee_id in employees_by_id:
                    employee_ids.add(employee_id)
                    continue
                normalized_name = self._normalize_name(candidate.get("name"))
                matches = employees_by_name.get(normalized_name, [])
                if len(matches) == 1:
                    employee_ids.add(int(matches[0].id))
        return tuple(
            SourceGrantDocument(
                grant_scope="employee",
                employee_id=employee_id,
                metadata={"origin": "meeting_participant"},
            )
            for employee_id in sorted(employee_ids)
        )

    @staticmethod
    def _normalize_name(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _safe_json(value: Any) -> Any:
        if value in (None, ""):
            return []
        if isinstance(value, (dict, list)):
            return value
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        return decoded if isinstance(decoded, (dict, list)) else []

    @staticmethod
    def _occurred_at(meeting: Meeting) -> datetime | None:
        if not meeting.actual_date:
            return None
        parsed_time = time()
        raw_time = str(meeting.actual_time or "").strip()
        if raw_time:
            try:
                parsed_time = time.fromisoformat(raw_time)
            except ValueError:
                parsed_time = time()
        return datetime.combine(meeting.actual_date, parsed_time)

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


__all__ = ["MeetingKnowledgeAdapter"]
