from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class ContractCatalogItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    parent_id: Optional[int] = None
    code_suffix: Optional[str] = Field(None, max_length=10)
    name: str = Field(..., min_length=2, max_length=255)
    item_kind: str = Field("service", pattern="^(service|product)$")
    description: Optional[str] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    accepts_contracting: bool = True
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code_suffix", "unit_code", mode="before")
    @classmethod
    def normalize_short_text(cls, value):
        return _normalize_text(value)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_long_text(cls, value):
        return _normalize_text(value)


class ContractCatalogItemUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: Optional[int] = None
    code_suffix: Optional[str] = Field(None, max_length=10)
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    item_kind: Optional[str] = Field(None, pattern="^(service|product)$")
    description: Optional[str] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    accepts_contracting: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code_suffix", "unit_code", mode="before")
    @classmethod
    def normalize_short_text(cls, value):
        return _normalize_text(value)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_long_text(cls, value):
        return _normalize_text(value)
