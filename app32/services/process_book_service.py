from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from models import (
    Company,
    Employee,
    Indicator,
    IndicatorData,
    IndicatorGoal,
    Process,
    ProcessBpmnDiagram,
    ProcessRoutine,
    ProcessStep,
    Routine,
    RoutineCollaborator,
)
from services.process_bpmn_service import sanitize_svg_snapshot
from services.process_sipoc_service import build_book_sipoc_context
from utils.indicator_filters import PROCESS_SOURCE_MODULES, build_indicator_process_filter


STRUCTURING_LABELS = {
    "inbox": "Inbox",
    "initiated": "Iniciado",
    "in_progress": "Em estruturação",
    "structured": "Estruturado",
    "stabilized": "Estabilizado",
    "stable": "Estável",
}

PERFORMANCE_LABELS = {
    "critical": "Crítico",
    "below": "Abaixo do esperado",
    "satisfactory": "Satisfatório",
}

SCHEDULE_LABELS = {
    "daily": "Diária",
    "weekly": "Semanal",
    "monthly": "Mensal",
    "quarterly": "Trimestral",
    "yearly": "Anual",
    "specific": "Data específica",
}

WEEKDAY_LABELS = {
    "monday": "Segunda",
    "tuesday": "Terça",
    "wednesday": "Quarta",
    "thursday": "Quinta",
    "friday": "Sexta",
    "saturday": "Sábado",
    "sunday": "Domingo",
    "mon": "Seg",
    "tue": "Ter",
    "wed": "Qua",
    "thu": "Qui",
    "fri": "Sex",
    "sat": "Sáb",
    "sun": "Dom",
}

POP_IMAGE_WIDTH_DEFAULT = 280
POP_IMAGE_WIDTH_MIN = 140
POP_IMAGE_WIDTH_MAX = 560


@dataclass(frozen=True)
class ProcessBookContext:
    process: Process
    company: Company
    generated_at: str
    first_page: dict[str, Any]
    sipoc: dict[str, Any] | None
    pop_activities: list[dict[str, Any]]
    routines: list[dict[str, Any]]
    indicators: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "process": self.process,
            "company": self.company,
            "generated_at": self.generated_at,
            "first_page": self.first_page,
            "sipoc": self.sipoc,
            "pop_activities": self.pop_activities,
            "routines": self.routines,
            "indicators": self.indicators,
        }


def build_process_book_context(process_id: int, company_id: int, request_root: str | None = None) -> dict[str, Any]:
    process = (
        Process.query.options(joinedload(Process.macro))
        .filter(Process.id == process_id, Process.company_id == company_id)
        .first()
    )
    if not process:
        raise ValueError("Processo não encontrado para a empresa ativa.")

    company = Company.query.filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Empresa não encontrada para o processo informado.")

    root_url = (request_root or "").rstrip("/")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    pop_activities = _load_pop_activities(process_id=process.id, company_id=company_id, root_url=root_url)
    routines = _load_routines(process_id=process.id, company_id=company_id)
    indicators = _load_indicators(process_id=process.id, company_id=company_id)
    sipoc = build_book_sipoc_context(process_id=process.id, company_id=company_id)

    context = ProcessBookContext(
        process=process,
        company=company,
        generated_at=generated_at,
        first_page=_build_first_page(
            process=process,
            company=company,
            generated_at=generated_at,
            root_url=root_url,
            pop_count=len(pop_activities),
            routine_count=len(routines),
            indicator_count=len(indicators),
        ),
        sipoc=sipoc,
        pop_activities=pop_activities,
        routines=routines,
        indicators=indicators,
    )
    return context.to_dict()


