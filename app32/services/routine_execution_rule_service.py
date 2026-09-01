from __future__ import annotations

import hashlib
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import (
    db,
    Employee,
    Process,
    ProcessInstance,
    ProcessInstanceCollaborator,
    Role,
    Routine,
    RoutineRoleAssignment,
    RoutineTrigger,
    RoutineTriggerEvent,
)
from services.process_routine_scheduler_service import (
    _build_collaborators_payload,
    calculate_due_date_for_routine,
)


VALID_EXECUTION_MODES = {"scheduled", "triggered", "hybrid"}


def get_execution_rule(company_id: int, routine_id: int) -> dict[str, Any]:
    routine = _get_routine(company_id, routine_id)
    roles = Role.query.filter_by(company_id=company_id).order_by(Role.title.asc(), Role.id.asc()).all()
    occupants_by_role = _occupants_by_role(company_id, [role.id for role in roles])

    assignments = (
        RoutineRoleAssignment.query.filter_by(company_id=company_id, routine_id=routine_id, is_active=True)
        .order_by(RoutineRoleAssignment.assignment_type.asc(), RoutineRoleAssignment.id.asc())
        .all()
    )
    triggers = (
        RoutineTrigger.query.filter_by(company_id=company_id, routine_id=routine_id, is_active=True)
        .order_by(RoutineTrigger.name.asc(), RoutineTrigger.id.asc())
        .all()
    )
    pending_events = (
        RoutineTriggerEvent.query.filter_by(
            company_id=company_id,
            routine_id=routine_id,
            status="pending_confirmation",
        )
        .order_by(RoutineTriggerEvent.received_at.desc())
        .limit(20)
        .all()
    )

    return {
        "routine_id": routine.id,
        "execution_mode": routine.execution_mode or "scheduled",
        "available_roles": [
            {
                "id": role.id,
                "title": role.title,
                "department": role.department,
                "occupants": occupants_by_role.get(role.id, []),
            }
            for role in roles
        ],
        "role_assignments": [
            _serialize_assignment(item, occupants_by_role.get(item.role_id, [])) for item in assignments
        ],
        "triggers": [_serialize_trigger(item) for item in triggers],
        "pending_events": [_serialize_event(item) for item in pending_events],
    }


