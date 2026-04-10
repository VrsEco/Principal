from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


DEFAULT_ANALYTICS_NARRATIVE_RULES = [
    "Basear a resposta apenas nos dados do envelope.",
    "Não inferir dados ausentes; declarar limitações quando houver lacuna.",
    "Não sugerir mutações pela surface analytics.",
    "Preservar escopo tenant-safe e não comparar empresas fora do filtro recebido.",
]


class AnalyticsGrounding(_StrictModel):
    source_read_models: list[str] = Field(default_factory=list, min_length=1)
    capability_names: list[str] = Field(default_factory=list)
    input_filters: dict[str, Any] = Field(default_factory=dict)
    row_count: int = Field(default=0, ge=0)
    tenant_safe: bool = True

    @model_validator(mode="after")
    def _validate_grounding(self):
        if not self.tenant_safe:
            raise ValueError("Grounding analítico deve ser tenant_safe=True.")
        return self


class AnalyticsAIEnvelope(_StrictModel):
    version: str = Field(default="app32.analytics.envelope.v1", min_length=1, max_length=80)
    analysis_id: str = Field(min_length=4, max_length=80)
    read_model: str = Field(min_length=4, max_length=120)
    company_id: int = Field(gt=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filters: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
    grounding: AnalyticsGrounding
    limitations: list[str] = Field(default_factory=list)
    narrative_rules: list[str] = Field(default_factory=lambda: list(DEFAULT_ANALYTICS_NARRATIVE_RULES))
    cross_tenant_allowed: bool = False
    sql_freeform_allowed: bool = False

    @model_validator(mode="after")
    def _validate_ai_envelope(self):
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at deve ser timezone-aware.")
        if self.cross_tenant_allowed:
            raise ValueError("Envelope analítico não pode liberar cross-tenant.")
        if self.sql_freeform_allowed:
            raise ValueError("Envelope analítico não pode liberar SQL livre.")
        if self.company_id != self.grounding.input_filters.get("company_id"):
            raise ValueError("company_id do envelope deve bater com grounding.input_filters.company_id.")
        return self


AnalyticsAIEnvelopeResponse = MCPSuccessEnvelope[AnalyticsAIEnvelope]


def build_analytics_ai_envelope(
    *,
    analysis_id: str,
    read_model: str,
    company_id: int,
    filters: dict[str, Any],
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    dimensions: dict[str, Any] | None = None,
    signals: dict[str, Any] | None = None,
    capability_names: list[str] | None = None,
    limitations: list[str] | None = None,
) -> AnalyticsAIEnvelope:
    normalized_filters = dict(filters)
    normalized_filters["company_id"] = int(company_id)
    return AnalyticsAIEnvelope(
        analysis_id=analysis_id,
        read_model=read_model,
        company_id=int(company_id),
        filters=normalized_filters,
        summary=summary,
        dimensions=dimensions or {},
        rows=rows,
        signals=signals or {},
        grounding=AnalyticsGrounding(
            source_read_models=[read_model],
            capability_names=capability_names or [],
            input_filters=normalized_filters,
            row_count=len(rows),
        ),
        limitations=limitations or [],
    )


__all__ = [
    "AnalyticsAIEnvelope",
    "AnalyticsAIEnvelopeResponse",
    "AnalyticsGrounding",
    "DEFAULT_ANALYTICS_NARRATIVE_RULES",
    "build_analytics_ai_envelope",
]
