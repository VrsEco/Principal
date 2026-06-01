from __future__ import annotations

from typing import Any, Optional

from app import create_app
from services.real_estate_auction_service import RealEstateAuctionError, RealEstateAuctionService
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _run(callback, *args, **kwargs) -> Any:
    app = create_app()
    with app.app_context():
        return callback(*args, **kwargs)


def _meta(
    operation: str,
    *,
    company_id: int | None = None,
    write: bool = False,
) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="real_estate_auctions",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        capability=f"real_estate_auctions.{operation}",
        human_gate_required=write,
        permissions=["real_estate_auctions.update" if write else "real_estate_auctions.read"],
        tags=["real-estate-auctions", "tenant-safe", "gandu-invest" if company_id else "client-module"],
    )


def _success(
    operation: str,
    data: Any,
    *,
    company_id: int | None = None,
    write: bool = False,
) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, company_id=company_id, write=write),
        message="Operação do módulo Leilões Imobiliários concluída.",
    ).model_dump(mode="json")


def _error(
    operation: str,
    exc: Exception,
    *,
    company_id: int | None = None,
    write: bool = False,
) -> dict[str, Any]:
    code = "real_estate_auction_error"
    if isinstance(exc, PermissionError):
        code = "real_estate_auction_forbidden"
    elif isinstance(exc, RealEstateAuctionError):
        code = "real_estate_auction_invalid_request"
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=str(exc)),
        meta=_meta(operation, company_id=company_id, write=write),
    ).model_dump(mode="json")


def register_real_estate_auction_tools(mcp: Any) -> None:
    """Registra tools MCP tenant-safe para o módulo Leilões Imobiliários."""

    @mcp.tool()
    def get_real_estate_auction_settings_tool(company_id: int) -> dict[str, Any]:
        """Lê a configuração do módulo Leilões Imobiliários para a empresa."""
        operation = "settings.get"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.get_tenant_settings, company_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def upsert_real_estate_auction_settings_tool(company_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Habilita/desabilita e configura o módulo Leilões Imobiliários para a empresa."""
        operation = "settings.upsert"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.upsert_tenant_settings, company_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def get_real_estate_auction_workspace_tool(company_id: int) -> dict[str, Any]:
        """Retorna workspace/resumo do módulo Leilões Imobiliários no tenant."""
        operation = "workspace.get"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.get_workspace, company_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def list_real_estate_auction_properties_tool(
        company_id: int,
        status: Optional[str] = None,
        triage_status: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Lista imóveis/leilões do módulo, sempre escopando por company_id."""
        operation = "properties.list"
        try:
            return _success(
                operation,
                _run(
                    RealEstateAuctionService.list_properties,
                    company_id,
                    status=status,
                    triage_status=triage_status,
                    city=city,
                    state=state,
                    limit=limit,
                ),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def get_real_estate_auction_property_tool(company_id: int, property_id: int) -> dict[str, Any]:
        """Retorna detalhe de um imóvel/leilão com ficha financeira, diligência, eventos e anexos."""
        operation = "properties.get"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.get_property_detail, company_id, property_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def create_real_estate_auction_property_tool(
        company_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cria um imóvel/leilão no tenant habilitado."""
        operation = "properties.create"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.create_property, company_id, payload, user_id=user_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def update_real_estate_auction_property_tool(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Atualiza um imóvel/leilão dentro do tenant."""
        operation = "properties.update"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.update_property, company_id, property_id, payload, user_id=user_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def archive_real_estate_auction_property_tool(
        company_id: int,
        property_id: int,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Arquiva logicamente um imóvel/leilão dentro do tenant."""
        operation = "properties.archive"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.archive_property, company_id, property_id, user_id=user_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def list_real_estate_auction_sources_tool(company_id: int) -> dict[str, Any]:
        """Lista fontes de captação/importação do tenant para o módulo Leilões Imobiliários."""
        operation = "sources.list"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.list_sources, company_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def create_real_estate_auction_source_tool(company_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Cria uma fonte de importação/captação do módulo no tenant."""
        operation = "sources.create"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.create_source, company_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def update_real_estate_auction_source_tool(
        company_id: int,
        source_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Atualiza uma fonte de importação/captação do módulo no tenant."""
        operation = "sources.update"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.update_source, company_id, source_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def delete_real_estate_auction_source_tool(company_id: int, source_id: int) -> dict[str, Any]:
        """Remove logicamente uma fonte do módulo dentro do tenant."""
        operation = "sources.delete"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.delete_source, company_id, source_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def create_real_estate_auction_event_tool(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Cria um evento de leilão vinculado a um imóvel do tenant."""
        operation = "events.create"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.create_event, company_id, property_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def update_real_estate_auction_event_tool(
        company_id: int,
        property_id: int,
        event_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Atualiza um evento de leilão existente no tenant."""
        operation = "events.update"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.update_event, company_id, property_id, event_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def delete_real_estate_auction_event_tool(
        company_id: int,
        property_id: int,
        event_id: int,
    ) -> dict[str, Any]:
        """Remove um evento de leilão do imóvel dentro do tenant."""
        operation = "events.delete"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.delete_event, company_id, property_id, event_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def upsert_real_estate_auction_financial_sheet_tool(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Cria ou atualiza a ficha financeira de um imóvel do tenant."""
        operation = "financial_sheet.upsert"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.upsert_financial_sheet, company_id, property_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def upsert_real_estate_auction_due_diligence_tool(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Cria ou atualiza a ficha de diligência/posse/riscos do imóvel."""
        operation = "due_diligence.upsert"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.upsert_due_diligence, company_id, property_id, payload),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def create_real_estate_auction_attachment_tool(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Registra metadado de anexo para um imóvel/leilão do tenant."""
        operation = "attachments.create"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.create_attachment, company_id, property_id, payload, user_id=user_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)

    @mcp.tool()
    def delete_real_estate_auction_attachment_tool(
        company_id: int,
        property_id: int,
        attachment_id: int,
    ) -> dict[str, Any]:
        """Remove metadado de anexo de um imóvel/leilão no tenant."""
        operation = "attachments.delete"
        try:
            return _success(
                operation,
                _run(RealEstateAuctionService.delete_attachment, company_id, property_id, attachment_id),
                company_id=company_id,
                write=True,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)


__all__ = ["register_real_estate_auction_tools"]
