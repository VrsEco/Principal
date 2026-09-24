"""Tools MCP do control plane de deploy do Squad Engenharia.

As tools só adaptam o contexto autenticado e delegam ao service. Não existe
tool para registrar sucesso/falha: isso é exclusivo do callback OIDC do
workflow oficial. O tenant vem do contexto validado pelo wrapper MCP, nunca de
um ``company_id`` livre do agente; o ``actor_kind`` é derivado do client_id.
"""
from __future__ import annotations
from typing import Any

AGENT_DEPLOYMENT_TOOL_NAMES = (
    "request_agent_deployment",
    "approve_agent_deployment",
    "get_agent_deployment",
    "list_agent_deployments",
)


def _identity():
    from src.core.mcp_http_auth import get_http_request_identity
    identity = get_http_request_identity()
    if identity is None:
        raise ValueError("deploy MCP exige identidade HTTP autenticada")
    return identity


def _company_id() -> int | None:
    from src.intelligence.tool_context import get_sapiens_context
    return get_sapiens_context().company_id


def register_agent_deployment_mcp_tools(mcp: Any) -> None:
    @mcp.tool()
    def request_agent_deployment(target_sha: str, mode: str = "quick", restart_mcp: bool = False,
                                 migration_confirmed: bool = False) -> dict:
        """Solicita deploy (fica pendente de aprovação humana). GitHub Actions é o único executor."""
        from services.agent_deployment_service import create_agent_deployment
        return create_agent_deployment(company_id=_company_id(), identity=_identity(), target_sha=target_sha,
                                       mode=mode, restart_mcp=restart_mcp, migration_confirmed=migration_confirmed)

    @mcp.tool()
    def approve_agent_deployment(deployment_id: int) -> dict:
        """Aprova (somente humano) e dispara o workflow oficial de deploy."""
        from services.agent_deployment_service import approve_agent_deployment as approve
        return approve(company_id=_company_id(), identity=_identity(), deployment_id=deployment_id)

    @mcp.tool()
    def get_agent_deployment(deployment_id: int) -> dict:
        """Consulta um deploy do tenant de governança com a trilha de eventos."""
        from services.agent_deployment_service import get_agent_deployment as get_one
        return get_one(company_id=_company_id(), identity=_identity(), deployment_id=deployment_id)

    @mcp.tool()
    def list_agent_deployments(limit: int = 20) -> dict:
        """Lista deploys do tenant de governança sem expor registros de outras empresas."""
        from services.agent_deployment_service import list_agent_deployments as list_items
        return {"items": list_items(company_id=_company_id(), identity=_identity(), limit=limit)}
