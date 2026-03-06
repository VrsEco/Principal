from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .common import coalesce_str


class OnboardingDiagnoseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_raw: str = "geral"

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple["OnboardingDiagnoseInput", None]:
        objective_raw = coalesce_str(
            payload,
            "objetivo",
            "o_que_quer_funcionar",
            "objetivo_de_funcionamento",
        ) or "geral"
        return cls(objective_raw=objective_raw), None


class OnboardingStartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    onboarding_type: str

    @classmethod
    def build_from_legacy_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[Optional["OnboardingStartInput"], Optional[str]]:
        tipo_raw = str(
            payload.get("tipo_cadastro")
            or payload.get("tipo")
            or payload.get("modelo")
            or ""
        ).strip().lower()

        if tipo_raw in {"", "real", "empresa_real", "oficial"}:
            return cls(onboarding_type="real"), None
        if tipo_raw in {"modelo", "exemplo", "mock"}:
            return cls(onboarding_type="modelo"), None
        return None, "Tipo de cadastro invalido. Use: real ou modelo."
