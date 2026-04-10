from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.intelligence.mcp_contracts import AnalyticsAIEnvelope, build_analytics_ai_envelope


def test_build_analytics_ai_envelope_sets_grounding_and_guardrails():
    envelope = build_analytics_ai_envelope(
        analysis_id="projects_execution_risk",
        read_model="projects.execution_risk",
        company_id=31,
        filters={"company_id": 31, "project_id": 7},
        summary={"risk_items": 1},
        rows=[{"task_id": 10, "risk_label": "watch"}],
        signals={"watch_items": 1},
        capability_names=["get_projects_execution_risk_read_model"],
        limitations=["Dados limitados ao company_id informado."],
    )

    assert envelope.version == "app32.analytics.envelope.v1"
    assert envelope.company_id == 31
    assert envelope.cross_tenant_allowed is False
    assert envelope.sql_freeform_allowed is False
    assert envelope.grounding.source_read_models == ["projects.execution_risk"]
    assert envelope.grounding.row_count == 1
    assert "Basear a resposta apenas nos dados do envelope." in envelope.narrative_rules


def test_analytics_ai_envelope_rejects_cross_tenant_and_sql_freeform():
    base = {
        "analysis_id": "projects_execution_risk",
        "read_model": "projects.execution_risk",
        "company_id": 31,
        "filters": {"company_id": 31},
        "summary": {},
        "rows": [],
        "grounding": {
            "source_read_models": ["projects.execution_risk"],
            "input_filters": {"company_id": 31},
            "row_count": 0,
        },
    }

    with pytest.raises(ValidationError):
        AnalyticsAIEnvelope(**{**base, "cross_tenant_allowed": True})

    with pytest.raises(ValidationError):
        AnalyticsAIEnvelope(**{**base, "sql_freeform_allowed": True})


def test_analytics_ai_envelope_rejects_company_mismatch_between_envelope_and_grounding():
    with pytest.raises(ValidationError, match="company_id"):
        AnalyticsAIEnvelope(
            analysis_id="projects_execution_risk",
            read_model="projects.execution_risk",
            company_id=31,
            filters={"company_id": 31},
            summary={},
            rows=[],
            grounding={
                "source_read_models": ["projects.execution_risk"],
                "input_filters": {"company_id": 99},
                "row_count": 0,
            },
        )
