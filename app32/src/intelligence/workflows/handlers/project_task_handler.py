from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import ProjectTaskCompleteInput, ProjectTaskCreateInput


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

        task_id = self._extract_id_from_code(execution_input.activity_code)
        if not task_id:
            return ProjectTaskCompleteResult(
                response_text=f"Nao consegui identificar o ID no codigo '{execution_input.activity_code}'."
            )

        task = self._load_task_by_id(task_id)
        if not task:
            return ProjectTaskCompleteResult(
                response_text=f"Atividade de projeto com codigo '{execution_input.activity_code}' nao encontrada."
            )

        project = getattr(task, "project", None)
        if not project:
            return ProjectTaskCompleteResult(
                response_text=f"A atividade '{getattr(task, 'what', 'Sem titulo')}' nao possui projeto vinculado."
            )

        project_company_id = getattr(project, "company_id", None)
        if (
            request.active_company_id
            and project_company_id
            and project_company_id != request.active_company_id
            and not self._user_can_access_company(request.user_id, int(project_company_id))
        ):
            return ProjectTaskCompleteResult(
                response_text="A atividade informada nao pertence ao contexto da empresa ativa."
            )

        desired_date = None
        if execution_input.completion_date_raw:
            desired_date = self._parse_completion_date(execution_input.completion_date_raw)
            if not desired_date:
                return ProjectTaskCompleteResult(
                    response_text="Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."
                )

        final_date = desired_date or self._today_provider()

        has_changes = False

        if getattr(task, "status", None) != "completed" or getattr(task, "stage", None) != "completed":
            task.status = "completed"
            task.stage = "completed"
            task.completion_date = final_date
            has_changes = True
        elif desired_date and getattr(task, "completion_date", None) != desired_date:
            task.completion_date = desired_date
            final_date = desired_date
            has_changes = True
        else:
            final_date = getattr(task, "completion_date", None) or final_date

        try:
            update_progress = getattr(project, "update_progress", None)
            if callable(update_progress):
                update_progress()
                has_changes = True
            if has_changes:
                self._commit_changes()
        except Exception:
            self._rollback_changes()
            task = self._load_task_by_id(task_id)
            project = getattr(task, "project", None) if task else None

        company = self._load_company_by_id(getattr(project, "company_id", 0)) if project else None
        company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
        project_code = str(getattr(project, "code", "") or "").strip() or f"{company_code}.J.{getattr(project, 'id', '-')}"
        activity_code = str(getattr(task, "code", "") or "").strip() or f"{project_code}.{getattr(task, 'id', '-')}"
        project_name = str(getattr(project, "name", "") or "").strip() or f"Projeto {getattr(project, 'id', '-')}"
        task_title = str(getattr(task, "what", "") or "").strip() or "Atividade"

        return ProjectTaskCompleteResult(
            response_text=(
                f"A atividade de projeto com o codigo \"{activity_code}\" foi concluida com sucesso!\n\n"
                f"- Projeto: {project_code} - {project_name}\n"
                f"- Atividade: {task_title}\n"
                f"- Data de Conclusao: {final_date.isoformat()}"
            )
        )
