"""Serviço analítico para a página Análise da Rotina."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import unquote, urlparse

import psycopg2
from flask import has_app_context
from psycopg2.extras import RealDictCursor



def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def _get_pg_connection():
    if has_app_context():
        try:
            from models import db

            return db.engine.raw_connection()
        except Exception:
            pass

    _load_env_file()
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=(parsed.path or "").lstrip("/"),
            user=parsed.username,
            password=unquote(parsed.password or ""),
            cursor_factory=RealDictCursor,
        )

    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "bdversusv2"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        cursor_factory=RealDictCursor,
    )

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


def _humanize_hours(hours: float) -> str:
    rounded = round(_safe_float(hours), 2)
    if rounded.is_integer():
        value = str(int(rounded))
    else:
        value = f"{rounded:.1f}".replace('.', ',')
    return f"{value} hora" if rounded == 1 else f"{value} horas"


def _describe_schedule(schedule_type: str, schedule_value: Any) -> str:
    raw = str(schedule_value or '').strip()
    if not raw:
        fallback = {
            'daily': 'Todos os dias',
            'weekly': 'Sem dia fixo informado',
            'monthly': 'Sem dia fixo informado',
            'quarterly': 'A cada trimestre',
            'yearly': 'Todo ano',
            'specific': 'Data específica',
        }
        return fallback.get(schedule_type, 'Agendamento não informado')

    if schedule_type == 'daily':
        return f"Todos os dias ({raw})" if raw else 'Todos os dias'

    if schedule_type == 'weekly':
        weekday_map = {
            '0': 'domingo',
            '1': 'segunda-feira',
            '2': 'terça-feira',
            '3': 'quarta-feira',
            '4': 'quinta-feira',
            '5': 'sexta-feira',
            '6': 'sábado',
        }
        raw_tokens = [token.strip() for token in raw.replace(';', ',').replace('|', ',').split(',') if token.strip()]
        labels = [weekday_map.get(token, token) for token in raw_tokens]
        if len(labels) == 1:
            return f"Toda {labels[0]}"
        if len(labels) > 1:
            return "Toda " + ", ".join(labels[:-1]) + f" e {labels[-1]}"

    if schedule_type == 'monthly':
        day_tokens = [token.strip() for token in raw.replace(';', ',').split(',') if token.strip()]
        if len(day_tokens) == 1:
            return f"Todo dia {day_tokens[0]}"
        if len(day_tokens) > 1:
            return "Todo dia " + ", ".join(day_tokens[:-1]) + f" e {day_tokens[-1]}"

    if schedule_type == 'yearly':
        return f"Todo ano em {raw}"

    if schedule_type == 'quarterly':
        return f"A cada trimestre ({raw})"

    if schedule_type == 'specific':
        return raw

    return raw


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
                "schedule_type": routine["schedule_type"],
                "schedule_label": _schedule_label(routine["schedule_type"]),
                "schedule_value": routine.get("schedule_value"),
                "schedule_description": _describe_schedule(routine["schedule_type"], routine.get("schedule_value")),
                "weekly_equivalent_hours": routine["weekly_equivalent_hours"],
                "hours_per_occurrence": routine["hours_per_occurrence"],
                "collaborators": list(routine["collaborators"]),
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
        "all_routines": top_routines,
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
    member_allocations = []

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
                    member_allocations.append({
                        "employee_id": employee_id,
                        "project_id": project_id,
                        "project_name": row.get("project_title") or "Projeto",
                        "task_id": task_id,
                        "task_name": row.get("what") or "Atividade",
                        "estimated_hours": round(estimated, 2),
                        "worked_hours": round(worked, 2),
                    })
        else:
            task_estimated = _safe_float(row.get("estimated_hours"))
            task_worked = _safe_float(row.get("worked_hours"))
            employee_id = _safe_int(row.get("employee_id"))
            if employee_id:
                member_hours[employee_id] += task_estimated
                member_allocations.append({
                    "employee_id": employee_id,
                    "project_id": project_id,
                    "project_name": row.get("project_title") or "Projeto",
                    "task_id": task_id,
                    "task_name": row.get("what") or "Atividade",
                    "estimated_hours": round(task_estimated, 2),
                    "worked_hours": round(task_worked, 2),
                })

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
        "member_allocations": member_allocations,
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
    meeting_details = []

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

        meeting_payload = {
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
            "matched_employee_ids": matched_employee_ids,
        }
        top_meetings.append(meeting_payload)
        meeting_details.append(meeting_payload)

    top_meetings.sort(key=lambda item: item["estimated_hours"], reverse=True)
    return {
        "open_meeting_count": open_count,
        "scheduled_meeting_count": scheduled_count,
        "estimated_hours_total": round(estimated_total, 2),
        "member_meeting_hours": {key: round(value, 2) for key, value in member_hours.items()},
        "top_meetings": top_meetings[:8],
        "meeting_details": meeting_details,
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
    total_project = 0.0
    total_meeting = 0.0
    overloaded_count = 0
    overloaded_total_count = 0
    attention_total_count = 0

    for employee in employees:
        employee_id = _safe_int(employee.get("id"))
        if employee_id is None:
            continue

        weekly_capacity = _resolve_capacity(employee.get("weekly_hours"))
        fixed_hours = _safe_float(fixed_member_hours.get(employee_id))
        project_hours = _safe_float(project_member_hours.get(employee_id))
        meeting_hours = _safe_float(meeting_member_hours.get(employee_id))
        total_commitment = fixed_hours + project_hours + meeting_hours
        remaining_capacity = weekly_capacity - fixed_hours
        remaining_after_total = weekly_capacity - total_commitment
        utilization_percent = round((fixed_hours / weekly_capacity) * 100, 1) if weekly_capacity else 0.0
        total_utilization_percent = round((total_commitment / weekly_capacity) * 100, 1) if weekly_capacity else 0.0
        status = _member_status(utilization_percent)
        total_status = _member_status(total_utilization_percent)
        risk_label = "Crítico" if total_utilization_percent >= 100 else "Atenção" if total_utilization_percent >= 85 else "Controlado"

        if status == "overload":
            overloaded_count += 1
        if total_status == "overload":
            overloaded_total_count += 1
        elif total_status == "attention":
            attention_total_count += 1

        total_capacity += weekly_capacity
        total_fixed += fixed_hours
        total_project += project_hours
        total_meeting += meeting_hours
        members.append(
            {
                "employee_id": employee_id,
                "name": employee.get("name") or "Colaborador",
                "department": employee.get("department") or "Não informado",
                "weekly_capacity": round(weekly_capacity, 2),
                "fixed_hours_weekly": round(fixed_hours, 2),
                "remaining_capacity_weekly": round(remaining_capacity, 2),
                "remaining_after_total_weekly": round(remaining_after_total, 2),
                "fixed_utilization_percent": utilization_percent,
                "project_open_hours": round(project_hours, 2),
                "meeting_estimated_hours": round(meeting_hours, 2),
                "total_commitment_hours": round(total_commitment, 2),
                "total_utilization_percent": total_utilization_percent,
                "status": status,
                "total_status": total_status,
                "risk_label": risk_label,
            }
        )

    members.sort(
        key=lambda item: (
            item["total_utilization_percent"],
            item["total_commitment_hours"],
            item["fixed_utilization_percent"],
        ),
        reverse=True,
    )

    total_available = total_capacity - total_fixed
    utilization_total = round((total_fixed / total_capacity) * 100, 1) if total_capacity else 0.0
    total_commitment_hours = total_fixed + total_project + total_meeting
    total_utilization_all = round((total_commitment_hours / total_capacity) * 100, 1) if total_capacity else 0.0
    top_bottlenecks = [
        {
            "employee_id": item["employee_id"],
            "name": item["name"],
            "department": item["department"],
            "total_commitment_hours": item["total_commitment_hours"],
            "total_utilization_percent": item["total_utilization_percent"],
            "remaining_after_total_weekly": item["remaining_after_total_weekly"],
            "risk_label": item["risk_label"],
            "status": item["total_status"],
        }
        for item in members[:8]
    ]
    return {
        "members": members,
        "summary": {
            "employee_count": len(members),
            "total_capacity_weekly_hours": round(total_capacity, 2),
            "total_fixed_weekly_hours": round(total_fixed, 2),
            "total_project_weekly_hours": round(total_project, 2),
            "total_meeting_weekly_hours": round(total_meeting, 2),
            "total_available_weekly_hours": round(total_available, 2),
            "fixed_utilization_percent": utilization_total,
            "overloaded_count": overloaded_count,
            "overloaded_total_count": overloaded_total_count,
            "attention_total_count": attention_total_count,
            "total_commitment_weekly_hours": round(total_commitment_hours, 2),
            "total_utilization_percent": total_utilization_all,
        },
        "top_bottlenecks": top_bottlenecks,
    }


def _normalize_filter_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_department_value(value: Any) -> str:
    normalized = _normalize_filter_text(value)
    return normalized or 'não informado'


def _apply_employee_filters(
    employees: Iterable[Dict[str, Any]],
    department: str | None = None,
    employee_id: int | None = None,
) -> List[Dict[str, Any]]:
    filtered = []
    dept_filter = _normalize_filter_text(department)

    for employee in employees:
        if employee_id and _safe_int(employee.get("id")) != employee_id:
            continue
        if dept_filter and _normalize_department_value(employee.get("department")) != _normalize_department_value(department):
            continue
        filtered.append(employee)
    return filtered


def _build_scope_label(
    department: str | None,
    employee_id: int | None,
    employee_options: List[Dict[str, Any]],
) -> str:
    if employee_id:
        match = next((item for item in employee_options if item["id"] == employee_id), None)
        if match:
            return f"Colaborador: {match['name']}"
        return "Colaborador filtrado"
    if department:
        return f"Departamento: {department}"
    return "Empresa inteira"


def _build_filter_metadata(
    employees: Iterable[Dict[str, Any]],
    department: str | None,
    employee_id: int | None,
) -> Dict[str, Any]:
    employee_list = list(employees)
    departments = sorted(
        {
            dept.strip()
            for dept in (emp.get("department") or "Não informado" for emp in employee_list)
            if dept.strip()
        }
    )
    selectable_employees = _apply_employee_filters(employee_list, department=department) if department else employee_list
    employee_options = [
        {"id": _safe_int(emp.get("id")), "name": emp.get("name") or "Colaborador"}
        for emp in selectable_employees
        if _safe_int(emp.get("id")) is not None
    ]
    employee_options.sort(key=lambda item: item["name"])
    all_employee_options = [
        {
            "id": _safe_int(emp.get("id")),
            "name": emp.get("name") or "Colaborador",
            "department": (emp.get("department") or "Não informado").strip() if isinstance(emp.get("department"), str) else (emp.get("department") or "Não informado"),
        }
        for emp in employee_list
        if _safe_int(emp.get("id")) is not None
    ]
    all_employee_options.sort(key=lambda item: item["name"])
    return {
        "department": department,
        "employee_id": employee_id,
        "departments": departments,
        "employees": employee_options,
        "all_employees": all_employee_options,
        "scope_label": _build_scope_label(department, employee_id, employee_options),
    }


def _get_scoped_employee_ids(employees: Iterable[Dict[str, Any]]) -> set[int]:
    return {
        employee_id
        for employee_id in (_safe_int(emp.get("id")) for emp in employees)
        if employee_id is not None
    }


def _apply_scope_to_routine_section(routine_section: Dict[str, Any], scoped_employee_ids: set[int]) -> Dict[str, Any]:
    if not scoped_employee_ids:
        return {**routine_section, "top_routines": [], "all_routines": [], "frequency_breakdown": [], "routine_count": 0}

    frequency_keys = ("daily", "weekly", "monthly", "quarterly", "yearly", "specific")
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
        for key in frequency_keys
    }

    scoped_routines = []
    for routine in routine_section.get("all_routines", []):
        scoped_collaborators = [
            collaborator
            for collaborator in routine.get("collaborators", [])
            if _safe_int(collaborator.get("employee_id")) in scoped_employee_ids
        ]
        if not scoped_collaborators:
            continue

        hours_per_occurrence = round(sum(_safe_float(item.get("hours_used")) for item in scoped_collaborators), 2)
        schedule_type = routine.get("schedule_type") or "weekly"
        scoped_routine = {
            "id": routine.get("id"),
            "name": routine.get("name") or "Rotina sem nome",
            "process_name": routine.get("process_name") or "Sem processo vinculado",
            "schedule_type": schedule_type,
            "schedule_label": routine.get("schedule_label") or _schedule_label(schedule_type),
            "schedule_value": routine.get("schedule_value"),
            "schedule_description": routine.get("schedule_description") or _describe_schedule(schedule_type, routine.get("schedule_value")),
            "hours_per_occurrence": hours_per_occurrence,
            "collaborators": scoped_collaborators,
        }
        scoped_routine.update(_build_period_metrics(hours_per_occurrence, schedule_type))
        scoped_routines.append(scoped_routine)

        if schedule_type in frequency_map:
            bucket = frequency_map[schedule_type]
            bucket["activity_count"] += 1
            for metric_key in ("hours_per_occurrence", "weekly_equivalent_hours", "monthly_equivalent_hours", "annual_equivalent_hours"):
                bucket[metric_key] += scoped_routine[metric_key]

    frequency_breakdown = []
    for key in frequency_keys:
        bucket = frequency_map[key]
        if not bucket["activity_count"] and not any(bucket[m] for m in ("hours_per_occurrence", "weekly_equivalent_hours", "monthly_equivalent_hours", "annual_equivalent_hours")):
            continue
        for metric_key in ("hours_per_occurrence", "weekly_equivalent_hours", "monthly_equivalent_hours", "annual_equivalent_hours"):
            bucket[metric_key] = round(bucket[metric_key], 2)
        frequency_breakdown.append(bucket)

    scoped_routines.sort(key=lambda item: item.get("weekly_equivalent_hours", 0), reverse=True)
    return {
        **routine_section,
        "frequency_breakdown": frequency_breakdown,
        "top_routines": scoped_routines[:8],
        "all_routines": scoped_routines,
        "total_fixed_weekly_hours": round(sum(item.get("weekly_equivalent_hours", 0.0) for item in scoped_routines), 2),
        "routine_count": len(scoped_routines),
    }


def _apply_scope_to_project_section(project_section: Dict[str, Any], scoped_employee_ids: set[int]) -> Dict[str, Any]:
    if not scoped_employee_ids:
        return {**project_section, "top_projects": [], "open_task_count": 0, "estimated_hours_total": 0.0, "worked_hours_total": 0.0}

    allocations = [
        item
        for item in project_section.get("member_allocations", [])
        if _safe_int(item.get("employee_id")) in scoped_employee_ids
    ]
    project_totals: Dict[int, Dict[str, Any]] = {}
    task_ids = set()

    for item in allocations:
        task_id = _safe_int(item.get("task_id"))
        if task_id is not None:
            task_ids.add(task_id)
        project_id = _safe_int(item.get("project_id")) or 0
        project_entry = project_totals.setdefault(
            project_id,
            {
                "project_id": project_id,
                "project_name": item.get("project_name") or "Projeto",
                "task_ids": set(),
                "estimated_hours": 0.0,
                "worked_hours": 0.0,
            },
        )
        if task_id is not None:
            project_entry["task_ids"].add(task_id)
        project_entry["estimated_hours"] += _safe_float(item.get("estimated_hours"))
        project_entry["worked_hours"] += _safe_float(item.get("worked_hours"))

    top_projects = []
    for item in project_totals.values():
        top_projects.append({
            "project_id": item["project_id"],
            "project_name": item["project_name"],
            "task_count": len(item["task_ids"]),
            "estimated_hours": round(item["estimated_hours"], 2),
            "worked_hours": round(item["worked_hours"], 2),
        })
    top_projects.sort(key=lambda item: item["estimated_hours"], reverse=True)

    return {
        **project_section,
        "open_task_count": len(task_ids),
        "estimated_hours_total": round(sum(_safe_float(item.get("estimated_hours")) for item in allocations), 2),
        "worked_hours_total": round(sum(_safe_float(item.get("worked_hours")) for item in allocations), 2),
        "top_projects": top_projects[:8],
    }


def _apply_scope_to_meeting_section(meeting_section: Dict[str, Any], scoped_employee_ids: set[int]) -> Dict[str, Any]:
    if not scoped_employee_ids:
        return {**meeting_section, "top_meetings": [], "meeting_details": [], "open_meeting_count": 0, "scheduled_meeting_count": 0, "estimated_hours_total": 0.0}

    scoped_meetings = []
    scoped_total = 0.0
    scheduled_count = 0

    for item in meeting_section.get("meeting_details", []):
        matched_ids = [_safe_int(employee_id) for employee_id in item.get("matched_employee_ids", [])]
        scope_matches = [employee_id for employee_id in matched_ids if employee_id in scoped_employee_ids]
        if not scope_matches:
            continue

        matched_count = len([employee_id for employee_id in matched_ids if employee_id is not None]) or 1
        scoped_hours = round(_safe_float(item.get("estimated_hours")) * (len(scope_matches) / matched_count), 2)
        scoped_item = {**item, "scoped_estimated_hours": scoped_hours}
        scoped_meetings.append(scoped_item)
        scoped_total += scoped_hours
        if item.get("scheduled_date"):
            scheduled_count += 1

    scoped_meetings.sort(key=lambda item: item.get("scoped_estimated_hours", item.get("estimated_hours", 0)), reverse=True)
    top_meetings = [
        {**item, "estimated_hours": item.get("scoped_estimated_hours", item.get("estimated_hours", 0.0))}
        for item in scoped_meetings[:8]
    ]

    return {
        **meeting_section,
        "open_meeting_count": len(scoped_meetings),
        "scheduled_meeting_count": scheduled_count,
        "estimated_hours_total": round(scoped_total, 2),
        "top_meetings": top_meetings,
        "meeting_details": scoped_meetings,
    }


def _build_employee_drilldown(
    employee_id: int | None,
    employee_by_id: Dict[int, Dict[str, Any]],
    routine_section: Dict[str, Any],
    project_section: Dict[str, Any],
    meeting_section: Dict[str, Any],
) -> Dict[str, Any] | None:
    if not employee_id or employee_id not in employee_by_id:
        return None

    employee = employee_by_id[employee_id]
    routine_groups_map: Dict[str, Dict[str, Any]] = {}
    group_order = [
        ('daily', 'Rotinas diárias'),
        ('weekly', 'Rotinas semanais'),
        ('monthly', 'Rotinas mensais'),
        ('quarterly', 'Rotinas trimestrais'),
        ('yearly', 'Rotinas anuais'),
        ('specific', 'Rotinas específicas'),
    ]

    for routine in routine_section.get("all_routines", []):
        match = next((item for item in routine.get("collaborators", []) if _safe_int(item.get("employee_id")) == employee_id), None)
        if not match:
            continue

        schedule_type = routine.get("schedule_type") or "weekly"
        group = routine_groups_map.setdefault(
            schedule_type,
            {
                "key": schedule_type,
                "title": dict(group_order).get(schedule_type, f"Rotinas {routine.get('schedule_label', schedule_type)}"),
                "total_hours": 0.0,
                "items": [],
            },
        )
        hours_per_occurrence = round(_safe_float(match.get("hours_used")), 2)
        group["total_hours"] += hours_per_occurrence
        group["items"].append({
            "id": routine["id"],
            "name": routine["name"],
            "process_name": routine["process_name"],
            "schedule_label": routine["schedule_label"],
            "schedule_description": routine.get("schedule_description") or _describe_schedule(schedule_type, routine.get("schedule_value")),
            "hours_per_occurrence": hours_per_occurrence,
            "hours_label": _humanize_hours(hours_per_occurrence),
            "weekly_equivalent_hours": round(hours_per_occurrence * _schedule_weekly_factor(schedule_type), 2),
        })

    routine_groups = []
    for key, title in group_order:
        group = routine_groups_map.get(key)
        if not group:
            continue
        group["items"].sort(key=lambda item: (item.get("hours_per_occurrence", 0), item.get("name", "")), reverse=True)
        group["total_hours"] = round(group["total_hours"], 2)
        group["total_hours_label"] = _humanize_hours(group["total_hours"])
        group["title"] = title
        routine_groups.append(group)

    project_items = [
        item for item in project_section.get("member_allocations", [])
        if _safe_int(item.get("employee_id")) == employee_id
    ]
    project_items.sort(key=lambda item: item.get("estimated_hours", 0), reverse=True)

    meeting_items = [
        {
            "id": item["id"],
            "title": item["title"],
            "project_name": item["project_name"],
            "scheduled_date": item["scheduled_date"],
            "scheduled_time": item["scheduled_time"],
            "estimated_hours": item["estimated_hours"],
            "duration_source": item["duration_source"],
        }
        for item in meeting_section.get("meeting_details", [])
        if employee_id in item.get("matched_employee_ids", [])
    ]
    meeting_items.sort(key=lambda item: item.get("estimated_hours", 0), reverse=True)

    return {
        "employee": {
            "id": employee_id,
            "name": employee.get("name") or "Colaborador",
            "department": employee.get("department") or "Não informado",
            "email": employee.get("email") or "",
        },
        "routine_groups": routine_groups,
        "routines": [item for group in routine_groups for item in group["items"]][:10],
        "projects": project_items[:10],
        "meetings": meeting_items[:10],
    }


def get_routine_analysis(company_id: int, department: str | None = None, employee_id: int | None = None) -> Dict[str, Any]:
    conn = _get_pg_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        employees, employee_by_id, employee_by_email = _load_employees(cursor, company_id)
        filtered_employees = _apply_employee_filters(employees, department, employee_id)
        scoped_employee_ids = _get_scoped_employee_ids(filtered_employees)
        filter_metadata = _build_filter_metadata(employees, department, employee_id)
        routine_section = _build_routine_section(_load_routines(cursor, company_id))
        project_section = _load_project_section(cursor, company_id)
        meeting_section = _load_meeting_section(cursor, company_id, employee_by_id, employee_by_email)
        scoped_routine_section = _apply_scope_to_routine_section(routine_section, scoped_employee_ids) if (department or employee_id) else routine_section
        scoped_project_section = _apply_scope_to_project_section(project_section, scoped_employee_ids) if (department or employee_id) else project_section
        scoped_meeting_section = _apply_scope_to_meeting_section(meeting_section, scoped_employee_ids) if (department or employee_id) else meeting_section
        member_section = _build_member_capacity_section(
            filtered_employees,
            routine_section["member_fixed_hours"],
            project_section["member_project_hours"],
            meeting_section["member_meeting_hours"],
        )

        project_hours_scope = sum(
            project_section["member_project_hours"].get(member["employee_id"], 0.0)
            for member in member_section["members"]
        )
        meeting_hours_scope = sum(
            meeting_section["member_meeting_hours"].get(member["employee_id"], 0.0)
            for member in member_section["members"]
        )

        summary = {
            **member_section["summary"],
            "routine_count": scoped_routine_section["routine_count"],
            "open_project_hours": project_section["estimated_hours_total"],
            "open_project_task_count": project_section["open_task_count"],
            "open_meeting_count": meeting_section["open_meeting_count"],
            "scheduled_meeting_count": meeting_section["scheduled_meeting_count"],
            "meeting_estimated_hours_total": meeting_section["estimated_hours_total"],
            "scoped_project_hours": round(project_hours_scope, 2),
            "scoped_meeting_hours": round(meeting_hours_scope, 2),
            "scope_label": filter_metadata["scope_label"],
        }

        total_commitment = summary["total_fixed_weekly_hours"] + summary["scoped_project_hours"] + summary["scoped_meeting_hours"]
        summary["scoped_total_commitment_hours"] = round(total_commitment, 2)
        summary["scoped_total_utilization_percent"] = round((total_commitment / summary["total_capacity_weekly_hours"]) * 100, 1) if summary["total_capacity_weekly_hours"] else 0.0

        drilldown = _build_employee_drilldown(employee_id, employee_by_id, routine_section, project_section, meeting_section)

        charts = {
            "capacity": {
                "labels": ["Capacidade semanal", "Rotina fixa", "Saldo disponível"],
                "values": [
                    summary["total_capacity_weekly_hours"],
                    summary["total_fixed_weekly_hours"],
                    summary["total_available_weekly_hours"],
                ],
            },
            "commitment": {
                "labels": ["Rotina fixa", "Projetos", "Reuniões"],
                "values": [
                    summary["total_fixed_weekly_hours"],
                    summary["scoped_project_hours"],
                    summary["scoped_meeting_hours"],
                ],
            },
        }

        return {
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "summary": summary,
            "frequency_breakdown": scoped_routine_section["frequency_breakdown"],
            "fixed_routines": {
                "top_routines": scoped_routine_section["top_routines"],
            },
            "projects": {
                "open_task_count": scoped_project_section["open_task_count"],
                "estimated_hours_total": scoped_project_section["estimated_hours_total"],
                "worked_hours_total": scoped_project_section["worked_hours_total"],
                "top_projects": scoped_project_section["top_projects"],
            },
            "meetings": {
                "open_meeting_count": scoped_meeting_section["open_meeting_count"],
                "scheduled_meeting_count": scoped_meeting_section["scheduled_meeting_count"],
                "estimated_hours_total": scoped_meeting_section["estimated_hours_total"],
                "top_meetings": scoped_meeting_section["top_meetings"],
                "estimation_basis": scoped_meeting_section["estimation_basis"],
            },
            "filters": filter_metadata,
            "charts": charts,
            "bottlenecks": member_section["top_bottlenecks"],
            "drilldown": drilldown,
            "members": member_section["members"],
        }
    finally:
        conn.close()
