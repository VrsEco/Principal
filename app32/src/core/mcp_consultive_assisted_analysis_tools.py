from __future__ import annotations

from typing import Any, Literal, Optional

from services.business_review_read_model_service import BusinessReviewReadModelService
from services.consultive_assisted_analysis_service import ConsultiveAssistedAnalysisService
from services.consultive_maturity_guidance_service import ConsultiveMaturityGuidanceService
from services.consultive_protocol_service import ConsultiveProtocolService
from services.urgent_business_review_common import UrgentBusinessReviewError
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


_RUNTIME_PROFILE_TO_VALIDATION_SQUAD = {
    "squad_cliente": "client",
    "squad_versus": "versus",
    "engineering": "engineering",
}


def _require_human_gate(confirmed: bool) -> None:
    if confirmed is not True:
        raise PermissionError("Confirmação humana explícita é obrigatória para esta operação consultiva.")


def _resolve_authenticated_user_id(requested_user_id: int | None) -> int | None:
    context = dict(get_http_request_context() or {})
    authenticated_user_id = context.get("user_id")
    if authenticated_user_id in (None, ""):
        return requested_user_id
    authenticated_user_id = int(authenticated_user_id)
    if requested_user_id not in (None, authenticated_user_id):
        raise PermissionError("user_id informado diverge do usuário autenticado no MCP.")
    return authenticated_user_id


def _require_own_squad_validation(squad: str) -> str:
    normalized_squad = str(squad or "").strip().lower()
    context = dict(get_http_request_context() or {})
    runtime_profile = str(context.get("runtime_profile") or "").strip().lower()
    expected_squad = _RUNTIME_PROFILE_TO_VALIDATION_SQUAD.get(runtime_profile)
    if expected_squad is None and get_http_actor_role() in {"cliente", "colaborador"}:
        expected_squad = "client"
    if expected_squad is not None and normalized_squad != expected_squad:
        raise PermissionError(
            f"O runtime {runtime_profile or get_http_actor_role()} só pode validar o próprio squad ({expected_squad})."
        )
    return normalized_squad


def _meta(operation: str, *, company_id: int | None = None, write: bool = False) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="consultive",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        actor_role=get_http_actor_role(),
        capability=f"consultive_assisted_analysis.{operation}",
        human_gate_required=write,
        permissions=["consultive.read"] if not write else ["consultive.write"],
        tags=["consultive", "assisted_analysis", "mcp_first", "tenant_safe"],
    )


def _success(operation: str, data: Any, *, company_id: int | None = None, write: bool = False) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, company_id=company_id, write=write),
    ).model_dump(mode="json")


def _error(operation: str, exc: Exception, *, company_id: int | None = None, write: bool = False) -> dict[str, Any]:
    code = "consultive_assisted_analysis_error"
    if isinstance(exc, PermissionError):
        code = "consultive_assisted_analysis_forbidden"
    elif isinstance(exc, (UrgentBusinessReviewError, ValueError)):
        code = "consultive_assisted_analysis_invalid_request"
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=str(exc)),
        meta=_meta(operation, company_id=company_id, write=write),
    ).model_dump(mode="json")


