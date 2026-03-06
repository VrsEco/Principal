from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Optional

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

    @classmethod
    def from_raw(cls, raw_field: Any) -> Optional["WorkflowRequiredField"]:
        if isinstance(raw_field, cls):
            return raw_field

        if isinstance(raw_field, dict):
            key = normalize_field_key(raw_field.get("key") or raw_field.get("label") or "")
            label = str(raw_field.get("label") or raw_field.get("key") or key or "Campo")
        else:
            label = str(raw_field or "").strip()
            key = normalize_field_key(label)

        if not key:
            return None
        return cls(key=key, label=label or key)

    @classmethod
    def normalize_many(cls, raw_fields: Any) -> List["WorkflowRequiredField"]:
        normalized: List[WorkflowRequiredField] = []
        for item in raw_fields or []:
            field = cls.from_raw(item)
            if field is not None:
                normalized.append(field)
        return normalized