def _build_first_page(
    *,
    process: Process,
    company: Company,
    generated_at: str,
    root_url: str,
    pop_count: int,
    routine_count: int,
    indicator_count: int,
) -> dict[str, Any]:
    macro = getattr(process, "macro", None)
    area = getattr(macro, "area", None) if macro else None

    flow_url = _resolve_asset_url(getattr(process, "flow_document", None), root_url=root_url)
    flow_extension = _extract_extension(getattr(process, "flow_document", None))
    bpmn_diagram = _load_book_bpmn_diagram(process_id=process.id, company_id=process.company_id)

    return {
        "title": _compose_process_title(process.code, process.name),
        "subtitle": process.description or "Documentação consolidada do processo, incluindo fluxo, POP, rotinas e indicadores.",
        "generated_at": generated_at,
        "company_name": company.name,
        "area_name": _compose_process_title(getattr(area, "code", None), getattr(area, "name", None), fallback="Não definido"),
        "macro_name": _compose_process_title(getattr(macro, "code", None), getattr(macro, "name", None), fallback="Não definido"),
        "owner_name": getattr(macro, "owner", None) or "Não definido",
        "responsible_name": process.responsible or "Não definido",
        "structuring_label": STRUCTURING_LABELS.get((process.structuring_level or "").lower(), "Não informado"),
        "performance_label": PERFORMANCE_LABELS.get((process.performance_level or "").lower(), "Não informado"),
        "notes": process.notes,
        "flow_url": flow_url,
        "flow_is_image": flow_extension in {"png", "jpg", "jpeg", "webp", "gif", "svg"},
        "flow_is_pdf": flow_extension == "pdf",
        "bpmn_svg": sanitize_svg_snapshot(bpmn_diagram.svg_snapshot) if bpmn_diagram and bpmn_diagram.svg_snapshot else None,
        "bpmn_status": bpmn_diagram.status if bpmn_diagram else None,
        "bpmn_version": bpmn_diagram.version if bpmn_diagram else None,
        "stats": [
            {"label": "Atividades POP", "value": pop_count},
            {"label": "Rotinas", "value": routine_count},
            {"label": "Indicadores", "value": indicator_count},
        ],
    }


