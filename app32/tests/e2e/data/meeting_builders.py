from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MeetingDraftPayload:
    title: str
    scheduled_date: str
    scheduled_time: str
    planned_duration_minutes: int
    invite_notes: str
    guests: dict
    agenda: list[dict]


@dataclass(frozen=True)
class MeetingExecutionPayload:
    actual_date: str
    actual_time: str
    actual_duration_minutes: int
    meeting_notes: str
    participants: dict
    discussions: list[dict]
    activities: list[dict]


def build_meeting_draft_payload(*, run_marker: str) -> MeetingDraftPayload:
    today = date.today().isoformat()
    return MeetingDraftPayload(
        title=f"{run_marker} Reunião E2E",
        scheduled_date=today,
        scheduled_time="09:00",
        planned_duration_minutes=60,
        invite_notes=f"Convite gerado para {run_marker}",
        guests={"internal": [], "external": []},
        agenda=[{"title": f"{run_marker} pauta inicial"}],
    )


def build_meeting_execution_payload(*, run_marker: str) -> MeetingExecutionPayload:
    today = date.today().isoformat()
    return MeetingExecutionPayload(
        actual_date=today,
        actual_time="09:05",
        actual_duration_minutes=55,
        meeting_notes=f"Conclusões da reunião {run_marker}",
        participants={"internal": [], "external": []},
        discussions=[{"title": "Alinhamento", "discussion": f"Discussão {run_marker}"}],
        activities=[
            {
                "title": f"Atividade {run_marker}",
                "responsible": "Codex",
                "deadline": today,
            }
        ],
    )
