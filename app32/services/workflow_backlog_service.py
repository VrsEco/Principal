from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectTask
from models.workflow_gap import WorkflowGapCandidate
from services.project_task_service import ProjectTaskService


class WorkflowRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    business_domain: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=10, max_length=3000)
    problem_statement: str = Field(min_length=10, max_length=3000)
    target_users: str = Field(min_length=3, max_length=500)
    desired_channels: str = Field(min_length=3, max_length=500)
    expected_result: str = Field(min_length=10, max_length=3000)
    user_examples: str = Field(min_length=10, max_length=3000)
    known_inputs: str | None = Field(default=None, max_length=3000)
    systems_involved: str | None = Field(default=None, max_length=1000)
    dependencies: str | None = Field(default=None, max_length=1000)
    responsible_area: str | None = Field(default=None, max_length=255)
    usage_frequency: str | None = Field(default=None, max_length=255)
    execution_profile: str = Field(default="action", pattern="^(query|action|hybrid)$")
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    requires_human_confirmation: str = Field(default="yes", pattern="^(yes|no|unknown)$")
    data_summary: str | None = Field(default=None, max_length=3000)
    source_channel: str = Field(default="ui_workflows_catalog", min_length=2, max_length=64)
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = Field(default=None, max_length=3000)


class WorkflowBacklogService:
    BACKLOG_PROJECT_CODE = "AA.J.31"
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }

    @staticmethod
    def _label_yes_no_unknown(value: str) -> str:
        return {
            "yes": "Sim",
            "no": "Não",
            "unknown": "A validar",
        }.get(str(value or "").strip().lower(), "A validar")

    @classmethod
    def _list_manual_request_tasks(cls) -> list[ProjectTask]:
        project, error = ProjectTaskService.resolve_project_by_code(cls.BACKLOG_PROJECT_CODE, allowed_company_ids=None)
        if error or project is None:
            return []
        return (
            ProjectTask.query.filter(
                ProjectTask.project_id == project.id,
                ProjectTask.notes.isnot(None),
                ProjectTask.notes.contains("source_channel=workflow_request_ui"),
            )
            .order_by(ProjectTask.updated_at.desc(), ProjectTask.id.desc())
            .all()
        )

    @classmethod
    def _list_gap_candidates(cls, active_company: Any | None = None) -> list[WorkflowGapCandidate]:
        company_id = getattr(active_company, "id", None)
        query = WorkflowGapCandidate.query.filter(WorkflowGapCandidate.app_task_id.isnot(None))
        if company_id is not None:
            query = query.filter(
                (WorkflowGapCandidate.company_id == company_id)
                | (WorkflowGapCandidate.company_id.is_(None))
            )
        query = query.filter(WorkflowGapCandidate.status != "resolved")
        return query.order_by(WorkflowGapCandidate.updated_at.desc(), WorkflowGapCandidate.id.desc()).all()

    @classmethod
    def _serialize_manual_request_task(cls, task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "inbox").strip().lower()
        notes = getattr(task, "notes", None) or ""

        def _extract(marker: str) -> str | None:
            prefix = f"{marker}="
            for line in notes.splitlines():
                if line.startswith(prefix):
                    return line[len(prefix):].strip() or None
            return None

        raw_title = str(getattr(task, "what", "") or "").strip()
        title = raw_title.replace("[Novo Workflow] ", "", 1) if raw_title.startswith("[Novo Workflow] ") else raw_title
        return {
            "id": f"manual:{getattr(task, 'id', None)}",
            "title": title,
            "business_domain": _extract("business_domain") or "Novo workflow",
            "source_kind": "manual_request",
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "backlog_stage": stage,
            "backlog_stage_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "urgency": _extract("urgency") or "medium",
            "created_at": getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else None,
            "updated_at": getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else None,
        }

    @classmethod
    def _serialize_gap_candidate(cls, candidate: WorkflowGapCandidate) -> dict[str, Any]:
        stage = str(getattr(getattr(candidate, "task", None), "stage", None) or "inbox").strip().lower()
        domain = str(getattr(candidate, "normalized_intent", None) or getattr(candidate, "suggested_flow_name", None) or "Gap detectado").strip()
        return {
            "id": f"gap:{getattr(candidate, 'id', None)}",
            "title": getattr(candidate, "suggested_flow_name", None) or getattr(candidate, "title", None) or "Workflow gap",
            "business_domain": domain,
            "source_kind": "gap_candidate",
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "backlog_task_id": getattr(candidate, "app_task_id", None),
            "backlog_task_code": getattr(candidate, "app_task_code", None),
            "backlog_stage": stage,
            "backlog_stage_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "urgency": "medium",
            "created_at": getattr(candidate, "created_at", None).isoformat() if getattr(candidate, "created_at", None) else None,
            "updated_at": getattr(candidate, "updated_at", None).isoformat() if getattr(candidate, "updated_at", None) else None,
        }

    @classmethod
    def create_request(
        cls,
        raw_payload: dict[str, Any],
        *,
        company_id: int | None,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> dict[str, Any]:
        payload = WorkflowRequestPayload.model_validate(raw_payload)
        description_lines = [
            "Solicitação estruturada de novo Workflow para especificação assistida por IA.",
            "",
            f"Workflow: {payload.title}",
            f"Domínio: {payload.business_domain}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Company ID: {company_id if company_id is not None else '-'}",
            f"Urgência: {payload.urgency}",
            f"Perfil de execução: {payload.execution_profile}",
            f"Sensibilidade: {payload.sensitivity_level}",
            f"Confirmação humana: {cls._label_yes_no_unknown(payload.requires_human_confirmation)}",
            "",
            "Objetivo de negócio:",
            payload.objective,
            "",
            "Problema a resolver:",
            payload.problem_statement,
            "",
            "Quem usa / solicitante-alvo:",
            payload.target_users,
            "",
            "Canais desejados:",
            payload.desired_channels,
            "",
            "Resultado esperado:",
            payload.expected_result,
            "",
            "Exemplos reais de solicitação do usuário:",
            payload.user_examples,
        ]
        if payload.known_inputs:
            description_lines.extend(["", "Dados de entrada já conhecidos:", payload.known_inputs])
        if payload.data_summary:
            description_lines.extend(["", "Dados / parâmetros / etapas esperadas:", payload.data_summary])
        if payload.systems_involved:
            description_lines.extend(["", "Sistemas / integrações envolvidos:", payload.systems_involved])
        if payload.dependencies:
            description_lines.extend(["", "Dependências / restrições conhecidas:", payload.dependencies])
        if payload.responsible_area:
            description_lines.extend(["", "Área responsável:", payload.responsible_area])
        if payload.usage_frequency:
            description_lines.extend(["", "Frequência de uso:", payload.usage_frequency])
        if payload.notes:
            description_lines.extend(["", "Observações:", payload.notes])
        description_lines.extend(
            [
                "",
                "Checklist esperado para especificação da IA:",
                "- propor action_key",
                "- propor domínio canônico",
                "- identificar canais",
                "- identificar contratos API/MCP",
                "- identificar tools necessárias",
                "- classificar permissões e human gate",
                "- listar configurações e dependências",
                "- apontar dúvidas/lacunas antes da implementação",
            ]
        )

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"[Novo Workflow] {payload.title}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description="\n".join(description_lines).strip(),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                "source_channel=workflow_request_ui\n"
                f"business_domain={payload.business_domain}\n"
                f"urgency={payload.urgency}\n"
                f"execution_profile={payload.execution_profile}\n"
                f"sensitivity_level={payload.sensitivity_level}\n"
                f"requires_human_confirmation={payload.requires_human_confirmation}\n"
                f"desired_channels={payload.desired_channels}\n"
                f"requester_user_id={requester_user_id}"
            ),
        )
        if error:
            raise ValueError(error)
        task = (result or {}).get("task")
        if task is None:
            raise ValueError("Não foi possível criar o card do workflow no backlog.")
        return cls._serialize_manual_request_task(task)

    @classmethod
    def list_requests(
        cls,
        *,
        active_company: Any | None = None,
        requester_user_id: int,
        requester_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = [cls._serialize_manual_request_task(task) for task in cls._list_manual_request_tasks()]
        items.extend(cls._serialize_gap_candidate(candidate) for candidate in cls._list_gap_candidates(active_company))
        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return items[:limit]
