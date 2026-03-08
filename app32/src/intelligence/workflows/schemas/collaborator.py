from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class CollaboratorOccupancyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = "collaborator.occupancy"


class CollaboratorOccupancyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class CollaboratorOccupancyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str
