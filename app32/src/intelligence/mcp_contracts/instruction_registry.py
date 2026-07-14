from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


InstructionDocumentClass = Literal["paper", "spec", "manifesto", "playbook", "runbook", "harness"]
InstructionChannel = Literal["stable", "beta", "hotfix"]
InstructionLayerName = Literal["global", "runtime", "agent", "tenant_override"]


class InstructionLayerDefinition(_StrictModel):
    layer: InstructionLayerName
    title: str = Field(min_length=8, max_length=120)
    precedence: int = Field(ge=1, le=10)
    mutable_remotely: bool = True
    objective: str = Field(min_length=16, max_length=320)


class InstructionDocumentRef(_StrictModel):
    doc_class: InstructionDocumentClass
    slug: str = Field(min_length=4, max_length=120)
    title: str = Field(min_length=8, max_length=180)
    version: str = Field(min_length=2, max_length=40)
    path: str = Field(min_length=12, max_length=400)
    purpose: str = Field(min_length=16, max_length=240)


class InstructionRule(_StrictModel):
    rule: str = Field(min_length=8, max_length=320)
    rationale: str = Field(min_length=8, max_length=320)


InstructionJourneyAutonomy = Literal["must", "may", "cannot", "gated"]


class InstructionJourneyState(_StrictModel):
    key: str = Field(min_length=3, max_length=80)
    responsible: str = Field(min_length=3, max_length=120)
    required_output: str = Field(min_length=8, max_length=320)


class InstructionJourneyActionPolicy(_StrictModel):
    action: str = Field(min_length=3, max_length=120)
    autonomy: InstructionJourneyAutonomy
    rule: str = Field(min_length=8, max_length=320)


class InstructionJourneyGuide(_StrictModel):
    version: str = Field(min_length=3, max_length=40)
    scope: str = Field(min_length=8, max_length=240)
    entry_state: str = Field(min_length=3, max_length=80)
    states: list[InstructionJourneyState] = Field(default_factory=list, min_length=7)
    action_policy: list[InstructionJourneyActionPolicy] = Field(default_factory=list, min_length=6)
    read_tool_sequence: list[str] = Field(default_factory=list, min_length=5)
    escalation_rules: list[str] = Field(default_factory=list, min_length=2)


class InstructionRuntimeGuide(_StrictModel):
    runtime_profile: str = Field(min_length=3, max_length=80)
    entry_agent: str = Field(min_length=3, max_length=80)
    default_harness_key: str = Field(min_length=8, max_length=120)
    surface: str = Field(min_length=3, max_length=40)
    summary: str = Field(min_length=16, max_length=320)
    recommended_channel: InstructionChannel = "stable"


class InstructionBootstrapBundle(_StrictModel):
    runtime_profile: str = Field(min_length=3, max_length=80)
    experience_label: str = Field(min_length=4, max_length=120)
    surface: str = Field(min_length=3, max_length=40)
    agent_key: str = Field(min_length=3, max_length=80)
    harness_key: str = Field(min_length=8, max_length=120)
    channel: InstructionChannel = "stable"
    bundle_version: str = Field(min_length=3, max_length=40)
    checksum: str = Field(min_length=8, max_length=64)
    invalidation_token: str = Field(min_length=4, max_length=64)
    cache_key: str = Field(min_length=8, max_length=240)
    company_id: int | None = Field(default=None, gt=0)
    summary: str = Field(min_length=16, max_length=400)
    introduction_message: str = Field(min_length=16, max_length=400)
    cache_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    source_scope: list[str] = Field(default_factory=list, min_length=1)
    startup_sequence: list[str] = Field(default_factory=list, min_length=3)
    mandatory_rules: list[InstructionRule] = Field(default_factory=list, min_length=3)
    handoff_rules: list[InstructionRule] = Field(default_factory=list, min_length=2)
    forbidden_actions: list[str] = Field(default_factory=list, min_length=2)
    layer_matrix: list[InstructionLayerDefinition] = Field(default_factory=list, min_length=3)
    doc_refs: list[InstructionDocumentRef] = Field(default_factory=list, min_length=3)
    journey_guide: InstructionJourneyGuide | None = None


class InstructionRegistryManifest(_StrictModel):
    version: str = Field(default="app32.mcp.instructions.v1", min_length=1, max_length=80)
    objective: str = Field(min_length=16, max_length=320)
    supported_channels: list[InstructionChannel] = Field(default_factory=lambda: ["stable", "beta", "hotfix"], min_length=1)
    layer_matrix: list[InstructionLayerDefinition] = Field(default_factory=list, min_length=3)
    runtime_guides: list[InstructionRuntimeGuide] = Field(default_factory=list, min_length=1)
    bundle_template_json: dict[str, Any] = Field(default_factory=dict)
    bundle_template_yaml: str = Field(min_length=24, max_length=4000)
    scalability_notes: list[str] = Field(default_factory=list, min_length=3)

    @model_validator(mode="after")
    def _validate_layers(self):
        precedences = [item.precedence for item in self.layer_matrix]
        if len(precedences) != len(set(precedences)):
            raise ValueError("Cada layer do instruction registry deve ter precedência única.")
        return self


InstructionBootstrapEnvelope = MCPSuccessEnvelope[InstructionRegistryManifest | InstructionBootstrapBundle]


