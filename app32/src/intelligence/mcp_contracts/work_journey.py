from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from .base import MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope, _StrictModel


WorkJourneyAction = Literal[
    "board.read",
    "block.list",
    "block.upsert",
    "rule.list",
    "rule.upsert",
    "agenda.read",
    "agenda.generate",
    "agenda.move",
]

WorkJourneyRole = Literal[
    "colaborador",
    "cliente",
    "administrador",
    "admin_tecnico",
]


class WorkJourneyPermissionRule(_StrictModel):
    """Regra de autorização do domínio piloto Work Journey."""

    action: WorkJourneyAction
    summary: str = Field(min_length=1, max_length=240)
    allowed_roles: list[WorkJourneyRole] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    human_gate_required: bool = False
    read_only: bool = False


class WorkJourneyDomainManifest(_StrictModel):
    """Manifesto de instrução/contrato para agentes no domínio Work Journey."""

    domain: Literal["work_journey"] = "work_journey"
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    operations: list[WorkJourneyPermissionRule] = Field(default_factory=list)


class WorkJourneyBoardQuery(_StrictModel):
    """Consulta piloto do quadro da jornada operacional."""

    company_id: int = Field(gt=0)
    employee_id: int = Field(gt=0)
    anchor_date: date
    scope: Literal["day", "week"] = "week"


class WorkJourneyBoardItem(_StrictModel):
    """Item normalizado de resposta do quadro de jornada."""

    item_id: int | None = Field(default=None, gt=0)
    source_type: Literal["manual", "process_instance", "project_task", "meeting"]
    title: str = Field(min_length=1, max_length=200)
    status: Literal["pending", "in_progress", "completed", "postponed", "suspended"]
    block_id: int | None = Field(default=None, gt=0)
    due_date: date | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=1440)
    worked_minutes: int | None = Field(default=None, ge=0, le=1440)


class WorkJourneyBoardPayload(_StrictModel):
    """Carga útil canônica do piloto Work Journey."""

    company_id: int = Field(gt=0)
    employee_id: int = Field(gt=0)
    anchor_date: date
    scope: Literal["day", "week"] = "week"
    items: list[WorkJourneyBoardItem] = Field(default_factory=list)
    summary: dict[str, int | float | str | None] = Field(default_factory=dict)


class WorkJourneyBoardErrorEnvelope(MCPErrorEnvelope):
    """Envelope de erro do domínio piloto."""


WorkJourneyBoardResponseEnvelope = MCPSuccessEnvelope[WorkJourneyBoardPayload]


def build_work_journey_pilot_manifest() -> WorkJourneyDomainManifest:
    return WorkJourneyDomainManifest(
        title="Work Journey MCP Pilot",
        description=(
            "Manifesto piloto de contratos MCP para o domínio Rotina / Work Journey, "
            "com foco em leitura do quadro operacional e disciplina de permissões."
        ),
        operations=[
            WorkJourneyPermissionRule(
                action="board.read",
                summary="Lê o quadro operacional da jornada do colaborador.",
                allowed_roles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                required_permissions=["work_journey.read"],
                read_only=True,
            ),
            WorkJourneyPermissionRule(
                action="block.list",
                summary="Lista blocos de jornada disponíveis para um colaborador.",
                allowed_roles=["colaborador", "administrador", "admin_tecnico"],
                required_permissions=["work_journey.block.read"],
                read_only=True,
            ),
            WorkJourneyPermissionRule(
                action="block.upsert",
                summary="Cria ou atualiza blocos de jornada operacional.",
                allowed_roles=["administrador", "admin_tecnico"],
                required_permissions=["work_journey.block.write"],
                human_gate_required=True,
            ),
            WorkJourneyPermissionRule(
                action="agenda.read",
                summary="Consulta a agenda materializada da jornada.",
                allowed_roles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                required_permissions=["work_journey.agenda.read"],
                read_only=True,
            ),
            WorkJourneyPermissionRule(
                action="agenda.generate",
                summary="Gera ou regenera a agenda materializada da jornada.",
                allowed_roles=["administrador", "admin_tecnico"],
                required_permissions=["work_journey.agenda.write"],
                human_gate_required=True,
            ),
            WorkJourneyPermissionRule(
                action="agenda.move",
                summary="Move itens da agenda entre blocos ou dias.",
                allowed_roles=["administrador", "admin_tecnico"],
                required_permissions=["work_journey.agenda.write"],
                human_gate_required=True,
            ),
            WorkJourneyPermissionRule(
                action="rule.list",
                summary="Lista regras operacionais recorrentes da jornada.",
                allowed_roles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                required_permissions=["work_journey.rule.read"],
                read_only=True,
            ),
            WorkJourneyPermissionRule(
                action="rule.upsert",
                summary="Cria ou atualiza regras operacionais recorrentes.",
                allowed_roles=["administrador", "admin_tecnico"],
                required_permissions=["work_journey.rule.write"],
                human_gate_required=True,
            ),
        ],
    )


WORK_JOURNEY_PILOT_MANIFEST = build_work_journey_pilot_manifest()
