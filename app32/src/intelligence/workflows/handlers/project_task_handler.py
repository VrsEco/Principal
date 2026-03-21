from __future__ import annotations

from datetime import date
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import ProjectTaskCompleteInput, ProjectTaskCreateInput, ProjectTaskUpdateInput


class ProjectTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class ProjectTaskCreateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class ProjectTaskCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class ProjectTaskCompleteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class ProjectTaskUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class ProjectTaskUpdateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class ProjectTaskAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class ProjectTaskAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class ProjectTaskCreateExecutionHandler:
    def __init__(
        self,
        *,
        resolve_company_ids_for_payload: Callable[
            [Dict[str, Any], Optional[int], int],
            Tuple[List[int], str],
        ],
        create_project_task: Callable[..., Tuple[Optional[Dict[str, Any]], Optional[str]]],
    ):
        self._resolve_company_ids_for_payload = resolve_company_ids_for_payload
        self._create_project_task = create_project_task

    def execute(self, request: ProjectTaskCreateRequest) -> ProjectTaskCreateResult:
        payload = dict(request.payload or {})

        execution_input, input_error = ProjectTaskCreateInput.build_from_legacy_payload(payload)
        if input_error:
            return ProjectTaskCreateResult(response_text=input_error)
        if not execution_input:
            return ProjectTaskCreateResult(
                response_text="Nao consegui interpretar o payload de criacao da atividade."
            )

        company_ids, company_label_or_error = self._resolve_company_ids_for_payload(
            payload,
            request.active_company_id,
            request.user_id,
        )
        if not company_ids:
            return ProjectTaskCreateResult(
                response_text=(
                    company_label_or_error
                    or "Nao foi possivel identificar a empresa do projeto."
                )
            )

        result, error = self._create_project_task(
            project_code=execution_input.project_code,
            task_name=execution_input.task_name,
            user_id=request.user_id,
            allowed_company_ids=company_ids,
            responsible_name=execution_input.responsible_name,
            due_date=execution_input.due_date,
            description=execution_input.description,
            amount=execution_input.amount,
            status=execution_input.status,
            stage=execution_input.stage,
            priority=execution_input.priority,
            notes=execution_input.notes,
        )
        if error:
            return ProjectTaskCreateResult(response_text=error)
        if not result:
            return ProjectTaskCreateResult(
                response_text="Nao foi possivel cadastrar a atividade de projeto."
            )

        task = result["task"]
        project = result["project"]
        company = result.get("company")
        responsible_name = (
            str(result.get("responsible_name") or "Nao informado").strip()
            or "Nao informado"
        )

        company_code = (
            str(getattr(company, "client_code", "") or "").strip()
            or "CP"
        )
        project_name = (
            str(getattr(project, "name", "") or "").strip()
            or f"Projeto {getattr(project, 'id', '-')}"
        )
        canonical_project_code = (
            str(getattr(project, "code", "") or "").strip()
            or f"{company_code}.J.{getattr(project, 'id', '-')}"
        )
        activity_code = (
            str(getattr(task, "code", "") or "").strip()
            or f"{canonical_project_code}.{getattr(task, 'id', '-')}"
        )
        task_title = str(getattr(task, "what", "") or "").strip() or execution_input.task_name

        return ProjectTaskCreateResult(
            response_text=(
                f"A atividade \"{task_title}\" foi cadastrada com sucesso no projeto "
                f"\"{canonical_project_code} - {project_name}\".\n\n"
                f"    Codigo da Atividade: {activity_code}\n"
                f"    Responsavel: {responsible_name}"
            )
        )


