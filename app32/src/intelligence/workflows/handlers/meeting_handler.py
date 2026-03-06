from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import MeetingReferenceInput, MeetingScheduleInput


class MeetingScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class MeetingScheduleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class MeetingStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class MeetingStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class MeetingSummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class MeetingSummarizeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class MeetingScheduleExecutionHandler:
    def __init__(
        self,
        *,
        resolve_company_ids_for_payload: Callable[
            [Dict[str, Any], Optional[int], int],
            Tuple[List[int], str],
        ],
        parse_meeting_datetime_input: Callable[..., Tuple[Optional[date], Optional[str], Optional[str]]],
        create_draft_meeting: Callable[..., Tuple[Optional[Any], Optional[str]]],
        load_company_by_id: Callable[[int], Any],
    ):
        self._resolve_company_ids_for_payload = resolve_company_ids_for_payload
        self._parse_meeting_datetime_input = parse_meeting_datetime_input
        self._create_draft_meeting = create_draft_meeting
        self._load_company_by_id = load_company_by_id

    def execute(self, request: MeetingScheduleRequest) -> MeetingScheduleResult:
        payload = dict(request.payload or {})

        execution_input, input_error = MeetingScheduleInput.build_from_legacy_payload(payload)
        if input_error:
            return MeetingScheduleResult(response_text=input_error)
        if not execution_input:
            return MeetingScheduleResult(
                response_text="Nao consegui interpretar o payload de agendamento da reuniao."
            )

        company_ids, company_label_or_error = self._resolve_company_ids_for_payload(
            payload,
            request.active_company_id,
            request.user_id,
        )
        if not company_ids:
            return MeetingScheduleResult(
                response_text=(
                    company_label_or_error
                    or "Nao foi possivel identificar a empresa da reuniao."
                )
            )
        if len(company_ids) > 1:
            return MeetingScheduleResult(
                response_text=(
                    "Encontrei mais de uma empresa no seu contexto. "
                    "Informe no formato: empresa: NOME_DA_EMPRESA"
                )
            )
        target_company_id = int(company_ids[0])

        scheduled_date, scheduled_time, parse_error = self._parse_meeting_datetime_input(
            datetime_raw=execution_input.datetime_raw or "",
            date_raw=execution_input.date_raw or "",
            time_raw=execution_input.time_raw or "",
        )
        if parse_error:
            return MeetingScheduleResult(response_text=parse_error)

        guest_values = list(execution_input.guests)
        guest_dict = {value: value for value in guest_values}
        agenda_values = list(execution_input.agenda_items)
        agenda = [{"title": value} for value in agenda_values]

        meeting, error = self._create_draft_meeting(
            company_id=target_company_id,
            title=execution_input.title,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            notes=execution_input.notes or "",
            guest_dict=guest_dict,
            agenda=agenda,
        )
        if error:
            return MeetingScheduleResult(response_text=error)

        company = self._load_company_by_id(target_company_id)
        company_label = self._format_company_label(company)
        guests_label = ", ".join(guest_values) if guest_values else "Nenhum informado"
        agenda_label = "; ".join(agenda_values) if agenda_values else "Sem pauta definida"
        meeting_id = getattr(meeting, "id", "-")
        return MeetingScheduleResult(
            response_text=(
                f"Reuniao '{execution_input.title}' agendada com sucesso!\n\n"
                f"- ID: {meeting_id}\n"
                f"- Empresa: {company_label}\n"
                f"- Data/Hora: {scheduled_date.isoformat()} {scheduled_time}\n"
                f"- Convidados: {guests_label}\n"
                f"- Pauta: {agenda_label}"
            )
        )

    def _format_company_label(self, company: Any) -> str:
        if not company:
            return "empresa"

        company_code = str(getattr(company, "client_code", "") or "").strip()
        company_name = str(getattr(company, "name", "") or "").strip()
        if company_code:
            return f"{company_code} - {company_name}"
        if company_name:
            return company_name
        return "empresa"


