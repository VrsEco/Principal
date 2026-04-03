from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ALLOWED_ITEM_TYPES = {'manual', 'process_instance', 'project_task', 'meeting'}
_ALLOWED_PRIORITIES = {'low', 'normal', 'high', 'urgent'}
_ALLOWED_ITEM_STATUSES = {'pending', 'in_progress', 'completed', 'postponed', 'suspended'}
_ALLOWED_ABSENCE_TYPES = {'vacation', 'absence', 'medical_leave'}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class WorkJourneyBlockCreateSchema(_StrictModel):
    employee_id: int
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    start_time: str
    end_time: str
    weekdays: list[int] = Field(default_factory=list)
    accepted_item_types: list[str] = Field(default_factory=list)
    order_index: int = 0
    is_active: bool = True

    @field_validator('weekdays')
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        unique = []
        for item in value:
            if item < 0 or item > 6:
                raise ValueError('Dias da semana devem estar entre 0 e 6.')
            if item not in unique:
                unique.append(item)
        return unique

    @field_validator('accepted_item_types')
    @classmethod
    def validate_item_types(cls, value: list[str]) -> list[str]:
        unique = []
        for item in value:
            normalized = str(item or '').strip().lower()
            if normalized not in _ALLOWED_ITEM_TYPES:
                raise ValueError(f'Tipo de atividade inválido: {item}')
            if normalized not in unique:
                unique.append(normalized)
        return unique


class WorkJourneyBlockUpdateSchema(WorkJourneyBlockCreateSchema):
    pass


class WorkJourneyRuleCreateSchema(_StrictModel):
    employee_id: int
    preferred_block_id: int | None = None
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    item_type: Literal['manual', 'process_instance', 'project_task', 'meeting'] = 'manual'
    recurrence_type: Literal['daily', 'weekly', 'monthly', 'annual', 'sporadic'] = 'daily'
    recurrence_config: dict[str, Any] = Field(default_factory=dict)
    estimated_minutes: int = Field(default=60, ge=5, le=720)
    priority: Literal['low', 'normal', 'high', 'urgent'] = 'normal'
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True

    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError('A data final deve ser maior ou igual à data inicial.')
        return self


class WorkJourneyRuleUpdateSchema(WorkJourneyRuleCreateSchema):
    pass


class WorkJourneyItemUpdateSchema(_StrictModel):
    block_id: int | None = None
    status: Literal['pending', 'in_progress', 'completed', 'postponed', 'suspended'] | None = None
    worked_minutes: int | None = Field(default=None, ge=0, le=1440)
    notes: str | None = None


class WorkJourneyTransferRequestCreateSchema(_StrictModel):
    to_employee_id: int
    reason: str | None = None


class WorkJourneyTransferApprovalSchema(_StrictModel):
    resolution_notes: str | None = None


class WorkJourneyAbsenceRequestCreateSchema(_StrictModel):
    employee_id: int
    absence_type: Literal['vacation', 'absence', 'medical_leave'] = 'vacation'
    start_date: date
    end_date: date
    reason: str | None = None

    @model_validator(mode='after')
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError('A data final deve ser maior ou igual à data inicial.')
        return self


class WorkJourneyAbsenceApprovalSchema(_StrictModel):
    cleanup_notes: str | None = None