class ProjectTaskAuditExecutionHandler:
    def __init__(
        self,
        *,
        resolve_company_ids_for_payload: Callable[
            [Dict[str, Any], Optional[int], int],
            Tuple[List[int], str],
        ],
        load_project_task_audit_rows: Callable[[List[int], str], List[Dict[str, Any]]],
        format_report: Callable[[List[Dict[str, Any]], str, str], str],
    ):
        self._resolve_company_ids_for_payload = resolve_company_ids_for_payload
        self._load_project_task_audit_rows = load_project_task_audit_rows
        self._format_report = format_report

    def execute(self, request: ProjectTaskAuditRequest) -> ProjectTaskAuditResult:
        payload = dict(request.payload or {})
        audit_type = str(
            payload.get("tipo_auditoria")
            or payload.get("audit_type")
            or ""
        ).strip().lower()
        if audit_type not in {"missing_responsible", "missing_due_date"}:
            return ProjectTaskAuditResult(
                response_text=(
                    "Nao identifiquei o tipo de auditoria. Use pedidos como "
                    "'atividades sem responsável' ou 'atividades sem data'."
                )
            )

        company_ids, company_label_or_error = self._resolve_company_ids_for_payload(
            payload,
            request.active_company_id,
            request.user_id,
        )
        if not company_ids:
            return ProjectTaskAuditResult(
                response_text=(
                    company_label_or_error
                    or "Nao consegui identificar o recorte de empresas para auditoria."
                )
            )

        rows = self._load_project_task_audit_rows(company_ids, audit_type)
        return ProjectTaskAuditResult(
            response_text=self._format_report(rows, audit_type, company_label_or_error or "empresas vinculadas")
        )


