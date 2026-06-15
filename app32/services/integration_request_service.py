from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from models import db
from models.integration_request import IntegrationRequest
from models.project import ProjectTask
from services.project_task_service import ProjectTaskService

logger = logging.getLogger(__name__)


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
    CATALOG_REQUEST_KEYS = ("open_finance", "financial_data_api", "erp_accounting_bridge")
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }
    CATALOG_STATUS_TO_STAGE = {
        "planned": "pending",
        "discovery": "inbox",
    }

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
        initial_status: str = "requested",
        initial_stage: str = "inbox",
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
            status=initial_status,
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
            stage=initial_stage,
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

    @classmethod
    def delete_request(
        cls,
        *,
        request_id: int,
        company_id: int,
        requester_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Remove uma solicitação de integração e o card de backlog gerado por ela.

        A remoção é física por desenho: `integration_requests` não possui
        soft-delete e o harness DEV_FULL precisa garantir resíduo textual zero.
        O card derivado só é apagado quando contém o marcador técnico da
        solicitação, evitando remoção acidental de tarefas manuais.
        """
        record = IntegrationRequest.query.filter(
            IntegrationRequest.id == int(request_id),
            IntegrationRequest.company_id == int(company_id),
        ).first()
        if record is None:
            return None

        backlog_task_id = int(record.backlog_task_id) if record.backlog_task_id else None
        deleted_task_id: int | None = None
        marker = f"integration_request_id={record.id}"

        if backlog_task_id:
            task = (
                ProjectTask.query.join(ProjectTask.project)
                .filter(
                    ProjectTask.id == backlog_task_id,
                    ProjectTask.notes.isnot(None),
                    ProjectTask.notes.contains(marker),
                    ProjectTask.project.has(company_id=int(company_id)),
                )
                .first()
            )
            if task is not None:
                deleted_task_id = int(task.id)
                db.session.delete(task)

        deleted_payload = {
            "id": int(record.id),
            "company_id": int(record.company_id),
            "requester_user_id": int(record.requester_user_id),
            "backlog_task_id": backlog_task_id,
            "deleted_backlog_task_id": deleted_task_id,
            "deleted_by_user_id": int(requester_user_id) if requester_user_id else None,
        }
        db.session.delete(record)
        db.session.commit()
        return deleted_payload

    @classmethod
    def _build_catalog_seed_payload(cls, item: dict[str, Any]) -> dict[str, Any]:
        use_cases = item.get("use_cases") or []
        requirements = item.get("activation_requirements") or []
        return {
            "title": item.get("title") or "Nova integração",
            "business_domain": item.get("category") or "Integrações",
            "integration_mode": item.get("integration_mode") or "bidirectional",
            "technical_channel": item.get("technical_channel") or "api",
            "source_channel": "catalog_seed",
            "external_system": item.get("title") or "Backlog APP32",
            "objective": item.get("summary") or item.get("description") or "Planejamento de integração no backlog corporativo.",
            "data_summary": " ; ".join(use_cases[:3]) or "Backlog consultivo de integração em evolução.",
            "notes": "\n".join(requirements[:3]) if requirements else None,
        }

    @classmethod
    def _build_catalog_seed_description(cls, item: dict[str, Any]) -> str:
        lines = [
            "Integração canônica do catálogo consultivo sincronizada com o backlog AA.J.31.",
            "",
            f"Chave do catálogo: {item.get('key')}",
            f"Status consultivo original: {item.get('status')}",
            f"Título: {item.get('title')}",
            f"Categoria: {item.get('category')}",
            f"Modo: {item.get('integration_mode')}",
            f"Canal técnico: {item.get('technical_channel')}",
            "",
            "Resumo:",
            item.get("summary") or item.get("description") or "Sem resumo.",
        ]
        use_cases = item.get("use_cases") or []
        if use_cases:
            lines.extend(["", "Casos de uso:"] + [f"- {entry}" for entry in use_cases[:5]])
        return "\n".join(lines).strip()

    @classmethod
    def _find_catalog_backlog_task(cls, catalog_key: str) -> ProjectTask | None:
        project, error = ProjectTaskService.resolve_project_by_code(cls.BACKLOG_PROJECT_CODE, allowed_company_ids=None)
        if error or project is None:
            return None
        marker = f"integration_catalog_key={catalog_key}"
        task = (
            ProjectTask.query.filter(
                ProjectTask.project_id == project.id,
                ProjectTask.notes.isnot(None),
                ProjectTask.notes.contains(marker),
            )
            .order_by(ProjectTask.id.asc())
            .first()
        )
        return task

    @classmethod
    def ensure_catalog_backlog_tasks(
        cls,
        *,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> list[dict[str, Any]]:
        from services.integration_catalog_service import IntegrationCatalogService

        seeded: list[dict[str, Any]] = []
        for key in cls.CATALOG_REQUEST_KEYS:
            item = IntegrationCatalogService.get_integration(key)
            if not item or item.get("status") == "available":
                continue

            task = cls._find_catalog_backlog_task(key)
            if task is None:
                seed_payload = cls._build_catalog_seed_payload(item)
                stage = cls.CATALOG_STATUS_TO_STAGE.get(str(item.get("status") or "").strip().lower(), "inbox")
                result, error = ProjectTaskService.create_project_task(
                    project_code=cls.BACKLOG_PROJECT_CODE,
                    task_name=f"[Integração Catálogo] {seed_payload['title']}",
                    user_id=int(requester_user_id),
                    allowed_company_ids=None,
                    responsible_name=requester_name,
                    description=cls._build_catalog_seed_description(item),
                    status="planned",
                    stage=stage,
                    priority="normal",
                    notes=(
                        f"integration_catalog_key={key}\n"
                        "source_channel=integration_catalog\n"
                        f"catalog_status={item.get('status')}\n"
                        f"technical_channel={item.get('technical_channel')}\n"
                        f"integration_mode={item.get('integration_mode')}"
                    ),
                )
                if error:
                    logger.warning("Falha ao sincronizar backlog canônico de integração %s: %s", key, error)
                    continue
                task = (result or {}).get("task")

            if task is not None:
                seeded.append(cls._serialize_catalog_backlog_item(item, task))
        return seeded

    @classmethod
    def _serialize_catalog_backlog_item(cls, item: dict[str, Any], task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "inbox").strip().lower()
        return {
            "id": f"catalog:{item.get('key')}",
            "company_id": None,
            "requester_user_id": None,
            "title": item.get("title"),
            "slug": cls._slugify(item.get("title") or item.get("key") or "integracao-catalogo"),
            "business_domain": item.get("category"),
            "integration_mode": item.get("integration_mode"),
            "technical_channel": item.get("technical_channel"),
            "source_channel": "integration_catalog",
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "external_system": item.get("title"),
            "objective": item.get("summary"),
            "data_summary": item.get("description"),
            "frequency": None,
            "urgency": "medium",
            "compliance_level": "internal",
            "provider_contact": None,
            "provider_docs_url": None,
            "notes": getattr(task, "notes", None),
            "payload": {"integration_catalog_key": item.get("key"), "catalog_status": item.get("status")},
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "backlog_stage": stage,
            "backlog_stage_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "created_at": getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else None,
            "updated_at": getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else None,
        }

    @classmethod
    def _load_backlog_task_map(cls, task_ids: list[int]) -> dict[int, ProjectTask]:
        normalized_ids = [int(task_id) for task_id in task_ids if task_id]
        if not normalized_ids:
            return {}
        tasks = ProjectTask.query.filter(ProjectTask.id.in_(normalized_ids)).all()
        return {task.id: task for task in tasks}

    @classmethod
    def _serialize_request_record(cls, record: IntegrationRequest, task_map: dict[int, ProjectTask]) -> dict[str, Any]:
        payload = record.to_dict()
        task = task_map.get(int(record.backlog_task_id)) if record.backlog_task_id else None
        if task is not None:
            stage = str(getattr(task, "stage", None) or payload.get("status") or "inbox").strip().lower()
            payload["status"] = stage
            payload["status_label"] = cls.BACKLOG_STAGE_LABELS.get(stage, stage)
            payload["backlog_stage"] = stage
            payload["backlog_stage_label"] = cls.BACKLOG_STAGE_LABELS.get(stage, stage)
            payload["backlog_task_code"] = getattr(task, "code", None)
            payload["created_at"] = getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else payload.get("created_at")
            payload["updated_at"] = getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else payload.get("updated_at")
        return payload

    @classmethod
    def list_requests(
        cls,
        *,
        company_id: int | None = None,
        limit: int = 20,
        requester_user_id: int | None = None,
        requester_name: str | None = None,
    ) -> list[dict[str, Any]]:
        seeded = []
        if requester_user_id:
            seeded = cls.ensure_catalog_backlog_tasks(
                requester_user_id=int(requester_user_id),
                requester_name=requester_name,
            )

        query = IntegrationRequest.query.order_by(IntegrationRequest.created_at.desc())
        if company_id is not None:
            query = query.filter(IntegrationRequest.company_id == int(company_id))
        records = query.limit(limit).all()
        task_map = cls._load_backlog_task_map([int(item.backlog_task_id) for item in records if item.backlog_task_id])
        merged = [cls._serialize_request_record(item, task_map) for item in records]
        merged.extend(seeded)
        merged.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return merged[:limit]
