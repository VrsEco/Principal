from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app import create_app
from models import WorkCalendarEvent
from schemas.work_journey import WorkCalendarEventCreateSchema, WorkCalendarEventUpdateSchema
from services.efficiency_collaborators_service import get_efficiency_collaborators, parse_efficiency_period
from services.routine_analysis_service import get_routine_analysis
from services.work_calendar_event_service import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    update_calendar_event,
)
from services.work_journey_agenda_service import get_work_journey_agenda
from services.work_journey_base import WorkJourneyError
from services.work_journey_mcp_access_service import (
    ensure_employee_mutation_allowed,
    resolve_actor_scope,
)
from services.work_journey_report_service import build_work_journey_management_report


def _run(callback, *args, **kwargs) -> Any:
    app = create_app()
    with app.app_context():
        return callback(*args, **kwargs)


def _parse_date(raw_value: str | date | None) -> date | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, date):
        return raw_value
    return date.fromisoformat(str(raw_value))


def _event_payload(raw_payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    if partial:
        payload = WorkCalendarEventUpdateSchema.model_validate(raw_payload).model_dump(exclude_unset=True)
    else:
        payload = WorkCalendarEventCreateSchema.model_validate(raw_payload).model_dump()
    if "start_time" in payload and payload.get("start_time") not in (None, ""):
        payload["start_time"] = datetime.strptime(str(payload["start_time"]), "%H:%M").time()
    if "end_time" in payload and payload.get("end_time") not in (None, ""):
        payload["end_time"] = datetime.strptime(str(payload["end_time"]), "%H:%M").time()
    return payload


def _summarize_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total_items": len(items),
        "allocated_items": 0,
        "unassigned_items": 0,
        "overdue_items": 0,
        "calendar_event_items": 0,
        "planned_minutes": 0,
        "worked_minutes": 0,
    }
    for item in items:
        lane = str(item.get("lane") or "").strip().lower()
        if lane == "allocated":
            summary["allocated_items"] += 1
        elif lane == "unassigned":
            summary["unassigned_items"] += 1
        elif lane == "overdue":
            summary["overdue_items"] += 1
        if item.get("item_kind") == "calendar_event":
            summary["calendar_event_items"] += 1
        summary["planned_minutes"] += int(item.get("planned_minutes") or item.get("allocated_minutes") or item.get("estimated_minutes") or 0)
        summary["worked_minutes"] += int(item.get("worked_minutes") or 0)
    return summary


