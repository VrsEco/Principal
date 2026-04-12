from __future__ import annotations

from typing import Any

from services.integration_catalog_service import IntegrationCatalogService
from services.integration_request_service import IntegrationRequestService


def register_integration_request_tools(mcp: Any) -> None:
    @mcp.tool()
    def list_app32_integrations_catalog() -> dict[str, Any]:
        """Lista o catálogo consultivo de integrações API/MCP do APP32."""
        return IntegrationCatalogService.build_catalog()

    @mcp.tool()
    def request_new_app32_integration(
        *,
        company_id: int,
        requester_user_id: int,
        title: str,
        business_domain: str,
        integration_mode: str,
        technical_channel: str,
        external_system: str,
        objective: str,
        data_summary: str,
        source_channel: str = "mcp",
        frequency: str | None = None,
        urgency: str = "medium",
        compliance_level: str = "internal",
        provider_contact: str | None = None,
        provider_docs_url: str | None = None,
        notes: str | None = None,
        requester_name: str | None = None,
    ) -> dict[str, Any]:
        record = IntegrationRequestService.create_request(
            {
                "title": title,
                "business_domain": business_domain,
                "integration_mode": integration_mode,
                "technical_channel": technical_channel,
                "external_system": external_system,
                "objective": objective,
                "data_summary": data_summary,
                "source_channel": source_channel,
                "frequency": frequency,
                "urgency": urgency,
                "compliance_level": compliance_level,
                "provider_contact": provider_contact,
                "provider_docs_url": provider_docs_url,
                "notes": notes,
            },
            company_id=company_id,
            requester_user_id=requester_user_id,
            requester_name=requester_name,
        )
        return {"success": True, "request": record.to_dict()}
