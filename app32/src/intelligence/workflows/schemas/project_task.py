from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .common import coalesce_str, positive_int_list


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
    activity_codes: List[str] = Field(default_factory=list)
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
        raw_ids = positive_int_list(payload.get("ids"))
        if not raw_ids:
            explicit_ids_text = str(payload.get("ids") or "").strip()
            raw_ids = positive_int_list(re.findall(r"\d+", explicit_ids_text)) if explicit_ids_text else []

        if not activity_code:
            if raw_ids:
                activity_code = str(raw_ids[0])
            else:
                return None, "Nao encontrei o codigo da atividade. Informe no formato: codigo_atividade: AA.J.26.175"

        if raw_ids:
            activity_codes = [str(value) for value in raw_ids]
        elif activity_code:
            normalized_activity_code = str(activity_code or "").strip()
            if re.search(r"[A-Za-z]", normalized_activity_code) and "." in normalized_activity_code:
                activity_codes = [normalized_activity_code]
            else:
                extracted_codes = re.findall(r"\b\d+\b", normalized_activity_code)
                activity_codes = [code.strip() for code in extracted_codes if str(code or "").strip()] or [normalized_activity_code]

        return cls(
            activity_code=activity_code,
            activity_codes=activity_codes,
            completion_date_raw=coalesce_str(payload, "completion_date", "data_finalizacao"),
        ), None
