from __future__ import annotations

from typing import Any, Optional

from services.strategy_alignment_n1_service import (
    StrategyAlignmentN1Error,
    StrategyAlignmentN1Service,
)
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(
    operation: str,
    *,
    company_id: int | None = None,
    write: bool = False,
    analytics: bool = False,
) -> MCPResponseMeta:
    permissions = ["strategy.alignment.read"]
    if write:
        permissions = ["strategy.alignment.update"]
    elif analytics:
        permissions = ["strategy.alignment.analyze"]

    return MCPResponseMeta(
        domain="strategy",
        operation=operation,
        scope="mcp_analytics" if analytics else "mcp_user",
        company_id=company_id,
        capability=f"strategy_alignment_n1.{operation}",
        human_gate_required=write,
        permissions=permissions,
        tags=["strategy", "alignment_n1", "tenant_safe", "read_model" if analytics else "crud"],
    )


def _success(
    operation: str,
    data: Any,
    *,
    company_id: int | None = None,
    write: bool = False,
    analytics: bool = False,
) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, company_id=company_id, write=write, analytics=analytics),
    ).model_dump(mode="json")


def _error(
    operation: str,
    exc: Exception,
    *,
    company_id: int | None = None,
    write: bool = False,
    analytics: bool = False,
) -> dict[str, Any]:
    code = "strategy_alignment_n1_error"
    if isinstance(exc, PermissionError):
        code = "strategy_alignment_n1_forbidden"
    elif isinstance(exc, StrategyAlignmentN1Error):
        code = "strategy_alignment_n1_invalid_request"

    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=str(exc)),
        meta=_meta(operation, company_id=company_id, write=write, analytics=analytics),
    ).model_dump(mode="json")


