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


class RoutineConsultIntentFormBuilder:
    def build(
        self,
        *,
        action: str,
        payload: Dict[str, Any],
        active_company_id: Optional[int],
        channel: str,
        raw_text: Optional[str] = None,
    ) -> Tuple[Optional[OperationalIntentForm], Optional[str]]:
        normalized_action = str(action or "").strip().lower()
        if normalized_action != "routine.consult":
            return None, "Acao invalida para formulario de consulta de rotina."

        normalized_payload = dict(payload or {})
        normalized_text = str(raw_text or "").strip().lower()

        explicit_company_term = str(
            normalized_payload.get("empresa")
            or normalized_payload.get("company")
            or normalized_payload.get("company_name")
            or ""
        ).strip()
        company_ids = []
        hidden_company_id = normalized_payload.get("_selected_company_id") or normalized_payload.get("_summary_company_id")
        if hidden_company_id not in (None, ""):
            try:
                company_ids = [int(hidden_company_id)]
            except (TypeError, ValueError):
                company_ids = []
        elif not explicit_company_term and active_company_id not in (None, ""):
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
        if not period_label:
            if "hoje" in normalized_text:
                period_label = "hoje"
            elif "semana" in normalized_text:
                period_label = "esta semana"
            elif "mes" in normalized_text:
                period_label = "este mes"

        entity_hint = str(normalized_payload.get("entidade") or normalized_payload.get("entity") or "").strip().lower()
        if not entity_hint:
            mentions_tasks = any(token in normalized_text for token in {"atividade", "atividades", "tarefa", "tarefas", "projeto", "projetos"})
            mentions_processes = any(token in normalized_text for token in {"processo", "processos", "instancia", "instancias"})
            mentions_meetings = any(
                token in normalized_text
                for token in {
                    "reuniao",
                    "reunioes",
                    "reunião",
                    "reuniões",
                    "agenda",
                    "compromisso",
                    "compromissos",
                }
            )
            detected = [
                candidate
                for candidate, matched in (
                    ("project_task", mentions_tasks),
                    ("process_instance", mentions_processes),
                    ("meeting", mentions_meetings),
                )
                if matched
            ]
            if len(detected) > 1:
                entity_hint = "mixed"
            elif detected:
                entity_hint = detected[0]
            else:
                entity_hint = "mixed"

        if entity_hint not in {"project_task", "process_instance", "meeting", "mixed"}:
            entity_hint = "mixed"

        status_value = str(normalized_payload.get("status_consulta") or "").strip().lower()
        if not status_value:
            if any(token in normalized_text for token in {"vencido", "vencidos", "vencida", "vencidas", "atrasado", "atrasados", "atrasada", "atrasadas"}):
                status_value = "overdue"
            elif any(token in normalized_text for token in {"concluido", "concluidos", "concluida", "concluidas", "finalizado", "finalizados", "finalizada", "finalizadas"}):
                status_value = "completed"
            else:
                status_value = "open"

        date_mode = "none"
        if period_label == "hoje":
            date_mode = "today"
        elif period_label == "esta semana":
            date_mode = "week"
        elif period_label == "este mes":
            date_mode = "month"
        elif normalized_payload.get("data_inicio") or normalized_payload.get("data_fim"):
            date_mode = "custom_range"

        form = OperationalIntentForm(
            intent_kind="query",
            intent_code="query.routine.consult",
            entity_type="mixed" if entity_hint == "mixed" else entity_hint,
            company_scope=CompanyScopeForm(
                company_ids=company_ids,
                selection_mode="explicit" if company_ids else ("implicit" if explicit_company_term else "none"),
                requires_disambiguation=not bool(company_ids) and bool(explicit_company_term),
            ),
            subject_scope=SubjectScopeForm(
                responsible_names=collaborator_names,
            ),
            filter_scope=FilterScopeForm(
                status=status_value,
                date_mode=date_mode,
                start_date=str(normalized_payload.get("data_inicio") or "").strip() or None,
                end_date=str(normalized_payload.get("data_fim") or "").strip() or None,
                period_label=period_label or None,
                entity_hint=entity_hint,
                sort="due_date_asc",
            ),
            output_scope=OutputScopeForm(
                format="detailed_list",
                channel=channel or "web",
                verbosity="standard",
            ),
            confirmation_scope=ConfirmationScopeForm(
                required=True,
                reason="consulta_operacional_pessoal",
                risk_level="low",
            ),
            resolution_scope=ResolutionScopeForm(
                status="ready",
                confidence=0.94,
                field_sources={
                    "action": "workflow_action",
                    "company_ids": "payload_hidden_or_active_company",
                    "empresa": "payload",
                    "colaborador": "payload",
                    "periodo": "payload_or_raw_text",
                    "entidade": "payload_or_raw_text",
                    "status_consulta": "payload_or_raw_text",
                },
                needs_human_clarification=False,
            ),
            source_scope=SourceScopeForm(
                raw_text=raw_text,
                origin_channel=channel or "web",
                detected_action_key=normalized_action,
            ),
            metadata={
                "form_version": "v1",
                "query_family": "routine_consult",
            },
        )
        return form, None
