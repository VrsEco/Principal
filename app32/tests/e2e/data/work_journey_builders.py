from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class WorkJourneyManualTaskPayload:
    employee_id: int
    block_id: int | None
    title: str
    description: str | None
    due_date: str
    estimated_minutes: int
    priority: str
    status: str
    worked_minutes: int


@dataclass(frozen=True)
class WorkJourneyManualTaskUpdatePayload:
    title: str
    description: str | None
    estimated_minutes: int
    priority: str
    status: str
    worked_minutes: int
    notes: str


def build_work_journey_manual_task_payload(
    *,
    employee_id: int,
    run_marker: str,
    due_in_days: int = 1,
) -> WorkJourneyManualTaskPayload:
    due_date = (date.today() + timedelta(days=due_in_days)).isoformat()
    return WorkJourneyManualTaskPayload(
        employee_id=employee_id,
        block_id=None,
        title=f"{run_marker} tarefa avulsa",
        description=f"Tarefa criada automaticamente pelo robô E2E ({run_marker}).",
        due_date=due_date,
        estimated_minutes=45,
        priority="normal",
        status="pending",
        worked_minutes=0,
    )


def build_work_journey_manual_task_update_payload(
    *,
    run_marker: str,
) -> WorkJourneyManualTaskUpdatePayload:
    return WorkJourneyManualTaskUpdatePayload(
        title=f"{run_marker} tarefa avulsa atualizada",
        description=f"Atualização automática da tarefa do robô ({run_marker}).",
        estimated_minutes=60,
        priority="high",
        status="completed",
        worked_minutes=60,
        notes=f"Atualização automática {run_marker}",
    )


def to_payload_dict(payload: WorkJourneyManualTaskPayload | WorkJourneyManualTaskUpdatePayload) -> dict:
    return asdict(payload)
