"""
Catálogo único de tools do APP32 para Sapiens e MCP.

Diretriz:
- Sapiens e MCP devem partir do mesmo ponto de verdade para o catálogo.
- Tools LangChain existentes seguem disponíveis para ambos.
- Registradores MCP adicionais podem complementar o catálogo sem duplicar o core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence

from src.intelligence.tools import tools as legacy_langchain_tools
from src.core.mcp_work_journey_tools import register_work_journey_tools


McpRegistrar = Callable[[object], None]


@dataclass(frozen=True)
class ToolCatalog:
    langchain_tools: Sequence[object]
    mcp_registrars: Sequence[McpRegistrar]

    def get_langchain_tools(self) -> List[object]:
        return list(self.langchain_tools)

    def iter_langchain_tools(self) -> Iterable[object]:
        return iter(self.langchain_tools)

    def register_mcp_tools(self, mcp: object) -> None:
        """
        Registra todas as tools compartilhadas no servidor MCP.
        """
        for tool in self.langchain_tools:
            if hasattr(tool, "func"):
                mcp.tool(name=tool.name, description=tool.description)(tool.func)
            else:
                def make_wrapper(current_tool):
                    @mcp.tool(name=current_tool.name, description=current_tool.description)
                    def mcp_tool_wrapper(*args, **kwargs):
                        return current_tool.invoke(kwargs if kwargs else args[0] if args else {})
                    return mcp_tool_wrapper

                make_wrapper(tool)

        for registrar in self.mcp_registrars:
            registrar(mcp)


catalog = ToolCatalog(
    langchain_tools=tuple(legacy_langchain_tools),
    mcp_registrars=(
        register_work_journey_tools,
    ),
)

# Compatibilidade legada: vários módulos ainda importam `tools`.
tools = catalog.get_langchain_tools()

