from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Iterable


STATUS_LABELS = {
    "draft": "Rascunho",
    "in_progress": "Em andamento",
    "completed": "Concluída",
}


def build_meeting_report_context(meeting_data: dict[str, Any] | None, employees: Iterable[Any] | None = None) -> dict[str, Any]:
    data = dict(meeting_data or {})
    employees_by_id, employees_by_name = _build_employee_maps(employees or [])
    guests_bucket = _normalize_people_bucket(data.get("guests"))
    participants_bucket = _normalize_people_bucket(data.get("participants"))

    attendees = _build_attendees(
        guests_bucket=guests_bucket,
        participants_bucket=participants_bucket,
        employees_by_id=employees_by_id,
        employees_by_name=employees_by_name,
    )

    project_label = _build_project_label(data)
    scheduled_for = _format_date_and_time(data.get("scheduled_date"), data.get("scheduled_time"))
    scheduled_recorded_at = _format_datetime_value(data.get("created_at"))
    actual_started_at = _format_date_and_time(data.get("actual_date"), data.get("actual_time"))
    actual_finished_at = _format_end_datetime(
        data.get("actual_date"),
        data.get("actual_time"),
        data.get("actual_duration_minutes"),
    )

    scheduling_items = [
        {
            "label": "Data e hora prevista",
            "value": scheduled_for or "Não informado",
        }
    ]
    if scheduled_recorded_at:
        scheduling_items.append(
            {
                "label": "Registro no sistema",
                "value": scheduled_recorded_at,
            }
        )

    return {
        "title": _clean_text(data.get("title")) or "Sem título",
        "project_label": project_label,
        "status_label": _status_label(data.get("status")),
        "dates": {
            "scheduling": {
                "title": "Agendamento",
                "items": scheduling_items,
            },
            "execution": {
                "title": "Realização",
                "items": [
                    {
                        "label": "Início",
                        "value": actual_started_at or "Não informado",
                    },
                    {
                        "label": "Fim",
                        "value": actual_finished_at or "Não informado",
                    },
                    {
                        "label": "Status",
                        "value": _status_label(data.get("status")),
                    },
                ],
            },
        },
        "participants": attendees,
        "counts": {
            "invited": sum(1 for attendee in attendees if attendee["invited"]),
            "present": sum(1 for attendee in attendees if attendee["present"]),
        },
    }


