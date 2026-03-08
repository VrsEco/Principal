from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

from models import db
from models.project import ProjectTask
from models.workflow_gap import WorkflowGapCandidate
from services.project_task_service import ProjectTaskService

logger = logging.getLogger(__name__)

DEFAULT_WORKFLOW_GAP_PROJECT_CODE = os.environ.get("WORKFLOW_GAP_PROJECT_CODE", "AA.J.31")
DEFAULT_WORKFLOW_GAP_TASK_STAGE = os.environ.get("WORKFLOW_GAP_TASK_STAGE", "inbox")
DEFAULT_WORKFLOW_GAP_TASK_STATUS = os.environ.get("WORKFLOW_GAP_TASK_STATUS", "planned")
DEFAULT_WORKFLOW_GAP_TASK_PRIORITY = os.environ.get("WORKFLOW_GAP_TASK_PRIORITY", "normal")


def _normalize_request_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _slugify_words(value: str) -> str:
    tokens = re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(value or "").lower())
    return " ".join(tokens[:12]).strip()


def _truncate(value: str, max_length: int) -> str:
    normalized = _normalize_request_text(value)
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _extract_candidate_codes(telemetry: Optional[Dict[str, Any]]) -> list[str]:
    workflow_discovery = dict((telemetry or {}).get("workflow_discovery") or {})
    top_matches = workflow_discovery.get("top_matches") or []
    codes: list[str] = []
    for item in top_matches:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if code and code not in codes:
            codes.append(code)
    confidence = workflow_discovery.get("confidence") or {}
    for code in confidence.get("candidate_codes") or []:
        normalized = str(code or "").strip()
        if normalized and normalized not in codes:
            codes.append(normalized)
    selected_code = str(workflow_discovery.get("selected_code") or "").strip()
    if selected_code and selected_code not in codes:
        codes.insert(0, selected_code)
    return codes


def _infer_suggested_flow_name(request_text: str) -> str:
    normalized = _slugify_words(request_text)
    if not normalized:
        return "novo_fluxo"
    return normalized.replace(" ", "_")[:120]


def _build_gap_title(*, channel: str, request_text: str) -> str:
    channel_label = str(channel or "web").strip().lower() or "web"
    return _truncate(f"[FLOW GAP][{channel_label}] {request_text}", 200)


def _build_gap_task_how(
    *,
    request_text: str,
    channel: str,
    company_id: Optional[int],
    user_id: Optional[int],
    thread_id: Optional[str],
    resolution_type: str,
    telemetry: Optional[Dict[str, Any]],
) -> str:
    candidate_codes = _extract_candidate_codes(telemetry)
    workflow_discovery = dict((telemetry or {}).get("workflow_discovery") or {})
    lines = [
        "Origem: conversa com usuário detectada sem fluxo determinístico dedicado.",
        f"Canal: {channel or 'web'}",
        f"Company ID: {company_id or 'N/A'}",
        f"User ID: {user_id or 'N/A'}",
        f"Thread ID: {thread_id or 'N/A'}",
        f"Resultado da tentativa atual: {resolution_type}",
        f"Pedido original: {request_text}",
    ]
    if candidate_codes:
        lines.append(f"Fluxos candidatos identificados: {', '.join(candidate_codes)}")
    confidence = workflow_discovery.get("confidence") or {}
    if confidence:
        lines.append(f"Rota de confiança: {confidence.get('route')}")
        if confidence.get('reason'):
            lines.append(f"Motivo da confiança: {confidence.get('reason')}")
    selected_action = str(workflow_discovery.get("selected_action_key") or "").strip()
    if selected_action:
        lines.append(f"Action key sugerida: {selected_action}")
    lines.append("Objetivo: avaliar se este pedido deve virar um workflow determinístico do catálogo V3.")
    return "\n".join(lines)


def _build_gap_task_notes(
    *,
    request_text: str,
    telemetry: Optional[Dict[str, Any]],
    response_text: Optional[str],
) -> str:
    parts = [
        "Card criado automaticamente pelo radar de gaps de workflows.",
        f"Pedido do usuário: {request_text}",
    ]
    if response_text:
        parts.append(f"Resposta atual entregue pela IA: {_truncate(response_text, 500)}")
    workflow_discovery = dict((telemetry or {}).get("workflow_discovery") or {})
    if workflow_discovery:
        parts.append(f"Telemetria workflow_discovery: {workflow_discovery}")
    return "\n\n".join(parts)


