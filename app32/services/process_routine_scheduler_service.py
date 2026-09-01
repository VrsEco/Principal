from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_

from models import db, Employee, Process, ProcessInstance, ProcessInstanceCollaborator, Routine, RoutineCollaborator


SCHEDULER_TIMEZONE = ZoneInfo("America/Sao_Paulo")
WEEKDAY_ALIASES = {
    "segunda": 0,
    "segunda-feira": 0,
    "monday": 0,
    "terca": 1,
    "terça": 1,
    "terca-feira": 1,
    "terça-feira": 1,
    "tuesday": 1,
    "quarta": 2,
    "quarta-feira": 2,
    "wednesday": 2,
    "quinta": 3,
    "quinta-feira": 3,
    "thursday": 3,
    "sexta": 4,
    "sexta-feira": 4,
    "friday": 4,
    "sabado": 5,
    "sábado": 5,
    "saturday": 5,
    "domingo": 6,
    "sunday": 6,
}


def get_scheduler_now(reference: Optional[datetime] = None) -> datetime:
    if reference is not None:
        return reference.astimezone(SCHEDULER_TIMEZONE) if reference.tzinfo else reference.replace(tzinfo=SCHEDULER_TIMEZONE)
    return datetime.now(SCHEDULER_TIMEZONE)


