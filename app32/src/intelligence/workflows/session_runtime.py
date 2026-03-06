from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def payload_without_navigation(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(payload or {})
    cleaned.pop("_nav_stack", None)
    return cleaned


def extract_navigation_stack(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = (payload or {}).get("_nav_stack")
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


class SessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    selected_option_id: Optional[int] = None
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[Dict[str, Any]] = Field(default_factory=list)


def build_session_snapshot(session: Any) -> Optional[SessionSnapshot]:
    if str(getattr(session, "status", "idle") or "idle") == "idle":
        return None

    return SessionSnapshot(
        status=str(getattr(session, "status", "idle") or "idle"),
        selected_option_id=getattr(session, "selected_option_id", None),
        collected_data=payload_without_navigation(getattr(session, "collected_data", {}) or {}),
        missing_fields=list(getattr(session, "missing_fields", []) or []),
    )


class SessionNavigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class SessionPromptRenderer:
    def __init__(
        self,
        *,
        render_root_menu: Callable[[Optional[int]], str],
        public_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
        render_confirmation: Callable[[Any, Dict[str, Any]], str],
        render_missing_fields: Callable[[Any, List[Dict[str, Any]], Dict[str, Any]], str],
        render_item_selection: Callable[[Any, Dict[str, Any]], str],
        render_operation_company: Callable[[Any, List[Dict[str, Any]]], str],
        render_summary_period: Callable[[Any], str],
        render_summary_company: Callable[[Any, List[Dict[str, Any]]], str],
        render_summary_collaborator: Callable[[Any, List[Dict[str, Any]]], str],
        render_summary_status: Callable[[Any, List[Dict[str, Any]]], str],
        summary_status_choices: Callable[[], List[Dict[str, Any]]],
        company_selection_status: str,
        summary_email_confirm_status: str,
        summary_email_custom_status: str,
        summary_email_offer_suffix: str,
        summary_email_custom_prompt: str = "Informe o e-mail de destino (ex: nome@empresa.com.br).",
        fallback_reset_prompt: str = "Sessao de menu reiniciada. Digite 'menu' para continuar.",
    ):
        self._render_root_menu = render_root_menu
        self._public_payload = public_payload
        self._render_confirmation = render_confirmation
        self._render_missing_fields = render_missing_fields
        self._render_item_selection = render_item_selection
        self._render_operation_company = render_operation_company
        self._render_summary_period = render_summary_period
        self._render_summary_company = render_summary_company
        self._render_summary_collaborator = render_summary_collaborator
        self._render_summary_status = render_summary_status
        self._summary_status_choices = summary_status_choices
        self._company_selection_status = company_selection_status
        self._summary_email_confirm_status = summary_email_confirm_status
        self._summary_email_custom_status = summary_email_custom_status
        self._summary_email_offer_suffix = summary_email_offer_suffix
        self._summary_email_custom_prompt = summary_email_custom_prompt
        self._fallback_reset_prompt = fallback_reset_prompt

    def render(self, session: Any) -> str:
        if str(getattr(session, "status", "idle") or "idle") == "idle":
            return self._render_root_menu(getattr(session, "company_id", None))

        option = getattr(session, "selected_option", None)
        if not option:
            return self._fallback_reset_prompt

        payload = dict(getattr(session, "collected_data", {}) or {})
        status = str(getattr(session, "status", "idle") or "idle")

        if status == "awaiting_confirmation":
            return self._render_confirmation(option, payload)
        if status == "awaiting_fields":
            return self._render_missing_fields(
                option,
                list(getattr(session, "missing_fields", []) or []),
                self._public_payload(payload_without_navigation(payload)),
            )
        if status == "awaiting_item_selection":
            return self._render_item_selection(
                option,
                {
                    "selection_kind": payload.get("_selection_kind"),
                    "scope_label": payload.get("_scope_label"),
                    "item_label_plural": payload.get("_item_label_plural"),
                    "choices": payload.get("_choices") or [],
                },
            )
        if status == self._company_selection_status:
            return self._render_operation_company(option, payload.get("_operation_company_choices") or [])
        if status == "awaiting_summary_dates":
            return self._render_summary_period(option)
        if status == "awaiting_summary_company":
            return self._render_summary_company(option, payload.get("_summary_company_choices") or [])
        if status == "awaiting_summary_collaborator":
            return self._render_summary_collaborator(option, payload.get("_summary_collaborator_choices") or [])
        if status == "awaiting_summary_status":
            return self._render_summary_status(
                option,
                payload.get("_summary_status_choices") or self._summary_status_choices(),
            )
        if status == self._summary_email_confirm_status:
            report_text = str(payload.get("_summary_report_text") or "").strip()
            if report_text:
                return f"{report_text}\n\n{self._summary_email_offer_suffix}"
            return self._summary_email_offer_suffix
        if status == self._summary_email_custom_status:
            return self._summary_email_custom_prompt

        return self._fallback_reset_prompt


class SessionNavigationRuntime:
    def __init__(
        self,
        *,
        commit_session: Callable[[], None],
        reset_session: Callable[[Any], None],
        prompt_renderer: SessionPromptRenderer,
    ):
        self._commit_session = commit_session
        self._reset_session = reset_session
        self._prompt_renderer = prompt_renderer

    def transition_state(
        self,
        session: Any,
        *,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        missing_fields: Optional[List[Dict[str, Any]]] = None,
        push_history: bool = True,
    ) -> None:
        history = extract_navigation_stack(getattr(session, "collected_data", {}) or {})
        if push_history:
            snapshot = build_session_snapshot(session)
            if snapshot is not None:
                history.append(snapshot.model_dump())
                history = history[-12:]

        next_payload = payload_without_navigation(payload or {})
        if history:
            next_payload["_nav_stack"] = history

        session.status = status
        session.collected_data = next_payload
        session.missing_fields = list(missing_fields or [])
        self._commit_session()

    def handle_back_navigation(self, session: Any) -> SessionNavigationResult:
        if str(getattr(session, "status", "idle") or "idle") == "idle":
            return SessionNavigationResult(response_text=self._prompt_renderer.render(session))

        payload = dict(getattr(session, "collected_data", {}) or {})
        history = extract_navigation_stack(payload)
        if not history:
            self._reset_session(session)
            return SessionNavigationResult(response_text=self._prompt_renderer.render(session))

        previous = history.pop() or {}
        restored_payload = payload_without_navigation(previous.get("collected_data") or {})
        if history:
            restored_payload["_nav_stack"] = history

        session.status = str(previous.get("status") or "idle")
        session.selected_option_id = previous.get("selected_option_id")
        session.collected_data = restored_payload
        session.missing_fields = list(previous.get("missing_fields") or [])
        self._commit_session()

        return SessionNavigationResult(response_text=self._prompt_renderer.render(session))
