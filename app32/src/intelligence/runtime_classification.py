from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


RuntimeStatus = Literal["official", "compatibility", "legacy", "deprecated_candidate"]
RuntimeKind = Literal["entrypoint", "router", "graph", "catalog", "support", "test_harness"]


@dataclass(frozen=True)
class RuntimeComponent:
    """Componente inventariado do runtime Sapiens/AI."""

    module: str
    kind: RuntimeKind
    status: RuntimeStatus
    responsibility: str
    allowed_for_new_work: bool
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "kind": self.kind,
            "status": self.status,
            "responsibility": self.responsibility,
            "allowed_for_new_work": self.allowed_for_new_work,
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class RuntimeTopology:
    """Marcações canônicas do runtime oficial e dos grafos legados do APP32."""

    official_entrypoint: str
    official_menu_router: str
    official_work_agent_graph: str
    official_tool_catalog: str
    legacy_graph_modules: tuple[str, ...]
    components: tuple[RuntimeComponent, ...]
    legacy_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "official": {
                "entrypoint": self.official_entrypoint,
                "menu_router": self.official_menu_router,
                "work_agent_graph": self.official_work_agent_graph,
                "tool_catalog": self.official_tool_catalog,
                "components": [
                    component.to_dict()
                    for component in self.components
                    if component.status == "official"
                ],
            },
            "legacy": {
                "graph_modules": list(self.legacy_graph_modules),
                "components": [
                    component.to_dict()
                    for component in self.components
                    if component.status in {"legacy", "deprecated_candidate"}
                ],
                "note": self.legacy_note,
            },
            "compatibility": {
                "components": [
                    component.to_dict()
                    for component in self.components
                    if component.status == "compatibility"
                ]
            },
        }


RUNTIME_COMPONENTS: tuple[RuntimeComponent, ...] = (
    RuntimeComponent(
        module="src.intelligence.execution.run_agent_with_context",
        kind="entrypoint",
        status="official",
        responsibility="Entrada auditável do Sapiens por usuário, empresa, canal e thread.",
        allowed_for_new_work=True,
        next_action="Manter como único entrypoint novo de runtime IA/Sapiens.",
    ),
    RuntimeComponent(
        module="src.intelligence.menu_engine.handle_menu_message",
        kind="router",
        status="official",
        responsibility="Roteador conversacional determinístico antes do grafo de agentes.",
        allowed_for_new_work=True,
        next_action="Concentrar evolução de intents e descoberta de workflows neste fluxo.",
    ),
    RuntimeComponent(
        module="src.intelligence.work_agents.graph.create_work_agent_workflow",
        kind="graph",
        status="official",
        responsibility="Grafo oficial Work Agents V2 com supervisor, agentes especialistas e ToolNode compartilhado.",
        allowed_for_new_work=True,
        next_action="Manter como grafo oficial para novas capacidades agenticas.",
    ),
    RuntimeComponent(
        module="src.intelligence.tool_catalog.catalog",
        kind="catalog",
        status="official",
        responsibility="Catálogo único de tools Sapiens/MCP com capabilities e registradores MCP.",
        allowed_for_new_work=True,
        next_action="Registrar novas tools/capabilities MCP First apenas por este catálogo.",
    ),
    RuntimeComponent(
        module="src.intelligence.graph.create_agent_workflow",
        kind="graph",
        status="legacy",
        responsibility="Grafo supervisor-worker antigo com expert/fiscal/financeiro e ToolNode legado.",
        allowed_for_new_work=False,
        next_action="Não evoluir; manter apenas compatibilidade até validação da 1318.",
    ),
    RuntimeComponent(
        module="src.intelligence.graphs.main_graph.create_main_graph",
        kind="graph",
        status="legacy",
        responsibility="Grafo antigo fiscal/financeiro com roteador simples e execução direta.",
        allowed_for_new_work=False,
        next_action="Não evoluir; preparar depreciação com guard rails na 1318.",
    ),
    RuntimeComponent(
        module="src.intelligence.test_agent",
        kind="test_harness",
        status="compatibility",
        responsibility="Harness/manual runner de testes legados do agente.",
        allowed_for_new_work=False,
        next_action="Reapontar para suíte pytest e remover uso operacional.",
    ),
    RuntimeComponent(
        module="src.intelligence.test_agent_mock",
        kind="test_harness",
        status="compatibility",
        responsibility="Harness mock legado para experimentação local.",
        allowed_for_new_work=False,
        next_action="Manter fora do runtime produtivo e substituir por testes automatizados.",
    ),
)


RUNTIME_TOPOLOGY = RuntimeTopology(
    official_entrypoint="src.intelligence.execution.run_agent_with_context",
    official_menu_router="src.intelligence.menu_engine.handle_menu_message",
    official_work_agent_graph="src.intelligence.work_agents.graph.create_work_agent_workflow",
    official_tool_catalog="src.intelligence.tool_catalog.catalog",
    legacy_graph_modules=(
        "src.intelligence.graph",
        "src.intelligence.graphs.main_graph",
    ),
    components=RUNTIME_COMPONENTS,
    legacy_note=(
        "Os módulos legados permanecem apenas para compatibilidade e análise histórica. "
        "O runtime oficial do Sapiens/AI é o fluxo execution -> menu_engine -> work_agents.graph."
    ),
)


def describe_runtime_topology() -> dict[str, Any]:
    """Retorna uma visão simples para documentação e auditoria."""

    return RUNTIME_TOPOLOGY.to_dict()


def list_runtime_components(*, status: RuntimeStatus | None = None, kind: RuntimeKind | None = None) -> tuple[RuntimeComponent, ...]:
    components = RUNTIME_COMPONENTS
    if status:
        components = tuple(component for component in components if component.status == status)
    if kind:
        components = tuple(component for component in components if component.kind == kind)
    return components


def list_legacy_graph_components() -> tuple[RuntimeComponent, ...]:
    return tuple(
        component
        for component in RUNTIME_COMPONENTS
        if component.kind == "graph" and component.status in {"legacy", "deprecated_candidate"}
    )


__all__ = [
    "RUNTIME_COMPONENTS",
    "RUNTIME_TOPOLOGY",
    "RuntimeComponent",
    "RuntimeKind",
    "RuntimeStatus",
    "RuntimeTopology",
    "describe_runtime_topology",
    "list_legacy_graph_components",
    "list_runtime_components",
]
