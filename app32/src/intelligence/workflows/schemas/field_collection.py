from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


def normalize_field_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


class WorkflowRequiredField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    required: bool = True
    category: Literal["required", "optional", "complementary"] = "required"

    @classmethod
    def from_raw(cls, raw_field: Any) -> Optional["WorkflowRequiredField"]:
        if isinstance(raw_field, cls):
            return raw_field

        if isinstance(raw_field, dict):
            key = normalize_field_key(raw_field.get("key") or raw_field.get("label") or "")
            label = str(raw_field.get("label") or raw_field.get("key") or key or "Campo")
            required = bool(raw_field.get("required", True))
            category = str(raw_field.get("category") or ("required" if required else "optional")).strip().lower()
        else:
            label = str(raw_field or "").strip()
            key = normalize_field_key(label)
            required = True
            category = "required"

        if not key:
            return None
        if category not in {"required", "optional", "complementary"}:
            category = "required" if required else "optional"
        if category == "required":
            required = True
        return cls(key=key, label=label or key, required=required, category=category)

    @classmethod
    def normalize_many(cls, raw_fields: Any) -> List["WorkflowRequiredField"]:
        normalized: List[WorkflowRequiredField] = []
        for item in raw_fields or []:
            field = cls.from_raw(item)
            if field is not None:
                normalized.append(field)
        return normalized
