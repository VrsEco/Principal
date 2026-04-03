from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoutineJourneyBindingUpsertSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    employee_id: int = Field(gt=0)
    block_id: Optional[int] = Field(default=None, gt=0)
    notes: Optional[str] = Field(default=None, max_length=1000)
