from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import MyWorkExecutionInput


class MyWorkExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class MyWorkExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class MyWorkExecutionHandler:
    def __init__(
        self,
        *,
        resolve_company_ids_for_payload: Callable[[Dict[str, Any], Optional[int], int], Tuple[List[int], str]],
        resolve_period_from_payload: Callable[[Dict[str, Any]], Tuple[Optional[date], Optional[date]]],
        load_project_tasks_report: Callable[..., List[Dict[str, Any]]],
        load_process_instances_report: Callable[..., List[Dict[str, Any]]],
        load_meetings_report: Callable[..., List[Dict[str, Any]]],
        format_my_work_report: Callable[..., str],
    ):
        self._resolve_company_ids_for_payload = resolve_company_ids_for_payload
        self._resolve_period_from_payload = resolve_period_from_payload
        self._load_project_tasks_report = load_project_tasks_report
        self._load_process_instances_report = load_process_instances_report
        self._load_meetings_report = load_meetings_report
        self._format_my_work_report = format_my_work_report

    def execute(self, request: MyWorkExecutionRequest) -> MyWorkExecutionResult:
        execution_input, input_error = MyWorkExecutionInput.build_from_action(request.action)
        if input_error:
            return MyWorkExecutionResult(response_text=input_error)
        if not execution_input:
            return MyWorkExecutionResult(
                response_text="Nao consegui interpretar a acao de consulta."
            )

        payload = dict(request.payload or {})
        company_ids, company_label_or_error = self._resolve_company_ids_for_payload(
            payload=payload,
            active_company_id=request.active_company_id,
            user_id=request.user_id,
        )
        if not company_ids:
            return MyWorkExecutionResult(
                response_text=company_label_or_error or "Nao foi possivel identificar a empresa para consulta."
            )

        start_date = None
        end_date = None
        if execution_input.requires_period:
            start_date, end_date = self._resolve_period_from_payload(payload)
            if not start_date or not end_date:
                return MyWorkExecutionResult(
                    response_text=(
                        "Para esta consulta, informe o periodo no formato:\n"
                        "periodo: 01/03/2026 a 07/03/2026\n"
                        "ou use periodos relativos: hoje | esta semana | este mes | proximos 15 dias"
                    )
                )

        tasks = self._load_project_tasks_report(
            company_ids=company_ids,
            mode=execution_input.action,
            start_date=start_date,
            end_date=end_date,
        )
        processes = self._load_process_instances_report(
            company_ids=company_ids,
            mode=execution_input.action,
            start_date=start_date,
            end_date=end_date,
        )
        meetings = self._load_meetings_report(
            company_ids=company_ids,
            mode=execution_input.action,
            start_date=start_date,
            end_date=end_date,
        )

        return MyWorkExecutionResult(
            response_text=self._format_my_work_report(
                action=execution_input.action,
                company_label=company_label_or_error,
                tasks=tasks,
                processes=processes,
                meetings=meetings,
                start_date=start_date,
                end_date=end_date,
                channel=request.channel,
                payload=payload,
                user_id=request.user_id,
            )
        )