def _default_layer_matrix() -> list[InstructionLayerDefinition]:
    return [
        InstructionLayerDefinition(
            layer="global",
            title="Núcleo Global de Governança",
            precedence=1,
            mutable_remotely=False,
            objective="Congelar princípios transversais como multi-tenancy, MCP First, safety e boundaries corporativos.",
        ),
        InstructionLayerDefinition(
            layer="runtime",
            title="Camada de Runtime/Squad",
            precedence=2,
            mutable_remotely=True,
            objective="Definir missão, surface, startup sequence e guardrails do runtime ativo.",
        ),
        InstructionLayerDefinition(
            layer="agent",
            title="Camada do Agente/Harness",
            precedence=3,
            mutable_remotely=True,
            objective="Especializar o comportamento para o agente líder e o harness ativo sem replicar a documentação inteira.",
        ),
        InstructionLayerDefinition(
            layer="tenant_override",
            title="Override Controlado por Tenant",
            precedence=4,
            mutable_remotely=True,
            objective="Permitir customização mínima por cliente, canal ou rollout sem quebrar a base canônica.",
        ),
    ]


def _default_runtime_guides() -> list[InstructionRuntimeGuide]:
    return [
        InstructionRuntimeGuide(
            runtime_profile="squad_cliente",
            entry_agent="SC-COORD",
            default_harness_key="harness_coordenador_cliente_v1",
            surface="user",
            summary="Entrada operacional do cliente com roteamento econômico, menor privilégio e foco em coprodução do dia a dia.",
        ),
        InstructionRuntimeGuide(
            runtime_profile="squad_versus",
            entry_agent="SV-COORD",
            default_harness_key="harness_coordenador_versus_v1",
            surface="admin",
            summary="Camada consultiva e de governança com company_id explícito, discovery reforçado e trilha auditável.",
        ),
        InstructionRuntimeGuide(
            runtime_profile="engineering",
            entry_agent="SE-COORD",
            default_harness_key="harness_coordenador_engenharia_v1",
            surface="ops",
            summary="Triagem técnica com evidência, boundaries fortes e roteamento disciplinado por especialidade.",
        ),
    ]


def build_app32_instruction_registry_manifest() -> InstructionRegistryManifest:
    example_json = {
        "runtime_profile": "squad_cliente",
        "experience_label": "Sapiens Cliente",
        "surface": "user",
        "agent_key": "SC-COORD",
        "harness_key": "harness_coordenador_cliente_v1",
        "channel": "stable",
        "bundle_version": "2026-05-17.1",
        "checksum": "seeded001",
        "invalidation_token": "stable-seed",
        "cache_key": "instruction-registry:squad_cliente:stable:31",
        "company_id": 31,
        "summary": "Bundle mínimo do Squad Cliente com bootstrap remoto, versionado e cacheável.",
        "startup_sequence": [
            "resolve_app32_instruction_bundle_tool",
            "describe_app32_squad_runtime_tool",
            "list_user_app32_capabilities",
            "describe_app32_profile_contracts_tool",
            "describe_app32_surface_playbooks_tool",
        ],
    }
    example_yaml = "\n".join(
        [
            "runtime_profile: squad_cliente",
            "experience_label: Sapiens Cliente",
            "surface: user",
            "agent_key: SC-COORD",
            "harness_key: harness_coordenador_cliente_v1",
            "channel: stable",
            "bundle_version: 2026-05-17.1",
            "checksum: seeded001",
            "invalidation_token: stable-seed",
            "cache_key: instruction-registry:squad_cliente:stable:31",
            "company_id: 31",
            "startup_sequence:",
            "  - resolve_app32_instruction_bundle_tool",
            "  - describe_app32_squad_runtime_tool",
            "  - list_user_app32_capabilities",
            "  - describe_app32_profile_contracts_tool",
            "  - describe_app32_surface_playbooks_tool",
        ]
    )
    return InstructionRegistryManifest(
        objective="Descrever e resolver bundles instrucionais mínimos, versionados e escaláveis para runtimes MCP do APP32.",
        layer_matrix=_default_layer_matrix(),
        runtime_guides=_default_runtime_guides(),
        bundle_template_json=example_json,
        bundle_template_yaml=example_yaml,
        scalability_notes=[
            "Carregar sempre o bundle mínimo e deixar docs completos apenas por referência.",
            "Compor instruções por camadas global -> runtime -> agente -> tenant override para evitar explosão de variantes.",
            "Reusar bundle por versionamento e cache TTL; só reidratar quando a versão ou o canal mudar.",
            "Tenant override deve ser pequeno, auditável e incapaz de violar guardrails globais.",
        ],
    )


APP32_INSTRUCTION_REGISTRY_MANIFEST = build_app32_instruction_registry_manifest()


__all__ = [
    "APP32_INSTRUCTION_REGISTRY_MANIFEST",
    "InstructionBootstrapBundle",
    "InstructionBootstrapEnvelope",
    "InstructionChannel",
    "InstructionDocumentClass",
    "InstructionDocumentRef",
    "InstructionLayerDefinition",
    "InstructionJourneyActionPolicy",
    "InstructionJourneyAutonomy",
    "InstructionJourneyGuide",
    "InstructionJourneyState",
    "InstructionRegistryManifest",
    "InstructionRule",
    "InstructionRuntimeGuide",
    "build_app32_instruction_registry_manifest",
]
