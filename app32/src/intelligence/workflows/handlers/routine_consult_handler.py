from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ...intents.schemas import OperationalIntentForm
from .my_work_handler import MyWorkExecutionRequest, MyWorkExecutionResult


class RoutineConsultExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class RoutineConsultExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class RoutineConsultExecutionHandler:
    def __init__(
        self,
        *,
        build_operational_form: Callable[
            [str, Dict[str, Any], Optional[int], str],
            Tuple[Optional[OperationalIntentForm], Optional[str]],
        ],
        execute_my_work: Callable[[MyWorkExecutionRequest], MyWorkExecutionResult],
    ):
        self._build_operational_form = build_operational_form
        self._execute_my_work = execute_my_work

    def execute(self, request: RoutineConsultExecutionRequest) -> RoutineConsultExecutionResult:
        payload = dict(request.payload or {})
        form, form_error = self._build_operational_form(
            request.action,
            payload,
            request.active_company_id,
            request.channel,
        )
        if form_error:
            return RoutineConsultExecutionResult(response_text=form_error)
        if form is not None:
            if form.resolution_scope.status == "missing_fields" and form.resolution_scope.missing_fields:
                missing_fields = ", ".join(form.resolution_scope.missing_fields)
                return RoutineConsultExecutionResult(
                    response_text=f"Formulario incompleto para a consulta de rotina. Campos faltantes: {missing_fields}"
                )
            payload = {**payload, **form.to_execution_payload()}

        my_work_action = self._resolve_consult_action(payload, form=form)
        result = self._execute_my_work(
            MyWorkExecutionRequest(
                action=my_work_action,
                payload=payload,
                active_company_id=request.active_company_id,
                user_id=request.user_id,
                channel=request.channel,
            )
        )
        return RoutineConsultExecutionResult(response_text=result.response_text)

    @staticmethod
    def _resolve_consult_action(
        payload: Dict[str, Any],
        *,
        form: Optional[OperationalIntentForm] = None,
    ) -> str:
        status_value = str(
            payload.get("status_consulta")
            or (form.filter_scope.status if form is not None else "")
            or ""
        ).strip().lower()
        has_period = bool(
            str(payload.get("periodo") or (form.filter_scope.period_label if form is not None else "") or "").strip()
            or str(payload.get("data_inicio") or payload.get("data_fim") or "").strip()
            or (
                form is not None
                and (str(form.filter_scope.start_date or "").strip() or str(form.filter_scope.end_date or "").strip())
            )
        )

        if status_value in {"completed", "concluido", "concluida", "concluidos", "concluidas"}:
            return "my_work.completed_range"
        if status_value in {"overdue", "vencido", "vencida", "vencidos", "vencidas", "atrasado", "atrasada"}:
            return "my_work.overdue"
        if has_period:
            return "my_work.due_range"
        return "my_work.open"
