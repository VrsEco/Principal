from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import SummaryExecutionInput


class SummaryExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class SummaryExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_text: str


class SummaryWorkflowExecutionHandler:
    def __init__(
        self,
        *,
        user_can_access_company: Callable[[int, int], bool],
        load_company_by_id: Callable[[int], Any],
        resolve_period_from_payload: Callable[[Dict[str, Any]], Tuple[Optional[date], Optional[date]]],
        load_employee_rows: Callable[[int, List[int]], Sequence[Any]],
        format_summary_collaborator_selection_label: Callable[[List[str], bool], str],
        load_project_tasks_report: Callable[..., List[Dict[str, Any]]],
        load_process_instances_report: Callable[..., List[Dict[str, Any]]],
        load_meetings_report: Callable[..., List[Dict[str, Any]]],
        merge_report_items: Callable[[List[Dict[str, Any]], str], List[Dict[str, Any]]],
        format_my_work_report: Callable[..., str],
    ):
        self._user_can_access_company = user_can_access_company
        self._load_company_by_id = load_company_by_id
        self._resolve_period_from_payload = resolve_period_from_payload
        self._load_employee_rows = load_employee_rows
        self._format_summary_collaborator_selection_label = (
            format_summary_collaborator_selection_label
        )
        self._load_project_tasks_report = load_project_tasks_report
        self._load_process_instances_report = load_process_instances_report
        self._load_meetings_report = load_meetings_report
        self._merge_report_items = merge_report_items
        self._format_my_work_report = format_my_work_report

    def execute(self, request: SummaryExecutionRequest) -> SummaryExecutionResult:
        payload = dict(request.payload or {})

        execution_input, input_error = SummaryExecutionInput.build_from_legacy_payload(
            payload,
            resolve_period_from_payload=self._resolve_period_from_payload,
        )
        if input_error:
            return SummaryExecutionResult(report_text=input_error)

        if not execution_input:
            return SummaryExecutionResult(
                report_text="Nao consegui interpretar o payload do resumo."
            )

        if not self._user_can_access_company(request.user_id, execution_input.selected_company_id):
            return SummaryExecutionResult(
                report_text="Voce nao possui acesso a empresa selecionada."
            )

        company = self._load_company_by_id(execution_input.selected_company_id)
        if not company:
            return SummaryExecutionResult(
                report_text="Empresa selecionada nao encontrada."
            )

        employee_ids = list(execution_input.employee_ids)
        start_date = execution_input.start_date
        end_date = execution_input.end_date

        employee_rows = list(self._load_employee_rows(execution_input.selected_company_id, employee_ids) or [])
        if not employee_rows:
            return SummaryExecutionResult(
                report_text="Colaborador selecionado nao pertence a empresa escolhida."
            )

        employees_by_id = {
            int(getattr(employee, "id")): employee
            for employee in employee_rows
            if getattr(employee, "id", None) is not None
        }
        missing_ids = [employee_id for employee_id in employee_ids if employee_id not in employees_by_id]
        if missing_ids:
            return SummaryExecutionResult(
                report_text="Colaborador selecionado nao pertence a empresa escolhida."
            )

        collaborator_terms: List[str] = []
        employee_names: List[str] = []
        for employee_id in employee_ids:
            employee = employees_by_id.get(employee_id)
            if not employee:
                continue
            employee_name = str(getattr(employee, "name", "") or "").strip()
            employee_email = str(getattr(employee, "email", "") or "").strip().lower()
            if employee_name:
                employee_names.append(employee_name)
                collaborator_terms.append(employee_name.lower())
            if employee_email:
                collaborator_terms.append(employee_email)

        normalized_payload = dict(payload)
        collaborator_label = self._format_summary_collaborator_selection_label(
            employee_names,
            all_selected=bool(execution_input.all_collaborators),
        )
        if collaborator_label:
            normalized_payload["colaborador"] = collaborator_label

        company_label = self._build_company_label(company)
        status_key = execution_input.status

        open_tasks = self._merge_report_items(
            self._load_project_tasks_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.overdue",
                start_date=start_date,
                end_date=end_date,
                employee_ids=employee_ids,
            )
            + self._load_project_tasks_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.due_range",
                start_date=start_date,
                end_date=end_date,
                employee_ids=employee_ids,
            ),
            unique_key="activity_code",
        )
        open_processes = self._merge_report_items(
            self._load_process_instances_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.overdue",
                start_date=start_date,
                end_date=end_date,
                employee_ids=employee_ids,
            )
            + self._load_process_instances_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.due_range",
                start_date=start_date,
                end_date=end_date,
                employee_ids=employee_ids,
            ),
            unique_key="instance_code",
        )
        open_meetings = self._merge_report_items(
            self._load_meetings_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.overdue",
                start_date=start_date,
                end_date=end_date,
                collaborator_terms=collaborator_terms,
            )
            + self._load_meetings_report(
                company_ids=[execution_input.selected_company_id],
                mode="my_work.due_range",
                start_date=start_date,
                end_date=end_date,
                collaborator_terms=collaborator_terms,
            ),
            unique_key="meeting_code",
        )

        completed_tasks = self._load_project_tasks_report(
            company_ids=[execution_input.selected_company_id],
            mode="my_work.completed_range",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        )
        completed_processes = self._load_process_instances_report(
            company_ids=[execution_input.selected_company_id],
            mode="my_work.completed_range",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        )
        completed_meetings = self._load_meetings_report(
            company_ids=[execution_input.selected_company_id],
            mode="my_work.completed_range",
            start_date=start_date,
            end_date=end_date,
            collaborator_terms=collaborator_terms,
        )

        open_report = self._format_my_work_report(
            action="my_work.due_range",
            company_label=company_label,
            tasks=open_tasks,
            processes=open_processes,
            meetings=open_meetings,
            start_date=start_date,
            end_date=end_date,
            channel=request.channel,
            payload=normalized_payload,
            user_id=request.user_id,
        )
        completed_report = self._format_my_work_report(
            action="my_work.completed_range",
            company_label=company_label,
            tasks=completed_tasks,
            processes=completed_processes,
            meetings=completed_meetings,
            start_date=start_date,
            end_date=end_date,
            channel=request.channel,
            payload=normalized_payload,
            user_id=request.user_id,
        )

        if status_key == "open":
            return SummaryExecutionResult(report_text=open_report)
        if status_key == "completed":
            return SummaryExecutionResult(report_text=completed_report)
        if status_key == "all":
            return SummaryExecutionResult(
                report_text=(
                    "STATUS: ABERTAS\n"
                    f"{open_report}\n\n"
                    "STATUS: CONCLUIDAS\n"
                    f"{completed_report}"
                )
            )

        return SummaryExecutionResult(
            report_text="Status invalido para resumo. Use: abertas, concluidas ou todas."
        )

    def _build_company_label(self, company: Any) -> str:
        company_code = str(getattr(company, "client_code", "") or "").strip()
        company_name = str(getattr(company, "name", "") or "").strip()
        if company_code:
            return f"empresa {company_code} - {company_name}"
        return f"empresa {company_name}"
