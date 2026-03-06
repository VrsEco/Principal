from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class OperationCompanyChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    company_id: int
    company_name: str
    company_code: str = ""
    label: str


class OperationCompanySelectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choices: List[OperationCompanyChoice] = Field(default_factory=list)

    @classmethod
    def build_from_payload(cls, payload: Dict[str, Any]) -> "OperationCompanySelectionContext":
        raw_choices = (payload or {}).get("_operation_company_choices") or []
        choices: List[OperationCompanyChoice] = []
        for item in raw_choices:
            if not isinstance(item, dict):
                continue
            try:
                choices.append(OperationCompanyChoice.model_validate(item))
            except Exception:
                continue
        return cls(choices=choices)
