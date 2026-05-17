from __future__ import annotations

from typing import Any

from services.mcp_connection_snippet_service import MCPConnectionSnippetService
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


class SapiensActivationService:
    """Resolve ativação genérica do Sapiens com seleção de squad quando aplicável."""

    ROLE_ALLOWED_SQUADS = {
        "admin": ("squad_cliente", "squad_versus", "engineering"),
        "administrator": ("squad_cliente", "squad_versus", "engineering"),
        "administrador": ("squad_cliente", "squad_versus", "engineering"),
        "consultant": ("squad_cliente", "squad_versus"),
        "consultor": ("squad_cliente", "squad_versus"),
        "collaborator": ("squad_cliente",),
        "colaborador": ("squad_cliente",),
        "client": ("squad_cliente",),
        "cliente": ("squad_cliente",),
        "user": ("squad_cliente",),
    }

    SQUAD_CHOICES = {
        "squad_cliente": {
            "choice_label": "Cliente",
            "experience_label": "Sapiens Cliente",
            "command": "/sapiens-cliente-on",
            "runtime_profile": "squad_cliente",
            "activation_status": "Sapiens Cliente Ativado",
            "session_badge": "Sapiens Cliente On",
        },
        "squad_versus": {
            "choice_label": "Versus",
            "experience_label": "Sapiens Consultor",
            "command": "/sapiens-consultor-on",
            "runtime_profile": "squad_versus",
            "activation_status": "Sapiens Consultor Ativado",
            "session_badge": "Sapiens Consultor On",
        },
        "engineering": {
            "choice_label": "Engenharia",
            "experience_label": "Sapiens Engenharia",
            "command": "/sapiens-engenharia-on",
            "runtime_profile": "engineering",
            "activation_status": "Sapiens Engenharia Ativado",
            "session_badge": "Sapiens Engenharia On",
        },
    }

    DEFAULT_SELECTION_PROMPT = "Escolha entre: Cliente, Versus ou Engenharia."

    @classmethod
    def normalize_squad(cls, squad: str | None) -> str | None:
        normalized = str(squad or "").strip().lower()
        if not normalized:
            return None
        aliases = {
            "cliente": "squad_cliente",
            "sapiens cliente": "squad_cliente",
            "squad cliente": "squad_cliente",
            "versus": "squad_versus",
            "consultor": "squad_versus",
            "sapiens consultor": "squad_versus",
            "squad versus": "squad_versus",
            "engenharia": "engineering",
            "sapiens engenharia": "engineering",
            "engineering": "engineering",
            "squad engenharia": "engineering",
        }
        if normalized in cls.SQUAD_CHOICES:
            return normalized
        return aliases.get(normalized)

    @classmethod
    def allowed_squads_for_role(cls, role: str | None) -> tuple[str, ...]:
        normalized = str(role or "").strip().lower()
        return cls.ROLE_ALLOWED_SQUADS.get(normalized, ("squad_cliente",))

    @classmethod
    def list_available_squads(
        cls,
        *,
        role: str | None = None,
        installed_squads: list[str] | tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        allowed = list(cls.allowed_squads_for_role(role))
        installed_normalized = {
            item for item in (cls.normalize_squad(raw) for raw in (installed_squads or ())) if item
        }
        if installed_normalized:
            allowed = [item for item in allowed if item in installed_normalized]
        if not allowed:
            allowed = ["squad_cliente"]
        return [cls._serialize_squad(item) for item in allowed]

    @classmethod
    def selection_prompt_for_squads(cls, squads: list[dict[str, Any]]) -> str | None:
        if len(squads) <= 1:
            return None
        labels = [item["choice_label"] for item in squads]
        if labels == ["Cliente", "Versus", "Engenharia"]:
            return cls.DEFAULT_SELECTION_PROMPT
        return "Escolha entre: " + ", ".join(labels) + "."

    @classmethod
    def resolve_activation(
        cls,
        *,
        role: str | None = None,
        squad: str | None = None,
        installed_squads: list[str] | tuple[str, ...] | None = None,
        company_id: int | None = None,
    ) -> dict[str, Any]:
        available = cls.list_available_squads(role=role, installed_squads=installed_squads)
        normalized_squad = cls.normalize_squad(squad)
        selection_prompt = cls.selection_prompt_for_squads(available)

        if normalized_squad is None:
            if len(available) == 1:
                normalized_squad = available[0]["key"]
            else:
                return {
                    "selection_required": True,
                    "selection_prompt": selection_prompt,
                    "available_squads": available,
                    "free_text_aliases": ["Sapiens On", "sapiens on", "/sapiens-on"],
                }

        selected = next((item for item in available if item["key"] == normalized_squad), None)
        if selected is None:
            raise ValueError("Squad solicitado não está disponível para este usuário/contexto.")

        runtime_spec = get_runtime_profile_spec(selected["runtime_profile"])
        startup_tools = list(
            MCPConnectionSnippetService.RUNTIME_PROFILES.get(selected["runtime_profile"], {}).get("startup_tools", [])
        )
        return {
            "selection_required": False,
            "available_squads": available,
            "selected_squad": selected,
            "selection_prompt": selection_prompt,
            "company_id": company_id,
            "session_title": selected["activation_status"],
            "session_badge": selected["session_badge"],
            "activation_message": f"{selected['activation_status']}.",
            "startup_tools": startup_tools,
            "surface": runtime_spec.default_surface if runtime_spec else None,
            "harness_key": runtime_spec.default_harness_key if runtime_spec else None,
            "harness_label": runtime_spec.default_harness_label if runtime_spec else None,
            "runtime_family_label": runtime_spec.family_label if runtime_spec else None,
            "free_text_aliases": ["Sapiens On", "sapiens on", "/sapiens-on"],
        }

    @classmethod
    def _serialize_squad(cls, key: str) -> dict[str, Any]:
        data = cls.SQUAD_CHOICES[key]
        return {
            "key": key,
            "choice_label": data["choice_label"],
            "experience_label": data["experience_label"],
            "command": data["command"],
            "runtime_profile": data["runtime_profile"],
            "activation_status": data["activation_status"],
            "session_badge": data["session_badge"],
        }


__all__ = ["SapiensActivationService"]
