"""Helpers to assemble the routines overview context shared by dashboards."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config_database import get_db

logger = logging.getLogger(__name__)


def _normalize_assigned_roles(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _build_employee_cache(db, company_id: int) -> Dict[int, Dict[str, Any]]:
    cache: Dict[int, Dict[str, Any]] = {}
    list_employees = getattr(db, "list_employees", None)
    if callable(list_employees):
        for employee in list_employees(company_id) or []:
            employee_id = employee.get("id")
            if employee_id is not None:
                cache[employee_id] = employee
    return cache


def _load_routine_collaborators(
    db, routine_ids: List[int], employee_cache: Dict[int, Dict[str, Any]]
) -> Dict[int, List[Dict[str, Any]]]:
    """Return collaborators grouped by routine_id using routine_collaborators table."""
    if not routine_ids:
        return {}

    collab_map: Dict[int, List[Dict[str, Any]]] = {}
    conn = None
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        placeholders = ", ".join(["%s"] * len(routine_ids))
        cursor.execute(
            f"""
            SELECT
                rc.id,
                rc.routine_id,
                rc.employee_id,
                rc.hours_used,
                rc.notes,
                e.name AS employee_name
            FROM routine_collaborators rc
            LEFT JOIN employees e ON e.id = rc.employee_id
            WHERE rc.routine_id IN ({placeholders})
            ORDER BY e.name
        """,
            tuple(routine_ids),
        )

        for row in cursor.fetchall():
            routine_id = row.get("routine_id")
            employee_id = row.get("employee_id")
            hours = row.get("hours_used")
            try:
                numeric_hours = float(hours) if hours is not None else 0.0
            except (TypeError, ValueError):
                numeric_hours = 0.0

            name = row.get("employee_name")
            if not name and employee_id:
                cached = employee_cache.get(employee_id)
                name = cached.get("name") if cached else None

            collab_map.setdefault(routine_id, []).append(
                {
                    "id": row.get("id"),
                    "employee_id": employee_id,
                    "employee_name": name or f"Colaborador {employee_id or '?'}",
                    "hours": numeric_hours,
                    "notes": row.get("notes") or "",
                }
            )
    except Exception as exc:
        logger.warning("Failed to load routine collaborators: %s", exc)
    finally:
        if conn:
            conn.close()

    return collab_map


def build_routines_overview_context(
    company_id: int, company: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Return routines, headers and filter metadata for dashboards."""

    db = get_db()
    company_data = company or db.get_company(company_id) or {}

    list_fn = getattr(db, "list_routines", None)
    get_fn = getattr(db, "get_routines", None)
    routines = []
    if callable(list_fn):
        routines = list_fn(company_id) or []
    elif callable(get_fn):
        routines = get_fn(company_id) or []
    process_map = {row.get("id"): row for row in (db.list_processes(company_id) or [])}
    employee_cache = _build_employee_cache(db, company_id)
    routine_ids = [
        routine.get("id") for routine in routines if routine.get("id") is not None
    ]
    collaborators_map = _load_routine_collaborators(db, routine_ids, employee_cache)

    for routine in routines:
        process = process_map.get(routine.get("process_id"))
        if process:
            process_code = process.get("code", "")
            process_name = process.get("name", "")
            if process_code and process_name:
                routine["process_name"] = f"{process_code} - {process_name.upper()}"
            elif process_name:
                routine["process_name"] = process_name.upper()
            else:
                routine["process_name"] = "Processo sem título"
            routine["process_code"] = process_code
        else:
            routine["process_name"] = "Processo sem título"
            routine["process_code"] = None

        collaborators: List[Dict[str, Any]] = []
        total_hours = 0.0
        routine_id = routine.get("id")

        if routine_id in collaborators_map:
            for collab in collaborators_map.get(routine_id, []):
                try:
                    hours_val = float(collab.get("hours", 0))
                except (TypeError, ValueError):
                    hours_val = 0.0
                employee_id = collab.get("employee_id")
                employee_name = collab.get("employee_name")
                if not employee_name and employee_id:
                    cached = employee_cache.get(employee_id)
                    employee_name = cached.get("name") if cached else None

                collaborators.append(
                    {
                        "id": collab.get("id"),
                        "employee_id": employee_id,
                        "employee_name": employee_name
                        or f"Colaborador {employee_id or '?'}",
                        "hours": hours_val,
                        "notes": collab.get("notes", ""),
                    }
                )
                total_hours += hours_val
        else:
            assigned_roles = _normalize_assigned_roles(routine.get("assigned_roles"))
            for role in assigned_roles:
                employee_id = role.get("employee_id")
                employee_name = role.get("employee_name")
                if not employee_name and employee_id:
                    cached = employee_cache.get(employee_id)
                    employee_name = cached.get("name") if cached else None
                hours = role.get("hours")
                if hours is None:
                    hours = role.get("hours_used")
                try:
                    numeric_hours = float(hours)
                except (TypeError, ValueError):
                    numeric_hours = 0.0

                collaborators.append(
                    {
                        "employee_id": employee_id,
                        "employee_name": employee_name
                        or f"Colaborador {employee_id or '?'}",
                        "role": role.get("role"),
                        "hours": numeric_hours,
                    }
                )
                total_hours += numeric_hours

        routine["collaborators_count"] = len(collaborators)
        routine["collaborators"] = collaborators
        routine["estimated_hours"] = total_hours
        routine["trigger_type_label"] = (routine.get("trigger_type") or "manual").title()
        routine["status_label"] = (routine.get("status") or "pending").title()
        routine["frequency_label"] = (
            routine.get("frequency_label") or routine.get("frequency") or "N/D"
        )

    headers = [
        {"key": "process_name", "title": "Processo"},
        {"key": "name", "title": "Rotina"},
        {"key": "trigger_type", "title": "Gatilho"},
        {"key": "frequency_label", "title": "Frequência"},
        {"key": "collaborators", "title": "Colaboradores"},
        {"key": "estimated_hours", "title": "Horas"},
        {"key": "status", "title": "Status"},
        {"key": "next_run", "title": "Próxima execução"},
        {"key": "actions", "title": "Ações"},
    ]

    def collect_options(key: str, fallback: Optional[str] = None) -> List[str]:
        values = set()
        for routine in routines:
            value = routine.get(key) or fallback
            if value:
                values.add(value)
        return sorted(values)

    filter_options = {
        "trigger": collect_options("trigger_type", "manual"),
        "frequency": collect_options("frequency_label"),
        "status": collect_options("status", "pending"),
    }

    total_collaborators = sum(r.get("collaborators_count", 0) for r in routines)

    return {
        "company": company_data,
        "routines": routines,
        "headers": headers,
        "filter_options": filter_options,
        "total_collaborators": total_collaborators,
    }
