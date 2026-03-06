from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .common import positive_int_list


class SummaryExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_company_id: int
    employee_ids: List[int] = Field(min_length=1)
    start_date: date
    end_date: date
    status: Literal["open", "completed", "all"] = "open"
    all_collaborators: bool = False

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
        *,
        resolve_period_from_payload: Callable[[Dict[str, Any]], Tuple[Optional[date], Optional[date]]],
    ) -> Tuple[Optional["SummaryExecutionInput"], Optional[str]]:
        selected_company_id = cls._extract_selected_company_id(payload)
        if not selected_company_id:
            return None, "Nao consegui identificar a empresa selecionada para o resumo."

        start_date, end_date = resolve_period_from_payload(dict(payload or {}))
        if not start_date or not end_date:
            return None, (
                "Nao consegui identificar o periodo do resumo.\n"
                "Use o formato: DD/MM/AAAA a DD/MM/AAAA."
            )

        employee_ids = cls._extract_selected_employee_ids(payload)
        if not employee_ids:
            return None, "Nao consegui identificar o colaborador selecionado."

        status = str(payload.get("_summary_status") or "open").strip().lower() or "open"
        if status not in {"open", "completed", "all"}:
            return None, "Status invalido para resumo. Use: abertas, concluidas ou todas."

        return cls(
            selected_company_id=selected_company_id,
            employee_ids=employee_ids,
            start_date=start_date,
            end_date=end_date,
            status=status,
            all_collaborators=bool(payload.get("_summary_all_collaborators")),
        ), None

    @staticmethod
    def _extract_selected_company_id(payload: Dict[str, Any]) -> Optional[int]:
        try:
            company_id = int(payload.get("_summary_company_id"))
        except (TypeError, ValueError):
            return None
        return company_id if company_id > 0 else None

    @staticmethod
    def _extract_selected_employee_ids(payload: Dict[str, Any]) -> List[int]:
        employee_ids = positive_int_list(payload.get("_summary_employee_ids"))
        if employee_ids:
            return employee_ids
        return positive_int_list(payload.get("_summary_employee_id"))
