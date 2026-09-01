from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_TRIGGER_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,99}$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RoutineRoleAssignmentInput(_StrictModel):
    role_id: int = Field(gt=0)
    assignment_type: Literal["responsible", "executor"]
    distribution_mode: Literal["collective", "individual", "pool"] = "collective"
    hours_used: float = Field(default=0, ge=0, le=744)
    notes: str | None = Field(default=None, max_length=1000)


class RoutineTriggerInput(_StrictModel):
    id: int | None = Field(default=None, gt=0)
    trigger_type: Literal["event", "manual"] = "event"
    trigger_code: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=160)
    activation_policy: Literal["automatic", "confirmation"] = "automatic"
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("trigger_code")
    @classmethod
    def normalize_trigger_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not _TRIGGER_CODE_RE.fullmatch(normalized):
            raise ValueError("Código do gatilho deve usar apenas letras minúsculas, números, ponto, hífen ou sublinhado.")
        return normalized


class RoutineExecutionRuleInput(_StrictModel):
    execution_mode: Literal["scheduled", "triggered", "hybrid"] = "scheduled"
    role_assignments: list[RoutineRoleAssignmentInput] = Field(default_factory=list)
    triggers: list[RoutineTriggerInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rule(self):
        responsible = [item for item in self.role_assignments if item.assignment_type == "responsible"]
        if len(responsible) > 1:
            raise ValueError("A rotina deve possuir no máximo uma função responsável.")

        assignment_keys = [(item.assignment_type, item.role_id) for item in self.role_assignments]
        if len(assignment_keys) != len(set(assignment_keys)):
            raise ValueError("A mesma função não pode ser repetida no mesmo tipo de vínculo.")

        trigger_codes = [item.trigger_code for item in self.triggers]
        if len(trigger_codes) != len(set(trigger_codes)):
            raise ValueError("Os códigos dos gatilhos devem ser únicos na rotina.")

        if self.execution_mode in {"triggered", "hybrid"} and not self.triggers:
            raise ValueError("Rotinas contínuas ou híbridas precisam de pelo menos um gatilho.")
        if self.execution_mode == "scheduled" and self.triggers:
            raise ValueError("Use o modo híbrido para combinar agenda periódica e gatilhos.")
        return self


class RoutineEventDispatchInput(_StrictModel):
    trigger_code: str = Field(min_length=2, max_length=100)
    event_key: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("trigger_code")
    @classmethod
    def normalize_dispatch_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not _TRIGGER_CODE_RE.fullmatch(normalized):
            raise ValueError("Código de gatilho inválido.")
        return normalized
