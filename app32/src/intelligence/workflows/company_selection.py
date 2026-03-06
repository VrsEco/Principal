from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from .schemas.company_selection import OperationCompanyChoice, OperationCompanySelectionContext
from .session import WorkflowSessionState

COMPANY_SELECTION_ROUTE_SKIP = "skip"
COMPANY_SELECTION_ROUTE_PROMPT = "prompt_selection"
COMPANY_SELECTION_ROUTE_ADVANCE = "advance"
COMPANY_SELECTION_ROUTE_ERROR = "error"


class CompanySelectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    choices: List[OperationCompanyChoice] = Field(default_factory=list)
    response_text: Optional[str] = None
    should_reset_session: bool = False


class OperationCompanySelectionCoordinator:
    def __init__(
        self,
        *,
        public_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
        summary_action_keys: Set[str],
    ):
        self._public_payload = public_payload
        self._summary_action_keys = {str(item or "").strip().lower() for item in summary_action_keys}

    def prepare_initial_selection(
        self,
        workflow_state: WorkflowSessionState,
        *,
        normalized_channel: str,
        explicit_company_id: Optional[int],
        choices: List[Dict[str, Any]],
    ) -> CompanySelectionDecision:
        action = str(workflow_state.workflow_action_key or "").strip().lower()
        if not action or normalized_channel == "web":
            return CompanySelectionDecision(route=COMPANY_SELECTION_ROUTE_SKIP)
        if explicit_company_id:
            return CompanySelectionDecision(route=COMPANY_SELECTION_ROUTE_SKIP)

        normalized_choices = self._normalize_choices(choices)
        if len(normalized_choices) <= 1:
            return CompanySelectionDecision(route=COMPANY_SELECTION_ROUTE_SKIP)

        payload = self._public_payload(workflow_state.payload or {})
        payload["_operation_company_choices"] = [choice.model_dump() for choice in normalized_choices]
        return CompanySelectionDecision(
            route=COMPANY_SELECTION_ROUTE_PROMPT,
            payload=payload,
            choices=normalized_choices,
        )

    def select_company(
        self,
        workflow_state: WorkflowSessionState,
        *,
        selected_index: Optional[int],
        user_can_access_company: Callable[[int, int], bool],
    ) -> CompanySelectionDecision:
        if selected_index is None:
            return CompanySelectionDecision(
                route=COMPANY_SELECTION_ROUTE_ERROR,
                response_text="Formato invalido. Responda apenas com o numero da empresa. Exemplo: 1",
            )

        context = OperationCompanySelectionContext.build_from_payload(workflow_state.payload)
        selected = next(
            (item for item in context.choices if int(item.index) == int(selected_index)),
            None,
        )
        if selected is None:
            return CompanySelectionDecision(
                route=COMPANY_SELECTION_ROUTE_ERROR,
                response_text="Indice de empresa invalido. Escolha uma opcao da lista.",
            )

        if not user_can_access_company(workflow_state.user_id, int(selected.company_id)):
            return CompanySelectionDecision(
                route=COMPANY_SELECTION_ROUTE_ERROR,
                response_text="Voce nao possui acesso a empresa selecionada.",
                should_reset_session=True,
            )

        payload = dict(workflow_state.payload or {})
        payload["empresa"] = selected.company_name
        payload["_selected_company_id"] = int(selected.company_id)
        payload["_selected_company_label"] = selected.label
        payload.pop("_operation_company_choices", None)

        action = str(workflow_state.workflow_action_key or "").strip().lower()
        if action in self._summary_action_keys:
            payload["_summary_company_id"] = int(selected.company_id)
            payload["_summary_company_label"] = selected.label

        return CompanySelectionDecision(
            route=COMPANY_SELECTION_ROUTE_ADVANCE,
            payload=payload,
        )

    @staticmethod
    def _normalize_choices(choices: List[Dict[str, Any]]) -> List[OperationCompanyChoice]:
        normalized: List[OperationCompanyChoice] = []
        for item in choices or []:
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(OperationCompanyChoice.model_validate(item))
            except Exception:
                continue
        return normalized
