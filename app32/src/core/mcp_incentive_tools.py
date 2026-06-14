from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from models import Indicator
from services.incentive_spider_web_service import IncentiveSpiderWebService
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(
    operation: str,
    *,
    domain: str = "incentives",
    scope: str = "mcp_user",
    capability: str = "incentives.get_incentive_indicators",
    permissions: list[str] | None = None,
    tags: list[str] | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> MCPResponseMeta:
    safe_company_id = company_id if company_id and company_id > 0 else None
    return MCPResponseMeta(
        domain=domain,
        operation=operation,
        scope=scope,
        company_id=safe_company_id,
        user_id=user_id,
        request_id=request_id,
        trace_id=trace_id,
        capability=capability,
        permissions=permissions or ["incentives.indicators.read"],
        tags=tags or ["incentives", "indicators", "catalog", "multi_tenant"],
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
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return _serialize_value(value)


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


def _analytics_context(
    operation: str,
    *,
    company_id: int,
    user_id: int | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "company_id": company_id,
        "user_id": user_id,
        "request_id": request_id,
        "trace_id": trace_id,
        "domain": "analytics",
        "scope": "mcp_analytics",
        "capability": f"analytics.{operation}",
        "permissions": ["analytics.read"],
        "tags": ["analytics", "strategic_connections", "incentives", "read_model", "multi_tenant"],
    }


def _build_connection_graph_payload(*, company_id: int, anonymize: bool = False) -> dict[str, Any]:
    graph = _json_safe(IncentiveSpiderWebService.build_graph(company_id))

    if anonymize:
        collaborator_index = 0
        for node in graph.get("nodes", []):
            if node.get("type") == "collaborator":
                collaborator_index += 1
                node["label"] = f"Colaborador {collaborator_index}"
                node.pop("department", None)

    return {
        "snapshot": {
            "company_id": company_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "strategic_connections.v1",
            "source": "incentive_spider_web_service",
            "anonymized": anonymize,
        },
        "graph": graph,
        "limitations": [
            "Leitura tenant-safe baseada nos vínculos já cadastrados no APP32.",
            "Ausência de vínculo pode indicar gap real ou cadastro incompleto.",
            "A análise não altera dados e não substitui aprovação humana.",
        ],
    }


def _calculate_connection_metrics(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes", []))
    links = list(graph.get("links", []))
    total_nodes = len(nodes)
    max_links = total_nodes * (total_nodes - 1) / 2 if total_nodes > 1 else 0
    by_type = graph.get("summary", {}).get("by_type", {})
    by_health: dict[str, int] = {}
    for node in nodes:
        health = node.get("health", "unknown")
        by_health[health] = by_health.get(health, 0) + 1

    top_central_nodes = sorted(
        (
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "type": node.get("type"),
                "degree": node.get("degree", 0),
                "health": node.get("health"),
            }
            for node in nodes
        ),
        key=lambda item: item["degree"],
        reverse=True,
    )[:10]

    return {
        "total_nodes": total_nodes,
        "total_links": len(links),
        "density": round(len(links) / max_links, 4) if max_links else 0,
        "by_type": by_type,
        "by_health": by_health,
        "orphan_nodes": [node for node in nodes if node.get("health") == "orphan"][:25],
        "fragile_nodes": [node for node in nodes if node.get("health") == "fragile"][:25],
        "top_central_nodes": top_central_nodes,
        "coverage": {
            "has_processes": by_type.get("process", 0) > 0,
            "has_routines": by_type.get("routine", 0) > 0,
            "has_capacity_blocks": by_type.get("capacity", 0) > 0,
            "has_indicators": by_type.get("indicator", 0) > 0,
            "has_projects": by_type.get("project", 0) > 0,
            "has_collaborators": by_type.get("collaborator", 0) > 0,
        },
    }


def _build_connection_findings(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if metrics["by_health"].get("orphan", 0):
        findings.append(
            {
                "gap_type": "ORPHAN_NODES",
                "severity": "high",
                "finding": "Existem nós sem conexão na Teia.",
                "evidence": {"count": metrics["by_health"]["orphan"]},
                "recommendation": "Revisar vínculos entre objetivos operacionais, indicadores, processos, rotinas, pessoas e capacidade.",
                "confidence": 0.86,
            }
        )

    if not metrics["coverage"]["has_routines"]:
        findings.append(
            {
                "gap_type": "NO_ROUTINES_IN_GRAPH",
                "severity": "high",
                "finding": "A Teia não encontrou rotinas ativas conectadas.",
                "evidence": {"routine_nodes": 0},
                "recommendation": "Cadastrar ou vincular rotinas aos processos críticos para evidenciar execução recorrente.",
                "confidence": 0.9,
            }
        )

    if not metrics["coverage"]["has_capacity_blocks"]:
        findings.append(
            {
                "gap_type": "NO_CAPACITY_BLOCKS_IN_GRAPH",
                "severity": "medium",
                "finding": "A Teia não encontrou blocos de jornada/capacidade conectados.",
                "evidence": {"capacity_nodes": 0},
                "recommendation": "Vincular rotinas a blocos de jornada para permitir leitura de capacidade executiva.",
                "confidence": 0.84,
            }
        )

    if not metrics["coverage"]["has_indicators"]:
        findings.append(
            {
                "gap_type": "NO_INDICATORS_IN_GRAPH",
                "severity": "medium",
                "finding": "A Teia não encontrou indicadores ativos conectados.",
                "evidence": {"indicator_nodes": 0},
                "recommendation": "Conectar indicadores a processos, projetos ou rotinas para medir a execução.",
                "confidence": 0.82,
            }
        )

    return findings


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

    @mcp.tool()
    def get_strategic_connection_graph(
        company_id: int,
        include_nodes: bool = True,
        include_links: bool = True,
        anonymize: bool = False,
        user_id: int | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Expõe a Teia de Conexões atual como grafo analítico tenant-safe para MCP/Sapiens."""

        operation = "get_strategic_connection_graph"
        context = _analytics_context(
            operation,
            company_id=company_id,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        if company_id <= 0:
            return _error("invalid_company_id", "company_id deve ser um inteiro positivo.", operation=operation, **context)

        payload = _build_connection_graph_payload(company_id=company_id, anonymize=anonymize)
        if not include_nodes:
            payload["graph"]["nodes"] = []
        if not include_links:
            payload["graph"]["links"] = []

        return _success(operation, payload, **context)

    @mcp.tool()
    def get_strategic_connection_metrics(
        company_id: int,
        anonymize: bool = True,
        user_id: int | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Retorna métricas pré-calculadas da Teia para análise executiva por IA externa."""

        operation = "get_strategic_connection_metrics"
        context = _analytics_context(
            operation,
            company_id=company_id,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        if company_id <= 0:
            return _error("invalid_company_id", "company_id deve ser um inteiro positivo.", operation=operation, **context)

        payload = _build_connection_graph_payload(company_id=company_id, anonymize=anonymize)
        metrics = _calculate_connection_metrics(payload["graph"])
        return _success(
            operation,
            {
                "snapshot": payload["snapshot"],
                "metrics": metrics,
                "limitations": payload["limitations"],
            },
            **context,
        )

    @mcp.tool()
    def generate_strategic_connection_summary(
        company_id: int,
        max_gaps: int = 10,
        anonymize: bool = True,
        user_id: int | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Gera relatório analítico sucinto da Teia com gaps e recomendações baseadas em evidências."""

        operation = "generate_strategic_connection_summary"
        context = _analytics_context(
            operation,
            company_id=company_id,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        if company_id <= 0:
            return _error("invalid_company_id", "company_id deve ser um inteiro positivo.", operation=operation, **context)
        if max_gaps < 1 or max_gaps > 50:
            return _error("invalid_limit", "max_gaps deve estar entre 1 e 50.", operation=operation, details={"max_gaps": max_gaps}, **context)

        payload = _build_connection_graph_payload(company_id=company_id, anonymize=anonymize)
        metrics = _calculate_connection_metrics(payload["graph"])
        findings = _build_connection_findings(metrics)[:max_gaps]
        executive_summary = (
            f"Teia com {metrics['total_nodes']} nós e {metrics['total_links']} conexões. "
            f"Foram identificados {metrics['by_health'].get('orphan', 0)} nós órfãos e "
            f"{metrics['by_health'].get('fragile', 0)} nós frágeis."
        )

        return _success(
            operation,
            {
                "snapshot": payload["snapshot"],
                "executive_summary": executive_summary,
                "metrics": metrics,
                "findings": findings,
                "recommended_next_steps": [
                    "Revisar nós órfãos e confirmar se são lacuna real ou cadastro incompleto.",
                    "Conectar rotinas e blocos de jornada aos processos críticos.",
                    "Conectar indicadores aos processos, projetos ou rotinas que sustentam a execução.",
                ],
                "limitations": payload["limitations"],
            },
            **context,
        )


__all__ = ["register_incentive_tools"]
