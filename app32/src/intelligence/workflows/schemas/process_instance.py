from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .common import coalesce_str


class ProcessInstanceCompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_code: str
    completion_date_raw: Optional[str] = None

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["ProcessInstanceCompleteInput"], Optional[str]]:
        instance_code = coalesce_str(
            payload,
            "codigo_instancia",
            "instance_code",
            "codigo",
        )
        if not instance_code:
            return None, "Nao encontrei o codigo da instancia. Informe no formato: codigo_instancia: CODIGO"

        return cls(
            instance_code=instance_code,
            completion_date_raw=coalesce_str(payload, "completion_date", "data_finalizacao"),
        ), None