def _load_book_bpmn_diagram(*, process_id: int, company_id: int) -> ProcessBpmnDiagram | None:
    published = (
        ProcessBpmnDiagram.query.filter_by(
            company_id=company_id,
            process_id=process_id,
            status="published",
        )
        .order_by(ProcessBpmnDiagram.version.desc(), ProcessBpmnDiagram.updated_at.desc())
        .first()
    )
    if published:
        return published

    return (
        ProcessBpmnDiagram.query.filter_by(
            company_id=company_id,
            process_id=process_id,
            status="draft",
        )
        .order_by(ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )


def _load_pop_activities(*, process_id: int, company_id: int, root_url: str) -> list[dict[str, Any]]:
    routines = (
        ProcessRoutine.query.filter(
            ProcessRoutine.company_id == company_id,
            ProcessRoutine.process_id == process_id,
            or_(ProcessRoutine.is_active.is_(True), ProcessRoutine.is_active.is_(None)),
        )
        .order_by(ProcessRoutine.order_index.asc(), ProcessRoutine.id.asc())
        .all()
    )

    if not routines:
        return []

    routine_ids = [routine.id for routine in routines]
    steps = (
        ProcessStep.query.filter(ProcessStep.routine_id.in_(routine_ids))
        .order_by(ProcessStep.routine_id.asc(), ProcessStep.order_index.asc(), ProcessStep.id.asc())
        .all()
    )

    steps_by_routine: dict[int, list[dict[str, Any]]] = {}
    for step in steps:
        image_width = _coerce_pop_image_width(step.image_width)
        steps_by_routine.setdefault(step.routine_id, []).append(
            {
                "name": step.name,
                "description": step.description,
                "expected_result": step.expected_result,
                "layout": step.layout or "single",
                "image_url": _resolve_asset_url(step.image_path, root_url=root_url),
                "image_width": image_width,
                "text_content": _join_non_empty(
                    [
                        step.description,
                        f"Resultado esperado: {step.expected_result}" if step.expected_result else None,
                    ]
                ),
            }
        )

    return [
        {
            "id": routine.id,
            "code": routine.code or "-",
            "name": routine.name,
            "description": routine.description,
            "entries": steps_by_routine.get(routine.id, []),
        }
        for routine in routines
    ]


def _coerce_pop_image_width(value: Any) -> int:
    try:
        width = int(value or POP_IMAGE_WIDTH_DEFAULT)
    except (TypeError, ValueError):
        width = POP_IMAGE_WIDTH_DEFAULT
    return max(POP_IMAGE_WIDTH_MIN, min(width, POP_IMAGE_WIDTH_MAX))


def _load_routines(*, process_id: int, company_id: int) -> list[dict[str, Any]]:
    routines = (
        Routine.query.filter(
            Routine.company_id == company_id,
            Routine.process_id == process_id,
            or_(Routine.is_active.is_(True), Routine.is_active.is_(None)),
        )
        .order_by(Routine.order_index.asc(), Routine.id.asc())
        .all()
    )

    if not routines:
        return []

    routine_ids = [routine.id for routine in routines]
    collaborator_rows = (
        RoutineCollaborator.query.join(
            Employee,
            and_(
                Employee.id == RoutineCollaborator.employee_id,
                Employee.company_id == company_id,
            ),
        )
        .filter(RoutineCollaborator.routine_id.in_(routine_ids))
        .add_entity(Employee)
        .all()
    )

    collaborators_by_routine: dict[int, list[dict[str, Any]]] = {}
    for collaborator, employee in collaborator_rows:
        collaborators_by_routine.setdefault(collaborator.routine_id, []).append(
            {
                "employee_name": employee.name,
                "employee_email": employee.email,
                "hours_used": _format_number(collaborator.hours_used),
                "notes": collaborator.notes,
            }
        )

    payload = []
    for routine in routines:
        collaborators = collaborators_by_routine.get(routine.id, [])
        total_hours = sum(float(item["hours_used"].replace(",", ".")) for item in collaborators) if collaborators else 0
        payload.append(
            {
                "id": routine.id,
                "code": routine.code or "-",
                "name": routine.name,
                "description": routine.description,
                "schedule_type": routine.schedule_type,
                "schedule_label": SCHEDULE_LABELS.get((routine.schedule_type or "").lower(), routine.schedule_type or "Não definido"),
                "schedule_value": routine.schedule_value,
                "start_time": routine.start_time,
                "schedule_detail": _format_schedule_detail(routine.schedule_type, routine.schedule_value, routine.start_time),
                "schedule_summary": _format_schedule_summary(routine.schedule_type, routine.schedule_value, routine.start_time),
                "deadline_days": routine.deadline_days or 0,
                "deadline_hours": routine.deadline_hours or 0,
                "deadline_date": routine.deadline_date.strftime("%d/%m/%Y") if routine.deadline_date else None,
                "total_hours": _format_number(total_hours),
                "collaborators": collaborators,
            }
        )

    return payload


def _load_indicators(*, process_id: int, company_id: int) -> list[dict[str, Any]]:
    indicators = (
        Indicator.query.options(joinedload(Indicator.group))
        .filter(Indicator.company_id == company_id)
        .filter(_build_indicator_process_filter(process_id))
        .order_by(Indicator.code.asc(), Indicator.id.asc())
        .all()
    )

    payload = []
    for indicator in indicators:
        latest_goal = (
            IndicatorGoal.query.filter(
                IndicatorGoal.company_id == company_id,
                IndicatorGoal.indicator_id == indicator.id,
            )
            .order_by(IndicatorGoal.goal_date.desc(), IndicatorGoal.created_at.desc())
            .first()
        )

        latest_record = (
            IndicatorData.query.filter(
                IndicatorData.company_id == company_id,
                IndicatorData.indicator_id == indicator.id,
            )
            .order_by(IndicatorData.measured_date.desc(), IndicatorData.created_at.desc())
            .first()
        )

        payload.append(
            {
                "code": indicator.code,
                "name": indicator.name,
                "group_name": indicator.group.name if indicator.group else None,
                "unit": indicator.unit,
                "formula": indicator.formula,
                "data_source": indicator.data_source,
                "polarity": indicator.polarity,
                "current_value": _format_indicator_value(latest_record.measured_value if latest_record else None, indicator.unit),
                "goal_value": _format_indicator_value(latest_goal.goal_value if latest_goal else None, indicator.unit),
                "goal_date": latest_goal.goal_date.strftime("%d/%m/%Y") if latest_goal and latest_goal.goal_date else None,
                "last_record_date": latest_record.measured_date.strftime("%d/%m/%Y") if latest_record and latest_record.measured_date else None,
            }
        )

    return payload


def _build_indicator_process_filter(process_id: int):
    if hasattr(Indicator, "source_module") and hasattr(Indicator, "source_id"):
        return or_(
            Indicator.process_id == process_id,
            and_(
                Indicator.source_module.in_(PROCESS_SOURCE_MODULES),
                Indicator.source_id == process_id,
            ),
        )
    return build_indicator_process_filter(process_id)


def _resolve_asset_url(path: str | None, *, root_url: str) -> str | None:
    if not path:
        return None

    normalized = str(path).strip().replace("\\", "/")
    if not normalized:
        return None
    if normalized.startswith(("http://", "https://", "data:")):
        return normalized
    if normalized.startswith("/uploads/") or normalized.startswith("/static/"):
        return f"{root_url}{normalized}" if root_url else normalized
    if normalized.startswith("uploads/") or normalized.startswith("static/"):
        return f"{root_url}/{normalized}" if root_url else f"/{normalized}"
    return f"{root_url}/uploads/{normalized}" if root_url else f"/uploads/{normalized}"


def _format_schedule_summary(schedule_type: str | None, schedule_value: str | None, start_time: str | None = None) -> str:
    label = SCHEDULE_LABELS.get((schedule_type or "").strip().lower(), schedule_type or "Não definido")
    detail = _format_schedule_detail(schedule_type, schedule_value, start_time)
    if not detail:
        return label
    return f"{label} · {detail}"


def _format_schedule_detail(schedule_type: str | None, schedule_value: str | None, start_time: str | None = None) -> str | None:
    normalized_type = str(schedule_type or "").strip().lower()
    raw_value = str(schedule_value or "").strip()
    raw_start_time = str(start_time or "").strip()
    time_suffix = f" às {raw_start_time}" if raw_start_time else ""

    if normalized_type == "daily":
        return raw_start_time or None

    if normalized_type == "weekly":
        weekdays = ", ".join(_normalize_weekday_label(part) for part in raw_value.split(",") if str(part).strip())
        return f"{weekdays}{time_suffix}" if weekdays else (raw_start_time or None)

    if normalized_type == "monthly":
        try:
            day = int(raw_value)
            return f"Dia {day}{time_suffix}"
        except (TypeError, ValueError):
            return f"{raw_value}{time_suffix}" if raw_value else (raw_start_time or None)

    if normalized_type == "quarterly":
        try:
            month_in_quarter_raw, day_raw = raw_value.split("-", 1)
            month_in_quarter = int(month_in_quarter_raw)
            day = int(day_raw)
            return f"Mês {month_in_quarter} do trimestre · Dia {day}{time_suffix}"
        except (AttributeError, TypeError, ValueError):
            return f"{raw_value}{time_suffix}" if raw_value else (raw_start_time or None)

    if normalized_type == "yearly":
        try:
            day_raw, month_raw = raw_value.split("/", 1)
            day = int(day_raw)
            month = int(month_raw)
            return f"{day:02d}/{month:02d}{time_suffix}"
        except (AttributeError, TypeError, ValueError):
            return f"{raw_value}{time_suffix}" if raw_value else (raw_start_time or None)

    if normalized_type == "specific":
        formatted_date = _format_specific_schedule_date(raw_value)
        if formatted_date:
            return f"{formatted_date}{time_suffix}"
        return f"{raw_value}{time_suffix}" if raw_value else (raw_start_time or None)

    return f"{raw_value}{time_suffix}" if raw_value else (raw_start_time or None)


def _format_specific_schedule_date(raw_value: str) -> str | None:
    if not raw_value:
        return None
    normalized = raw_value[:10]
    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.strftime("%d/%m/%Y")


def _normalize_weekday_label(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return WEEKDAY_LABELS.get(normalized.lower(), normalized)


def _extract_extension(path: str | None) -> str:
    if not path or "." not in str(path):
        return ""
    return str(path).rsplit(".", 1)[-1].lower()


def _compose_process_title(code: str | None, name: str | None, fallback: str = "Não definido") -> str:
    safe_name = (name or "").strip()
    safe_code = (code or "").strip()
    if safe_code and safe_name:
        return f"{safe_code} - {safe_name}"
    if safe_name:
        return safe_name
    if safe_code:
        return safe_code
    return fallback


def _join_non_empty(parts: list[str | None]) -> str | None:
    cleaned = [str(part).strip() for part in parts if part and str(part).strip()]
    if not cleaned:
        return None
    return "\n\n".join(cleaned)


def _format_number(value: Any) -> str:
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}".replace(".", ",")
    return str(value)


def _format_indicator_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "Não informado"
    formatted = _format_number(value)
    if unit:
        return f"{formatted} {unit}"
    return formatted
