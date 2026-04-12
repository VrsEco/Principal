from __future__ import annotations

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from models import db
from models.integration_request import IntegrationRequest
from services.project_task_service import ProjectTaskService


class IntegrationRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    business_domain: str = Field(min_length=2, max_length=80)
    integration_mode: str = Field(pattern="^(consume|provide|bidirectional)$")
    technical_channel: str = Field(pattern="^(api|mcp|api_mcp)$")
    source_channel: str = Field(default="ui", min_length=2, max_length=64)
    external_system: str = Field(min_length=2, max_length=255)
    objective: str = Field(min_length=10, max_length=3000)
    data_summary: str = Field(min_length=10, max_length=3000)
    frequency: str | None = Field(default=None, max_length=64)
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    compliance_level: str = Field(default="internal", pattern="^(internal|restricted|sensitive)$")
    provider_contact: str | None = Field(default=None, max_length=255)
    provider_docs_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=3000)


class IntegrationRequestService:
    BACKLOG_PROJECT_CODE = "AA.J.31"

    @staticmethod
    def _slugify(value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return re.sub(r"-{2,}", "-", text).strip("-") or "nova-integracao"

    @classmethod
    def _build_description(
        cls,
        payload: IntegrationRequestPayload,
        *,
        requester_name: str | None,
        company_id: int,
        requester_user_id: int,
    ) -> str:
        lines = [
            "Solicitação estruturada pelo Assistente de Nova Integração.",
            "",
            f"Título: {payload.title}",
            f"Domínio: {payload.business_domain}",
            f"Modo: {payload.integration_mode}",
            f"Canal técnico: {payload.technical_channel}",
            f"Sistema externo: {payload.external_system}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Company ID: {company_id}",
            f"Canal de origem: {payload.source_channel}",
            f"Urgência: {payload.urgency}",
            f"Compliance: {payload.compliance_level}",
            "",
            "Objetivo:",
            payload.objective,
            "",
            "Dados envolvidos:",
            payload.data_summary,
        ]
        if payload.frequency:
            lines.extend(["", f"Frequência: {payload.frequency}"])
        if payload.provider_contact:
            lines.append(f"Contato do fornecedor: {payload.provider_contact}")
        if payload.provider_docs_url:
            lines.append(f"Documentação: {payload.provider_docs_url}")
        if payload.notes:
            lines.extend(["", "Observações:", payload.notes])
        return "\n".join(lines).strip()

    @classmethod
    def create_request(
        cls,
        raw_payload: dict[str, Any],
        *,
        company_id: int,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> IntegrationRequest:
        payload = IntegrationRequestPayload.model_validate(raw_payload)

        record = IntegrationRequest(
            company_id=int(company_id),
            requester_user_id=int(requester_user_id),
            title=payload.title,
            slug=cls._slugify(payload.title),
            business_domain=payload.business_domain,
            integration_mode=payload.integration_mode,
            technical_channel=payload.technical_channel,
            source_channel=payload.source_channel,
            status="requested",
            external_system=payload.external_system,
            objective=payload.objective,
            data_summary=payload.data_summary,
            frequency=payload.frequency,
            urgency=payload.urgency,
            compliance_level=payload.compliance_level,
            provider_contact=payload.provider_contact,
            provider_docs_url=str(payload.provider_docs_url) if payload.provider_docs_url else None,
            notes=payload.notes,
            payload=payload.model_dump(mode="json"),
        )
        db.session.add(record)
        db.session.flush()

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"[Nova Integração] {payload.title} - {payload.external_system}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description=cls._build_description(
                payload,
                requester_name=requester_name,
                company_id=int(company_id),
                requester_user_id=int(requester_user_id),
            ),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                f"integration_request_id={record.id}\n"
                f"source_channel={payload.source_channel}\n"
                f"technical_channel={payload.technical_channel}\n"
                f"integration_mode={payload.integration_mode}"
            ),
        )
        if error:
            raise ValueError(error)
        task = (result or {}).get("task")
        if task is not None:
            record.backlog_task_id = getattr(task, "id", None)
        db.session.commit()
        return record

    @staticmethod
    def list_requests(*, company_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query = IntegrationRequest.query.order_by(IntegrationRequest.created_at.desc())
        if company_id is not None:
            query = query.filter(IntegrationRequest.company_id == int(company_id))
        return [item.to_dict() for item in query.limit(limit).all()]
