from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_usage_dashboard_tools import register_usage_dashboard_tools
from src.intelligence.mcp_contracts import (
    APP32_USAGE_DASHBOARD_MANIFEST,
    UsageDashboardManifest,
    UsageDashboardMetric,
    UsageDashboardPanel,
)


SPEC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_usage_dashboard_spec.md"


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_usage_dashboard_manifest_defines_required_metrics_and_panels():
    manifest = APP32_USAGE_DASHBOARD_MANIFEST
    metric_ids = {metric.metric_id for metric in manifest.metrics}
    panel_ids = {panel.panel_id for panel in manifest.panels}

    assert manifest.version == "app32.ai-mcp.usage-dashboard.v1"
    assert manifest.tenant_scope_required is True
    assert manifest.sql_freeform_allowed is False
    assert {"company_id", "date_from", "date_to"} <= set(manifest.required_global_filters)
    assert {
        "ai_mcp_calls_total",
        "ai_mcp_error_rate",
        "mcp_tool_usage_by_domain",
        "workflow_resolution_trace",
        "agent_messages_volume",
        "catalog_surface_coverage",
    } <= metric_ids
    assert {"executive_overview", "mcp_operations", "sapiens_workflow_resolution"} <= panel_ids


def test_usage_dashboard_metrics_are_tenant_safe_and_no_sql_freeform():
    for metric in APP32_USAGE_DASHBOARD_MANIFEST.metrics:
        assert "company_id" in metric.required_filters
        assert metric.max_rows <= 1000
    assert any("SQL livre é proibido" in rule for rule in APP32_USAGE_DASHBOARD_MANIFEST.access_rules)


def test_usage_dashboard_tool_describes_manifest_and_metric():
    mcp = _FakeMCP()
    register_usage_dashboard_tools(mcp)
    tool = mcp.registered["describe_app32_usage_dashboard_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["meta"]["operation"] == "usage_dashboard.describe"
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.usage-dashboard.v1"

    metric_payload = tool("ai_mcp_error_rate")
    assert metric_payload["success"] is True
    assert metric_payload["data"]["metric_id"] == "ai_mcp_error_rate"
    assert metric_payload["data"]["source"] == "ai_audit_log"

    missing_payload = tool("missing")
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "usage_dashboard_metric_not_found"


def test_usage_dashboard_spec_doc_references_canonical_manifest_and_smoke():
    text = SPEC.read_text(encoding="utf-8")

    assert "Dashboard e Relatório de Uso IA/MCP" in text
    assert "APP32_USAGE_DASHBOARD_MANIFEST" in text
    assert "describe_app32_usage_dashboard_tool" in text
    assert "AI_MCP_USAGE_DASHBOARD_SPEC_OK 6 3" in text
    assert "`company_id`" in text
    assert "SQL livre é proibido" in text


def test_usage_dashboard_contract_rejects_missing_company_filter_and_broken_panel():
    with pytest.raises(ValidationError):
        UsageDashboardMetric(
            metric_id="unsafe_metric",
            title="Métrica insegura",
            kind="counter",
            source="workflow_usage",
            description="Métrica sem filtro de empresa deve falhar.",
            required_filters=["date_from", "date_to"],
            dimensions=["channel"],
            allowed_surfaces=["admin"],
        )

    valid_metric = UsageDashboardMetric(
        metric_id="safe_metric",
        title="Métrica segura",
        kind="counter",
        source="workflow_usage",
        description="Métrica com filtro obrigatório de empresa.",
        required_filters=["company_id"],
        dimensions=["channel"],
        allowed_surfaces=["admin"],
    )
    with pytest.raises(ValidationError):
        UsageDashboardManifest(
            data_sources=["workflow_usage"],
            metrics=[valid_metric],
            panels=[
                UsageDashboardPanel(
                    panel_id="broken",
                    title="Painel quebrado",
                    objective="Referenciar uma métrica inexistente deve falhar.",
                    metrics=["missing_metric"],
                    refresh_policy="Atualização sob demanda.",
                )
            ],
            operational_alerts=["alerta"],
            access_rules=["regra"],
        )