class MeetingStartExecutionHandler:
    def __init__(
        self,
        *,
        load_meeting_by_id: Callable[[int], Any],
        user_can_access_company: Callable[[int, int], bool],
        now_provider: Callable[[], datetime],
        ensure_linked_project: Callable[[Any, datetime], Tuple[Optional[Any], Optional[str]]],
        commit_changes: Callable[[], None],
        rollback_changes: Callable[[], None],
        load_company_by_id: Callable[[int], Any],
    ):
        self._load_meeting_by_id = load_meeting_by_id
        self._user_can_access_company = user_can_access_company
        self._now_provider = now_provider
        self._ensure_linked_project = ensure_linked_project
        self._commit_changes = commit_changes
        self._rollback_changes = rollback_changes
        self._load_company_by_id = load_company_by_id

    def execute(self, request: MeetingStartRequest) -> MeetingStartResult:
        meeting_input, input_error = MeetingReferenceInput.build_from_legacy_payload(
            dict(request.payload or {})
        )
        if input_error:
            return MeetingStartResult(response_text=input_error)
        if not meeting_input:
            return MeetingStartResult(
                response_text="Nao consegui interpretar a reuniao informada."
            )

        meeting = self._load_meeting_by_id(meeting_input.meeting_id)
        if not meeting:
            return MeetingStartResult(
                response_text=f"Reuniao ID {meeting_input.meeting_id} nao encontrada."
            )

        meeting_company_id = int(getattr(meeting, "company_id"))
        if (
            request.active_company_id
            and meeting_company_id != int(request.active_company_id)
            and not self._user_can_access_company(request.user_id, meeting_company_id)
        ):
            return MeetingStartResult(
                response_text="A reuniao informada nao pertence ao contexto da empresa ativa."
            )
        if not self._user_can_access_company(request.user_id, meeting_company_id):
            return MeetingStartResult(
                response_text="Voce nao possui acesso a esta reuniao."
            )

        if str(getattr(meeting, "status", "") or "").lower() == "completed":
            return MeetingStartResult(
                response_text=f"A reuniao '{meeting.title}' ja esta concluida."
            )

        started_at = self._now_provider()
        meeting.actual_date = started_at.date()
        meeting.actual_time = started_at.strftime("%H:%M")
        meeting.status = "in_progress"

        try:
            project, project_error = self._ensure_linked_project(meeting, started_at)
            if project_error:
                self._rollback_changes()
                return MeetingStartResult(response_text=project_error)
            self._commit_changes()
        except Exception as exc:
            self._rollback_changes()
            return MeetingStartResult(
                response_text=f"Erro ao iniciar reuniao: {str(exc)}"
            )

        company = self._load_company_by_id(meeting_company_id)
        company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
        project_code = self._resolve_project_code(meeting, project, company_code)
        return MeetingStartResult(
            response_text=(
                f"Reuniao '{meeting.title}' iniciada com sucesso!\n\n"
                f"- ID Reuniao: {meeting.id}\n"
                f"- Inicio: {started_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"- Projeto vinculado: {project_code}"
            )
        )

    def _resolve_project_code(
        self,
        meeting: Any,
        project: Optional[Any],
        company_code: str,
    ) -> str:
        if project is not None:
            project_code = str(getattr(project, "code", "") or "").strip()
            if project_code:
                return project_code

        project_id = getattr(meeting, "project_id", None)
        if project_id:
            return f"{company_code}.J.{project_id}"
        return "-"


