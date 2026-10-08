"""Contrato automático das coortes de leitura do mcp-versus.

Uma tool só pode entrar numa coorte de leitura se passar em TODAS as regras abaixo.
Foi a conferência manual destas regras que, na onda 1 de ``routine``, achou a agenda
com ``force_regenerate`` (leitura que escreve), as ferramentas legadas sem ``company_id``
e a combinação de escopos nova; aqui ela vira teste repetível.
"""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

from src.core import mcp_read_cohorts

READ_VERBS = frozenset({"get", "list", "search", "describe", "read", "find", "show"})

# Exceções REVISADAS: tool -> motivo. Entram só com revisão do código da tool.
REVIEWED_VERB_EXCEPTIONS: dict[str, str] = {}
# tool -> {parametro: motivo}
REVIEWED_PARAM_EXCEPTIONS: dict[str, dict[str, str]] = {}

_SUSPICIOUS_PARAM = re.compile(
    r"(force|regenerate|apply|confirm|approve|execute|trigger|send|publish|delete|remove|overwrite|reset|"
    r"lock|commit|write|save|create|update|sync|import|dispatch|dry_run)",
    re.IGNORECASE,
)
_WRITE_IN_SOURCE = re.compile(
    r"(\.commit\(|session\.add\(|session\.add_all\(|session\.delete\(|session\.merge\(|bulk_save_objects|"
    r"bulk_insert_mappings|bulk_update_mappings|\.delete\(\)|INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+\w+\s+SET)",
    re.IGNORECASE,
)
_COMPANY_PARAMS = ("company_id", "company_ref")


@dataclass(frozen=True)
class ToolProbe:
    schema: dict[str, Any] | None
    source: str | None


def probe_registered_tools() -> dict[str, ToolProbe]:
    """Constrói um servidor MCP de teste com todos os registradores e lê esquema e fonte."""
    from mcp.server.fastmcp import FastMCP

    from src.intelligence.tool_catalog import catalog

    probes: dict[str, ToolProbe] = {}
    server = FastMCP("cohort-contract-probe")
    for registrar in catalog.mcp_registrars:
        try:
            registrar(server)
        except Exception:  # um registrador quebrado não pode esconder os demais
            continue
    for tool in server._tool_manager.list_tools():
        probes[tool.name] = ToolProbe(schema=dict(tool.parameters or {}), source=_source_of(tool.fn))
    for tool in catalog.get_langchain_tools():
        name = getattr(tool, "name", None)
        if not name or name in probes:
            continue
        schema: dict[str, Any] = {}
        try:
            if getattr(tool, "args_schema", None) is not None:
                schema = tool.args_schema.model_json_schema()
        except Exception:
            schema = {}
        probes[name] = ToolProbe(schema=schema, source=_source_of(getattr(tool, "func", None)))
    return probes


def _source_of(fn: Any) -> str | None:
    if fn is None:
        return None
    try:
        return inspect.getsource(inspect.unwrap(fn))
    except (OSError, TypeError):
        return None


def audit_read_tool(name: str, *, capability: Any, probe: ToolProbe | None) -> list[str]:
    """Devolve as violações do contrato (lista vazia = pode entrar numa coorte de leitura)."""
    problems: list[str] = []
    if capability is None:
        return [f"{name}: ausente do catálogo de capabilities"]
    if probe is None or probe.schema is None:
        problems.append(f"{name}: não está registrada como ferramenta MCP")
        return problems

    risk = getattr(getattr(capability, "risk", None), "value", getattr(capability, "risk", None))
    if risk != "low":
        problems.append(f"{name}: risco '{risk}' (coorte de leitura exige 'low')")
    if getattr(capability, "human_gate", False):
        problems.append(f"{name}: tem gate humano (é mutação, não leitura)")

    verb = name.split("_")[0]
    if verb not in READ_VERBS and name not in REVIEWED_VERB_EXCEPTIONS:
        problems.append(f"{name}: verbo '{verb}' não é de leitura (exceção só com revisão registrada)")

    params = tuple((probe.schema or {}).get("properties", {}).keys())
    if not any(param in params for param in _COMPANY_PARAMS):
        problems.append(f"{name}: sem company_id/company_ref (o grant por empresa não seria validado)")
    excused = REVIEWED_PARAM_EXCEPTIONS.get(name, {})
    for param in params:
        if _SUSPICIOUS_PARAM.search(param) and param not in excused:
            problems.append(f"{name}: parâmetro suspeito '{param}' (leitura que pode escrever)")

    if mcp_read_cohorts.token_scope_for(capability) is None:
        problems.append(f"{name}: sem escopo alcançável pelo token (precisa de mcp_user, mcp_analytics ou mcp_finance)")

    tags = set(getattr(capability, "tags", ()) or ())
    if not tuple(getattr(capability, "permissions", ()) or ()) and "no_permission_required" not in tags:
        problems.append(f"{name}: sem permissão declarada")

    if probe.source and _WRITE_IN_SOURCE.search(probe.source):
        problems.append(f"{name}: o código da tool contém operação de escrita")
    return problems
