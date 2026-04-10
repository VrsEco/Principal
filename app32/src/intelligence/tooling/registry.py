from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .capabilities import (
    ToolCapability,
    ToolScope,
    build_capability_index,
    build_capability_manifest,
)


@dataclass(frozen=True)
class ToolCapabilityRegistry:
    """Índice consultável de capacidades de IA/MCP do APP32."""

    capabilities: dict[str, ToolCapability]

    @classmethod
    def from_tools(cls, tools: Iterable[Any]) -> "ToolCapabilityRegistry":
        return cls(capabilities=build_capability_index(tools))

    def get(self, tool_name: str) -> ToolCapability | None:
        return self.capabilities.get(tool_name)

    def iter(self, *, scope: str | ToolScope | Sequence[str | ToolScope] | None = None, domain: str | Sequence[str] | None = None) -> list[ToolCapability]:
        filtered = build_capability_manifest(self.capabilities.values(), scope=scope, domain=domain, include_tools=False)
        ordered_names = [name for names in filtered["domains"].values() for name in names]
        lookup = self.capabilities
        result: list[ToolCapability] = []
        for name in ordered_names:
            capability = lookup.get(name)
            if capability and capability not in result:
                result.append(capability)
        return result

    def list_domains(self) -> list[str]:
        return sorted({cap.domain for cap in self.capabilities.values()})

    def list_scopes(self) -> list[str]:
        return sorted({scope for cap in self.capabilities.values() for scope in cap.scopes})

    def to_manifest(
        self,
        *,
        scope: str | ToolScope | Sequence[str | ToolScope] | None = None,
        domain: str | Sequence[str] | None = None,
        include_tools: bool = True,
    ) -> dict[str, Any]:
        return build_capability_manifest(
            self.capabilities.values(),
            scope=scope,
            domain=domain,
            include_tools=include_tools,
        )
