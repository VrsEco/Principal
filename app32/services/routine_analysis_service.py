"""Serviço analítico para a página Análise da Rotina."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from config_database import get_db

DEFAULT_WEEKLY_CAPACITY = 40.0
DEFAULT_MEETING_DURATION_HOURS = 1.0
_CLOSED_STATUSES = {"completed", "done", "cancelled", "canceled", "archived"}
_CLOSED_STAGES = {"completed", "done", "cancelled", "canceled", "archived"}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_json_payload(raw_value: Any) -> Any:
    if raw_value in (None, "", []):
        return []
    if isinstance(raw_value, (list, dict)):
        return raw_value
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _normalize_schedule_type(raw_value: Any) -> str:
    normalized = str(raw_value or "weekly").strip().lower()
    aliases = {
        "day": "daily",
        "diario": "daily",
        "diária": "daily",
        "daily": "daily",
        "week": "weekly",
        "semanal": "weekly",
        "weekly": "weekly",
        "month": "monthly",
        "mensal": "monthly",
        "monthly": "monthly",
        "quarterly": "quarterly",
        "trimestral": "quarterly",
        "yearly": "yearly",
        "annual": "yearly",
        "anual": "yearly",
        "year": "yearly",
    }
    return aliases.get(normalized, normalized or "weekly")


def _schedule_label(schedule_type: str) -> str:
    labels = {
        "daily": "Diárias",
        "weekly": "Semanais",
        "monthly": "Mensais",
        "quarterly": "Trimestrais",
        "yearly": "Anuais",
        "specific": "Específicas",
    }
    return labels.get(schedule_type, schedule_type.title())


def _schedule_weekly_factor(schedule_type: str) -> float:
    factors = {
        "daily": 5.0,
        "weekly": 1.0,
        "monthly": 12.0 / 52.0,
        "quarterly": 4.0 / 52.0,
        "yearly": 1.0 / 52.0,
        "specific": 0.0,
    }
    return factors.get(schedule_type, 1.0)


def _build_period_metrics(hours_per_occurrence: float, schedule_type: str) -> Dict[str, float]:
    weekly_hours = hours_per_occurrence * _schedule_weekly_factor(schedule_type)
    monthly_hours = weekly_hours * (52.0 / 12.0)
    annual_hours = weekly_hours * 52.0
    return {
        "hours_per_occurrence": round(hours_per_occurrence, 2),
        "weekly_equivalent_hours": round(weekly_hours, 2),
        "monthly_equivalent_hours": round(monthly_hours, 2),
        "annual_equivalent_hours": round(annual_hours, 2),
    }


def _resolve_capacity(raw_value: Any) -> float:
    capacity = _safe_float(raw_value)
    return capacity if capacity > 0 else DEFAULT_WEEKLY_CAPACITY


def _member_status(utilization_percent: float) -> str:
    if utilization_percent >= 100:
        return "overload"
    if utilization_percent >= 85:
        return "attention"
    if utilization_percent >= 70:
        return "balanced"
    return "available"


def _is_open_work_item(status: Any, stage: Any = None) -> bool:
    normalized_status = str(status or "").strip().lower()
    normalized_stage = str(stage or "").strip().lower()
    return normalized_status not in _CLOSED_STATUSES and normalized_stage not in _CLOSED_STAGES


def _normalize_participant_items(payload: Any) -> List[Dict[str, Any]]:
    data = _parse_json_payload(payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if all(isinstance(v, dict) for v in data.values()):
            return list(data.values())
        return [data]
    return []


def _resolve_meeting_participants(
    participants_raw: Any,
    guests_raw: Any,
    employee_by_id: Dict[int, Dict[str, Any]],
    employee_by_email: Dict[str, Dict[str, Any]],
) -> Tuple[int, List[int]]:
    unique_tokens = set()
    matched_employee_ids = set()

    for item in _normalize_participant_items(participants_raw) + _normalize_participant_items(guests_raw):
        employee_id = _safe_int(item.get("employee_id") or item.get("id"))
        if employee_id and employee_id in employee_by_id:
            unique_tokens.add(f"id:{employee_id}")
            matched_employee_ids.add(employee_id)
            continue

        email = str(item.get("email") or "").strip().lower()
        if email:
            unique_tokens.add(f"email:{email}")
            employee = employee_by_email.get(email)
            if employee:
                matched_employee_ids.add(employee["id"])
            continue

        name = str(item.get("name") or item.get("title") or "").strip().lower()
        if name:
            unique_tokens.add(f"name:{name}")

    if not unique_tokens:
        return 1, []
    return len(unique_tokens), sorted(matched_employee_ids)


def _load_employees(cursor, company_id: int) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    cursor.execute(
        """
        SELECT id, name, email, department, weekly_hours
        FROM employees
        WHERE company_id = %s
          AND status = 'active'
        ORDER BY name
        """,
        (company_id,),
    )
    employees = [dict(row) for row in cursor.fetchall()]
    by_id = {int(emp["id"]): emp for emp in employees if emp.get("id") is not None}
    by_email = {
        str(emp.get("email") or "").strip().lower(): emp
        for emp in employees
        if str(emp.get("email") or "").strip()
    }
    return employees, by_id, by_email


def _load_routines(cursor, company_id: int) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            r.id,
            r.name,
            r.description,
            r.schedule_type,
            r.schedule_value,
            p.code AS process_code,
            p.name AS process_name,
            rc.employee_id,
            e.name AS employee_name,
            rc.hours_used
        FROM routines r
        LEFT JOIN processes p
            ON p.id = r.process_id
           AND p.company_id = r.company_id
        LEFT JOIN routine_collaborators rc
            ON rc.routine_id = r.id
        LEFT JOIN employees e
            ON e.id = rc.employee_id
           AND e.company_id = r.company_id
        WHERE r.company_id = %s
          AND COALESCE(r.is_active, TRUE) = TRUE
        ORDER BY r.name, e.name
        """,
        (company_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _build_routine_section(routine_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    routines_map: Dict[int, Dict[str, Any]] = {}
    frequency_map: Dict[str, Dict[str, Any]] = {
        key: {
            "key": key,
            "label": _schedule_label(key),
            "activity_count": 0,
            "hours_per_occurrence": 0.0,
            "weekly_equivalent_hours": 0.0,
            "monthly_equivalent_hours": 0.0,
            "annual_equivalent_hours": 0.0,
        }
        for key in ("daily", "weekly", "monthly", "yearly")
    }
    member_fixed_hours = defaultdict(float)

    for row in routine_rows:
        routine_id = _safe_int(row.get("id"))
        if routine_id is None:
            continue

        routine = routines_map.setdefault(
            routine_id,
            {
                "id": routine_id,
                "name": row.get("name") or "Rotina sem nome",
                "description": row.get("description") or "",
                "schedule_type": _normalize_schedule_type(row.get("schedule_type")),
                "schedule_value": row.get("schedule_value"),
                "process_code": row.get("process_code"),
                "process_name": row.get("process_name") or "Sem processo vinculado",
                "collaborators": [],
                "hours_per_occurrence": 0.0,
            },
        )

        employee_id = _safe_int(row.get("employee_id"))
        hours_used = _safe_float(row.get("hours_used"))
        if employee_id:
            routine["collaborators"].append(
                {
                    "employee_id": employee_id,
                    "employee_name": row.get("employee_name") or f"Colaborador {employee_id}",
                    "hours_used": round(hours_used, 2),
                }
            )
            routine["hours_per_occurrence"] += hours_used

    top_routines = []
    for routine in routines_map.values():
        metrics = _build_period_metrics(routine["hours_per_occurrence"], routine["schedule_type"])
        routine.update(metrics)
        if routine["schedule_type"] in frequency_map:
            bucket = frequency_map[routine["schedule_type"]]
            bucket["activity_count"] += 1
            for key in ("hours_per_occurrence", "weekly_equivalent_hours", "monthly_equivalent_hours", "annual_equivalent_hours"):
                bucket[key] += routine[key]

        for collaborator in routine["collaborators"]:
            member_fixed_hours[collaborator["employee_id"]] += (
                collaborator["hours_used"] * _schedule_weekly_factor(routine["schedule_type"])
            )

        top_routines.append(
            {
                "id": routine["id"],
                "name": routine["name"],
                "process_name": (
                    f'{routine["process_code"]} - {routine["process_name"]}'
                    if routine.get("process_code")
                    else routine["process_name"]
                ),
                "schedule_label": _schedule_label(routine["schedule_type"]),
                "weekly_equivalent_hours": routine["weekly_equivalent_hours"],
                "hours_per_occurrence": routine["hours_per_occurrence"],
            }
        )

    frequency_breakdown = []
    for key in ("daily", "weekly", "monthly", "yearly"):
        bucket = frequency_map[key]
        for metric_key in ("hours_per_occurrence", "weekly_equivalent_hours", "monthly_equivalent_hours", "annual_equivalent_hours"):
            bucket[metric_key] = round(bucket[metric_key], 2)
        frequency_breakdown.append(bucket)

    top_routines.sort(key=lambda item: item["weekly_equivalent_hours"], reverse=True)
    total_fixed_weekly = round(sum(item["weekly_equivalent_hours"] for item in top_routines), 2)

    return {
        "frequency_breakdown": frequency_breakdown,
        "member_fixed_hours": {key: round(value, 2) for key, value in member_fixed_hours.items()},
        "top_routines": top_routines[:8],
        "total_fixed_weekly_hours": total_fixed_weekly,
        "routine_count": len(routines_map),
    }


def _load_project_section(cursor, company_id: int) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT
            pt.id,
            pt.project_id,
            p.title AS project_title,
            pt.what,
            pt.employee_id,
            e.name AS employee_name,
            pt.estimated_hours,
            pt.worked_hours,
            pt.status,
            pt.stage
        FROM project_tasks pt
        JOIN projects p
            ON p.id = pt.project_id
        LEFT JOIN employees e
            ON e.id = pt.employee_id
           AND e.company_id = p.company_id
        WHERE p.company_id = %s
        ORDER BY p.title, pt.id
        """,
        (company_id,),
    )
    task_rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            pac.activity_id AS task_id,
            pac.employee_id,
            e.name AS employee_name,
            pac.estimated_hours,
            pac.worked_hours
        FROM project_activity_collaborators pac
        JOIN project_tasks pt
            ON pt.id = pac.activity_id
        JOIN projects p
            ON p.id = pt.project_id
        LEFT JOIN employees e
            ON e.id = pac.employee_id
           AND e.company_id = p.company_id
        WHERE p.company_id = %s
          AND COALESCE(pac.is_deleted, FALSE) = FALSE
        ORDER BY pac.activity_id, e.name
        """,
        (company_id,),
    )
    collaborator_rows = [dict(row) for row in cursor.fetchall()]
    collaborator_map: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in collaborator_rows:
        task_id = _safe_int(row.get("task_id"))
        if task_id is not None:
            collaborator_map[task_id].append(row)

    project_totals: Dict[int, Dict[str, Any]] = {}
    member_hours = defaultdict(float)
    open_task_count = 0
    estimated_total = 0.0
    worked_total = 0.0

    for row in task_rows:
        if not _is_open_work_item(row.get("status"), row.get("stage")):
            continue

        open_task_count += 1
        task_id = _safe_int(row.get("id"))
        project_id = _safe_int(row.get("project_id")) or 0
        assigned_rows = collaborator_map.get(task_id or -1, [])
        task_estimated = 0.0
        task_worked = 0.0

        if assigned_rows:
            for assigned in assigned_rows:
                estimated = _safe_float(assigned.get("estimated_hours"))
                worked = _safe_float(assigned.get("worked_hours"))
                employee_id = _safe_int(assigned.get("employee_id"))
                task_estimated += estimated
                task_worked += worked
                if employee_id:
                    member_hours[employee_id] += estimated
        else:
            task_estimated = _safe_float(row.get("estimated_hours"))
            task_worked = _safe_float(row.get("worked_hours"))
            employee_id = _safe_int(row.get("employee_id"))
            if employee_id:
                member_hours[employee_id] += task_estimated

        estimated_total += task_estimated
        worked_total += task_worked

        project_entry = project_totals.setdefault(
            project_id,
            {
                "project_id": project_id,
                "project_name": row.get("project_title") or "Projeto",
                "task_count": 0,
                "estimated_hours": 0.0,
                "worked_hours": 0.0,
            },
        )
        project_entry["task_count"] += 1
        project_entry["estimated_hours"] += task_estimated
        project_entry["worked_hours"] += task_worked

    top_projects = sorted(
        (
            {
                **item,
                "estimated_hours": round(item["estimated_hours"], 2),
                "worked_hours": round(item["worked_hours"], 2),
            }
            for item in project_totals.values()
        ),
        key=lambda item: item["estimated_hours"],
        reverse=True,
    )

    return {
        "open_task_count": open_task_count,
        "estimated_hours_total": round(estimated_total, 2),
        "worked_hours_total": round(worked_total, 2),
        "member_project_hours": {key: round(value, 2) for key, value in member_hours.items()},
        "top_projects": top_projects[:8],
    }


def _load_meeting_section(
    cursor,
    company_id: int,
    employee_by_id: Dict[int, Dict[str, Any]],
    employee_by_email: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT
            m.id,
            m.title,
            m.status,
            m.scheduled_date,
            m.scheduled_time,
            m.guests_json,
            m.participants_json,
            m.planned_duration_minutes,
            m.actual_duration_minutes,
            p.title AS project_title
        FROM meetings m
        LEFT JOIN projects p
            ON p.id = m.project_id
           AND p.company_id = m.company_id
        WHERE m.company_id = %s
        ORDER BY m.scheduled_date NULLS LAST, m.id DESC
        """,
        (company_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]

    member_hours = defaultdict(float)
    estimated_total = 0.0
    open_count = 0
    scheduled_count = 0
    top_meetings = []

    for row in rows:
        if not _is_open_work_item(row.get("status")):
            continue

        open_count += 1
        if row.get("scheduled_date"):
            scheduled_count += 1

        participant_count, matched_employee_ids = _resolve_meeting_participants(
            row.get("participants_json"),
            row.get("guests_json"),
            employee_by_id,
            employee_by_email,
        )
        planned_duration_minutes = _safe_float(row.get("planned_duration_minutes"))
        actual_duration_minutes = _safe_float(row.get("actual_duration_minutes"))
        duration_hours = 0.0
        duration_source = "heuristic"
        if actual_duration_minutes > 0:
            duration_hours = actual_duration_minutes / 60.0
            duration_source = "actual"
        elif planned_duration_minutes > 0:
            duration_hours = planned_duration_minutes / 60.0
            duration_source = "planned"
        else:
            duration_hours = participant_count * DEFAULT_MEETING_DURATION_HOURS

        estimated_total += duration_hours

        if matched_employee_ids:
            per_member_hours = duration_hours / len(matched_employee_ids) if matched_employee_ids else 0.0
            for employee_id in matched_employee_ids:
                member_hours[employee_id] += per_member_hours

        top_meetings.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "Reunião",
                "project_name": row.get("project_title") or "Sem projeto vinculado",
                "scheduled_date": (
                    row["scheduled_date"].strftime("%d/%m/%Y")
                    if getattr(row.get("scheduled_date"), "strftime", None)
                    else None
                ),
                "scheduled_time": row.get("scheduled_time"),
                "participant_count": participant_count,
                "estimated_hours": round(duration_hours, 2),
                "duration_source": duration_source,
            }
        )

    top_meetings.sort(key=lambda item: item["estimated_hours"], reverse=True)
    return {
        "open_meeting_count": open_count,
        "scheduled_meeting_count": scheduled_count,
        "estimated_hours_total": round(estimated_total, 2),
        "member_meeting_hours": {key: round(value, 2) for key, value in member_hours.items()},
        "top_meetings": top_meetings[:8],
        "estimation_basis": "Prioriza duração real, depois planejada; sem duração estruturada, usa heurística de 1h por participante identificado.",
    }


def _build_member_capacity_section(
    employees: Iterable[Dict[str, Any]],
    fixed_member_hours: Dict[int, float],
    project_member_hours: Dict[int, float],
    meeting_member_hours: Dict[int, float],
) -> Dict[str, Any]:
    members = []
    total_capacity = 0.0
    total_fixed = 0.0
    overloaded_count = 0

    for employee in employees:
        employee_id = _safe_int(employee.get("id"))
        if employee_id is None:
            continue

        weekly_capacity = _resolve_capacity(employee.get("weekly_hours"))
        fixed_hours = _safe_float(fixed_member_hours.get(employee_id))
        project_hours = _safe_float(project_member_hours.get(employee_id))
        meeting_hours = _safe_float(meeting_member_hours.get(employee_id))
        remaining_capacity = weekly_capacity - fixed_hours
        utilization_percent = round((fixed_hours / weekly_capacity) * 100, 1) if weekly_capacity else 0.0
        status = _member_status(utilization_percent)
        if status == "overload":
            overloaded_count += 1

        total_capacity += weekly_capacity
        total_fixed += fixed_hours
        members.append(
            {
                "employee_id": employee_id,
                "name": employee.get("name") or "Colaborador",
                "department": employee.get("department") or "Não informado",
                "weekly_capacity": round(weekly_capacity, 2),
                "fixed_hours_weekly": round(fixed_hours, 2),
                "remaining_capacity_weekly": round(remaining_capacity, 2),
                "fixed_utilization_percent": utilization_percent,
                "project_open_hours": round(project_hours, 2),
                "meeting_estimated_hours": round(meeting_hours, 2),
                "status": status,
            }
        )

    members.sort(
        key=lambda item: (
            item["fixed_utilization_percent"],
            item["project_open_hours"],
            item["meeting_estimated_hours"],
        ),
        reverse=True,
    )

    total_available = total_capacity - total_fixed
    utilization_total = round((total_fixed / total_capacity) * 100, 1) if total_capacity else 0.0
    return {
        "members": members,
        "summary": {
            "employee_count": len(members),
            "total_capacity_weekly_hours": round(total_capacity, 2),
            "total_fixed_weekly_hours": round(total_fixed, 2),
            "total_available_weekly_hours": round(total_available, 2),
            "fixed_utilization_percent": utilization_total,
            "overloaded_count": overloaded_count,
        },
    }


def get_routine_analysis(company_id: int) -> Dict[str, Any]:
    db = get_db()
    conn = db._get_connection()
    try:
        cursor = conn.cursor()
        employees, employee_by_id, employee_by_email = _load_employees(cursor, company_id)
        routine_section = _build_routine_section(_load_routines(cursor, company_id))
        project_section = _load_project_section(cursor, company_id)
        meeting_section = _load_meeting_section(cursor, company_id, employee_by_id, employee_by_email)
        member_section = _build_member_capacity_section(
            employees,
            routine_section["member_fixed_hours"],
            project_section["member_project_hours"],
            meeting_section["member_meeting_hours"],
        )

        summary = {
            **member_section["summary"],
            "routine_count": routine_section["routine_count"],
            "open_project_hours": project_section["estimated_hours_total"],
            "open_project_task_count": project_section["open_task_count"],
            "open_meeting_count": meeting_section["open_meeting_count"],
            "scheduled_meeting_count": meeting_section["scheduled_meeting_count"],
            "meeting_estimated_hours_total": meeting_section["estimated_hours_total"],
        }

        return {
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "summary": summary,
            "frequency_breakdown": routine_section["frequency_breakdown"],
            "fixed_routines": {
                "top_routines": routine_section["top_routines"],
            },
            "projects": {
                "open_task_count": project_section["open_task_count"],
                "estimated_hours_total": project_section["estimated_hours_total"],
                "worked_hours_total": project_section["worked_hours_total"],
                "top_projects": project_section["top_projects"],
            },
            "meetings": {
                "open_meeting_count": meeting_section["open_meeting_count"],
                "scheduled_meeting_count": meeting_section["scheduled_meeting_count"],
                "estimated_hours_total": meeting_section["estimated_hours_total"],
                "top_meetings": meeting_section["top_meetings"],
                "estimation_basis": meeting_section["estimation_basis"],
            },
            "members": member_section["members"],
        }
    finally:
        conn.close()