def _build_attendees(
    *,
    guests_bucket: dict[str, list[Any]],
    participants_bucket: dict[str, list[Any]],
    employees_by_id: dict[int, Any],
    employees_by_name: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    attendee_store: dict[str, dict[str, Any]] = {}

    external_guest_contacts: dict[str, dict[str, str]] = {}
    for guest in guests_bucket["external"]:
        if not isinstance(guest, dict):
            continue
        normalized_name = _normalize_name_key(guest.get("name"))
        if normalized_name and normalized_name not in external_guest_contacts:
            external_guest_contacts[normalized_name] = {
                "email": _clean_text(guest.get("email")),
                "phone": _first_not_empty(guest.get("phone"), guest.get("whatsapp")),
            }

    for guest in guests_bucket["internal"]:
        if not isinstance(guest, dict):
            continue
        employee_id, employee = _resolve_internal_employee(guest, employees_by_id, employees_by_name)
        _merge_attendee(
            attendee_store,
            {
                "key": _build_attendee_key(
                    employee_id=employee_id,
                    email=_clean_text(guest.get("email")) or _employee_value(employee, "email"),
                    phone=_first_not_empty(
                        guest.get("phone"),
                        guest.get("whatsapp"),
                        _employee_value(employee, "phone"),
                        _employee_value(employee, "whatsapp"),
                    ),
                    name=_clean_text(guest.get("name")) or _employee_value(employee, "name"),
                    attendee_type="Colaborador",
                ),
                "name": _clean_text(guest.get("name")) or _employee_value(employee, "name") or "Colaborador",
                "email": _clean_text(guest.get("email")) or _employee_value(employee, "email"),
                "phone": _first_not_empty(
                    guest.get("phone"),
                    guest.get("whatsapp"),
                    _employee_value(employee, "phone"),
                    _employee_value(employee, "whatsapp"),
                ),
                "type_label": "Colaborador",
                "invited": True,
                "present": False,
            },
        )

    for participant in participants_bucket["internal"]:
        if not isinstance(participant, dict):
            continue
        employee_id, employee = _resolve_internal_employee(participant, employees_by_id, employees_by_name)
        _merge_attendee(
            attendee_store,
            {
                "key": _build_attendee_key(
                    employee_id=employee_id,
                    email=_clean_text(participant.get("email")) or _employee_value(employee, "email"),
                    phone=_first_not_empty(
                        participant.get("phone"),
                        participant.get("whatsapp"),
                        _employee_value(employee, "phone"),
                        _employee_value(employee, "whatsapp"),
                    ),
                    name=_clean_text(participant.get("name")) or _employee_value(employee, "name"),
                    attendee_type="Colaborador",
                ),
                "name": _clean_text(participant.get("name")) or _employee_value(employee, "name") or "Colaborador",
                "email": _clean_text(participant.get("email")) or _employee_value(employee, "email"),
                "phone": _first_not_empty(
                    participant.get("phone"),
                    participant.get("whatsapp"),
                    _employee_value(employee, "phone"),
                    _employee_value(employee, "whatsapp"),
                ),
                "type_label": "Colaborador",
                "invited": False,
                "present": True,
            },
        )

    for guest in guests_bucket["external"]:
        if not isinstance(guest, dict):
            continue
        _merge_attendee(
            attendee_store,
            {
                "key": _build_attendee_key(
                    email=_clean_text(guest.get("email")),
                    phone=_first_not_empty(guest.get("phone"), guest.get("whatsapp")),
                    name=_clean_text(guest.get("name")),
                    attendee_type="Externo",
                ),
                "name": _clean_text(guest.get("name")) or "Convidado externo",
                "email": _clean_text(guest.get("email")),
                "phone": _first_not_empty(guest.get("phone"), guest.get("whatsapp")),
                "type_label": "Externo",
                "invited": True,
                "present": False,
            },
        )

    for participant in participants_bucket["external"]:
        if not isinstance(participant, dict):
            continue
        normalized_name = _normalize_name_key(participant.get("name"))
        guest_fallback = external_guest_contacts.get(normalized_name, {})
        _merge_attendee(
            attendee_store,
            {
                "key": _build_attendee_key(
                    email=_clean_text(participant.get("email")) or guest_fallback.get("email"),
                    phone=_first_not_empty(
                        participant.get("phone"),
                        participant.get("whatsapp"),
                        guest_fallback.get("phone"),
                    ),
                    name=_clean_text(participant.get("name")),
                    attendee_type="Externo",
                ),
                "name": _clean_text(participant.get("name")) or "Participante externo",
                "email": _clean_text(participant.get("email")) or guest_fallback.get("email"),
                "phone": _first_not_empty(
                    participant.get("phone"),
                    participant.get("whatsapp"),
                    guest_fallback.get("phone"),
                ),
                "type_label": "Externo",
                "invited": False,
                "present": True,
            },
        )

    attendees = list(attendee_store.values())
    attendees.sort(
        key=lambda item: (
            item["name"].lower(),
            not item["invited"],
            not item["present"],
        )
    )
    return attendees


def _merge_attendee(attendee_store: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    existing = attendee_store.get(payload["key"])
    if not existing:
        attendee_store[payload["key"]] = {
            "name": payload["name"],
            "email": _clean_text(payload.get("email")),
            "phone": _format_phone(payload.get("phone")),
            "type_label": payload["type_label"],
            "invited": bool(payload.get("invited")),
            "present": bool(payload.get("present")),
        }
        return

    if not existing.get("email") and payload.get("email"):
        existing["email"] = _clean_text(payload["email"])
    if not existing.get("phone") and payload.get("phone"):
        existing["phone"] = _format_phone(payload["phone"])
    if not existing.get("name") and payload.get("name"):
        existing["name"] = payload["name"]

    existing["invited"] = existing["invited"] or bool(payload.get("invited"))
    existing["present"] = existing["present"] or bool(payload.get("present"))


def _build_employee_maps(employees: Iterable[Any]) -> tuple[dict[int, Any], dict[str, list[Any]]]:
    by_id: dict[int, Any] = {}
    by_name: dict[str, list[Any]] = {}

    for employee in employees:
        employee_id = _parse_optional_int(_employee_value(employee, "id"))
        if employee_id is not None:
            by_id[employee_id] = employee

        normalized_name = _normalize_name_key(_employee_value(employee, "name"))
        if normalized_name:
            by_name.setdefault(normalized_name, []).append(employee)

    return by_id, by_name


def _resolve_internal_employee(person: dict[str, Any], employees_by_id: dict[int, Any], employees_by_name: dict[str, list[Any]]) -> tuple[int | None, Any]:
    employee_id = _parse_optional_int(person.get("employee_id") or person.get("id"))
    if employee_id is not None and employee_id in employees_by_id:
        return employee_id, employees_by_id[employee_id]

    normalized_name = _normalize_name_key(person.get("name"))
    if normalized_name:
        matches = employees_by_name.get(normalized_name) or []
        if len(matches) == 1:
            employee = matches[0]
            return _parse_optional_int(_employee_value(employee, "id")), employee

    return employee_id, None


def _normalize_people_bucket(raw_value: Any) -> dict[str, list[Any]]:
    if isinstance(raw_value, dict):
        internal = raw_value.get("internal")
        external = raw_value.get("external")
        return {
            "internal": internal if isinstance(internal, list) else [],
            "external": external if isinstance(external, list) else [],
        }
    if isinstance(raw_value, list):
        return {"internal": raw_value, "external": []}
    return {"internal": [], "external": []}


def _build_project_label(meeting_data: dict[str, Any]) -> str:
    project_title = _clean_text(meeting_data.get("project_title"))
    project_code = _clean_text(meeting_data.get("project_code"))
    if project_title and project_code:
        return f"{project_code} - {project_title}"
    return project_title or project_code


def _build_attendee_key(*, employee_id: int | None = None, email: Any = None, phone: Any = None, name: Any = None, attendee_type: str = "") -> str:
    if employee_id is not None:
        return f"employee:{employee_id}"

    normalized_email = _clean_text(email).lower()
    if normalized_email:
        return f"email:{normalized_email}"

    normalized_phone = _normalize_phone(phone)
    if normalized_phone:
        return f"phone:{normalized_phone}"

    normalized_name = _normalize_name_key(name)
    return f"name:{normalized_name or 'sem-nome'}:{attendee_type.lower()}"


def _format_date_and_time(date_value: Any, time_value: Any) -> str:
    date_label = _format_date_value(date_value)
    time_label = _clean_text(time_value)
    if date_label and time_label:
        return f"{date_label} às {time_label[:5]}"
    return date_label or time_label


def _format_end_datetime(date_value: Any, time_value: Any, duration_minutes: Any) -> str:
    start_dt = _combine_date_and_time(date_value, time_value)
    duration_int = _parse_optional_int(duration_minutes)
    if start_dt is None or duration_int is None:
        return ""
    return (start_dt + timedelta(minutes=duration_int)).strftime("%d/%m/%Y às %H:%M")


def _combine_date_and_time(date_value: Any, time_value: Any) -> datetime | None:
    raw_date = _clean_text(date_value)
    raw_time = _clean_text(time_value)
    if not raw_date or not raw_time:
        return None

    try:
        date_part = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
    except ValueError:
        return None

    raw_time = raw_time[:5]
    try:
        time_part = datetime.strptime(raw_time, "%H:%M").time()
    except ValueError:
        return None

    return datetime.combine(date_part, time_part)


def _format_date_value(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return raw


def _format_datetime_value(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return raw


def _format_phone(value: Any) -> str:
    digits = _normalize_phone(value)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return _clean_text(value)


def _status_label(value: Any) -> str:
    normalized = _clean_text(value).lower()
    return STATUS_LABELS.get(normalized, _clean_text(value) or "Sem status")


def _normalize_name_key(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value).lower())


def _normalize_phone(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _employee_value(employee: Any, field_name: str) -> Any:
    if employee is None:
        return None
    if isinstance(employee, dict):
        return employee.get(field_name)
    return getattr(employee, field_name, None)


def _first_not_empty(*values: Any) -> str:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _parse_optional_int(value: Any) -> int | None:
    try:
        if value in (None, "", []):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
