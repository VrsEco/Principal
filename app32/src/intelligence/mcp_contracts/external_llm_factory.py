from __future__ import annotations

from pydantic import Field

from .base import MCPSuccessEnvelope, MCPResponseMeta, _StrictModel


class ExternalLLMFactoryStrategy(_StrictModel):
    mode: str = Field(min_length=2, max_length=80)
    decision: str = Field(min_length=10, max_length=400)


class ExternalLLMFactoryManifest(_StrictModel):
    surface_key: str = "external_factory"
    current_strategy: ExternalLLMFactoryStrategy
    current_scope: list[str]
    future_scope: list[str]
    guardrails: list[str]
    evolution_rules: list[str]


class ExternalLLMFactoryEnvelope(MCPSuccessEnvelope[ExternalLLMFactoryManifest]):
    meta: MCPResponseMeta


def build_external_llm_factory_manifest() -> ExternalLLMFactoryManifest:
    return ExternalLLMFactoryManifest(
        current_strategy=ExternalLLMFactoryStrategy(
            mode="single_surface_now_split_ready",
            decision=(
                "Adotar uma surface única focada na Factory nesta fase, preparada para split futuro "
                "em Factory e Operations sem ruptura de contrato."
            ),
        ),
        current_scope=[
            "diagnóstico de mudanças",
            "catálogo de capacidades e dependências",
            "avaliação de risco e governança",
            "preparação de planos de mudança",
        ],
        future_scope=["financeiro", "rotina operacional", "planejamento estratégico", "processos", "analytics"],
        guardrails=[
            "Sem acesso direto ao banco por LLM externa.",
            "Toda execução sensível permanece validada pelo APP32.",
            "Tenant-scope, RBAC e audit trail obrigatórios.",
        ],
        evolution_rules=[
            "Separar surfaces quando operação multi-módulo exigir políticas distintas.",
            "Preservar contratos estáveis para clientes externos durante a evolução.",
        ],
    )


APP32_EXTERNAL_LLM_FACTORY_MANIFEST = build_external_llm_factory_manifest()