def _agenda_inventory_rows(agenda_payload: dict[str, Any], employee_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in agenda_payload.get("overdue_items") or []:
        rows.append({
            **item,
            "employee_id": employee_id,
            "lane": "overdue",
            "day_date": item.get("planned_date") or item.get("date"),
            "block_name": None,
        })
    for item in agenda_payload.get("unassigned_items") or []:
        rows.append({
            **item,
            "employee_id": employee_id,
            "lane": "unassigned",
            "day_date": item.get("planned_date") or item.get("date"),
            "block_name": None,
        })
    for day in agenda_payload.get("days") or []:
        for block in day.get("blocks") or []:
            for item in block.get("items") or []:
                rows.append({
                    **item,
                    "employee_id": employee_id,
                    "lane": "allocated",
                    "day_date": day.get("date"),
                    "block_id": block.get("id"),
                    "block_name": block.get("name"),
                    "block_mode": block.get("block_mode"),
                })
        for item in day.get("unassigned_items") or []:
            rows.append({
                **item,
                "employee_id": employee_id,
                "lane": "unassigned",
                "day_date": day.get("date"),
                "block_name": None,
            })
    return rows


def register_work_journey_analytics_tools(mcp: Any) -> None:
    @mcp.tool()
    def list_work_calendar_events_tool(
        company_id: int,
        employee_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        include_all: bool = False,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Lista eventos do calendário operacional respeitando o escopo do colaborador logado ou visibilidade privilegiada."""
        scope = _run(
            resolve_actor_scope,
            company_id=company_id,
            employee_id=employee_id,
            include_all=include_all,
            department=department,
            payload={
                "company_id": company_id,
                "employee_id": employee_id,
                "include_all": include_all,
                "department": department,
            },
        )
        scoped_start = _parse_date(start_date)
        scoped_end = _parse_date(end_date)
        employees_payload = []
        for scoped_employee_id in scope.employee_ids:
            events = _run(
                list_calendar_events,
                scope.company_id,
                scoped_employee_id,
                start_date=scoped_start,
                end_date=scoped_end,
                source_type=source_type,
                source_id=source_id,
            )
            employees_payload.append(
                {
                    "employee_id": scoped_employee_id,
                    "events": events,
                    "count": len(events),
                }
            )
        return {
            "company_id": scope.company_id,
            "scope": "all" if scope.privileged and (include_all or department) else "self_or_selected",
            "employees": employees_payload,
            "count": sum(item["count"] for item in employees_payload),
        }

    @mcp.tool()
    def create_work_calendar_event_tool(company_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Cria um evento de calendário operacional com validação de escopo do colaborador."""
        data = _event_payload(payload, partial=False)
        resolved_company_id, execution_context = _run(
            ensure_employee_mutation_allowed,
            company_id=company_id,
            employee_id=int(data["employee_id"]),
            payload={"company_id": company_id, **payload},
        )
        event = _run(
            create_calendar_event,
            resolved_company_id,
            data,
            execution_context.user_id,
        )
        return {"event": event}

    @mcp.tool()
    def update_work_calendar_event_tool(company_id: int, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Atualiza um evento do calendário operacional respeitando a visibilidade do colaborador."""
        data = _event_payload(payload, partial=True)
        current_event = _run(lambda: WorkCalendarEvent.query.filter_by(company_id=company_id, id=event_id).first())
        if not current_event:
            raise WorkJourneyError("Evento de calendário não encontrado.")
        target_employee_id = int(data.get("employee_id") or current_event.employee_id or 0)
        resolved_company_id, execution_context = _run(
            ensure_employee_mutation_allowed,
            company_id=company_id,
            employee_id=target_employee_id,
            payload={"company_id": company_id, **payload},
        )
        event = _run(
            update_calendar_event,
            resolved_company_id,
            event_id,
            data,
            getattr(execution_context, "user_id", None),
        )
        return {"event": event}

    @mcp.tool()
    def delete_work_calendar_event_tool(company_id: int, event_id: int, employee_id: int) -> dict[str, Any]:
        """Exclui um evento do calendário operacional respeitando o escopo do colaborador."""
        current_event = _run(lambda: WorkCalendarEvent.query.filter_by(company_id=company_id, id=event_id).first())
        if not current_event:
            raise WorkJourneyError("Evento de calendário não encontrado.")
        resolved_company_id, _execution_context = _run(
            ensure_employee_mutation_allowed,
            company_id=company_id,
            employee_id=int(current_event.employee_id or employee_id),
            payload={"company_id": company_id, "employee_id": int(current_event.employee_id or employee_id)},
        )
        _run(delete_calendar_event, resolved_company_id, event_id)
        return {"success": True}

    @mcp.tool()
    def list_work_journey_task_inventory_tool(
        company_id: int,
        employee_id: int | None = None,
        anchor_date: str | None = None,
        scope: str = "week",
        include_all: bool = False,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Retorna tarefas da jornada classificadas em alocadas, não alocadas e atrasadas."""
        actor_scope = _run(
            resolve_actor_scope,
            company_id=company_id,
            employee_id=employee_id,
            include_all=include_all,
            department=department,
            payload={
                "company_id": company_id,
                "employee_id": employee_id,
                "include_all": include_all,
                "department": department,
            },
        )
        scoped_anchor = _parse_date(anchor_date) or date.today()
        employees_payload = []
        merged_items: list[dict[str, Any]] = []
        for scoped_employee_id in actor_scope.employee_ids:
            agenda_payload = _run(
                get_work_journey_agenda,
                actor_scope.company_id,
                scoped_employee_id,
                scoped_anchor,
                scope,
                False,
            )
            items = _agenda_inventory_rows(agenda_payload, scoped_employee_id)
            merged_items.extend(items)
            employees_payload.append(
                {
                    "employee_id": scoped_employee_id,
                    "employee_name": agenda_payload.get("agenda", {}).get("employee_name") or agenda_payload.get("employee_name"),
                    "summary": _summarize_inventory(items),
                    "items": items,
                }
            )
        return {
            "company_id": actor_scope.company_id,
            "anchor_date": scoped_anchor.isoformat(),
            "scope": scope,
            "summary": _summarize_inventory(merged_items),
            "employees": employees_payload,
        }

    @mcp.tool()
    def get_work_journey_capacity_report_tool(
        company_id: int,
        anchor_date: str | None = None,
        employee_id: int | None = None,
        department: str | None = None,
        include_all: bool = False,
    ) -> dict[str, Any]:
        """Retorna capacidade operacional, capacidade tomada, ociosa e sobrecarga por colaborador/bloco."""
        actor_scope = _run(
            resolve_actor_scope,
            company_id=company_id,
            employee_id=employee_id,
            include_all=include_all,
            department=department,
            payload={
                "company_id": company_id,
                "employee_id": employee_id,
                "include_all": include_all,
                "department": department,
            },
        )
        resolved_employee_id = actor_scope.employee_ids[0] if len(actor_scope.employee_ids) == 1 else None
        payload = _run(
            build_work_journey_management_report,
            actor_scope.company_id,
            _parse_date(anchor_date) or date.today(),
            department=department if actor_scope.privileged else None,
            employee_id=resolved_employee_id,
        )
        return {"data": payload}

    @mcp.tool()
    def get_process_routines_analysis_tool(
        company_id: int,
        employee_id: int | None = None,
        department: str | None = None,
        include_all: bool = False,
    ) -> dict[str, Any]:
        """Retorna a análise de rotinas, compromissos e capacidade semanal do domínio process-routines/analysis."""
        actor_scope = _run(
            resolve_actor_scope,
            company_id=company_id,
            employee_id=employee_id,
            include_all=include_all,
            department=department,
            payload={
                "company_id": company_id,
                "employee_id": employee_id,
                "include_all": include_all,
                "department": department,
            },
        )
        resolved_employee_id = actor_scope.employee_ids[0] if len(actor_scope.employee_ids) == 1 else None
        data = _run(
            get_routine_analysis,
            actor_scope.company_id,
            department if actor_scope.privileged else None,
            resolved_employee_id,
        )
        return {"data": data}

    @mcp.tool()
    def get_efficiency_collaborators_analysis_tool(
        company_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        employee_id: int | None = None,
        include_all: bool = False,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Retorna a análise de eficiência por colaborador usada na página efficiency-analysis."""
        actor_scope = _run(
            resolve_actor_scope,
            company_id=company_id,
            employee_id=employee_id,
            include_all=include_all,
            department=department,
            payload={
                "company_id": company_id,
                "employee_id": employee_id,
                "include_all": include_all,
                "department": department,
            },
        )
        scoped_start, scoped_end = parse_efficiency_period(
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        )
        data = _run(
            get_efficiency_collaborators,
            company_id=actor_scope.company_id,
            start_date=scoped_start,
            end_date=scoped_end,
            employee_ids=actor_scope.employee_ids,
        )
        return {
            "company_id": actor_scope.company_id,
            "start_date": scoped_start.isoformat(),
            "end_date": scoped_end.isoformat(),
            "employees": data,
            "count": len(data),
        }


__all__ = ["register_work_journey_analytics_tools"]