class WorkflowGapService:
    @staticmethod
    def create_gap_candidate(
        *,
        user_id: Optional[int],
        company_id: Optional[int],
        channel: str,
        thread_id: Optional[str],
        request_text: str,
        response_text: Optional[str],
        resolution_type: str = "resolved_by_ai",
        source: str = "ai_fallback",
        telemetry: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowGapCandidate]:
        normalized_request = _normalize_request_text(request_text)
        if not normalized_request:
            return None

        title = _build_gap_title(channel=channel, request_text=normalized_request)
        suggested_flow_name = _infer_suggested_flow_name(normalized_request)
        candidate_codes = _extract_candidate_codes(telemetry)

        gap = WorkflowGapCandidate(
            company_id=company_id,
            user_id=user_id,
            channel=str(channel or "web").strip().lower() or "web",
            thread_id=str(thread_id or "").strip() or None,
            source=str(source or "ai_fallback").strip() or "ai_fallback",
            status="inbox",
            resolution_type=str(resolution_type or "resolved_by_ai").strip() or "resolved_by_ai",
            title=title,
            user_request_text=normalized_request,
            normalized_intent=_slugify_words(normalized_request) or None,
            suggested_flow_name=suggested_flow_name,
            business_outcome=(
                "Criar um fluxo determinístico capaz de atender este pedido com precisão operacional."
            ),
            matched_workflow_codes=candidate_codes,
            telemetry=dict(telemetry or {}),
        )

        try:
            db.session.add(gap)
            db.session.flush()

            task = WorkflowGapService._create_backlog_task(
                gap=gap,
                response_text=response_text,
            )
            if task is not None:
                gap.app_project_id = task.project_id
                gap.app_task_id = task.id
                gap.app_task_code = task.code

            db.session.commit()
            return gap
        except Exception:
            db.session.rollback()
            logger.exception("Erro ao criar workflow gap candidate para request=%r", normalized_request)
            return None

    @staticmethod
    def _create_backlog_task(
        *,
        gap: WorkflowGapCandidate,
        response_text: Optional[str],
    ) -> Optional[ProjectTask]:
        result, error = ProjectTaskService.create_project_task(
            project_code=DEFAULT_WORKFLOW_GAP_PROJECT_CODE,
            task_name=gap.title,
            user_id=int(gap.user_id or 0),
            responsible_name=None,
            due_date=None,
            description=_build_gap_task_how(
                request_text=gap.user_request_text,
                channel=gap.channel,
                company_id=gap.company_id,
                user_id=gap.user_id,
                thread_id=gap.thread_id,
                resolution_type=gap.resolution_type,
                telemetry=gap.telemetry,
            ),
            amount=None,
            status=DEFAULT_WORKFLOW_GAP_TASK_STATUS,
            stage=DEFAULT_WORKFLOW_GAP_TASK_STAGE,
            priority=DEFAULT_WORKFLOW_GAP_TASK_PRIORITY,
            notes=_build_gap_task_notes(
                request_text=gap.user_request_text,
                telemetry=gap.telemetry,
                response_text=response_text,
            ),
            allowed_company_ids=None,
        )
        if error:
            logger.warning("Nao foi possivel criar card inbox para workflow gap %s: %s", gap.id, error)
            return None
        if not result:
            return None
        task = result.get("task") if isinstance(result, dict) else None
        if task is None:
            logger.warning("Resultado de ProjectTaskService sem task para workflow gap %s", gap.id)
            return None
        return task




def serialize_workflow_gap_candidate(candidate: Any) -> Dict[str, Any]:
    telemetry = dict(getattr(candidate, "telemetry", None) or {})
    return {
        "id": getattr(candidate, "id", None),
        "company_id": getattr(candidate, "company_id", None),
        "user_id": getattr(candidate, "user_id", None),
        "channel": getattr(candidate, "channel", None),
        "thread_id": getattr(candidate, "thread_id", None),
        "source": getattr(candidate, "source", None),
        "status": getattr(candidate, "status", None),
        "resolution_type": getattr(candidate, "resolution_type", None),
        "title": getattr(candidate, "title", None),
        "user_request_text": getattr(candidate, "user_request_text", None),
        "normalized_intent": getattr(candidate, "normalized_intent", None),
        "suggested_flow_name": getattr(candidate, "suggested_flow_name", None),
        "business_outcome": getattr(candidate, "business_outcome", None),
        "matched_workflow_codes": list(getattr(candidate, "matched_workflow_codes", None) or []),
        "telemetry": telemetry,
        "app_card": {
            "project_id": getattr(candidate, "app_project_id", None),
            "task_id": getattr(candidate, "app_task_id", None),
            "task_code": getattr(candidate, "app_task_code", None),
        },
        "created_at": getattr(candidate, "created_at", None).isoformat() if getattr(candidate, "created_at", None) else None,
        "updated_at": getattr(candidate, "updated_at", None).isoformat() if getattr(candidate, "updated_at", None) else None,
    }

def capture_workflow_gap(**kwargs: Any) -> Optional[WorkflowGapCandidate]:
    return WorkflowGapService.create_gap_candidate(**kwargs)
