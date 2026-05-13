from __future__ import annotations

from typing import Any

from services.implantation_persona_profile_service import (
    ImplantationPersonaProfileError,
    ImplantationPersonaProfilePermissionError,
    ImplantationPersonaProfileService,
)
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)
from src.intelligence.tool_context import get_sapiens_context


def _identity_payload(company_id: int | None) -> tuple[int | None, int | None]:
    identity = get_sapiens_context()
    return identity.user_id, company_id or identity.company_id


def _meta(
    operation: str,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    actor_role: str | None = None,
    human_gate_required: bool = False,
) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="plans_implantation_model",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=actor_role,
        capability=f"plans.implantation.model.persona_profile.{operation}",
        human_gate_required=human_gate_required,
        permissions=["plans.implantation.model.edit"],
        tags=["plans", "implantation", "persona", "profile", "sapiens"],
    )


def _error(code: str, message: str, *, operation: str, company_id: int | None = None, user_id: int | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message),
        meta=_meta(operation, company_id=company_id, user_id=user_id),
    ).model_dump(mode="json")


def register_implantation_persona_profile_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_implantation_persona_profile_tool() -> dict[str, Any]:
        """Descreve a capability MCP para leitura simulada e atualização de perfil de persona em planos de implantação."""
        return MCPSuccessEnvelope[Any](
            data={
                "surface": "user",
                "domain": "plans_implantation_model",
                "operations": [
                    "preview_app32_implantation_persona_profile_update_tool",
                    "apply_app32_implantation_persona_profile_update_tool",
                ],
                "required_fields": [
                    "plan_id",
                    "segment_name",
                    "persona_name",
                    "profile_text",
                ],
                "context_resolution": {
                    "company_id": "payload ou contexto MCP autenticado",
                    "user_id": "contexto MCP autenticado",
                },
                "guardrails": [
                    "company_id obrigatório",
                    "plano deve pertencer ao tenant",
                    "plano deve estar em modo implantation",
                    "segmento e persona devem ser resolvidos de forma única",
                    "persistência via PlanService.save_implantation_data",
                ],
            },
            meta=_meta("describe"),
            message="Capability de perfil de persona descrita com sucesso.",
        ).model_dump(mode="json")

    @mcp.tool()
    def preview_app32_implantation_persona_profile_update_tool(
        plan_id: int,
        segment_name: str,
        persona_name: str,
        profile_text: str,
        company_id: int | None = None,
    ) -> dict[str, Any]:
        """Simula a alteração do campo Perfil de uma persona do plano de implantação sem persistir."""
        actor_user_id, resolved_company_id = _identity_payload(company_id)
        if actor_user_id is None or resolved_company_id is None:
            return _error(
                "missing_mcp_context",
                "Sessão MCP sem user_id/company_id resolvido.",
                operation="preview",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )

        try:
            result = ImplantationPersonaProfileService.preview_update(
                actor_user_id=actor_user_id,
                company_id=resolved_company_id,
                plan_id=plan_id,
                segment_name=segment_name,
                persona_name=persona_name,
                profile_text=profile_text,
            )
        except ImplantationPersonaProfilePermissionError as exc:
            return _error(
                "permission_denied",
                str(exc),
                operation="preview",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )
        except ImplantationPersonaProfileError as exc:
            return _error(
                "persona_profile_preview_invalid",
                str(exc),
                operation="preview",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )

        return MCPSuccessEnvelope[Any](
            data=result.to_dict(),
            meta=_meta(
                "preview",
                company_id=result.company_id,
                user_id=result.actor_user_id,
                actor_role=result.actor_role,
            ),
            message="Prévia da alteração gerada com sucesso.",
        ).model_dump(mode="json")

    @mcp.tool()
    def apply_app32_implantation_persona_profile_update_tool(
        plan_id: int,
        segment_name: str,
        persona_name: str,
        profile_text: str,
        company_id: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Aplica a alteração do campo Perfil de uma persona do plano de implantação."""
        actor_user_id, resolved_company_id = _identity_payload(company_id)
        if actor_user_id is None or resolved_company_id is None:
            return _error(
                "missing_mcp_context",
                "Sessão MCP sem user_id/company_id resolvido.",
                operation="apply",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )

        try:
            result = ImplantationPersonaProfileService.apply_update(
                actor_user_id=actor_user_id,
                company_id=resolved_company_id,
                plan_id=plan_id,
                segment_name=segment_name,
                persona_name=persona_name,
                profile_text=profile_text,
                dry_run=dry_run,
            )
        except ImplantationPersonaProfilePermissionError as exc:
            return _error(
                "permission_denied",
                str(exc),
                operation="apply",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )
        except ImplantationPersonaProfileError as exc:
            return _error(
                "persona_profile_apply_invalid",
                str(exc),
                operation="apply",
                company_id=resolved_company_id,
                user_id=actor_user_id,
            )

        return MCPSuccessEnvelope[Any](
            data=result.to_dict(),
            meta=_meta(
                "apply",
                company_id=result.company_id,
                user_id=result.actor_user_id,
                actor_role=result.actor_role,
                human_gate_required=False,
            ),
            message="Alteração de perfil de persona processada com sucesso.",
        ).model_dump(mode="json")


__all__ = ["register_implantation_persona_profile_tools"]
