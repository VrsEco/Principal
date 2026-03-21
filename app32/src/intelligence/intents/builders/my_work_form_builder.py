from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..schemas.operational_form import (
    CompanyScopeForm,
    ConfirmationScopeForm,
    FilterScopeForm,
    OperationalIntentForm,
    OutputScopeForm,
    ResolutionScopeForm,
    SourceScopeForm,
    SubjectScopeForm,
)
from ...workflows.schemas import MyWorkExecutionInput

_ACTION_TO_INTENT = {
    "my_work.open": "query.my_work.open",
    "my_work.overdue": "query.my_work.overdue",
    "my_work.due_range": "query.my_work.due_range",
    "my_work.completed_range": "query.my_work.completed_range",
}

_STATUS_BY_ACTION = {
    "my_work.open": "open",
    "my_work.overdue": "overdue",
    "my_work.due_range": "due_range",
    "my_work.completed_range": "completed",
}

_PERIOD_LABELS = {"hoje", "esta semana", "este mes", "próximos 15 dias", "proximos 15 dias"}


class MyWorkIntentFormBuilder:
    def build(
        self,
        *,
        action: str,
        payload: Dict[str, Any],
        active_company_id: Optional[int],
        channel: str,
        raw_text: Optional[str] = None,
    ) -> Tuple[Optional[OperationalIntentForm], Optional[str]]:
        execution_input, input_error = MyWorkExecutionInput.build_from_action(action)
        if input_error:
            return None, input_error
        if not execution_input:
            return None, "Nao foi possivel montar o formulario da consulta."

        normalized_payload = dict(payload or {})
        company_ids = []
        hidden_company_id = normalized_payload.get("_selected_company_id") or normalized_payload.get("_summary_company_id")
        if hidden_company_id not in (None, ""):
            try:
                company_ids = [int(hidden_company_id)]
            except (TypeError, ValueError):
                company_ids = []
        elif active_company_id not in (None, ""):
            try:
                company_ids = [int(active_company_id)]
            except (TypeError, ValueError):
                company_ids = []

        collaborator_names = []
        collaborator_term = str(
            normalized_payload.get("colaborador")
            or normalized_payload.get("collaborator")
            or normalized_payload.get("responsavel")
            or ""
        ).strip()
        if collaborator_term:
            collaborator_names.append(collaborator_term)

        period_label = str(normalized_payload.get("periodo") or "").strip().lower()
        date_mode = "none"
        if execution_input.requires_period:
            if period_label in {"hoje"}:
                date_mode = "today"
            elif period_label in {"esta semana"}:
                date_mode = "week"
            elif period_label in {"este mes"}:
                date_mode = "month"
            elif normalized_payload.get("data_inicio") or normalized_payload.get("data_fim"):
                date_mode = "custom_range"
            elif period_label:
                date_mode = "relative"
            else:
                date_mode = "none"

        entity_hint = str(normalized_payload.get("entidade") or normalized_payload.get("entity") or "mixed").strip().lower() or "mixed"
        if entity_hint not in {"project_task", "process_instance", "meeting", "mixed"}:
            entity_hint = "mixed"

        resolution_status = "ready"
        missing_fields = []
        if execution_input.requires_period and not period_label and not (
            normalized_payload.get("data_inicio") and normalized_payload.get("data_fim")
        ):
            resolution_status = "missing_fields"
            missing_fields.append("periodo")

        form = OperationalIntentForm(
            intent_kind="query",
            intent_code=_ACTION_TO_INTENT[execution_input.action],
            entity_type="mixed" if entity_hint == "mixed" else entity_hint,
            company_scope=CompanyScopeForm(
                company_ids=company_ids,
                selection_mode="explicit" if company_ids else "none",
                requires_disambiguation=not bool(company_ids),
            ),
            subject_scope=SubjectScopeForm(
                responsible_names=collaborator_names,
            ),
            filter_scope=FilterScopeForm(
                status=_STATUS_BY_ACTION[execution_input.action],
                date_mode=date_mode,
                start_date=str(normalized_payload.get("data_inicio") or "").strip() or None,
                end_date=str(normalized_payload.get("data_fim") or "").strip() or None,
                period_label=period_label or None,
                entity_hint=entity_hint,
                sort="due_date_asc",
            ),
            output_scope=OutputScopeForm(
                format="executive_summary",
                channel=channel or "web",
                verbosity="standard",
            ),
            confirmation_scope=ConfirmationScopeForm(
                required=False,
                reason="consulta_read_only",
                risk_level="low",
            ),
            resolution_scope=ResolutionScopeForm(
                status=resolution_status,
                confidence=0.92 if resolution_status == "ready" else 0.65,
                missing_fields=missing_fields,
                field_sources={
                    "action": "workflow_action",
                    "company_ids": "payload_hidden_or_active_company",
                    "colaborador": "payload",
                    "periodo": "payload",
                    "entidade": "payload",
                },
                needs_human_clarification=resolution_status != "ready",
            ),
            source_scope=SourceScopeForm(
                raw_text=raw_text,
                origin_channel=channel or "web",
                detected_action_key=execution_input.action,
            ),
            metadata={
                "form_version": "v1",
                "requires_period": execution_input.requires_period,
            },
        )
        return form, None