def register_consultive_assisted_analysis_tools(mcp: Any) -> None:
    """Registra tools MCP para IA/CLI ler contexto e devolver análise ao APP32."""

    @mcp.tool()
    def consultive_get_next_action(
        company_id: int,
        front_key: str,
        subphase_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Retorna estado, próximo responsável, ação, entradas, tools e gate da maturidade assistida."""
        operation = "next_action.get"
        try:
            return _success(
                operation,
                ConsultiveMaturityGuidanceService.get_next_action(
                    company_id=company_id,
                    front_key=front_key,
                    subphase_key=subphase_key,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_get_front_context(company_id: int, front_key: str) -> dict[str, Any]:
        """Retorna o contexto consolidado da frente consultiva no tenant."""
        operation = "front_context.get"
        try:
            return _success(
                operation,
                BusinessReviewReadModelService.get_structural_front_analysis(
                    company_id=company_id,
                    front_key=front_key,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_get_front_evidence(company_id: int, front_key: str) -> dict[str, Any]:
        """Lista evidências internas consideradas na frente consultiva."""
        operation = "front_evidence.get"
        try:
            payload = BusinessReviewReadModelService.get_structural_front_analysis(
                company_id=company_id,
                front_key=front_key,
            )
            return _success(operation, payload.get("internal_evidence", []), company_id=company_id)
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_get_front_gaps(company_id: int, front_key: str) -> dict[str, Any]:
        """Lista gaps metodológicos e técnicos da frente consultiva."""
        operation = "front_gaps.get"
        try:
            payload = BusinessReviewReadModelService.get_structural_front_analysis(
                company_id=company_id,
                front_key=front_key,
            )
            return _success(
                operation,
                {
                    "gaps": payload.get("gaps", []),
                    "engineering_gaps": payload.get("engineering_gaps", []),
                },
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_get_methodology_guidance(company_id: int, front_key: str) -> dict[str, Any]:
        """Retorna recomendações metodológicas Versus para análise assistida da frente."""
        operation = "methodology_guidance.get"
        try:
            payload = BusinessReviewReadModelService.get_structural_front_analysis(
                company_id=company_id,
                front_key=front_key,
            )
            protocol = ConsultiveProtocolService.resolve_protocol(
                company_id=company_id,
                front_key=front_key,
                subphase_key=None,
                audience="ai_cli",
            )
            return _success(
                operation,
                {
                    "front_key": front_key,
                    "active_protocol": protocol,
                    "recommendations": payload.get("recommendations", []),
                    "next_action": payload.get("next_action", {}),
                    "human_gate": "Não tomar decisão final. Registrar decisão do consultor no APP32.",
                    "token_policy": "Custo, tokens e capacidade pertencem ao tenant/cliente quando a análise for feita via IA/CLI externa.",
                },
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_resolve_protocol(
        company_id: int,
        front_key: str,
        subphase_key: Optional[str] = None,
        audience: Optional[str] = "ai_cli",
        depth_level: Optional[str] = None,
    ) -> dict[str, Any]:
        """Resolve o protocolo consultivo ativo, versionado e modificável para frente/subfase/audiência."""
        operation = "protocol.resolve"
        try:
            return _success(
                operation,
                ConsultiveProtocolService.resolve_protocol(
                    company_id=company_id,
                    front_key=front_key,
                    subphase_key=subphase_key,
                    audience=audience or "ai_cli",
                    depth_level=depth_level,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_upsert_protocol(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria ou atualiza um protocolo consultivo tenant-owned, versionado e reutilizável."""
        operation = "protocol.upsert"
        try:
            return _success(
                operation,
                ConsultiveProtocolService.upsert_protocol(
                    payload=payload,
                    company_id=company_id,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def consultive_register_assisted_analysis(
        company_id: int,
        front_key: str,
        payload: dict[str, Any],
        human_gate_confirmed: bool = False,
        analysis_type: Optional[Literal["methodological", "technical_test"]] = None,
        subphase_key: Optional[str] = None,
        human_evidence: Optional[list[str]] = None,
        internal_evidence: Optional[list[str]] = None,
        benchmark_not_applicable_reason: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Registra análise assistida após confirmação humana.

        A classificação e as evidências estruturadas são argumentos explícitos
        para aparecerem no schema MCP. O APP32 calcula journey_eligible; o
        cliente nunca pode forçar o avanço da jornada.
        """
        operation = "assisted_analysis.register"
        try:
            _require_human_gate(human_gate_confirmed)
            actor_user_id = _resolve_authenticated_user_id(user_id)
            normalized_payload = dict(payload)
            explicit_fields = {
                "analysis_type": analysis_type,
                "subphase_key": subphase_key,
                "human_evidence": human_evidence,
                "internal_evidence": internal_evidence,
                "benchmark_not_applicable_reason": benchmark_not_applicable_reason,
            }
            normalized_payload.update(
                {key: value for key, value in explicit_fields.items() if value is not None}
            )
            return _success(
                operation,
                ConsultiveAssistedAnalysisService.register_assisted_analysis(
                    company_id=company_id,
                    front_key=front_key,
                    payload=normalized_payload,
                    user_id=actor_user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def consultive_list_assisted_analyses(
        company_id: int,
        front_key: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = 100,
    ) -> dict[str, Any]:
        """Lista o histórico tenant-safe de análises assistidas e decisões consultivas."""
        operation = "assisted_analysis.list"
        try:
            return _success(
                operation,
                ConsultiveAssistedAnalysisService.list_analyses(
                    company_id=company_id,
                    front_key=front_key,
                    status=status,
                    limit=limit or 100,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def consultive_register_squad_validation(
        company_id: int,
        analysis_id: int,
        squad: str,
        status: str,
        notes: Optional[str] = None,
        human_gate_confirmed: bool = False,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Registra validação do próprio squad após confirmação humana explícita."""
        operation = "squad_validation.register"
        try:
            _require_human_gate(human_gate_confirmed)
            normalized_squad = _require_own_squad_validation(squad)
            actor_user_id = _resolve_authenticated_user_id(user_id)
            return _success(
                operation,
                ConsultiveAssistedAnalysisService.register_squad_validation(
                    company_id=company_id,
                    analysis_id=analysis_id,
                    squad=normalized_squad,
                    status=status,
                    notes=notes,
                    user_id=actor_user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def consultive_register_consultant_decision(
        company_id: int,
        analysis_id: int,
        payload: dict[str, Any],
        human_gate_confirmed: bool = False,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Registra o gate humano exclusivo do consultor antes da conversão operacional."""
        operation = "consultant_decision.register"
        try:
            _require_human_gate(human_gate_confirmed)
            actor_user_id = _resolve_authenticated_user_id(user_id)
            return _success(
                operation,
                ConsultiveAssistedAnalysisService.register_consultant_decision(
                    company_id=company_id,
                    analysis_id=analysis_id,
                    payload=payload,
                    user_id=actor_user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def consultive_create_recommended_action(
        company_id: int,
        analysis_id: int,
        conversion_target: str,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Registra intenção de conversão; criação operacional ocorre por tool específica com gate humano."""
        operation = "recommended_action.create"
        try:
            return _success(
                operation,
                ConsultiveAssistedAnalysisService.create_recommended_action(
                    company_id=company_id,
                    analysis_id=analysis_id,
                    conversion_target=conversion_target,
                    payload=payload,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)


__all__ = ["register_consultive_assisted_analysis_tools"]
