"""Contrato automático das coortes de leitura do mcp-versus.

Uma tool só pode entrar numa coorte de leitura se passar em TODAS as regras abaixo.
Foi a conferência manual destas regras que, na onda 1 de ``routine``, achou a agenda
com ``force_regenerate`` (leitura que escreve), as ferramentas legadas sem ``company_id``
e a combinação de escopos nova; aqui ela vira teste repetível.
"""
from __future__ import annotations

import importlib
import inspect
import re
from dataclasses import dataclass
from typing import Any

from src.core import mcp_read_cohorts

READ_VERBS = frozenset({"get", "list", "search", "describe", "read", "find", "show"})

# Exceções REVISADAS: tool -> motivo. Entram só com revisão do código da tool.
# Leituras SEM company_id explícito, revisadas: a lista de empresas vem do servidor e cada uma é validada.
REVIEWED_COMPANY_PARAM_EXCEPTIONS: dict[str, str] = {
    "list_my_work_all_companies": (
        "Agrega só atividades pessoais nas empresas com grant ativo do principal; a lista vem do servidor "
        "(nunca do cliente) e cada empresa é validada individualmente (grant e teto) antes de ler."
    ),
}
REVIEWED_VERB_EXCEPTIONS: dict[str, str] = {
    "answer_organizational_question_secure": (
        "Responde com claims e citações de conhecimento autorizado; o serviço só lê e registra "
        "medição de uso (telemetria), como a ferramenta original."
    ),
}
# tool -> {parametro: motivo}
REVIEWED_PARAM_EXCEPTIONS: dict[str, dict[str, str]] = {}

_SUSPICIOUS_PARAM = re.compile(
    r"(force|regenerate|apply|confirm|approve|execute|trigger|send|publish|delete|remove|overwrite|reset|"
    r"lock|commit|write|save|create|update|sync|import|dispatch|dry_run|user_id|actor|request_id|trace_id)",
    re.IGNORECASE,
)
_WRITE_IN_SOURCE = re.compile(
    r"(\.commit\(|session\.add\(|session\.add_all\(|session\.delete\(|session\.merge\(|bulk_save_objects|"
    r"bulk_insert_mappings|bulk_update_mappings|\.delete\(\)|INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+\w+\s+SET)",
    re.IGNORECASE,
)
_COMPANY_PARAMS = ("company_id", "company_ref")
_IDENTIFIER = re.compile(r'\b([A-Za-z_]\w+)\b')
_FROM_IMPORT = re.compile(r'from\s+([\w.]+)\s+import\s+\(?([\w,\s]+)\)?')
_SERVICE_PREFIXES = ("services", "src.core", "src.intelligence")
_MODULE_ROOTS = ("services", "models", "src", "api", "utils")

# Escritas INDIRETAS revisadas: tool -> {"modulo.funcao": motivo}. Uma leitura que chama um serviço
# que grava só entra com revisão explícita (a varredura do código da própria tool não as vê).
_DERIVED = (
    "Atualiza dados derivados (snapshot da agenda / itens da jornada) exatamente como a tela ao abrir; "
    "idempotente, preserva agenda travada e movimentos manuais. Revisado em 2026-10-08."
)
REVIEWED_INDIRECT_WRITE_EXCEPTIONS: dict[str, dict[str, str]] = {
    "list_work_journey_task_inventory_tool": {
        "work_journey_agenda_service.get_work_journey_agenda": _DERIVED,
        "work_journey_agenda_service._get_or_build_agenda": _DERIVED,
    },
    "get_work_journey_board_tool": {
        "work_journey_service.sync_work_journey_items": _DERIVED,
    },
}


