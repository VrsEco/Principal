from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import Indicator
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(
    operation: str,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="incentives",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        request_id=request_id,
        trace_id=trace_id,
        capability="incentives.get_incentive_indicators",
        permissions=["incentives.indicators.read"],
        tags=["incentives", "indicators", "catalog", "multi_tenant"],
        tenant_safe=True,
        human_gate_required=False,
    )


def _success(operation: str, data: Any, **context: Any) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, **context),
        message="Catálogo de indicadores retornado com sucesso.",
    ).model_dump(mode="json")


def _error(code: str, message: str, *, operation: str, details: dict[str, Any] | None = None, **context: Any) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(
            code=code,
            message=message,
            details=details or {},
        ),
        meta=_meta(operation, **context),
    ).model_dump(mode="json")


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _serialize_indicator(indicator: Any) -> dict[str, Any]:
    return {
        "id": indicator.id,
        "company_id": indicator.company_id,
        "code": indicator.code,
        "full_code": getattr(indicator, "full_code", None),
        "name": indicator.name,
        "description": getattr(indicator, "description", None),
        "indicator_type": getattr(indicator, "indicator_type", None),
        "source_module": getattr(indicator, "source_module", None),
        "source_id": getattr(indicator, "source_id", None),
        "source_scope": getattr(indicator, "source_scope", None),
        "source_config": getattr(indicator, "source_config", None),
        "collection_mode": getattr(indicator, "collection_mode", None),
        "aggregation_function": getattr(indicator, "aggregation_function", None),
        "unit": getattr(indicator, "unit", None),
        "polarity": getattr(indicator, "polarity", None),
        "measurement_frequency": getattr(indicator, "measurement_frequency", None),
        "responsible_id": getattr(indicator, "responsible_id", None),
        "is_active": getattr(indicator, "is_active", None),
        "created_at": _serialize_value(getattr(indicator, "created_at", None)),
        "updated_at": _serialize_value(getattr(indicator, "updated_at", None)),
    }


def _fetch_indicator_catalog(
    *,
    company_id: int,
    is_active: bool | None,
    collection_mode: str | None,
    source_module: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    query = Indicator.query.filter_by(company_id=company_id)

    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    if collection_mode:
        query = query.filter_by(collection_mode=collection_mode.strip().lower())
    if source_module:
        query = query.filter_by(source_module=source_module.strip().lower())

    indicators = query.limit(limit).all()
    return [_serialize_indicator(indicator) for indicator in indicators]


def register_incentive_tools(mcp: Any) -> None:
    @mcp.tool()
    def get_incentive_indicators(
        company_id: int,
        is_active: bool | None = True,
        collection_mode: str | None = None,
        source_module: str | None = None,
        limit: int = 100,
        user_id: int | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Expõe via MCP o catálogo multi-tenant de indicadores canônicos do domínio de incentivos."""

        operation = "get_incentive_indicators"
        context = {
            "company_id": company_id,
            "user_id": user_id,
            "request_id": request_id,
            "trace_id": trace_id,
        }

        if company_id <= 0:
            return _error(
                "invalid_company_id",
                "company_id deve ser um inteiro positivo.",
                operation=operation,
                details={"company_id": company_id},
                **context,
            )

        if limit < 1 or limit > 500:
            return _error(
                "invalid_limit",
                "limit deve estar entre 1 e 500.",
                operation=operation,
                details={"limit": limit},
                **context,
            )

        items = _fetch_indicator_catalog(
            company_id=company_id,
            is_active=is_active,
            collection_mode=collection_mode,
            source_module=source_module,
            limit=limit,
        )

        return _success(
            operation,
            {
                "items": items,
                "count": len(items),
                "filters": {
                    "company_id": company_id,
                    "is_active": is_active,
                    "collection_mode": collection_mode,
                    "source_module": source_module,
                    "limit": limit,
                },
                "model": "Indicator",
            },
            **context,
        )


__all__ = ["register_incentive_tools"]
