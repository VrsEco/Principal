from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from models import db
from models.meeting import Meeting
from models.employee import Employee
from models.project import Project, ProjectTask
from services.project_task_service import ProjectTaskService


class MeetingMCPService:
    """Regras tenant-safe para o workspace de reuniões consumido por Sapiens/MCP."""

    MEETING_UPDATE_FIELDS = frozenset(
        {
            "title",
            "project_id",
            "meeting_notes",
            "participants",
            "actual_date",
            "actual_time",
            "actual_duration_minutes",
            "status",
        }
    )
    TOPIC_UPDATE_FIELDS = frozenset({"title", "notes", "status"})
    DECISION_UPDATE_FIELDS = frozenset({"text", "rationale", "owner"})
    ACTIVITY_UPDATE_FIELDS = frozenset(
        {
            "title",
            "responsible",
            "employee_id",
            "deadline",
            "budget",
            "estimated_hours",
            "priority",
            "status",
            "how",
            "project_id",
        }
    )

    @staticmethod
    def _load_list(raw: str | None) -> list[dict[str, Any]]:
        try:
            value = json.loads(raw or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            value = []
        return [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    @staticmethod
    def _dump(value: list[dict[str, Any]]) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _ensure_ids(items: list[dict[str, Any]]) -> None:
        for item in items:
            item.setdefault("id", uuid4().hex)

    @staticmethod
    def _find(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
        return next((item for item in items if str(item.get("id")) == str(item_id)), None)

    @staticmethod
    def _validate_fields(changes: dict[str, Any], allowed: frozenset[str]) -> str | None:
        invalid = sorted(set(changes) - allowed)
        if invalid:
            return f"Campos não permitidos: {', '.join(invalid)}"
        return None

    @staticmethod
    def _parse_date(value: Any):
        parsed, error = ProjectTaskService.parse_due_date(value)
        return parsed, error

    @staticmethod
    def _parse_decimal(value: Any, field: str) -> tuple[Decimal | None, str | None]:
        if value in (None, ""):
            return None, None
        try:
            parsed = Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return None, f"{field} deve ser numérico."
        if parsed < 0:
            return None, f"{field} não pode ser negativo."
        return parsed, None

    @staticmethod
    def get_meeting(*, company_id: int, meeting_id: int) -> tuple[Meeting | None, str | None]:
        meeting = Meeting.query.filter_by(id=int(meeting_id), company_id=int(company_id)).first()
        if meeting is None:
            return None, "Reunião não encontrada no tenant informado."
        return meeting, None

    @staticmethod
    def _validate_project(*, company_id: int, project_id: Any) -> tuple[Project | None, str | None]:
        if project_id in (None, ""):
            return None, None
        try:
            normalized_id = int(project_id)
        except (TypeError, ValueError):
            return None, "project_id inválido."
        project = Project.query.filter_by(id=normalized_id, company_id=int(company_id), is_deleted=False).first()
        if project is None:
            return None, "Projeto não encontrado no tenant informado."
        return project, None

    @staticmethod
    def _validate_employee(*, company_id: int, employee_id: Any) -> tuple[int | None, str | None]:
        if employee_id in (None, ""):
            return None, None
        try:
            normalized_id = int(employee_id)
        except (TypeError, ValueError):
            return None, "employee_id inválido."
        employee = Employee.query.filter_by(id=normalized_id, company_id=int(company_id)).first()
        if employee is None:
            return None, "Responsável não encontrado no tenant informado."
        return normalized_id, None

    @staticmethod
    def create_meeting(
        *,
        company_id: int,
        title: str,
        project_id: int | None = None,
        participants: list[Any] | dict[str, Any] | None = None,
        meeting_notes: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        normalized_title = str(title or "").strip()
        if not normalized_title:
            return None, "Informe o título da reunião."
        project, error = MeetingMCPService._validate_project(company_id=company_id, project_id=project_id)
        if error:
            return None, error
        meeting = Meeting(
            company_id=int(company_id),
            project_id=project.id if project else None,
            title=normalized_title,
            status="draft",
            meeting_notes=str(meeting_notes or "").strip() or None,
            participants_json=json.dumps(participants or [], ensure_ascii=False),
            discussions_json="[]",
            activities_json="[]",
        )
        db.session.add(meeting)
        db.session.commit()
        return {"meeting": meeting.to_dict()}, None

    @staticmethod
    def update_meeting(*, company_id: int, meeting_id: int, changes: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        normalized = dict(changes or {})
        error = MeetingMCPService._validate_fields(normalized, MeetingMCPService.MEETING_UPDATE_FIELDS)
        if error:
            return None, error
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error

        if "title" in normalized:
            title = str(normalized["title"] or "").strip()
            if not title:
                return None, "O título da reunião não pode ficar vazio."
            meeting.title = title
        if "project_id" in normalized:
            project, project_error = MeetingMCPService._validate_project(
                company_id=company_id, project_id=normalized.get("project_id")
            )
            if project_error:
                return None, project_error
            meeting.project_id = project.id if project else None
        if "meeting_notes" in normalized:
            meeting.meeting_notes = str(normalized.get("meeting_notes") or "").strip() or None
        if "participants" in normalized:
            participants = normalized.get("participants")
            if not isinstance(participants, (list, dict)):
                return None, "participants deve ser lista ou objeto."
            meeting.participants_json = json.dumps(participants, ensure_ascii=False)
        if "actual_date" in normalized:
            meeting.actual_date, date_error = MeetingMCPService._parse_date(normalized.get("actual_date"))
            if date_error:
                return None, date_error
        if "actual_time" in normalized:
            meeting.actual_time = str(normalized.get("actual_time") or "").strip() or None
        if "actual_duration_minutes" in normalized:
            try:
                duration = int(normalized.get("actual_duration_minutes"))
            except (TypeError, ValueError):
                return None, "actual_duration_minutes deve ser inteiro."
            if duration < 0:
                return None, "actual_duration_minutes não pode ser negativo."
            meeting.actual_duration_minutes = duration
        if "status" in normalized:
            meeting.status = str(normalized.get("status") or "").strip() or meeting.status

        db.session.commit()
        return {"meeting": meeting.to_dict()}, None

    @staticmethod
    def create_topic(*, company_id: int, meeting_id: int, title: str, notes: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        normalized_title = str(title or "").strip()
        if not normalized_title:
            return None, "Informe o tema discutido."
        topics = MeetingMCPService._load_list(meeting.discussions_json)
        MeetingMCPService._ensure_ids(topics)
        topic = {
            "id": uuid4().hex,
            "title": normalized_title,
            "notes": str(notes or "").strip(),
            "status": "open",
            "decision": "",
            "decisions": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        topics.append(topic)
        meeting.discussions_json = MeetingMCPService._dump(topics)
        db.session.commit()
        return {"topic": topic, "meeting_id": meeting.id}, None

    @staticmethod
    def update_topic(*, company_id: int, meeting_id: int, topic_id: str, changes: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        normalized = dict(changes or {})
        error = MeetingMCPService._validate_fields(normalized, MeetingMCPService.TOPIC_UPDATE_FIELDS)
        if error:
            return None, error
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        topics = MeetingMCPService._load_list(meeting.discussions_json)
        MeetingMCPService._ensure_ids(topics)
        topic = MeetingMCPService._find(topics, topic_id)
        if topic is None:
            return None, "Tema não encontrado na reunião."
        for key in normalized:
            topic[key] = str(normalized[key] or "").strip()
        if "title" in normalized and not topic["title"]:
            return None, "O título do tema não pode ficar vazio."
        meeting.discussions_json = MeetingMCPService._dump(topics)
        db.session.commit()
        return {"topic": topic, "meeting_id": meeting.id}, None

    @staticmethod
    def delete_topic(*, company_id: int, meeting_id: int, topic_id: str) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        topics = MeetingMCPService._load_list(meeting.discussions_json)
        MeetingMCPService._ensure_ids(topics)
        remaining = [item for item in topics if str(item.get("id")) != str(topic_id)]
        if len(remaining) == len(topics):
            return None, "Tema não encontrado na reunião."
        meeting.discussions_json = MeetingMCPService._dump(remaining)
        db.session.commit()
        return {"deleted_topic_id": str(topic_id), "meeting_id": meeting.id}, None

    @staticmethod
    def _topic_with_decisions(meeting: Meeting, topic_id: str):
        topics = MeetingMCPService._load_list(meeting.discussions_json)
        MeetingMCPService._ensure_ids(topics)
        topic = MeetingMCPService._find(topics, topic_id)
        if topic is None:
            return topics, None, []
        decisions = topic.get("decisions") if isinstance(topic.get("decisions"), list) else []
        decisions = [dict(item) for item in decisions if isinstance(item, dict)]
        MeetingMCPService._ensure_ids(decisions)
        topic["decisions"] = decisions
        return topics, topic, decisions

    @staticmethod
    def create_decision(*, company_id: int, meeting_id: int, topic_id: str, text: str, rationale: str | None = None, owner: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        normalized_text = str(text or "").strip()
        if not normalized_text:
            return None, "Informe a decisão tomada."
        topics, topic, decisions = MeetingMCPService._topic_with_decisions(meeting, topic_id)
        if topic is None:
            return None, "Tema não encontrado na reunião."
        decision = {
            "id": uuid4().hex,
            "text": normalized_text,
            "rationale": str(rationale or "").strip(),
            "owner": str(owner or "").strip(),
            "created_at": datetime.utcnow().isoformat(),
        }
        decisions.append(decision)
        topic["decision"] = normalized_text
        meeting.discussions_json = MeetingMCPService._dump(topics)
        db.session.commit()
        return {"decision": decision, "topic_id": str(topic_id), "meeting_id": meeting.id}, None

    @staticmethod
    def update_decision(*, company_id: int, meeting_id: int, topic_id: str, decision_id: str, changes: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        normalized = dict(changes or {})
        error = MeetingMCPService._validate_fields(normalized, MeetingMCPService.DECISION_UPDATE_FIELDS)
        if error:
            return None, error
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        topics, topic, decisions = MeetingMCPService._topic_with_decisions(meeting, topic_id)
        if topic is None:
            return None, "Tema não encontrado na reunião."
        decision = MeetingMCPService._find(decisions, decision_id)
        if decision is None:
            return None, "Decisão não encontrada no tema."
        for key in normalized:
            decision[key] = str(normalized[key] or "").strip()
        if "text" in normalized and not decision["text"]:
            return None, "O texto da decisão não pode ficar vazio."
        topic["decision"] = str(decisions[-1].get("text") or "") if decisions else ""
        meeting.discussions_json = MeetingMCPService._dump(topics)
        db.session.commit()
        return {"decision": decision, "topic_id": str(topic_id), "meeting_id": meeting.id}, None

    @staticmethod
    def delete_decision(*, company_id: int, meeting_id: int, topic_id: str, decision_id: str) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        topics, topic, decisions = MeetingMCPService._topic_with_decisions(meeting, topic_id)
        if topic is None:
            return None, "Tema não encontrado na reunião."
        remaining = [item for item in decisions if str(item.get("id")) != str(decision_id)]
        if len(remaining) == len(decisions):
            return None, "Decisão não encontrada no tema."
        topic["decisions"] = remaining
        topic["decision"] = str(remaining[-1].get("text") or "") if remaining else ""
        meeting.discussions_json = MeetingMCPService._dump(topics)
        db.session.commit()
        return {"deleted_decision_id": str(decision_id), "topic_id": str(topic_id), "meeting_id": meeting.id}, None

    @staticmethod
    def create_activity(
        *, company_id: int, meeting_id: int, title: str, responsible: str | None = None,
        deadline: str | None = None, budget: str | None = None, estimated_hours: Any = None,
        priority: str = "normal", how: str | None = None, employee_id: int | None = None,
        project_id: int | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        normalized_title = str(title or "").strip()
        if not normalized_title:
            return None, "Informe o título da atividade."
        due_date, date_error = MeetingMCPService._parse_date(deadline)
        if date_error:
            return None, date_error
        hours, hours_error = MeetingMCPService._parse_decimal(estimated_hours, "estimated_hours")
        if hours_error:
            return None, hours_error
        normalized_employee_id, employee_error = MeetingMCPService._validate_employee(
            company_id=company_id, employee_id=employee_id
        )
        if employee_error:
            return None, employee_error
        target_project_id = project_id or meeting.project_id
        if target_project_id:
            _, project_error = MeetingMCPService._validate_project(company_id=company_id, project_id=target_project_id)
            if project_error:
                return None, project_error
        activities = MeetingMCPService._load_list(meeting.activities_json)
        MeetingMCPService._ensure_ids(activities)
        activity = {
            "id": uuid4().hex,
            "title": normalized_title,
            "responsible": str(responsible or "").strip(),
            "employee_id": normalized_employee_id,
            "deadline": due_date.isoformat() if due_date else None,
            "budget": str(budget or "").strip() or None,
            "estimated_hours": float(hours) if hours is not None else None,
            "priority": str(priority or "normal").strip() or "normal",
            "status": "planned",
            "how": str(how or "").strip(),
            "project_id": int(target_project_id) if target_project_id else None,
            "project_task_id": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        activities.append(activity)
        meeting.activities_json = MeetingMCPService._dump(activities)
        db.session.commit()
        return {"activity": activity, "meeting_id": meeting.id}, None

    @staticmethod
    def update_activity(*, company_id: int, meeting_id: int, activity_id: str, changes: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        normalized = dict(changes or {})
        error = MeetingMCPService._validate_fields(normalized, MeetingMCPService.ACTIVITY_UPDATE_FIELDS)
        if error:
            return None, error
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        activities = MeetingMCPService._load_list(meeting.activities_json)
        MeetingMCPService._ensure_ids(activities)
        activity = MeetingMCPService._find(activities, activity_id)
        if activity is None:
            return None, "Atividade não encontrada na reunião."

        if "title" in normalized:
            title = str(normalized.get("title") or "").strip()
            if not title:
                return None, "O título da atividade não pode ficar vazio."
            activity["title"] = title
        for key in ("responsible", "budget", "priority", "status", "how"):
            if key in normalized:
                activity[key] = str(normalized.get(key) or "").strip() or None
        if "employee_id" in normalized:
            normalized_employee_id, employee_error = MeetingMCPService._validate_employee(
                company_id=company_id, employee_id=normalized.get("employee_id")
            )
            if employee_error:
                return None, employee_error
            activity["employee_id"] = normalized_employee_id
        if "deadline" in normalized:
            due_date, date_error = MeetingMCPService._parse_date(normalized.get("deadline"))
            if date_error:
                return None, date_error
            activity["deadline"] = due_date.isoformat() if due_date else None
        if "estimated_hours" in normalized:
            hours, hours_error = MeetingMCPService._parse_decimal(normalized.get("estimated_hours"), "estimated_hours")
            if hours_error:
                return None, hours_error
            activity["estimated_hours"] = float(hours) if hours is not None else None
        if "project_id" in normalized:
            project, project_error = MeetingMCPService._validate_project(
                company_id=company_id, project_id=normalized.get("project_id")
            )
            if project_error:
                return None, project_error
            activity["project_id"] = project.id if project else None
            activity["project_task_id"] = None

        meeting.activities_json = MeetingMCPService._dump(activities)
        db.session.commit()
        return {"activity": activity, "meeting_id": meeting.id}, None

    @staticmethod
    def delete_activity(*, company_id: int, meeting_id: int, activity_id: str) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        activities = MeetingMCPService._load_list(meeting.activities_json)
        MeetingMCPService._ensure_ids(activities)
        remaining = [item for item in activities if str(item.get("id")) != str(activity_id)]
        if len(remaining) == len(activities):
            return None, "Atividade não encontrada na reunião."
        meeting.activities_json = MeetingMCPService._dump(remaining)
        db.session.commit()
        return {"deleted_activity_id": str(activity_id), "meeting_id": meeting.id}, None

    @staticmethod
    def sync_activities(*, company_id: int, meeting_id: int, activity_ids: list[str] | None = None) -> tuple[dict[str, Any] | None, str | None]:
        meeting, error = MeetingMCPService.get_meeting(company_id=company_id, meeting_id=meeting_id)
        if error or meeting is None:
            return None, error
        activities = MeetingMCPService._load_list(meeting.activities_json)
        MeetingMCPService._ensure_ids(activities)
        selected = {str(value) for value in activity_ids or [] if str(value).strip()}
        created = updated = skipped = 0

        for activity in activities:
            if selected and str(activity.get("id")) not in selected:
                continue
            target_project_id = activity.get("project_id") or meeting.project_id
            project, project_error = MeetingMCPService._validate_project(
                company_id=company_id, project_id=target_project_id
            )
            if project_error or project is None:
                skipped += 1
                continue
            due_date, date_error = MeetingMCPService._parse_date(activity.get("deadline"))
            if date_error:
                return None, f"Atividade {activity.get('id')}: {date_error}"
            hours, hours_error = MeetingMCPService._parse_decimal(activity.get("estimated_hours"), "estimated_hours")
            if hours_error:
                return None, f"Atividade {activity.get('id')}: {hours_error}"
            normalized_employee_id, employee_error = MeetingMCPService._validate_employee(
                company_id=company_id, employee_id=activity.get("employee_id")
            )
            if employee_error:
                return None, f"Atividade {activity.get('id')}: {employee_error}"

            task = None
            if activity.get("project_task_id"):
                task = ProjectTask.query.join(Project, Project.id == ProjectTask.project_id).filter(
                    ProjectTask.id == int(activity["project_task_id"]),
                    Project.company_id == int(company_id),
                    ProjectTask.project_id == int(project.id),
                    ProjectTask.is_deleted.is_(False),
                ).first()
            if task is None:
                task = ProjectTask(project_id=project.id, what=str(activity.get("title") or "").strip())
                db.session.add(task)
                created += 1
            else:
                updated += 1
            task.what = str(activity.get("title") or "").strip()
            task.who = str(activity.get("responsible") or "").strip() or None
            task.employee_id = normalized_employee_id
            task.due_date = due_date
            task.how = str(activity.get("how") or "").strip() or None
            task.amount = str(activity.get("budget") or "").strip() or None
            task.estimated_hours = hours or Decimal("0")
            task.priority = str(activity.get("priority") or "normal").strip() or "normal"
            task.status = str(activity.get("status") or "planned").strip() or "planned"
            db.session.flush()
            activity["project_id"] = project.id
            activity["project_task_id"] = task.id

        meeting.activities_json = MeetingMCPService._dump(activities)
        db.session.commit()
        return {
            "meeting_id": meeting.id,
            "created_tasks": created,
            "updated_tasks": updated,
            "skipped_activities": skipped,
            "activities": activities,
        }, None


__all__ = ["MeetingMCPService"]
