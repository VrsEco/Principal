from flask import current_app, request
from flask_login import current_user
from flask_restful import Resource

from models.project import ProjectTask
from schemas.project import project_task_schema
from services.backlog_human_gate_service import (
    build_backlog_human_gate_context,
    execute_backlog_human_gate_operation,
    serialize_linked_agent_action,
)
from utils.permissions import has_company_full_access, permission_required

from .project import get_request_company_id
from .project_task import PUBLIC_ERROR_MESSAGE, apply_task_employee_filter


def _serialize_task_with_human_gate(task):
    payload = project_task_schema.dump(task)
    backlog_human_gate = build_backlog_human_gate_context(task)
    if backlog_human_gate:
        payload["backlog_human_gate"] = backlog_human_gate
    return payload


class ProjectTaskBacklogActionResource(Resource):
    @permission_required("projects", "edit")
    def post(self, project_id, task_id, operation):
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()

        project_company_id = getattr(getattr(task, "project", None), "company_id", None)
        if not has_company_full_access(project_company_id):
            return {"success": False, "error": "Sem permissão para operar este card do backlog."}, 403

        try:
            data = request.get_json(silent=True) or {}
            outcome = execute_backlog_human_gate_operation(
                task=task,
                operation=operation,
                actor_user_id=int(getattr(current_user, "id", 0) or 0),
                actor_name=str(getattr(current_user, "name", None) or "Operação"),
                feedback=data.get("feedback"),
            )
            if not outcome.success:
                return {
                    "success": False,
                    "error": outcome.message,
                    "action": serialize_linked_agent_action(outcome.action),
                    "approval_metadata": outcome.audit_metadata,
                }, outcome.http_status

            return {
                "success": True,
                "message": outcome.message,
                "task": _serialize_task_with_human_gate(task),
                "action": serialize_linked_agent_action(outcome.action),
                "resume_payload": outcome.resume_payload,
                "resume_result": outcome.resume_result,
                "approval_metadata": outcome.audit_metadata,
            }, outcome.http_status
        except Exception:
            current_app.logger.exception(
                "Erro ao operar backlog HITL project_id=%s task_id=%s operation=%s",
                project_id,
                task_id,
                operation,
            )
            return {"success": False, "error": PUBLIC_ERROR_MESSAGE}, 500