def normalize_schedule_value(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def parse_daily_time(value: Optional[str]) -> Optional[time]:
    raw = normalize_schedule_value(value)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        return None


def resolve_routine_start_time(routine: Routine) -> Optional[time]:
    start_time = parse_daily_time(getattr(routine, "start_time", None))
    if start_time is not None:
        return start_time

    schedule_type = normalize_schedule_value(getattr(routine, "schedule_type", None))
    if schedule_type == "daily":
        return parse_daily_time(getattr(routine, "schedule_value", None))
    return None


def is_routine_time_due(routine: Routine, now: Optional[datetime] = None) -> bool:
    current = get_scheduler_now(now)
    routine_time = resolve_routine_start_time(routine)
    if routine_time is None:
        return False
    return current.hour == routine_time.hour and current.minute == routine_time.minute


def is_routine_due(routine: Routine, now: Optional[datetime] = None) -> bool:
    current = get_scheduler_now(now)
    schedule_type = normalize_schedule_value(getattr(routine, "schedule_type", None))
    schedule_value = normalize_schedule_value(getattr(routine, "schedule_value", None))

    if not schedule_type:
        return False

    if schedule_type == "daily":
        return is_routine_time_due(routine, current)

    if schedule_type == "weekly":
        selected_days = {
            WEEKDAY_ALIASES[token.strip()]
            for token in schedule_value.split(",")
            if token.strip() in WEEKDAY_ALIASES
        }
        return current.weekday() in selected_days and is_routine_time_due(routine, current)

    if schedule_type == "monthly":
        try:
            day = int(schedule_value)
        except (TypeError, ValueError):
            return False
        last_day = _last_day_of_month(current.year, current.month)
        return current.day == min(day, last_day) and is_routine_time_due(routine, current)

    if schedule_type == "quarterly":
        try:
            month_in_quarter_raw, day_raw = schedule_value.split("-", 1)
            month_in_quarter = int(month_in_quarter_raw)
            day = int(day_raw)
        except (AttributeError, TypeError, ValueError):
            return False

        if month_in_quarter not in (1, 2, 3):
            return False

        current_month_in_quarter = ((current.month - 1) % 3) + 1
        if current_month_in_quarter != month_in_quarter:
            return False

        last_day = _last_day_of_month(current.year, current.month)
        return current.day == min(day, last_day) and is_routine_time_due(routine, current)

    if schedule_type == "yearly":
        try:
            day_raw, month_raw = schedule_value.split("/", 1)
            day = int(day_raw)
            month = int(month_raw)
        except (AttributeError, TypeError, ValueError):
            return False

        if current.month != month:
            return False

        last_day = _last_day_of_month(current.year, month)
        return current.day == min(day, last_day) and is_routine_time_due(routine, current)

    if schedule_type == "specific":
        try:
            target_date = datetime.strptime(schedule_value, "%Y-%m-%d").date()
        except ValueError:
            return False
        return current.date() == target_date and is_routine_time_due(routine, current)

    return False


def build_automatic_instance_code(routine: Routine, now: Optional[datetime] = None) -> str:
    current = get_scheduler_now(now)
    process_code = getattr(getattr(routine, "process", None), "code", None) or f"P{routine.process_id}"
    return f"{process_code}-RT{routine.id}-{current.strftime('%Y%m%d')}"


def build_automatic_instance_code_for_target(
    routine: Routine,
    target_key: str | int | None,
    now: Optional[datetime] = None,
) -> str:
    base_code = build_automatic_instance_code(routine, now)
    if not target_key:
        return base_code
    safe_target = "".join(char for char in str(target_key) if char.isalnum() or char in "-_")[:24]
    return f"{base_code}-{safe_target}"[:100]


def calculate_due_date_for_routine(routine: Routine, now: Optional[datetime] = None) -> date:
    current = get_scheduler_now(now)

    if getattr(routine, "deadline_date", None):
        return routine.deadline_date

    deadline_days = int(getattr(routine, "deadline_days", 0) or 0)
    deadline_hours = int(getattr(routine, "deadline_hours", 0) or 0)
    return (current + timedelta(days=deadline_days, hours=deadline_hours)).date()


def sync_overdue_process_instances(now: Optional[datetime] = None) -> int:
    current_date = get_scheduler_now(now).date()
    updated = (
        ProcessInstance.query.filter(
            ProcessInstance.company_id.isnot(None),
            ProcessInstance.due_date.isnot(None),
            ProcessInstance.due_date < current_date,
            ProcessInstance.status.in_(["pending", "in_progress"]),
        )
        .update({"status": "overdue"}, synchronize_session=False)
    )
    db.session.commit()
    return int(updated or 0)


def process_scheduled_routines(now: Optional[datetime] = None) -> dict:
    current = get_scheduler_now(now)
    created = 0
    skipped = 0

    routines = (
        Routine.query.filter(
            Routine.company_id.isnot(None),
            or_(Routine.is_active.is_(True), Routine.is_active.is_(None)),
        )
        .order_by(Routine.company_id.asc(), Routine.id.asc())
        .all()
    )

    for routine in routines:
        if str(getattr(routine, "execution_mode", "scheduled") or "scheduled").lower() == "triggered":
            continue
        if not is_routine_due(routine, current):
            continue

        process = Process.query.filter_by(id=routine.process_id, company_id=routine.company_id).first()
        if process is None:
            skipped += 1
            continue

        direct_collaborators = _build_collaborators_payload(routine, routine.company_id)
        from services.routine_execution_rule_service import resolve_execution_groups_for_routine

        resolved = resolve_execution_groups_for_routine(routine)
        if resolved:
            groups, responsible_snapshot = resolved
        else:
            groups = [{
                "distribution_mode": "collective",
                "target_employee_id": None,
                "executor_id": _first_executor_id(direct_collaborators),
                "collaborators": direct_collaborators,
            }]
            responsible_snapshot = []

        for group in groups:
            collaborators = _merge_collaborators(group.get("collaborators", []), direct_collaborators)
            target_key = group.get("target_employee_id")
            instance_code = build_automatic_instance_code_for_target(routine, target_key, current)
            existing_instance = ProcessInstance.query.filter_by(
                company_id=routine.company_id,
                routine_id=routine.id,
                instance_code=instance_code,
            ).first()
            if existing_instance is not None:
                skipped += 1
                continue

            responsible_id = (
                responsible_snapshot[0].get("id") if responsible_snapshot else process.responsible_id
            )
            instance = ProcessInstance(
                company_id=routine.company_id,
                process_id=process.id,
                routine_id=routine.id,
                instance_code=instance_code,
                title=routine.name,
                description=routine.description,
                status="pending",
                priority="normal",
                due_date=calculate_due_date_for_routine(routine, current),
                trigger_type="automatic",
                owner_employee_id=process.owner_employee_id,
                responsible_id=responsible_id,
                executor_id=group.get("executor_id"),
                collaborators_json=collaborators,
                runtime_context_json={
                    "role_snapshot": {
                        "responsible": responsible_snapshot,
                        "executors": collaborators,
                    }
                },
                score_weight=float(_normalize_numeric(getattr(routine, "score_weight", 1.0), default=1.0)),
                created_by="scheduler",
            )
            db.session.add(instance)
            db.session.flush()

            _persist_instance_collaborators(instance.id, collaborators)
            created += 1

    db.session.commit()
    overdue_updated = sync_overdue_process_instances(current)
    return {
        "processed": len(routines),
        "created": created,
        "skipped": skipped,
        "overdue_updated": overdue_updated,
        "timestamp": current.isoformat(),
    }


def _persist_instance_collaborators(instance_id: int, collaborators: Iterable[dict]) -> None:
    for collaborator in collaborators:
        employee_id = collaborator.get("id") or collaborator.get("employee_id")
        if not employee_id:
            continue
        db.session.add(
            ProcessInstanceCollaborator(
                process_instance_id=instance_id,
                employee_id=employee_id,
                role=collaborator.get("role", "executor"),
                estimated_hours=_normalize_numeric(collaborator.get("hours"), default=0),
                notes=collaborator.get("notes"),
            )
        )


def _build_collaborators_payload(routine: Routine, company_id: int) -> list[dict]:
    collaborators = []
    seen_ids = set()

    for relation in RoutineCollaborator.query.filter_by(routine_id=routine.id).all():
        employee = Employee.query.filter_by(id=relation.employee_id, company_id=company_id).first()
        if employee is None or employee.id in seen_ids:
            continue

        collaborators.append(
            {
                "id": employee.id,
                "name": employee.name,
                "role": "executor",
                "hours": float(_normalize_numeric(relation.hours_used, default=0)),
                "actual_hours": 0,
                "notes": relation.notes,
            }
        )
        seen_ids.add(employee.id)

    return collaborators


def _first_executor_id(collaborators: Iterable[dict]) -> Optional[int]:
    for collaborator in collaborators:
        employee_id = collaborator.get("id") or collaborator.get("employee_id")
        if employee_id:
            return int(employee_id)
    return None


def _merge_collaborators(*groups: Iterable[dict]) -> list[dict]:
    result = []
    seen_ids = set()
    for group in groups:
        for collaborator in group:
            employee_id = collaborator.get("id") or collaborator.get("employee_id")
            if not employee_id or employee_id in seen_ids:
                continue
            seen_ids.add(employee_id)
            result.append(collaborator)
    return result


def _normalize_numeric(value: object, default: float = 0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day
