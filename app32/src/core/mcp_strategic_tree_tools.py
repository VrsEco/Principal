from __future__ import annotations

from typing import Any, Optional

from services.knowledge.strategic_tree_policy import StrategicTreeActor
from services.knowledge.strategic_tree_service import StrategicTreeService
from src.core.mcp_runtime import resolve_mcp_execution_context


def _actor(company_id: int) -> StrategicTreeActor:
    context = resolve_mcp_execution_context({"company_id": company_id})
    if context.user_id is None or context.company_id is None:
        raise PermissionError("Contexto autenticado com user_id e company_id é obrigatório.")
    if int(context.company_id) != int(company_id):
        raise PermissionError("company_id informado diverge do tenant resolvido pelo runtime.")
    profile = {
        "administrador": "administrator",
        "administrador_tecnico": "administrator",
        "cliente": "client",
        "consultor": "consultant",
    }.get(context.role, "collaborator")
    return StrategicTreeActor(
        user_id=int(context.user_id),
        company_id=int(context.company_id),
        profile=profile,
        accessible_company_ids=tuple(context.accessible_company_ids or ()),
    )


def _response(operation: str, company_id: int, data: dict) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "meta": {
            "domain": "knowledge",
            "capability": "strategic_tree",
            "operation": operation,
            "company_id": int(company_id),
            "tenant_safe": True,
            "canonical_write": False,
        },
    }


def register_strategic_tree_tools(mcp: Any) -> None:
    service = StrategicTreeService()

    @mcp.tool()
    def strategic_tree_list(company_id: int) -> dict[str, Any]:
        """Lista Árvores Estratégicas autorizadas da empresa informada."""
        return _response("list", company_id, service.list_trees(_actor(company_id)))

    @mcp.tool()
    def strategic_tree_get(company_id: int, tree_id: int) -> dict[str, Any]:
        """Obtém estrutura, ramos e contagens de uma Árvore Estratégica tenant-safe."""
        return _response("get", company_id, service.get_tree(_actor(company_id), tree_id))

    @mcp.tool()
    def strategic_tree_get_branch(company_id: int, tree_id: int, node_id: int) -> dict[str, Any]:
        """Lê um ramo autorizado, seu breadcrumb, contribuições e próxima ação."""
        return _response(
            "branch.get",
            company_id,
            service.get_branch(_actor(company_id), tree_id=tree_id, node_id=node_id),
        )

    @mcp.tool()
    def strategic_tree_add_contribution(
        company_id: int,
        tree_id: int,
        content: str,
        node_id: Optional[int] = None,
        attribution_mode: str = "identified",
        visibility_scope: str = "company_authorized",
        idempotency_key: Optional[str] = None,
        human_gate_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Registra contribuição humana confirmada, sem promover conteúdo a dado canônico."""
        if human_gate_confirmed is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para registrar uma contribuição.")
        if not str(idempotency_key or "").strip():
            raise ValueError("idempotency_key é obrigatória para escrita via MCP.")
        result = service.add_contribution(
            _actor(company_id),
            tree_id=tree_id,
            node_id=node_id,
            content=content,
            attribution_mode=attribution_mode,
            visibility_scope=visibility_scope,
            source_type="mcp",
            idempotency_key=idempotency_key,
            surface="mcp",
        )
        return _response("contribution.create", company_id, result)


__all__ = ["register_strategic_tree_tools"]
