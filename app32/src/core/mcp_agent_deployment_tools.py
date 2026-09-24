"""Tools MCP do control plane de deploy do Squad Engenharia."""
from __future__ import annotations
from typing import Any


def _identity():
    from src.core.mcp_http_auth import get_http_request_identity
    identity = get_http_request_identity()
    if identity is None:
        raise ValueError("deploy MCP exige identidade HTTP autenticada")
    return identity


def register_agent_deployment_mcp_tools(mcp: Any) -> None:
    @mcp.tool()
    def request_agent_deployment(company_id: int, actor_kind: str, target_sha: str,
                                 mode: str = "quick", restart_mcp: bool = False) -> dict:
        """Registra solicitação de deploy. GitHub Actions é o único executor."""
        from services.agent_deployment_service import create_agent_deployment
        return create_agent_deployment(company_id=company_id, identity=_identity(), actor_kind=actor_kind,
                                       target_sha=target_sha, mode=mode, restart_mcp=restart_mcp)

    @mcp.tool()
    def list_agent_deployments(company_id: int, limit: int = 20) -> dict:
        """Lista deploys do tenant autenticado sem expor registros de outras empresas."""
        from services.agent_deployment_service import list_agent_deployments
        return {"company_id": company_id, "items": list_agent_deployments(company_id=company_id, identity=_identity(), limit=limit)}

    @mcp.tool()
    def record_agent_deployment_run(company_id: int, deployment_id: int, github_run_url: str,
                                    status: str) -> dict:
        """Registra o run GitHub correlacionado pelo mesmo agente autenticado."""
        from services.agent_deployment_service import record_agent_deployment_run
        return record_agent_deployment_run(company_id=company_id, identity=_identity(), deployment_id=deployment_id,
                                           github_run_url=github_run_url, status=status)