class MeetingSummarizeExecutionHandler:
    def __init__(
        self,
        *,
        load_meeting_by_id: Callable[[int], Any],
        user_can_access_company: Callable[[int, int], bool],
    ):
        self._load_meeting_by_id = load_meeting_by_id
        self._user_can_access_company = user_can_access_company

    def execute(self, request: MeetingSummarizeRequest) -> MeetingSummarizeResult:
        meeting_input, input_error = MeetingReferenceInput.build_from_legacy_payload(
            dict(request.payload or {})
        )
        if input_error:
            return MeetingSummarizeResult(response_text=input_error)
        if not meeting_input:
            return MeetingSummarizeResult(
                response_text="Nao consegui interpretar a reuniao informada."
            )

        meeting = self._load_meeting_by_id(meeting_input.meeting_id)
        if not meeting:
            return MeetingSummarizeResult(
                response_text=f"Reuniao ID {meeting_input.meeting_id} nao encontrada."
            )

        meeting_company_id = int(getattr(meeting, "company_id"))
        if (
            request.active_company_id
            and meeting_company_id != int(request.active_company_id)
            and not self._user_can_access_company(request.user_id, meeting_company_id)
        ):
            return MeetingSummarizeResult(
                response_text="A reuniao informada nao pertence ao contexto da empresa ativa."
            )
        if not self._user_can_access_company(request.user_id, meeting_company_id):
            return MeetingSummarizeResult(
                response_text="Voce nao possui acesso a esta reuniao."
            )

        guests = self._safe_load_json_object(getattr(meeting, "guests_json", None))
        discussions = self._safe_load_json_list(getattr(meeting, "discussions_json", None))
        activities = self._safe_load_json_list(getattr(meeting, "activities_json", None))

        scheduled_when = (
            f"{meeting.scheduled_date.isoformat() if getattr(meeting, 'scheduled_date', None) else '-'} "
            f"{getattr(meeting, 'scheduled_time', None) or '-'}"
        )
        actual_when = (
            f"{meeting.actual_date.isoformat() if getattr(meeting, 'actual_date', None) else '-'} "
            f"{getattr(meeting, 'actual_time', None) or '-'}"
        )
        status = getattr(meeting, "status", None) or "draft"

        lines = [
            f"Resumo da reuniao ID {meeting.id} - {meeting.title}",
            f"- Status: {status}",
            f"- Data prevista: {scheduled_when}",
            f"- Data real: {actual_when}",
        ]

        if guests:
            guest_names = list(guests.keys())
            preview = ", ".join(guest_names[:10])
            extra = "" if len(guest_names) <= 10 else f" (+{len(guest_names) - 10})"
            lines.append(f"- Participantes: {preview}{extra}")
        else:
            lines.append("- Participantes: Nao registrados")

        if getattr(meeting, "project_id", None):
            lines.append(f"- Projeto vinculado: {meeting.project_id}")

        if discussions:
            lines.append("")
            lines.append("Principais pontos:")
            for idx, item in enumerate(discussions[:10], start=1):
                topic = str(item.get("title") or "Topico nao informado").strip()
                decision = str(item.get("decision") or "").strip()
                responsible = str(item.get("responsible") or "").strip()
                deadline = str(item.get("deadline") or "").strip()
                line = f"{idx}. {topic}"
                details: List[str] = []
                if decision:
                    details.append(f"Decisao: {decision}")
                if responsible:
                    details.append(f"Responsavel: {responsible}")
                if deadline:
                    details.append(f"Prazo: {deadline}")
                if details:
                    line += " | " + " | ".join(details)
                lines.append(line)

        if activities:
            lines.append("")
            lines.append("Atividades registradas:")
            for idx, item in enumerate(activities[:10], start=1):
                title = str(item.get("title") or "Atividade").strip()
                responsible = str(item.get("responsible") or "Sem responsavel").strip()
                deadline = str(item.get("deadline") or "-").strip()
                lines.append(f"{idx}. {title} | Responsavel: {responsible} | Prazo: {deadline}")

        if not discussions and not activities:
            notes = str(getattr(meeting, "meeting_notes", None) or "").strip()
            lines.append("")
            if notes:
                compact = " ".join(notes.split())
                preview = compact[:900] + ("..." if len(compact) > 900 else "")
                lines.append("Resumo registrado:")
                lines.append(preview)
            else:
                lines.append("Nao ha discussoes, atividades ou ata registrada para esta reuniao.")

        return MeetingSummarizeResult(response_text="\n".join(lines))

    def _safe_load_json_object(self, raw_value: Any) -> Dict[str, Any]:
        if not raw_value:
            return {}
        try:
            parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _safe_load_json_list(self, raw_value: Any) -> List[Dict[str, Any]]:
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in parsed:
            if isinstance(item, dict):
                normalized.append(item)
        return normalized
