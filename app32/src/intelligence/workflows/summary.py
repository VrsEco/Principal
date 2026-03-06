from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .session import WorkflowSessionState


SUMMARY_STATUS_AWAITING_DATES = "awaiting_summary_dates"
SUMMARY_STATUS_AWAITING_COMPANY = "awaiting_summary_company"
SUMMARY_STATUS_AWAITING_COLLABORATOR = "awaiting_summary_collaborator"
SUMMARY_STATUS_AWAITING_STATUS = "awaiting_summary_status"

SUMMARY_WIZARD_STATUSES = {
    SUMMARY_STATUS_AWAITING_DATES,
    SUMMARY_STATUS_AWAITING_COMPANY,
    SUMMARY_STATUS_AWAITING_COLLABORATOR,
    SUMMARY_STATUS_AWAITING_STATUS,
}

SUMMARY_ACTION_PERIOD_MAP = {
    "summary.today": "today",
    "summary.week": "week",
    "summary.month": "month",
    "summary.custom": "custom",
}

SUMMARY_ROUTE_SKIP = "skip"
SUMMARY_ROUTE_ERROR = "error"
SUMMARY_ROUTE_RESET = "reset"
SUMMARY_ROUTE_PROMPT_DATES = "prompt_dates"
SUMMARY_ROUTE_PROMPT_COMPANY = "prompt_company"
SUMMARY_ROUTE_PROMPT_COLLABORATOR = "prompt_collaborator"
SUMMARY_ROUTE_PROMPT_STATUS = "prompt_status"
SUMMARY_ROUTE_EMAIL_CONFIRMATION = "email_confirmation"
SUMMARY_ROUTE_COMPLETED = "completed"


class SummaryRouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handled: bool
    route: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = None
    response_text: Optional[str] = None
    report_text: Optional[str] = None


