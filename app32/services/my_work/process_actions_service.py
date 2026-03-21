import json
from datetime import date, datetime

from models import db, Employee, ProcessInstance
from utils.permissions import has_permission


def _instance_visible_to_employee(instance, employee_id):
    if not instance or not employee_id:
        return False

    if (
        instance.owner_employee_id == employee_id
        or instance.responsible_id == employee_id
        or instance.executor_id == employee_id
    ):
        return True

    collaborators = instance.collaborators_json or []
    if isinstance(collaborators, list):
        for item in collaborators:
            if item == employee_id:
                return True
            if isinstance(item, dict):
                raw_id = item.get("employee_id") or item.get("id")
                try:
                    if raw_id is not None and int(raw_id) == int(employee_id):
                        return True
                except (TypeError, ValueError):
                    continue

    return False


def _normalize_notes(raw_notes):
    if isinstance(raw_notes, list):
        return raw_notes

    if isinstance(raw_notes, str) and raw_notes.strip():
        try:
            parsed = json.loads(raw_notes)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    return []


def complete_process_instance_for_my_work(
    *,
    user_id: int,
    instance_id: int,
    company_id: int,
    completion_comment: str | None = None,
):
    instance = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first()
    if not instance:
        return {
            "success": False,
            "status_code": 404,
            "error": "Instância não encontrada no tenant informado.",
        }

    has_full_edit = has_permission(company_id, "processes", "edit")
    employee = Employee.query.filter_by(user_id=user_id, company_id=company_id).first()

    if not has_full_edit:
        if not employee or not _instance_visible_to_employee(instance, employee.id):
            return {
                "success": False,
                "status_code": 403,
                "error": "Acesso negado: você só pode concluir instâncias nas quais participa.",
            }

    try:
        notes_log = _normalize_notes(instance.notes)
        final_comment = str(completion_comment or "").strip()
        if final_comment:
            notes_log.insert(
                0,
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "author": "Executor (Minhas Atividades)",
                    "content": f"{final_comment} (Nota de finalização)",
                },
            )
            instance.notes = json.dumps(notes_log, ensure_ascii=False)

        instance.status = "completed"
        instance.actual_end_date = date.today()
        if not instance.completed_at:
            instance.completed_at = datetime.utcnow()

        db.session.commit()
        return {"success": True, "data": {"id": instance.id, "status": instance.status}}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "status_code": 500, "error": str(exc)}
