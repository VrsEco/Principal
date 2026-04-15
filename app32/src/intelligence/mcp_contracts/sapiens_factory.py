from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import MCPSuccessEnvelope, MCPResponseMeta, _StrictModel


class SapiensFactorySupportedIntent(_StrictModel):
    change_type: Literal["create", "alter", "activate", "deactivate", "fix", "refactor", "diagnose"]
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=240)


class SapiensFactoryManifest(_StrictModel):
    product_name: str = "Sapiens Factory"
    surface_key: str = "factory"
    current_focus: str = "Evolução técnica assistida com governança e human gate."
    rule_of_execution: str = "Service -> Tool + contrato -> REST/MCP -> Workflow -> UI/Sapiens"
    intents: list[SapiensFactorySupportedIntent]
    target_layers: list[str]
    execution_modes: list[str]
    guardrails: list[str]


class SapiensFactoryEnvelope(MCPSuccessEnvelope[SapiensFactoryManifest]):
    meta: MCPResponseMeta


def build_app32_sapiens_factory_manifest() -> SapiensFactoryManifest:
    return SapiensFactoryManifest(
        intents=[
            SapiensFactorySupportedIntent(change_type="create", title="Criar", description="Criação de nova capacidade técnica ponta a ponta."),
            SapiensFactorySupportedIntent(change_type="alter", title="Alterar", description="Mudança incremental em capacidade já existente."),
            SapiensFactorySupportedIntent(change_type="activate", title="Ativar", description="Ativação controlada de capability, workflow ou surface."),
            SapiensFactorySupportedIntent(change_type="deactivate", title="Desativar", description="Desativação controlada com rollback previsto."),
            SapiensFactorySupportedIntent(change_type="fix", title="Corrigir", description="Correção de defeito em service, tool, contrato ou workflow."),
            SapiensFactorySupportedIntent(change_type="refactor", title="Refatorar", description="Refino arquitetural, boundary e cognição do Sapiens."),
            SapiensFactorySupportedIntent(change_type="diagnose", title="Diagnosticar", description="Classificação e análise inicial do problema técnico."),
        ],
        target_layers=["service", "tool_contract", "rest_mcp", "workflow", "ui_sapiens"],
        execution_modes=["diagnose", "plan", "prepare", "execute_controlled"],
        guardrails=[
            "Mudanças sensíveis exigem tenant-scope, RBAC e trilha de auditoria.",
            "A LLM interpreta; a execução real continua governada pelo APP32.",
            "Ativar/desativar requer human gate explícito.",
        ],
    )


APP32_SAPIENS_FACTORY_MANIFEST = build_app32_sapiens_factory_manifest()