class ProjectTaskCompleteExecutionHandler:
    def __init__(
        self,
        *,
        extract_id_from_code: Callable[[str], Optional[int]],
        parse_completion_date: Callable[[str], Optional[date]],
        today_provider: Callable[[], date],
        load_task_by_id: Callable[[int], Any],
        load_company_by_id: Callable[[int], Any],
        user_can_access_company: Callable[[int, int], bool],
        commit_changes: Callable[[], None],
        rollback_changes: Callable[[], None],
    ):
        self._extract_id_from_code = extract_id_from_code
        self._parse_completion_date = parse_completion_date
        self._today_provider = today_provider
        self._load_task_by_id = load_task_by_id
        self._load_company_by_id = load_company_by_id
        self._user_can_access_company = user_can_access_company
        self._commit_changes = commit_changes
        self._rollback_changes = rollback_changes

    def execute(self, request: ProjectTaskCompleteRequest) -> ProjectTaskCompleteResult:
        payload = dict(request.payload or {})

        execution_input, input_error = ProjectTaskCompleteInput.build_from_legacy_payload(payload)
        if input_error:
            return ProjectTaskCompleteResult(response_text=input_error)
        if not execution_input:
            return ProjectTaskCompleteResult(
                response_text="Nao consegui interpretar o payload de conclusao da atividade."
            )

        desired_date = None
        if execution_input.completion_date_raw:
            desired_date = self._parse_completion_date(execution_input.completion_date_raw)
            if not desired_date:
                return ProjectTaskCompleteResult(
                    response_text="Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."
                )

        final_date = desired_date or self._today_provider()

        requested_codes = execution_input.activity_codes or [execution_input.activity_code]
        resolved_items: list[tuple[str, int]] = []
        unresolved_codes: list[str] = []
        for raw_code in requested_codes:
            task_id = self._resolve_task_id(raw_code)
            if not task_id:
                unresolved_codes.append(raw_code)
                continue
            resolved_items.append((raw_code, task_id))

        if not resolved_items:
            return ProjectTaskCompleteResult(
                response_text=f"Nao consegui identificar o ID no codigo '{execution_input.activity_code}'."
            )

        completed_lines: list[str] = []
        not_found_lines: list[str] = [f"- {code}: ID nao identificado" for code in unresolved_codes]
        has_changes = False
        last_single_payload: Optional[Dict[str, Any]] = None

        for raw_code, task_id in resolved_items:
            task = self._load_task_by_id(task_id)
            if not task:
                not_found_lines.append(f"- {raw_code}: atividade nao encontrada")
                continue

            project = getattr(task, "project", None)
            if not project:
                not_found_lines.append(
                    f"- {raw_code}: atividade '{getattr(task, 'what', 'Sem titulo')}' sem projeto vinculado"
                )
                continue

            project_company_id = getattr(project, "company_id", None)
            if (
                request.active_company_id
                and project_company_id
                and project_company_id != request.active_company_id
                and not self._user_can_access_company(request.user_id, int(project_company_id))
            ):
                not_found_lines.append(f"- {raw_code}: fora do contexto da empresa ativa")
                continue

            current_final_date = final_date
            item_changed = False
            task_title = str(getattr(task, "what", "") or "").strip() or "Atividade"
            if getattr(task, "status", None) != "completed" or getattr(task, "stage", None) != "completed":
                task.status = "completed"
                task.stage = "completed"
                task.completion_date = current_final_date
                item_changed = True
            elif desired_date and getattr(task, "completion_date", None) != desired_date:
                task.completion_date = desired_date
                current_final_date = desired_date
                item_changed = True
            else:
                current_final_date = getattr(task, "completion_date", None) or current_final_date

            try:
                update_progress = getattr(project, "update_progress", None)
                if callable(update_progress):
                    update_progress()
                    item_changed = True
            except Exception:
                self._rollback_changes()
                return ProjectTaskCompleteResult(
                    response_text=(
                        "Erro ao concluir atividades: falha ao atualizar o progresso do projeto "
                        f"para '{raw_code}' ({task_title}). Nenhuma alteracao foi persistida."
                    )
                )

            has_changes = has_changes or item_changed
            company = self._load_company_by_id(getattr(project, "company_id", 0)) if project else None
            company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
            project_code = str(getattr(project, "code", "") or "").strip() or f"{company_code}.J.{getattr(project, 'id', '-')}"
            activity_code = str(getattr(task, "code", "") or "").strip() or f"{project_code}.{getattr(task, 'id', '-')}"
            project_name = str(getattr(project, "name", "") or "").strip() or f"Projeto {getattr(project, 'id', '-')}"

            last_single_payload = {
                "activity_code": activity_code,
                "project_code": project_code,
                "project_name": project_name,
                "task_title": task_title,
                "final_date": current_final_date,
            }
            completed_lines.append(
                f"- {activity_code} | {task_title} | Projeto: {project_code} - {project_name} | Data: {current_final_date.isoformat()}"
            )

        if has_changes:
            try:
                self._commit_changes()
            except Exception:
                self._rollback_changes()
                return ProjectTaskCompleteResult(
                    response_text=(
                        "Erro ao concluir atividades: a transacao de persistencia falhou e foi revertida. "
                        "Nenhuma alteracao foi salva."
                    )
                )

        if len(completed_lines) == 1 and not not_found_lines and last_single_payload:
            return ProjectTaskCompleteResult(
                response_text=(
                    f"A atividade de projeto com o codigo \"{last_single_payload['activity_code']}\" foi concluida com sucesso!\n\n"
                    f"- Projeto: {last_single_payload['project_code']} - {last_single_payload['project_name']}\n"
                    f"- Atividade: {last_single_payload['task_title']}\n"
                    f"- Data de Conclusao: {last_single_payload['final_date'].isoformat()}"
                )
            )

        lines = [f"Conclusao em lote processada: {len(completed_lines)} atividade(s) concluida(s)."]
        if completed_lines:
            lines.append("")
            lines.append("Atividades concluídas:")
            lines.extend(completed_lines)
        if not_found_lines:
            lines.append("")
            lines.append("Pendencias encontradas:")
            lines.extend(not_found_lines)
        return ProjectTaskCompleteResult(response_text="\n".join(lines))

    def _resolve_task_id(self, raw_code: str) -> Optional[int]:
        normalized_code = str(raw_code or "").strip()
        if not normalized_code:
            return None
        task_id = self._extract_id_from_code(normalized_code)
        if task_id:
            return int(task_id)
        if normalized_code.isdigit():
            return int(normalized_code)
        numeric_tail = re.search(r"(\d+)$", normalized_code)
        if numeric_tail:
            return int(numeric_tail.group(1))
        return None


