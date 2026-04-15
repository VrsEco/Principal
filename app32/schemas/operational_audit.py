from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OperationalAuditPanelQuery(BaseModel):
    """Contrato de filtros da API de auditoria operacional."""

    model_config = ConfigDict(extra="forbid")

    company_id: Optional[int] = Field(default=None, ge=1)
    source: Optional[Literal["ai_mcp_runtime", "human_review", "sapiens_workflow", "agent_action"]] = None
    limit: int = Field(default=50, ge=1, le=200)