@dataclass(frozen=True)
class ToolProbe:
    schema: dict[str, Any] | None
    source: str | None
    fn: Any = None


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
        probes[tool.name] = ToolProbe(schema=dict(tool.parameters or {}), source=_source_of(tool.fn), fn=tool.fn)
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
        # O que o cliente MCP vê: sem os parâmetros ocultos pelo adaptador (mcp_param_hiding).
        from src.core.mcp_param_hiding import HIDDEN_CLIENT_PARAMETERS

        for hidden in HIDDEN_CLIENT_PARAMETERS.get(name, ()):
            (schema.get("properties") or {}).pop(hidden, None)
            if hidden in (schema.get("required") or []):
                schema["required"].remove(hidden)
        probes[name] = ToolProbe(schema=schema, source=_source_of(getattr(tool, "func", None)), fn=getattr(tool, "func", None))
    return probes


def _source_of(fn: Any) -> str | None:
    if fn is None:
        return None
    try:
        return inspect.getsource(inspect.unwrap(fn))
    except (OSError, TypeError):
        return None


def _referenced_service_functions(fn: Any, prefixes: tuple[str, ...]) -> list[Any]:
    """Funções de serviço citadas no código de ``fn`` (chamadas OU passadas como argumento)."""
    source = _source_of(fn) or ""
    try:
        namespace = getattr(inspect.unwrap(fn), "__globals__", {})
    except Exception:
        namespace = {}
    imported: dict[str, str] = {}
    for match in _FROM_IMPORT.finditer(source):
        for imported_name in (part.strip() for part in match.group(2).split(",") if part.strip()):
            imported[imported_name] = match.group(1)
    found: list[Any] = []
    for identifier in set(_IDENTIFIER.findall(source)):
        obj = namespace.get(identifier)
        if obj is None and identifier in imported:
            try:
                obj = getattr(importlib.import_module(imported[identifier]), identifier, None)
            except Exception:
                obj = None
        if inspect.isfunction(obj) and str(getattr(obj, "__module__", "")).startswith(prefixes):
            found.append(obj)
    return found


def indirect_write_hits(fn: Any, *, depth: int = 2, prefixes: tuple[str, ...] | None = None) -> list[str]:
    """``modulo.funcao`` dos serviços (até ``depth`` níveis) cujo código grava no banco."""
    prefixes = prefixes if prefixes is not None else _SERVICE_PREFIXES
    hits: list[str] = []
    seen: set[tuple[str, str]] = set()
    frontier = [fn]
    for _ in range(depth):
        next_frontier: list[Any] = []
        for current in frontier:
            for callee in _referenced_service_functions(current, prefixes):
                key = (callee.__module__, callee.__name__)
                if key in seen:
                    continue
                seen.add(key)
                if _WRITE_IN_SOURCE.search(_source_of(callee) or ""):
                    hits.append(f"{callee.__module__.split('.')[-1]}.{callee.__name__}")
                next_frontier.append(callee)
        frontier = next_frontier
    return sorted(hits)


def missing_imported_modules(source: str | None) -> list[str]:
    """Módulos do próprio app importados pelo código da tool que não existem (falha só em runtime)."""
    import importlib.util

    missing: list[str] = []
    for match in re.finditer(r"^\s*from\s+([\w.]+)\s+import\s", source or "", re.MULTILINE):
        module = match.group(1)
        if module.split(".")[0] not in _MODULE_ROOTS:
            continue
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        if not found and module not in missing:
            missing.append(module)
    return missing


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
    if not any(param in params for param in _COMPANY_PARAMS) and name not in REVIEWED_COMPANY_PARAM_EXCEPTIONS:
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

    for module in missing_imported_modules(probe.source):
        problems.append(f"{name}: importa módulo inexistente '{module}' (a ferramenta falharia em toda chamada)")

    if probe.source and _WRITE_IN_SOURCE.search(probe.source):
        problems.append(f"{name}: o código da tool contém operação de escrita")
    if probe.fn is not None:
        allowed = REVIEWED_INDIRECT_WRITE_EXCEPTIONS.get(name, {})
        for hit in indirect_write_hits(probe.fn):
            if hit not in allowed:
                problems.append(f"{name}: escrita indireta via serviço {hit} (leitura que grava; exceção só com revisão)")
    return problems
