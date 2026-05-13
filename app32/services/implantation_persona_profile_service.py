from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from models import db
from services.plan_service import PlanService
from utils.permissions import (
    PROFILE_ADMINISTRATOR,
    PROFILE_CLIENT,
    get_access_profile,
)


class ImplantationPersonaProfileError(ValueError):
    """Erro de domínio para operações de perfil de persona."""


class ImplantationPersonaProfilePermissionError(PermissionError):
    """Erro de permissão para operações de perfil de persona."""


@dataclass(frozen=True)
class ImplantationPersonaProfilePreview:
    company_id: int
    plan_id: int
    plan_title: str
    segment_name: str
    persona_name: str
    before: str
    after: str
    has_changes: bool
    actor_user_id: int
    actor_role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "plan_id": self.plan_id,
            "plan_title": self.plan_title,
            "segment_name": self.segment_name,
            "persona_name": self.persona_name,
            "before": self.before,
            "after": self.after,
            "has_changes": self.has_changes,
            "actor_user_id": self.actor_user_id,
            "actor_role": self.actor_role,
        }


@dataclass(frozen=True)
class ImplantationPersonaProfileApplyResult(ImplantationPersonaProfilePreview):
    saved: bool
    section_key: str = "model"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "saved": self.saved,
                "section_key": self.section_key,
            }
        )
        return payload


class ImplantationPersonaProfileService:
    SECTION_KEY = "model"

    @staticmethod
    def _load_actor(user_id: int):
        from models.user import User

        actor = db.session.get(User, int(user_id))
        if actor is None:
            raise ImplantationPersonaProfilePermissionError("Usuário MCP não encontrado.")
        return actor

    @staticmethod
    def _resolve_actor_role(*, user_id: int, company_id: int) -> str:
        actor = ImplantationPersonaProfileService._load_actor(user_id)
        profile = get_access_profile(company_id, user=actor)
        if profile not in {PROFILE_ADMINISTRATOR, PROFILE_CLIENT}:
            raise ImplantationPersonaProfilePermissionError(
                "Usuário não possui acesso total ao planejamento nesta empresa."
            )
        return str(profile)

    @staticmethod
    def _load_plan_and_content(*, company_id: int, plan_id: int) -> tuple[Any, dict[str, Any]]:
        plan = PlanService.get_plan(plan_id, company_id)
        if plan is None:
            raise ImplantationPersonaProfileError("Plano não encontrado para a empresa informada.")
        if getattr(plan, "mode", None) != "implantation":
            raise ImplantationPersonaProfileError("O plano informado não é do tipo implantação.")

        section_data = PlanService.get_implantation_data(plan_id, company_id, ImplantationPersonaProfileService.SECTION_KEY)
        content = deepcopy(getattr(section_data, "content", None) or {})
        if not isinstance(content, dict):
            raise ImplantationPersonaProfileError("Conteúdo da seção model está inválido.")
        segments = content.get("segments")
        if not isinstance(segments, list):
            raise ImplantationPersonaProfileError("A seção model não possui segmentos válidos.")
        return plan, content

    @staticmethod
    def _resolve_segment(content: dict[str, Any], *, segment_name: str) -> dict[str, Any]:
        segments = content.get("segments") or []
        normalized = segment_name.strip()
        matches = [
            segment
            for segment in segments
            if isinstance(segment, dict) and str(segment.get("name") or "").strip() == normalized
        ]
        if not matches:
            raise ImplantationPersonaProfileError(f"Segmento não encontrado: {segment_name}.")
        if len(matches) > 1:
            raise ImplantationPersonaProfileError(f"Segmento ambíguo: {segment_name}.")
        return matches[0]

    @staticmethod
    def _resolve_persona(segment: dict[str, Any], *, persona_name: str) -> dict[str, Any]:
        personas = segment.get("personas") or []
        normalized = persona_name.strip()
        matches = [
            persona
            for persona in personas
            if isinstance(persona, dict) and str(persona.get("name") or "").strip() == normalized
        ]
        if not matches:
            raise ImplantationPersonaProfileError(f"Persona não encontrada: {persona_name}.")
        if len(matches) > 1:
            raise ImplantationPersonaProfileError(f"Persona ambígua: {persona_name}.")
        return matches[0]

    @staticmethod
    def preview_update(
        *,
        actor_user_id: int,
        company_id: int,
        plan_id: int,
        segment_name: str,
        persona_name: str,
        profile_text: str,
    ) -> ImplantationPersonaProfilePreview:
        actor_role = ImplantationPersonaProfileService._resolve_actor_role(
            user_id=actor_user_id,
            company_id=company_id,
        )
        plan, content = ImplantationPersonaProfileService._load_plan_and_content(
            company_id=company_id,
            plan_id=plan_id,
        )
        segment = ImplantationPersonaProfileService._resolve_segment(content, segment_name=segment_name)
        persona = ImplantationPersonaProfileService._resolve_persona(segment, persona_name=persona_name)

        before = str(persona.get("profile") or "")
        after = str(profile_text or "").strip()

        return ImplantationPersonaProfilePreview(
            company_id=company_id,
            plan_id=plan_id,
            plan_title=str(getattr(plan, "title", "") or ""),
            segment_name=str(segment.get("name") or segment_name).strip(),
            persona_name=str(persona.get("name") or persona_name).strip(),
            before=before,
            after=after,
            has_changes=before != after,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )

    @staticmethod
    def apply_update(
        *,
        actor_user_id: int,
        company_id: int,
        plan_id: int,
        segment_name: str,
        persona_name: str,
        profile_text: str,
        dry_run: bool = False,
    ) -> ImplantationPersonaProfileApplyResult:
        preview = ImplantationPersonaProfileService.preview_update(
            actor_user_id=actor_user_id,
            company_id=company_id,
            plan_id=plan_id,
            segment_name=segment_name,
            persona_name=persona_name,
            profile_text=profile_text,
        )
        if dry_run or not preview.has_changes:
            return ImplantationPersonaProfileApplyResult(**preview.to_dict(), saved=False)

        _, content = ImplantationPersonaProfileService._load_plan_and_content(
            company_id=company_id,
            plan_id=plan_id,
        )
        segment = ImplantationPersonaProfileService._resolve_segment(content, segment_name=segment_name)
        persona = ImplantationPersonaProfileService._resolve_persona(segment, persona_name=persona_name)
        persona["profile"] = preview.after
        PlanService.save_implantation_data(
            plan_id,
            company_id,
            ImplantationPersonaProfileService.SECTION_KEY,
            content,
        )
        return ImplantationPersonaProfileApplyResult(**preview.to_dict(), saved=True)
