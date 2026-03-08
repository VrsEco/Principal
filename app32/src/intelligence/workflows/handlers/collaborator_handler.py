from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, Optional, Tuple

from ..schemas.collaborator import (
    CollaboratorOccupancyInput,
    CollaboratorOccupancyRequest,
    CollaboratorOccupancyResult,
)


class CollaboratorOccupancyExecutionHandler:
    def __init__(
        self,
        *,
        resolve_single_company_for_operation: Callable[[Dict[str, Any], Optional[int], int], Tuple[Optional[int], Optional[str]]],
        resolve_period_from_payload: Callable[[Dict[str, Any]], Tuple[Optional[date], Optional[date]]],
        resolve_employee_for_company: Callable[[int, str], Tuple[Optional[Any], Optional[str]]],
        calculate_available_hours: Callable[[Any, date, date], float],
        load_process_hours_taken: Callable[[Any, date, date], float],
        load_project_hours_taken: Callable[[Any, date, date], float],
        load_project_hours_committed: Callable[[Any, date, date], float],
        format_report: Callable[..., str],
    ):
        self._resolve_single_company_for_operation = resolve_single_company_for_operation
        self._resolve_period_from_payload = resolve_period_from_payload
        self._resolve_employee_for_company = resolve_employee_for_company
        self._calculate_available_hours = calculate_available_hours
        self._load_process_hours_taken = load_process_hours_taken
        self._load_project_hours_taken = load_project_hours_taken
        self._load_project_hours_committed = load_project_hours_committed
        self._format_report = format_report

    def execute(self, request: CollaboratorOccupancyRequest) -> CollaboratorOccupancyResult:
        _ = CollaboratorOccupancyInput()
        payload = dict(request.payload or {})

        company_id, company_error = self._resolve_single_company_for_operation(
            payload,
            request.active_company_id,
            request.user_id,
        )
        if company_error:
            return CollaboratorOccupancyResult(response_text=str(company_error))
        if not company_id:
            return CollaboratorOccupancyResult(response_text="Nao consegui identificar a empresa para analisar a ocupacao.")

        collaborator_term = str(
            payload.get("colaborador")
            or payload.get("colaborador_nome")
            or payload.get("usuario")
            or payload.get("usuario_nome")
            or ""
        ).strip()
        if not collaborator_term:
            return CollaboratorOccupancyResult(
                response_text=(
                    "Informe o colaborador no formato:\n"
                    "colaborador: NOME_DO_COLABORADOR"
                )
            )

        start_date, end_date = self._resolve_period_from_payload(payload)
        if not start_date or not end_date:
            return CollaboratorOccupancyResult(
                response_text=(
                    "Informe o periodo no formato:\n"
                    "periodo: 01/03/2026 a 07/03/2026\n"
                    "ou use periodos relativos: hoje | esta semana | este mes | proximos 15 dias"
                )
            )

        employee, employee_error = self._resolve_employee_for_company(company_id, collaborator_term)
        if employee_error:
            return CollaboratorOccupancyResult(response_text=str(employee_error))
        if employee is None:
            return CollaboratorOccupancyResult(
                response_text=f"Nao encontrei colaborador para '{collaborator_term}'."
            )

        available_hours = float(self._calculate_available_hours(employee, start_date, end_date) or 0.0)
        process_hours_taken = float(self._load_process_hours_taken(employee, start_date, end_date) or 0.0)
        project_hours_taken = float(self._load_project_hours_taken(employee, start_date, end_date) or 0.0)
        project_hours_committed = float(self._load_project_hours_committed(employee, start_date, end_date) or 0.0)

        return CollaboratorOccupancyResult(
            response_text=self._format_report(
                collaborator_name=str(getattr(employee, "name", "") or collaborator_term),
                company_label=str(payload.get("_selected_company_label") or payload.get("empresa") or f"empresa {company_id}"),
                start_date=start_date,
                end_date=end_date,
                available_hours=available_hours,
                process_hours_taken=process_hours_taken,
                project_hours_taken=project_hours_taken,
                project_hours_committed=project_hours_committed,
                channel=request.channel or "web",
            )
        )