def save_execution_rule(company_id: int, routine_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    routine = _get_routine(company_id, routine_id)
    execution_mode = str(payload.get("execution_mode") or "scheduled").strip().lower()
    if execution_mode not in VALID_EXECUTION_MODES:
        raise ValueError("Modo de execução inválido.")

    assignments = list(payload.get("role_assignments") or [])
    triggers = list(payload.get("triggers") or [])
    role_ids = {int(item["role_id"]) for item in assignments}
    valid_role_ids = {
        role.id for role in Role.query.filter(Role.company_id == company_id, Role.id.in_(role_ids or {-1})).all()
    }
    if role_ids != valid_role_ids:
        raise ValueError("Uma ou mais funções não pertencem à empresa ativa.")

    try:
        routine.execution_mode = execution_mode
        RoutineRoleAssignment.query.filter_by(company_id=company_id, routine_id=routine_id).delete(
            synchronize_session=False
        )

        for item in assignments:
            db.session.add(
                RoutineRoleAssignment(
                    company_id=company_id,
                    routine_id=routine_id,
                    role_id=int(item["role_id"]),
                    assignment_type=item["assignment_type"],
                    distribution_mode=item.get("distribution_mode") or "collective",
                    hours_used=_to_decimal(item.get("hours_used")),
                    notes=item.get("notes"),
                    is_active=True,
                )
            )

        existing_triggers = RoutineTrigger.query.filter_by(company_id=company_id, routine_id=routine_id).all()
        existing_by_id = {item.id: item for item in existing_triggers}
        existing_by_code = {item.trigger_code: item for item in existing_triggers}
        retained_trigger_ids: set[int] = set()
        for item in triggers:
            trigger_by_id = existing_by_id.get(item.get("id"))
            trigger_by_code = existing_by_code.get(item["trigger_code"])
            if trigger_by_id and trigger_by_code and trigger_by_id.id != trigger_by_code.id:
                raise ValueError("Código de gatilho já pertence a outro gatilho desta rotina.")
            trigger = trigger_by_id or trigger_by_code
            if trigger is None:
                trigger = RoutineTrigger(
                    company_id=company_id,
                    routine_id=routine_id,
                )
                db.session.add(trigger)
                db.session.flush()
            elif trigger.company_id != company_id or trigger.routine_id != routine_id:
                raise ValueError("Gatilho não pertence à rotina e empresa ativas.")
            trigger.trigger_type = item.get("trigger_type") or "event"
            trigger.trigger_code = item["trigger_code"]
            trigger.name = item["name"]
            trigger.activation_policy = item.get("activation_policy") or "automatic"
            trigger.config_json = item.get("config") or {}
            trigger.is_active = True
            retained_trigger_ids.add(trigger.id)

        for trigger in existing_triggers:
            if trigger.id not in retained_trigger_ids:
                trigger.is_active = False

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return get_execution_rule(company_id, routine_id)


def dispatch_routine_event(
    company_id: int,
    trigger_code: str,
    event_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_code = str(trigger_code or "").strip().lower()
    triggers = (
        RoutineTrigger.query.join(Routine, Routine.id == RoutineTrigger.routine_id)
        .filter(
            RoutineTrigger.company_id == company_id,
            RoutineTrigger.trigger_code == normalized_code,
            RoutineTrigger.is_active.is_(True),
            Routine.company_id == company_id,
            Routine.execution_mode.in_(["triggered", "hybrid"]),
            Routine.is_active.isnot(False),
        )
        .order_by(RoutineTrigger.id.asc())
        .all()
    )
    if not triggers:
        raise ValueError("Nenhum gatilho ativo encontrado para a empresa.")

    results = []
    try:
        for trigger in triggers:
            event_id = db.session.execute(
                pg_insert(RoutineTriggerEvent)
                .values(
                    company_id=company_id,
                    routine_id=trigger.routine_id,
                    trigger_id=trigger.id,
                    event_key=event_key,
                    payload_json=payload or {},
                    status="received",
                    created_instances_json=[],
                    received_at=datetime.utcnow(),
                )
                .on_conflict_do_nothing(
                    index_elements=["company_id", "trigger_id", "event_key"]
                )
                .returning(RoutineTriggerEvent.id)
            ).scalar_one_or_none()
            if event_id is None:
                existing = RoutineTriggerEvent.query.filter_by(
                    company_id=company_id,
                    trigger_id=trigger.id,
                    event_key=event_key,
                ).first()
                results.append({"event": _serialize_event(existing), "duplicate": True})
                continue
            event = db.session.get(RoutineTriggerEvent, event_id)

            if trigger.activation_policy == "confirmation":
                event.status = "pending_confirmation"
                instance_ids: list[int] = []
            else:
                instance_ids = _create_triggered_instances(trigger, event)
                event.status = "processed"
                event.created_instances_json = instance_ids
                event.processed_at = datetime.utcnow()

            results.append({"event": _serialize_event(event), "duplicate": False})

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"trigger_code": normalized_code, "events": results}


def confirm_trigger_event(company_id: int, event_id: int) -> dict[str, Any]:
    event = RoutineTriggerEvent.query.filter_by(id=event_id, company_id=company_id).first()
    if not event:
        raise ValueError("Evento não encontrado para a empresa ativa.")
    if event.status == "processed":
        return _serialize_event(event)
    if event.status != "pending_confirmation":
        raise ValueError("Somente eventos aguardando confirmação podem ser executados.")

    trigger = RoutineTrigger.query.filter_by(
        id=event.trigger_id,
        routine_id=event.routine_id,
        company_id=company_id,
        is_active=True,
    ).first()
    if not trigger:
        raise ValueError("Gatilho inativo ou removido.")

    try:
        instance_ids = _create_triggered_instances(trigger, event)
        event.status = "processed"
        event.created_instances_json = instance_ids
        event.processed_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return _serialize_event(event)


def resolve_execution_groups_for_routine(routine: Routine) -> tuple[list[dict], list[dict]] | None:
    assignments = RoutineRoleAssignment.query.filter_by(
        company_id=routine.company_id,
        routine_id=routine.id,
        is_active=True,
    ).all()
    if not assignments:
        return None
    occupants = _occupants_by_role(routine.company_id, [item.role_id for item in assignments])
    return build_execution_groups(assignments, occupants)


def _create_triggered_instances(trigger: RoutineTrigger, event: RoutineTriggerEvent) -> list[int]:
    routine = _get_routine(event.company_id, event.routine_id)
    process = Process.query.filter_by(id=routine.process_id, company_id=event.company_id).first()
    if not process:
        raise ValueError("Processo da rotina não pertence à empresa ativa.")

    assignments = RoutineRoleAssignment.query.filter_by(
        company_id=event.company_id,
        routine_id=routine.id,
        is_active=True,
    ).all()
    role_ids = [item.role_id for item in assignments]
    occupants = _occupants_by_role(event.company_id, role_ids)
    groups, responsible_snapshot = build_execution_groups(assignments, occupants)
    direct_collaborators = _build_collaborators_payload(routine, event.company_id)
    responsible_id = responsible_snapshot[0]["id"] if responsible_snapshot else process.responsible_id
    created_ids: list[int] = []

    for group in groups:
        target_key = str(group.get("target_employee_id") or group.get("distribution_mode") or "collective")
        instance_code = build_event_instance_code(
            process.code,
            routine.id,
            trigger.trigger_code,
            event.event_key,
            target_key,
        )
        existing = ProcessInstance.query.filter_by(
            company_id=event.company_id,
            routine_id=routine.id,
            instance_code=instance_code,
        ).first()
        if existing:
            created_ids.append(existing.id)
            continue

        collaborators = _dedupe_people([*group["collaborators"], *direct_collaborators])
        role_snapshot = {
            "responsible": responsible_snapshot,
            "executors": collaborators,
        }
        instance = ProcessInstance(
            company_id=event.company_id,
            process_id=process.id,
            routine_id=routine.id,
            instance_code=instance_code,
            title=routine.name,
            description=routine.description,
            status="pending",
            priority="normal",
            due_date=calculate_due_date_for_routine(routine),
            trigger_type="event",
            owner_employee_id=process.owner_employee_id,
            responsible_id=responsible_id,
            executor_id=group.get("executor_id"),
            collaborators_json=collaborators,
            runtime_context_json={
                "routine_trigger": {
                    "trigger_id": trigger.id,
                    "trigger_code": trigger.trigger_code,
                    "trigger_name": trigger.name,
                    "event_key": event.event_key,
                    "activation_policy": trigger.activation_policy,
                },
                "role_snapshot": role_snapshot,
                "event_payload": event.payload_json or {},
            },
            score_weight=float(routine.score_weight or 1),
            created_by=f"routine-trigger:{trigger.trigger_code}"[:100],
        )
        db.session.add(instance)
        db.session.flush()
        _persist_instance_collaborators(instance.id, collaborators)
        created_ids.append(instance.id)

    return created_ids


def build_execution_groups(assignments, occupants_by_role: dict[int, list[dict]]) -> tuple[list[dict], list[dict]]:
    responsible_snapshot: list[dict] = []
    collective: list[dict] = []
    pool: list[dict] = []
    individual: list[dict] = []

    for assignment in assignments:
        occupants = occupants_by_role.get(assignment.role_id, [])
        enriched = [
            {
                **occupant,
                "role_id": assignment.role_id,
                "role_title": getattr(getattr(assignment, "role", None), "title", occupant.get("role_title")),
                "assignment_type": assignment.assignment_type,
                "distribution_mode": assignment.distribution_mode,
                "hours": float(assignment.hours_used or 0),
                "notes": assignment.notes,
            }
            for occupant in occupants
        ]
        if assignment.assignment_type == "responsible":
            responsible_snapshot.extend(enriched)
        elif assignment.distribution_mode == "individual":
            individual.extend(enriched)
        elif assignment.distribution_mode == "pool":
            pool.extend(enriched)
        else:
            collective.extend(enriched)

    groups: list[dict] = []
    if individual:
        for target in _dedupe_people(individual):
            collaborators = _dedupe_people([*collective, target])
            groups.append(
                {
                    "distribution_mode": "individual",
                    "target_employee_id": target["id"],
                    "executor_id": target["id"],
                    "collaborators": collaborators,
                }
            )
    else:
        collaborators = _dedupe_people([*collective, *pool])
        executor_id = None if pool and not collective else (collaborators[0]["id"] if collaborators else None)
        groups.append(
            {
                "distribution_mode": "pool" if pool and not collective else "collective",
                "target_employee_id": None,
                "executor_id": executor_id,
                "collaborators": collaborators,
            }
        )
    return groups, _dedupe_people(responsible_snapshot)


def build_event_instance_code(
    process_code: str | None,
    routine_id: int,
    trigger_code: str,
    event_key: str,
    target_key: str,
) -> str:
    digest = hashlib.sha256(
        f"{routine_id}|{trigger_code}|{event_key}|{target_key}".encode("utf-8")
    ).hexdigest()[:16]
    safe_process = re.sub(r"[^A-Za-z0-9._-]", "-", process_code or f"P{routine_id}")[:28]
    safe_trigger = re.sub(r"[^a-z0-9._-]", "-", trigger_code.lower())[:20]
    return f"{safe_process}-RT{routine_id}-{safe_trigger}-{digest}"[:100]


def _persist_instance_collaborators(instance_id: int, collaborators: list[dict]) -> None:
    for collaborator in collaborators:
        db.session.add(
            ProcessInstanceCollaborator(
                process_instance_id=instance_id,
                employee_id=collaborator["id"],
                role="executor",
                estimated_hours=_to_decimal(collaborator.get("hours")),
                notes=collaborator.get("notes"),
            )
        )


def _get_routine(company_id: int, routine_id: int) -> Routine:
    routine = Routine.query.filter_by(id=routine_id, company_id=company_id).first()
    if not routine:
        raise ValueError("Rotina não encontrada para a empresa ativa.")
    return routine


def _occupants_by_role(company_id: int, role_ids: list[int]) -> dict[int, list[dict]]:
    if not role_ids:
        return {}
    employees = (
        Employee.query.filter(
            Employee.company_id == company_id,
            Employee.role_id.in_(set(role_ids)),
            Employee.status == "active",
        )
        .order_by(Employee.name.asc(), Employee.id.asc())
        .all()
    )
    result: dict[int, list[dict]] = {}
    for employee in employees:
        result.setdefault(employee.role_id, []).append(
            {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "role_title": employee.role.title if employee.role else None,
            }
        )
    return result


def _serialize_assignment(item: RoutineRoleAssignment, occupants: list[dict]) -> dict[str, Any]:
    return {
        "id": item.id,
        "role_id": item.role_id,
        "role_title": item.role.title if item.role else None,
        "assignment_type": item.assignment_type,
        "distribution_mode": item.distribution_mode,
        "hours_used": float(item.hours_used or 0),
        "notes": item.notes,
        "occupants": occupants,
    }


def _serialize_trigger(item: RoutineTrigger) -> dict[str, Any]:
    return {
        "id": item.id,
        "trigger_type": item.trigger_type,
        "trigger_code": item.trigger_code,
        "name": item.name,
        "activation_policy": item.activation_policy,
        "config": item.config_json or {},
    }


def _serialize_event(item: RoutineTriggerEvent) -> dict[str, Any]:
    trigger = getattr(item, "trigger_rel", None)
    return {
        "id": item.id,
        "routine_id": item.routine_id,
        "trigger_id": item.trigger_id,
        "trigger_code": trigger.trigger_code if trigger else None,
        "trigger_name": trigger.name if trigger else None,
        "event_key": item.event_key,
        "status": item.status,
        "created_instance_ids": item.created_instances_json or [],
        "received_at": item.received_at.isoformat() if item.received_at else None,
        "processed_at": item.processed_at.isoformat() if item.processed_at else None,
    }


def _dedupe_people(items: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for item in items:
        employee_id = item.get("id")
        if not employee_id or employee_id in seen:
            continue
        seen.add(employee_id)
        result.append(item)
    return result


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")
