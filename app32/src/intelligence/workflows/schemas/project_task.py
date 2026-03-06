from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .common import coalesce_str


class ProjectTaskCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_code: str
    task_name: str
    responsible_name: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[str] = None
    status: str = "planned"
    stage: str = "inbox"
    priority: str = "normal"
    notes: Optional[str] = None

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["ProjectTaskCreateInput"], Optional[str]]:
        project_code = coalesce_str(payload, "codigo_projeto", "project_code", "codigo")
        if not project_code:
            return None, "Nao encontrei o codigo do projeto. Informe no formato: codigo_projeto: AA.J.12"

        task_name = coalesce_str(
            payload,
            "nome_atividade",
            "atividade",
            "task_name",
            "what",
            "titulo",
        )
        if not task_name:
            return None, "Nao encontrei o nome da atividade. Informe no formato: nome_atividade: Nome da Atividade"

        return cls(
            project_code=project_code,
            task_name=task_name,
            responsible_name=coalesce_str(payload, "responsavel", "who"),
            due_date=coalesce_str(payload, "prazo", "due_date", "data_limite"),
            description=coalesce_str(payload, "como", "descricao", "description"),
            amount=coalesce_str(payload, "valor", "amount"),
            status=coalesce_str(payload, "status") or "planned",
            stage=coalesce_str(payload, "etapa", "stage") or "inbox",
            priority=coalesce_str(payload, "prioridade", "priority") or "normal",
            notes=coalesce_str(payload, "observacoes", "notes"),
        ), None


class ProjectTaskCompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_code: str
    completion_date_raw: Optional[str] = None

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["ProjectTaskCompleteInput"], Optional[str]]:
        activity_code = coalesce_str(
            payload,
            "codigo_atividade",
            "activity_code",
            "task_code",
            "codigo",
        )
        if not activity_code:
            return None, "Nao encontrei o codigo da atividade. Informe no formato: codigo_atividade: AA.J.26.175"

        return cls(
            activity_code=activity_code,
            completion_date_raw=coalesce_str(payload, "completion_date", "data_finalizacao"),
        ), None
