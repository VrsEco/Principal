from __future__ import annotations

from typing import Any

from services.sapiens_factory_schema import ExternalLLMFactorySessionRequest


class ExternalLLMFactoryService:
    """Surface consultiva para clientes LLM externos focados na Sapiens Factory."""

    @classmethod
    def build_surface_manifest(cls) -> dict[str, Any]:
        return {
            "surface_key": "external_factory",
            "current_strategy": {
                "mode": "single_surface_now_split_ready",
                "decision": (
                    "Usar uma surface única focada na Factory nesta fase, preparada para evoluir "
                    "para duas surfaces independentes (Factory e Operations) sem ruptura de contrato."
                ),
            },
            "current_scope": [
                "diagnóstico de mudanças",
                "catálogo de capacidades e dependências",
                "avaliação de risco e governança",
                "preparação de planos de mudança",
            ],
            "future_scope": ["financeiro", "rotina operacional", "planejamento estratégico", "processos", "analytics"],
            "guardrails": [
                "A LLM externa não acessa banco diretamente.",
                "Toda execução sensível continua validada pelo APP32.",
                "Tenant-scope, RBAC e audit trail são obrigatórios.",
            ],
            "evolution_rules": [
                "Split de surfaces quando a operação multi-módulo exigir políticas mais distintas.",
                "Manter contratos estáveis para clientes externos durante a separação futura.",
            ],
        }

    @classmethod
    def evaluate_external_session(cls, raw_payload: dict[str, Any]) -> dict[str, Any]:
        payload = ExternalLLMFactorySessionRequest.model_validate(raw_payload)
        manifest = cls.build_surface_manifest()
        requested_surface = str(payload.requested_surface or "factory").strip().lower()
        is_factory_surface = requested_surface in {"factory", "external_factory", "mcp_factory"}
        allowed = is_factory_surface
        recommended_next_step = (
            "Consumir o catálogo consultivo e iniciar pelo assessment de mudança."
            if allowed
            else "Usar a surface factory nesta fase; a surface operacional multi-módulo permanece roadmap."
        )
        return {
            "allowed": allowed,
            "requested_surface": requested_surface,
            "recommended_surface": "external_factory",
            "recommended_next_step": recommended_next_step,
            "manifest_summary": manifest["current_strategy"],
            "session": payload.model_dump(mode="json"),
        }
