from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .common import coalesce_str, split_text_values


class MeetingScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    datetime_raw: Optional[str] = None
    date_raw: Optional[str] = None
    time_raw: Optional[str] = None
    guests: List[str] = Field(default_factory=list)
    agenda_items: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["MeetingScheduleInput"], Optional[str]]:
        title = coalesce_str(payload, "titulo", "title")
        if not title:
            return None, "Nao encontrei o titulo da reuniao. Informe no formato: titulo: Nome da Reuniao"

        return cls(
            title=title,
            datetime_raw=coalesce_str(payload, "data_hora", "datahora"),
            date_raw=coalesce_str(payload, "data", "date"),
            time_raw=coalesce_str(payload, "hora", "time"),
            guests=split_text_values(
                coalesce_str(payload, "convidados", "guests", "participantes") or "",
                r"[,\n;]+",
            ),
            agenda_items=split_text_values(
                coalesce_str(payload, "pauta", "agenda", "agenda_itens", "itens_agenda") or "",
                r"[;\n]+",
            ),
            notes=coalesce_str(payload, "observacoes", "notas", "notes", "dados"),
        ), None


class MeetingReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: int

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["MeetingReferenceInput"], Optional[str]]:
        meeting_value = coalesce_str(
            payload,
            "id_reuniao",
            "meeting_id",
            "codigo_reuniao",
            "codigo",
        )
        if not meeting_value:
            return None, "Nao encontrei o ID da reuniao. Informe no formato: id_reuniao: 123"

        meeting_id = cls._extract_id_from_code(meeting_value)
        if not meeting_id:
            return None, f"Nao consegui identificar o ID da reuniao em '{meeting_value}'."

        return cls(meeting_id=meeting_id), None

    @staticmethod
    def _extract_id_from_code(code_value: str) -> Optional[int]:
        tokens = re.findall(r"\d+", str(code_value or ""))
        if not tokens:
            return None
        try:
            parsed = int(tokens[-1])
        except ValueError:
            return None
        return parsed if parsed > 0 else None