def register_strategy_alignment_tools(mcp: Any) -> None:
    """Registra tools MCP para identidade estruturada e alinhamento estratégico N1."""

    def _get_identity(company_id: int) -> dict[str, Any]:
        operation = "identity.get"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.get_identity(company_id=company_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    def _upsert_identity(company_id: int, payload: dict[str, Any], user_id: Optional[int] = None) -> dict[str, Any]:
        operation = "identity.upsert"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.upsert_identity(
                    company_id=company_id,
                    payload=payload,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    def _get_process_profile(company_id: int, process_id: int) -> dict[str, Any]:
        operation = "process_profile.get"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.get_process_profile(
                    company_id=company_id,
                    process_id=process_id,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    def _upsert_process_profile(
        company_id: int,
        process_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        operation = "process_profile.upsert"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.upsert_process_profile(
                    company_id=company_id,
                    process_id=process_id,
                    payload=payload,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    def _get_readiness(company_id: int) -> dict[str, Any]:
        operation = "readiness.get"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.get_readiness(company_id=company_id),
                company_id=company_id,
                analytics=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, analytics=True)

    def _run_analysis(company_id: int) -> dict[str, Any]:
        operation = "analysis.run"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.run_alignment_analysis(company_id=company_id),
                company_id=company_id,
                analytics=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, analytics=True)

    @mcp.tool()
    def get_strategy_identity_tool(company_id: int) -> dict[str, Any]:
        """Lê a identidade organizacional estruturada do tenant, com fallback dos campos MVV legados."""
        return _get_identity(company_id)

    @mcp.tool()
    def get_organizational_identity_tool(company_id: int) -> dict[str, Any]:
        """Alias canônico consultivo: lê a identidade organizacional estruturada do tenant."""
        return _get_identity(company_id)

    @mcp.tool()
    def upsert_strategy_identity_tool(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria ou atualiza a identidade organizacional estruturada do tenant."""
        return _upsert_identity(company_id, payload, user_id=user_id)

    @mcp.tool()
    def upsert_organizational_identity_tool(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Alias canônico consultivo: cria ou atualiza a identidade organizacional estruturada."""
        return _upsert_identity(company_id, payload, user_id=user_id)

    @mcp.tool()
    def get_process_strategy_profile_tool(company_id: int, process_id: int) -> dict[str, Any]:
        """Lê o perfil estratégico estruturado de um processo dentro do tenant."""
        return _get_process_profile(company_id, process_id)

    @mcp.tool()
    def get_process_strategic_profile_tool(company_id: int, process_id: int) -> dict[str, Any]:
        """Alias canônico consultivo: lê o perfil estratégico estruturado de um processo."""
        return _get_process_profile(company_id, process_id)

    @mcp.tool()
    def upsert_process_strategy_profile_tool(
        company_id: int,
        process_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria ou atualiza objetivo, dono, cliente, indicadores, criticidade, maturidade, SIPOC e políticas do processo."""
        return _upsert_process_profile(company_id, process_id, payload, user_id=user_id)

    @mcp.tool()
    def upsert_process_strategic_profile_tool(
        company_id: int,
        process_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Alias canônico consultivo: cria ou atualiza o perfil estratégico estruturado do processo."""
        return _upsert_process_profile(company_id, process_id, payload, user_id=user_id)

    @mcp.tool()
    def list_process_strategy_alignment_links_tool(
        company_id: int,
        process_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Lista vínculos Processo -> objetivo/pilar/proposta/diferencial/competência/política."""
        operation = "alignment_links.list"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.list_alignment_links(
                    company_id=company_id,
                    process_id=process_id,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def upsert_process_strategy_alignment_link_tool(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria ou atualiza vínculo estratégico de processo para os cruzamentos de alinhamento N1."""
        operation = "alignment_links.upsert"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.upsert_alignment_link(
                    company_id=company_id,
                    payload=payload,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def delete_process_strategy_alignment_link_tool(company_id: int, link_id: int) -> dict[str, Any]:
        """Remove um vínculo estratégico de processo dentro do tenant."""
        operation = "alignment_links.delete"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.delete_alignment_link(
                    company_id=company_id,
                    link_id=link_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def list_indicator_line_of_sight_tool(
        company_id: int,
        process_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Lista vínculos Indicador de processo -> Indicador corporativo."""
        operation = "indicator_line_of_sight.list"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.list_indicator_line_of_sight(
                    company_id=company_id,
                    process_id=process_id,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def upsert_indicator_line_of_sight_tool(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria ou atualiza a linha de visada entre indicador de processo e indicador corporativo."""
        operation = "indicator_line_of_sight.upsert"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.upsert_indicator_line_of_sight(
                    company_id=company_id,
                    payload=payload,
                    user_id=user_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def delete_indicator_line_of_sight_tool(company_id: int, link_id: int) -> dict[str, Any]:
        """Remove linha de visada de indicadores dentro do tenant."""
        operation = "indicator_line_of_sight.delete"
        try:
            return _success(
                operation,
                StrategyAlignmentN1Service.delete_indicator_line_of_sight(
                    company_id=company_id,
                    link_id=link_id,
                ),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def get_strategy_alignment_n1_readiness_tool(company_id: int) -> dict[str, Any]:
        """Retorna readiness de dados para a Análise N1 de alinhamento estratégico."""
        return _get_readiness(company_id)

    @mcp.tool()
    def get_strategic_alignment_n1_readiness_tool(company_id: int) -> dict[str, Any]:
        """Alias canônico consultivo: retorna readiness para a Análise N1."""
        return _get_readiness(company_id)

    @mcp.tool()
    def run_strategy_alignment_n1_analysis_tool(company_id: int) -> dict[str, Any]:
        """Executa a Análise N1 e devolve mapa de alinhamento x desalinhamento tenant-safe."""
        return _run_analysis(company_id)

    @mcp.tool()
    def analyze_strategic_alignment_n1_tool(company_id: int) -> dict[str, Any]:
        """Alias canônico consultivo: executa a Análise N1 de alinhamento estratégico."""
        return _run_analysis(company_id)


__all__ = ["register_strategy_alignment_tools"]
