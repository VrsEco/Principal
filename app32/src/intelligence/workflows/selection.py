from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .schemas import AssistedSelectionContext
from .session import WorkflowSessionState


SELECTION_ROUTE_SKIP = "skip"
SELECTION_ROUTE_ERROR = "error"
SELECTION_ROUTE_ADVANCE = "advance"
SELECTION_ROUTE_CONFIRM = "confirm"


class SelectionRouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handled: bool
    route: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    response_text: Optional[str] = None


class AssistedSelectionCoordinator:
    def __init__(
        self,
        *,
        extract_fields_from_text: Callable[[str], Dict[str, str]],
        parse_selection_number_date: Callable[[str], Optional[tuple[int, Optional[str]]]],
        parse_completion_date: Callable[[str], Any],
        public_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self._extract_fields_from_text = extract_fields_from_text
        self._parse_selection_number_date = parse_selection_number_date
        self._parse_completion_date = parse_completion_date
        self._public_payload = public_payload

    def handle_reply(
        self,
        state: WorkflowSessionState,
        *,
        text: str,
    ) -> SelectionRouteDecision:
        payload = dict(state.payload or {})
        context = AssistedSelectionContext.build_from_payload(payload)
        direct_fields = self._extract_fields_from_text(text)

        direct_route = self._handle_direct_field_shortcuts(
            payload=payload,
            context=context,
            direct_fields=direct_fields,
        )
        if direct_route is not None:
            return direct_route

        parsed = self._parse_selection_number_date(text)
        if not parsed:
            return SelectionRouteDecision(
                handled=True,
                route=SELECTION_ROUTE_ERROR,
                payload=payload,
                response_text=self._build_invalid_selection_message(context),
            )

        choice_index, date_raw = parsed
        selected = self._find_choice_by_index(context.choices, choice_index)
        if not selected:
            return SelectionRouteDecision(
                handled=True,
                route=SELECTION_ROUTE_ERROR,
                payload=payload,
                response_text="Indice nao encontrado na lista. Informe um numero valido conforme as opcoes exibidas.",
            )

        date_iso, error = self._resolve_completion_date_iso(context, date_raw)
        if error:
            return SelectionRouteDecision(
                handled=True,
                route=SELECTION_ROUTE_ERROR,
                payload=payload,
                response_text=error,
            )

        merged = self._public_payload(payload)
        if context.selection_kind == "project_picker":
            merged[context.selection_field_key or "codigo_projeto"] = (
                selected.get(context.selection_value_key) or selected.get("code")
            )
            return SelectionRouteDecision(
                handled=True,
                route=SELECTION_ROUTE_ADVANCE,
                payload=merged,
            )

        if context.selection_action == "project_task.complete":
            merged["codigo_atividade"] = selected.get("code")
        elif context.selection_action == "process_instance.complete":
            merged["codigo_instancia"] = selected.get("code")
        elif context.selection_action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}:
            merged["id_reuniao"] = str(selected.get("id") or selected.get("code") or "")
        elif context.selection_action == "onboarding.diagnose":
            merged["objetivo"] = str(selected.get("objective") or selected.get("code") or "")
        else:
            merged["codigo"] = selected.get("code")

        if date_iso:
            merged["data_finalizacao"] = date_iso

        return SelectionRouteDecision(
            handled=True,
            route=SELECTION_ROUTE_CONFIRM,
            payload=merged,
        )

    def _handle_direct_field_shortcuts(
        self,
        *,
        payload: Dict[str, Any],
        context: AssistedSelectionContext,
        direct_fields: Dict[str, str],
    ) -> Optional[SelectionRouteDecision]:
        if context.selection_kind == "project_picker" and context.selection_field_key:
            project_value = (
                direct_fields.get(context.selection_field_key)
                or direct_fields.get("project_code")
                or direct_fields.get("codigo")
            )
            if project_value:
                merged = self._public_payload(payload)
                merged[context.selection_field_key] = str(project_value).strip()
                for key, value in direct_fields.items():
                    if key in {context.selection_field_key, "project_code", "codigo"}:
                        continue
                    merged[key] = value
                return SelectionRouteDecision(
                    handled=True,
                    route=SELECTION_ROUTE_ADVANCE,
                    payload=merged,
                )

        if context.selection_action == "project_task.complete" and "codigo_atividade" in direct_fields:
            merged = self._public_payload(payload)
            merged.update(direct_fields)
            return SelectionRouteDecision(handled=True, route=SELECTION_ROUTE_CONFIRM, payload=merged)

        if context.selection_action == "process_instance.complete" and "codigo_instancia" in direct_fields:
            merged = self._public_payload(payload)
            merged.update(direct_fields)
            return SelectionRouteDecision(handled=True, route=SELECTION_ROUTE_CONFIRM, payload=merged)

        if context.selection_action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"} and any(
            key in direct_fields for key in ("id_reuniao", "meeting_id", "codigo_reuniao", "codigo")
        ):
            merged = self._public_payload(payload)
            meeting_value = (
                direct_fields.get("id_reuniao")
                or direct_fields.get("meeting_id")
                or direct_fields.get("codigo_reuniao")
                or direct_fields.get("codigo")
            )
            merged["id_reuniao"] = str(meeting_value).strip()
            for key, value in direct_fields.items():
                if key in {"id_reuniao", "meeting_id", "codigo_reuniao", "codigo"}:
                    continue
                merged[key] = value
            return SelectionRouteDecision(handled=True, route=SELECTION_ROUTE_CONFIRM, payload=merged)

        if context.selection_action == "onboarding.diagnose" and any(
            key in direct_fields for key in ("objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento")
        ):
            merged = self._public_payload(payload)
            objective_value = (
                direct_fields.get("objetivo")
                or direct_fields.get("o_que_quer_funcionar")
                or direct_fields.get("objetivo_de_funcionamento")
            )
            merged["objetivo"] = str(objective_value).strip()
            for key, value in direct_fields.items():
                if key in {"objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento"}:
                    continue
                merged[key] = value
            return SelectionRouteDecision(handled=True, route=SELECTION_ROUTE_CONFIRM, payload=merged)

        return None

    def _build_invalid_selection_message(self, context: AssistedSelectionContext) -> str:
        if context.selection_kind == "project_picker":
            return (
                "Formato invalido. Informe apenas o numero do projeto (ex: 1).\n"
                "Se preferir, envie o codigo diretamente no formato codigo_projeto: AA.J.12."
            )
        if context.selection_action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp", "onboarding.diagnose"}:
            return (
                "Formato invalido. Informe apenas o numero da opcao (ex: 1).\n"
                "Se quiser, voce tambem pode enviar o ID diretamente no formato campo: valor."
            )
        return (
            "Formato invalido. Informe no formato numero: data (ex: 1: 27/02/2026).\n"
            "Se quiser, voce tambem pode enviar o codigo diretamente no formato campo: valor."
        )

    def _find_choice_by_index(
        self,
        choices: List[Dict[str, Any]],
        choice_index: int,
    ) -> Optional[Dict[str, Any]]:
        for item in choices or []:
            try:
                item_index = int(item.get("index", -1))
            except (TypeError, ValueError):
                continue
            if item_index == int(choice_index):
                return item
        return None

    def _resolve_completion_date_iso(
        self,
        context: AssistedSelectionContext,
        date_raw: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        if not date_raw:
            return None, None
        if context.selection_kind == "project_picker":
            return None, (
                "Formato invalido. Informe apenas o numero do projeto (ex: 1).\n"
                "Se preferir, envie o codigo diretamente no formato codigo_projeto: AA.J.12."
            )

        parsed_date = self._parse_completion_date(date_raw)
        if not parsed_date:
            return None, "Data invalida. Use DD/MM/AAAA ou AAAA-MM-DD."
        return parsed_date.isoformat(), None


def build_assisted_selection_payload(
    base_payload: Dict[str, Any],
    *,
    selection_action: str,
    selection: Dict[str, Any],
    selection_kind: Optional[str] = None,
    selection_field_key: Optional[str] = None,
    selection_value_key: Optional[str] = None,
) -> Dict[str, Any]:
    payload = dict(base_payload or {})
    payload["_selection_action"] = str(selection_action or "").strip().lower()
    effective_selection_kind = selection_kind or selection.get("selection_kind")
    if effective_selection_kind:
        payload["_selection_kind"] = str(effective_selection_kind).strip().lower()
    effective_field_key = selection_field_key or selection.get("field_key")
    if effective_field_key:
        payload["_selection_field_key"] = str(effective_field_key).strip().lower()
    effective_value_key = selection_value_key or selection.get("value_key") or "code"
    payload["_selection_value_key"] = str(effective_value_key).strip() or "code"
    payload["_choices"] = list(selection.get("choices") or [])
    payload["_scope_label"] = selection.get("scope_label")
    payload["_item_label_plural"] = selection.get("item_label_plural")
    return payload