class SummaryWorkflowCoordinator:
    def __init__(
        self,
        *,
        resolve_period_from_payload: Callable[[Dict[str, Any]], Tuple[Optional[date], Optional[date]]],
        apply_preselected_summary_company_selection: Optional[Callable[..., Optional[Dict[str, Any]]]] = None,
        apply_single_summary_company_selection: Optional[
            Callable[[Dict[str, Any], List[Dict[str, Any]]], Optional[Dict[str, Any]]]
        ] = None,
        load_summary_company_choices: Optional[Callable[[int], List[Dict[str, Any]]]] = None,
        load_summary_collaborator_choices: Optional[Callable[[int], List[Dict[str, Any]]]] = None,
        summary_status_choices: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        user_can_access_company: Optional[Callable[[int, int], bool]] = None,
        execute_summary_menu_report: Optional[Callable[..., str]] = None,
        format_summary_collaborator_selection_label: Optional[Callable[[Sequence[str], bool], str]] = None,
    ):
        self._resolve_period_from_payload = resolve_period_from_payload
        self._apply_preselected_summary_company_selection = (
            apply_preselected_summary_company_selection
            or (lambda **kwargs: None)
        )
        self._apply_single_summary_company_selection = (
            apply_single_summary_company_selection
            or (lambda payload, choices: None)
        )
        self._load_summary_company_choices = load_summary_company_choices or (
            lambda user_id: [
                {
                    "index": 1,
                    "company_id": 1,
                    "company_name": "Empresa",
                    "company_code": "",
                    "label": "Empresa",
                }
            ]
        )
        self._load_summary_collaborator_choices = (
            load_summary_collaborator_choices
            or (
                lambda company_id: [
                    {
                        "index": 1,
                        "employee_id": 1,
                        "name": "Colaborador",
                    }
                ]
            )
        )
        self._summary_status_choices = summary_status_choices or (lambda: [])
        self._user_can_access_company = user_can_access_company or (lambda user_id, company_id: True)
        self._execute_summary_menu_report = execute_summary_menu_report or (lambda **kwargs: "")
        self._format_summary_collaborator_selection_label = (
            format_summary_collaborator_selection_label
            or (
                lambda employee_names, all_selected=False: (
                    "Todos"
                    if all_selected
                    else ", ".join(
                        str(name).strip()
                        for name in employee_names
                        if str(name).strip()
                    )
                )
            )
        )

    def is_summary_workflow(self, action_key: Optional[str]) -> bool:
        return str(action_key or "").strip().lower() in SUMMARY_ACTION_PERIOD_MAP

    def prepare_initial_step(self, state: WorkflowSessionState) -> SummaryRouteDecision:
        action_key = str(state.workflow_action_key or "").strip().lower()
        period_kind = SUMMARY_ACTION_PERIOD_MAP.get(action_key)
        if not period_kind:
            return SummaryRouteDecision(handled=False, route=SUMMARY_ROUTE_SKIP)

        payload = dict(state.payload or {})
        payload["_summary_action"] = action_key

        if period_kind == "today":
            payload["periodo"] = "hoje"
        elif period_kind == "week":
            payload["periodo"] = "esta semana"
        elif period_kind == "month":
            payload["periodo"] = "este mes"
        else:
            start_date, end_date = self._resolve_period_from_payload(payload)
            if not start_date or not end_date:
                return SummaryRouteDecision(
                    handled=True,
                    route=SUMMARY_ROUTE_PROMPT_DATES,
                    status=SUMMARY_STATUS_AWAITING_DATES,
                    payload=payload,
                )
            payload["periodo"] = (
                f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
            )

        return self.prepare_company_prompt(state.with_payload(payload))

    def advance_custom_period(
        self,
        state: WorkflowSessionState,
        *,
        payload: Dict[str, Any],
    ) -> SummaryRouteDecision:
        action_key = str(state.workflow_action_key or "").strip().lower()
        if SUMMARY_ACTION_PERIOD_MAP.get(action_key) != "custom":
            return SummaryRouteDecision(handled=False, route=SUMMARY_ROUTE_SKIP)

        next_payload = dict(payload or {})
        start_date, end_date = self._resolve_period_from_payload(next_payload)
        if not start_date or not end_date:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_DATES,
                payload=next_payload,
                response_text=(
                    "Periodo invalido. Informe no formato:\n"
                    "DD/MM/AAAA a DD/MM/AAAA\n"
                    "Exemplo: 01/03/2026 a 31/03/2026"
                ),
            )

        next_payload["data_inicial"] = start_date.isoformat()
        next_payload["data_final"] = end_date.isoformat()
        next_payload["periodo"] = (
            f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        )

        return self.prepare_company_prompt(state.with_payload(next_payload))

    def prepare_company_prompt(self, state: WorkflowSessionState) -> SummaryRouteDecision:
        payload = dict(state.payload or {})
        choices = self._load_summary_company_choices(state.user_id)
        if not choices:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_RESET,
                payload=payload,
                response_text="Nenhuma empresa vinculada foi encontrada para gerar o resumo.",
            )

        payload["_summary_company_choices"] = choices

        explicit_selected_payload = self._apply_preselected_summary_company_selection(
            payload=payload,
            user_id=state.user_id,
            choices=choices,
        )
        if explicit_selected_payload is not None:
            return self.prepare_collaborator_prompt(state.with_payload(explicit_selected_payload))

        auto_selected_payload = self._apply_single_summary_company_selection(
            payload=payload,
            choices=choices,
        )
        if auto_selected_payload is not None:
            return self.prepare_collaborator_prompt(state.with_payload(auto_selected_payload))

        return SummaryRouteDecision(
            handled=True,
            route=SUMMARY_ROUTE_PROMPT_COMPANY,
            status=SUMMARY_STATUS_AWAITING_COMPANY,
            payload=payload,
        )

    def select_company(
        self,
        state: WorkflowSessionState,
        *,
        selected_index: Optional[int],
    ) -> SummaryRouteDecision:
        if selected_index is None:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_COMPANY,
                payload=dict(state.payload or {}),
                response_text="Formato invalido. Responda apenas com o numero da empresa. Exemplo: 1",
            )

        payload = dict(state.payload or {})
        choices = payload.get("_summary_company_choices") or []
        selected = next(
            (item for item in choices if int(item.get("index", -1)) == int(selected_index)),
            None,
        )
        if not selected:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_COMPANY,
                payload=payload,
                response_text="Indice de empresa invalido. Escolha uma opcao da lista.",
            )

        company_id = int(selected.get("company_id"))
        if not self._user_can_access_company(state.user_id, company_id):
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_RESET,
                payload=payload,
                response_text="Voce nao possui acesso a empresa selecionada.",
            )

        payload["_summary_company_id"] = company_id
        payload["_summary_company_label"] = selected.get("label")
        payload["empresa"] = selected.get("company_name")

        return self.prepare_collaborator_prompt(state.with_payload(payload))

    def prepare_collaborator_prompt(self, state: WorkflowSessionState) -> SummaryRouteDecision:
        payload = dict(state.payload or {})
        company_id = payload.get("_summary_company_id")
        if not company_id:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_RESET,
                payload=payload,
                response_text=(
                    "Nao consegui identificar a empresa selecionada. "
                    "Digite 'menu' e tente novamente."
                ),
            )

        choices = self._load_summary_collaborator_choices(int(company_id))
        if not choices:
            company_choices = payload.get("_summary_company_choices") or self._load_summary_company_choices(state.user_id)
            payload["_summary_company_choices"] = company_choices
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_PROMPT_COMPANY,
                status=SUMMARY_STATUS_AWAITING_COMPANY,
                payload=payload,
                response_text="Nao encontrei colaboradores ativos na empresa selecionada. Escolha outra empresa:",
            )

        payload["_summary_collaborator_choices"] = choices
        return SummaryRouteDecision(
            handled=True,
            route=SUMMARY_ROUTE_PROMPT_COLLABORATOR,
            status=SUMMARY_STATUS_AWAITING_COLLABORATOR,
            payload=payload,
        )

    def select_collaborators(
        self,
        state: WorkflowSessionState,
        *,
        selected_indexes: List[int],
    ) -> SummaryRouteDecision:
        if not selected_indexes:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_COLLABORATOR,
                payload=dict(state.payload or {}),
                response_text=(
                    "Formato invalido. Responda com 0 (todos), um numero (ex: 1) "
                    "ou varios numeros (ex: 1,3,4)."
                ),
            )

        payload = dict(state.payload or {})
        choices = payload.get("_summary_collaborator_choices") or []
        if not choices:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_COLLABORATOR,
                payload=payload,
                response_text="Nao encontrei colaboradores para esta empresa. Escolha outra empresa.",
            )

        by_index = {
            int(item.get("index", -1)): item
            for item in choices
            if item.get("index") is not None
        }
        select_all = 0 in selected_indexes
        if select_all:
            selected_items = list(choices)
        else:
            invalid = [idx for idx in selected_indexes if idx not in by_index]
            if invalid:
                invalid_list = ", ".join(str(v) for v in invalid)
                return SummaryRouteDecision(
                    handled=True,
                    route=SUMMARY_ROUTE_ERROR,
                    status=SUMMARY_STATUS_AWAITING_COLLABORATOR,
                    payload=payload,
                    response_text=(
                        f"Indice de colaborador invalido ({invalid_list}). "
                        "Escolha opcao(oes) da lista."
                    ),
                )
            selected_items = [by_index[idx] for idx in selected_indexes]

        employee_ids = [
            int(item.get("employee_id"))
            for item in selected_items
            if item.get("employee_id") is not None
        ]
        employee_names = [
            str(item.get("name") or "").strip()
            for item in selected_items
            if str(item.get("name") or "").strip()
        ]
        if not employee_ids:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_COLLABORATOR,
                payload=payload,
                response_text=(
                    "Nao consegui identificar colaboradores validos para o filtro informado."
                ),
            )

        payload["_summary_all_collaborators"] = bool(select_all)
        payload["_summary_employee_ids"] = employee_ids
        payload["_summary_employee_names"] = employee_names
        payload["_summary_employee_id"] = int(employee_ids[0])
        payload["_summary_employee_name"] = self._format_summary_collaborator_selection_label(
            employee_names,
            all_selected=bool(select_all),
        )
        payload["colaborador"] = payload["_summary_employee_name"]

        return self.prepare_status_prompt(state.with_payload(payload))

    def prepare_status_prompt(self, state: WorkflowSessionState) -> SummaryRouteDecision:
        payload = dict(state.payload or {})
        payload["_summary_status_choices"] = self._summary_status_choices()
        return SummaryRouteDecision(
            handled=True,
            route=SUMMARY_ROUTE_PROMPT_STATUS,
            status=SUMMARY_STATUS_AWAITING_STATUS,
            payload=payload,
        )

    def select_status(
        self,
        state: WorkflowSessionState,
        *,
        selected_index: Optional[int],
    ) -> SummaryRouteDecision:
        if selected_index is None:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_STATUS,
                payload=dict(state.payload or {}),
                response_text="Formato invalido. Responda apenas com o numero do status. Exemplo: 1",
            )

        payload = dict(state.payload or {})
        choices = payload.get("_summary_status_choices") or self._summary_status_choices()
        selected = next(
            (item for item in choices if int(item.get("index", -1)) == int(selected_index)),
            None,
        )
        if not selected:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_ERROR,
                status=SUMMARY_STATUS_AWAITING_STATUS,
                payload=payload,
                response_text="Indice de status invalido. Escolha uma opcao da lista.",
            )

        payload["_summary_status"] = selected.get("key")
        payload["status"] = selected.get("label")

        try:
            report = self._execute_summary_menu_report(
                payload=payload,
                active_company_id=state.company_id,
                user_id=state.user_id,
                channel=state.channel or "web",
            )
        except Exception as exc:
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_RESET,
                payload=payload,
                response_text=f"Nao consegui gerar o resumo agora: {str(exc)}",
            )

        normalized_channel = str(state.channel or "").strip().lower()
        if normalized_channel in {"telegram", "whatsapp"}:
            payload["_summary_report_text"] = report
            return SummaryRouteDecision(
                handled=True,
                route=SUMMARY_ROUTE_EMAIL_CONFIRMATION,
                status="awaiting_summary_email_confirmation",
                payload=payload,
                report_text=report,
            )

        return SummaryRouteDecision(
            handled=True,
            route=SUMMARY_ROUTE_COMPLETED,
            payload=payload,
            report_text=report,
        )
