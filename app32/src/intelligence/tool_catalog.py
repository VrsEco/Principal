"""
Catálogo único de tools do APP32 para Sapiens e MCP.

Diretriz:
- Sapiens e MCP devem partir do mesmo ponto de verdade para o catálogo.
- Tools LangChain existentes seguem disponíveis para ambos.
- Registradores MCP adicionais podem complementar o catálogo sem duplicar o core.
"""

from __future__ import annotations

import logging
from functools import wraps
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Sequence

from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event
from src.intelligence.tools import tools as legacy_langchain_tools
from src.core.mcp_analysis_catalog_tools import register_analysis_catalog_tools
from src.core.mcp_crud_contract_tools import register_crud_contract_tools
from src.core.mcp_domain_playbook_tools import register_domain_playbook_tools
from src.core.mcp_profile_contract_tools import register_profile_contract_tools
from src.core.mcp_release_checklist_tools import register_release_checklist_tools
from src.core.mcp_surface_playbook_tools import register_surface_playbook_tools
from src.core.mcp_usage_dashboard_tools import register_usage_dashboard_tools
from src.core.mcp_work_journey_tools import register_work_journey_tools
from src.intelligence.tooling.registry import ToolCapabilityRegistry
from src.intelligence.tooling.capabilities import ToolScope


McpRegistrar = Callable[[object], None]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCatalog:
    langchain_tools: Sequence[object]
    mcp_registrars: Sequence[McpRegistrar]
    capability_registry: ToolCapabilityRegistry = field(default_factory=lambda: ToolCapabilityRegistry(capabilities={}))

    def get_langchain_tools(self) -> List[object]:
        return list(self.langchain_tools)

    def iter_langchain_tools(self) -> Iterable[object]:
        return iter(self.langchain_tools)

    def get_tool_capability(self, tool_name: str):
        return self.capability_registry.get(tool_name)

    def iter_capabilities(self, scope: str | ToolScope | Sequence[str | ToolScope] | None = None, domain: str | Sequence[str] | None = None):
        return self.capability_registry.iter(scope=scope, domain=domain)

    def get_capability_manifest(
        self,
        *,
        scope: str | ToolScope | Sequence[str | ToolScope] | None = None,
        domain: str | Sequence[str] | None = None,
        include_tools: bool = True,
    ) -> dict:
        return self.capability_registry.to_manifest(scope=scope, domain=domain, include_tools=include_tools)

    def register_mcp_tools(self, mcp: object) -> None:
        """
        Registra todas as tools compartilhadas no servidor MCP.
        """
        def _extract_context(raw: object) -> dict[str, object]:
            payload: dict[str, object] = {}
            if isinstance(raw, dict):
                payload = dict(raw)
            elif isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], dict):
                payload = dict(raw[0])

            context: dict[str, object] = {}
            for key in ("company_id", "user_id", "thread_id", "request_id", "trace_id"):
                if payload.get(key) is not None:
                    context[key] = payload.get(key)
            return context

        def _safe_int(value: object) -> int | None:
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())
            return None

        def _audit_mcp_tool(
            *,
            tool_name: str,
            status: str,
            payload: dict[str, object] | None = None,
            error: Exception | None = None,
            domain: str | None = None,
        ) -> None:
            capability = self.get_tool_capability(tool_name)
            metadata = {
                "risk": getattr(capability, "risk", None).value if getattr(capability, "risk", None) else None,
                "error_type": error.__class__.__name__ if error else None,
                "error_message": str(error) if error else None,
            }
            record = build_ai_execution_audit_record(
                event_type=f"mcp.{tool_name}.{status}",
                runtime="mcp",
                status=status,
                domain=domain or getattr(capability, "domain", None),
                operation=tool_name,
                tool_name=tool_name,
                scope="mcp",
                company_id=_safe_int((payload or {}).get("company_id")),
                user_id=_safe_int((payload or {}).get("user_id")),
                thread_id=str((payload or {}).get("thread_id")) if (payload or {}).get("thread_id") else None,
                request_id=str((payload or {}).get("request_id")) if (payload or {}).get("request_id") else None,
                trace_id=str((payload or {}).get("trace_id")) if (payload or {}).get("trace_id") else None,
                metadata={key: value for key, value in metadata.items() if value is not None},
            )
            emit_ai_execution_audit_event(record, logger=logger)

        for tool in self.langchain_tools:
            if hasattr(tool, "func"):
                original_func = tool.func

                @mcp.tool(name=tool.name, description=tool.description)
                @wraps(original_func)
                def _wrapped_tool(*args, __current_tool=tool, **kwargs):
                    payload = _extract_context(kwargs if kwargs else (args[0] if args else {}))
                    _audit_mcp_tool(tool_name=__current_tool.name, status="start", payload=payload)
                    try:
                        result = original_func(*args, **kwargs)
                        _audit_mcp_tool(tool_name=__current_tool.name, status="success", payload=payload)
                        return result
                    except Exception as exc:
                        _audit_mcp_tool(tool_name=__current_tool.name, status="failure", payload=payload, error=exc)
                        raise
            else:
                def make_wrapper(current_tool):
                    original_invoke = current_tool.invoke

                    @mcp.tool(name=current_tool.name, description=current_tool.description)
                    @wraps(original_invoke)
                    def mcp_tool_wrapper(*args, **kwargs):
                        payload = _extract_context(kwargs if kwargs else (args[0] if args else {}))
                        _audit_mcp_tool(tool_name=current_tool.name, status="start", payload=payload)
                        try:
                            result = original_invoke(kwargs if kwargs else args[0] if args else {})
                            _audit_mcp_tool(tool_name=current_tool.name, status="success", payload=payload)
                            return result
                        except Exception as exc:
                            _audit_mcp_tool(tool_name=current_tool.name, status="failure", payload=payload, error=exc)
                            raise
                    return mcp_tool_wrapper

                make_wrapper(tool)

        for registrar in self.mcp_registrars:
            registrar(mcp)

        @mcp.tool(
            name="list_app32_capabilities",
            description="Lista as capacidades e metadados de segurança do catálogo MCP/Sapiens do APP32.",
        )
        def list_app32_capabilities(
            scope: str | None = None,
            domain: str | None = None,
            include_tools: bool = True,
        ) -> dict:
            """Manifesto consultável por agentes para descoberta de capacidades."""

            scope_filter: str | ToolScope | Sequence[str | ToolScope] | None = scope
            domain_filter: str | Sequence[str] | None = domain
            manifest = self.get_capability_manifest(
                scope=scope_filter,
                domain=domain_filter,
                include_tools=include_tools,
            )
            _audit_mcp_tool(
                tool_name="list_app32_capabilities",
                status="success",
                payload={
                    "scope": scope or "",
                    "domain": domain or "",
                },
                domain="governance",
            )
            return manifest


_legacy_tool_registry = ToolCapabilityRegistry.from_tools(legacy_langchain_tools)

catalog = ToolCatalog(
    langchain_tools=tuple(legacy_langchain_tools),
    mcp_registrars=(
        register_analysis_catalog_tools,
        register_crud_contract_tools,
        register_domain_playbook_tools,
        register_profile_contract_tools,
        register_release_checklist_tools,
        register_surface_playbook_tools,
        register_usage_dashboard_tools,
        register_work_journey_tools,
    ),
    capability_registry=_legacy_tool_registry,
)

# Compatibilidade legada: vários módulos ainda importam `tools`.
tools = catalog.get_langchain_tools()