class ProjectTaskUpdateExecutionHandler:
    def __init__(
        self,
        *,
        extract_id_from_code: Callable[[str], Optional[int]],
        parse_due_date: Callable[[str], tuple[Optional[date], Optional[str]]],
        load_task_by_id: Callable[[int], Any],
        load_company_by_id: Callable[[int], Any],
        user_can_access_company: Callable[[int, int], bool],
        commit_changes: Callable[[], None],
    ):
        self._extract_id_from_code = extract_id_from_code
        self._parse_due_date = parse_due_date
        self._load_task_by_id = load_task_by_id
        self._load_company_by_id = load_company_by_id
        self._user_can_access_company = user_can_access_company
        self._commit_changes = commit_changes

    def execute(self, request: ProjectTaskUpdateRequest) -> ProjectTaskUpdateResult:
        payload = dict(request.payload or {})

        execution_input, input_error = ProjectTaskUpdateInput.build_from_legacy_payload(payload)
        if input_error:
            return ProjectTaskUpdateResult(response_text=input_error)
        if not execution_input:
            return ProjectTaskUpdateResult(
                response_text="Nao consegui interpretar o payload de atualizacao da atividade."
            )

        parsed_due_date = None
        if execution_input.due_date_raw:
            parsed_due_date, due_date_error = self._parse_due_date(execution_input.due_date_raw)
            if due_date_error:
                return ProjectTaskUpdateResult(response_text=due_date_error)

        requested_codes = execution_input.activity_codes or [execution_input.activity_code]
        resolved_items: list[tuple[str, int]] = []
        unresolved_codes: list[str] = []
        for raw_code in requested_codes:
            task_id = self._resolve_task_id(raw_code)
            if not task_id:
                unresolved_codes.append(raw_code)
                continue
            resolved_items.append((raw_code, task_id))

        if not resolved_items:
            return ProjectTaskUpdateResult(
                response_text=f"Nao consegui identificar o ID no codigo '{execution_input.activity_code}'."
            )

        changed_lines: list[str] = []
        not_found_lines: list[str] = [f"- {code}: ID nao identificado" for code in unresolved_codes]

        for raw_code, task_id in resolved_items:
            task = self._load_task_by_id(task_id)
            if not task:
                not_found_lines.append(f"- {raw_code}: atividade nao encontrada")
                continue

            project = getattr(task, "project", None)
            if not project:
                not_found_lines.append(
                    f"- {raw_code}: atividade '{getattr(task, 'what', 'Sem titulo')}' sem projeto vinculado"
                )
                continue

            project_company_id = getattr(project, "company_id", None)
            if (
                request.active_company_id
                and project_company_id
                and project_company_id != request.active_company_id
                and not self._user_can_access_company(request.user_id, int(project_company_id))
            ):
                not_found_lines.append(f"- {raw_code}: fora do contexto da empresa ativa")
                continue

            if parsed_due_date is not None:
                task.due_date = parsed_due_date
            if execution_input.notes:
                current_notes = str(getattr(task, "notes", None) or "").strip()
                extra_notes = str(execution_input.notes).strip()
                task.notes = f"{current_notes}\n\n{extra_notes}".strip() if current_notes else extra_notes

            company = self._load_company_by_id(getattr(project, "company_id", 0)) if project else None
            company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
            project_code = str(getattr(project, "code", "") or "").strip() or f"{company_code}.J.{getattr(project, 'id', '-')}"
            activity_code = str(getattr(task, "code", "") or "").strip() or f"{project_code}.{getattr(task, 'id', '-')}"
            task_title = str(getattr(task, "what", "") or "").strip() or "Atividade"
            parts = [f"- {activity_code} | {task_title}"]
            if parsed_due_date is not None:
                parts.append(f"Novo prazo: {parsed_due_date.isoformat()}")
            if execution_input.notes:
                parts.append("Observacao registrada")
            changed_lines.append(" | ".join(parts))

        if changed_lines:
            self._commit_changes()

        if len(changed_lines) == 1 and not not_found_lines:
            return ProjectTaskUpdateResult(
                response_text=f"Atualizacao concluida com sucesso.\n\n{changed_lines[0]}"
            )

        lines = [f"Atualizacao em lote processada: {len(changed_lines)} atividade(s) atualizada(s)."]
        if changed_lines:
            lines.append("")
            lines.append("Atividades atualizadas:")
            lines.extend(changed_lines)
        if not_found_lines:
            lines.append("")
            lines.append("Pendencias encontradas:")
            lines.extend(not_found_lines)
        return ProjectTaskUpdateResult(response_text="\n".join(lines))

    def _resolve_task_id(self, raw_code: str) -> Optional[int]:
        normalized_code = str(raw_code or "").strip()
        if not normalized_code:
            return None
        task_id = self._extract_id_from_code(normalized_code)
        if task_id:
            return int(task_id)
        if normalized_code.isdigit():
            return int(normalized_code)
        numeric_tail = re.search(r"(\d+)$", normalized_code)
        if numeric_tail:
            return int(numeric_tail.group(1))
        return None
