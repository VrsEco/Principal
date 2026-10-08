"""Coortes de leitura do mcp-versus por domínio (SPEC classificacao_dominios_mcp_versus_v1).

Cada domínio publica um conjunto fixo de leituras, revisadas pelo contrato automático
(``mcp_cohort_contract``). A publicação é controlada por UMA variável:

    MCP_VERSUS_READ_DOMAINS=strategy,governance,processes

Domínios fora da lista não são listados **nem registrados** (uma tool oculta mas
registrada seria invocável por quem conhecesse o nome). Vazia ou ausente = nada novo.
A coorte de ``routine`` mantém a sua flag própria (MCP_VERSUS_ROUTINE_READ_ENABLED).
"""
from __future__ import annotations

import os
from typing import Any, Iterable

ENV_DOMAINS = "MCP_VERSUS_READ_DOMAINS"

# domínio -> leituras publicáveis. Preenchido por domínio, cada nome validado pelo contrato.
READ_COHORT_TOOL_NAMES: dict[str, tuple[str, ...]] = {}

# Prioridade do escopo de token usado para publicar a tool (somente os que os clientes recebem).
_SCOPE_PRIORITY = (("mcp_user", "mcp:user", "user"), ("mcp_analytics", "mcp:analytics", "analytics"), ("mcp_finance", "mcp:finance", "finance"))


def enabled_read_domains() -> frozenset[str]:
    raw = os.getenv(ENV_DOMAINS, "")
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def all_read_cohort_names() -> tuple[str, ...]:
    return tuple(name for names in READ_COHORT_TOOL_NAMES.values() for name in names)


def enabled_read_cohort_names() -> tuple[str, ...]:
    enabled = enabled_read_domains()
    return tuple(name for domain, names in READ_COHORT_TOOL_NAMES.items() if domain in enabled for name in names)


def _scopes_of(capability: Any) -> Iterable[str]:
    return tuple(getattr(capability, "scopes", ()) or ())


def token_scope_for(capability: Any) -> str | None:
    """Escopo OAuth que o token precisa ter para a tool aparecer (None = inalcançável hoje)."""
    scopes = set(_scopes_of(capability))
    for catalog_scope, token_scope, _surface in _SCOPE_PRIORITY:
        if catalog_scope in scopes:
            return token_scope
    return None


def policy_surface_for(capability: Any) -> str:
    """Surface da política de execução, coerente com o escopo de token escolhido."""
    scopes = set(_scopes_of(capability))
    for catalog_scope, _token_scope, surface in _SCOPE_PRIORITY:
        if catalog_scope in scopes:
            return surface
    return "user"
