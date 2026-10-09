"""Coortes de ESCRITA do mcp-versus (onda 2), no molde das coortes de leitura.

Cada coorte é um assunto. A variável ``MCP_VERSUS_WRITE_DOMAINS`` no ambiente do servidor liga os assuntos
(``projects,operations,meetings``); ausente, vazia ou ``none`` mantém tudo desligado. Assunto desligado não é
listado nem registrado. A porta de entrada é o contrato de mutações: só entra numa coorte a ferramenta sem
violação na linha de base (``tests/data/mcp_mutation_violations_baseline.json``).

A aprovação humana segue a regra D6 (``mcp_gate_policy``) e é aplicada pelo runtime.
"""

from __future__ import annotations

import os

ENV_DOMAINS = "MCP_VERSUS_WRITE_DOMAINS"

# Sub-onda 2A (SPEC onda2_mutacoes_mcp_versus_v1, seção 9).
WRITE_COHORT_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    "projects": (
        "create_project",
        "update_project",
        "update_project_task_secure",
    ),
    "operations": (
        "request_engineering_suggestion",
        "request_new_app32_integration",
    ),
    "meetings": (
        "log_meeting_discussion",
    ),
}


def enabled_write_domains() -> frozenset[str]:
    raw = os.environ.get(ENV_DOMAINS)
    if raw is None:
        return frozenset()
    parts = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return frozenset() if "none" in parts else frozenset(parts)


def all_write_cohort_names() -> tuple[str, ...]:
    return tuple(name for names in WRITE_COHORT_TOOL_NAMES.values() for name in names)


def enabled_write_cohort_names() -> tuple[str, ...]:
    enabled = enabled_write_domains()
    return tuple(name for domain, names in WRITE_COHORT_TOOL_NAMES.items() if domain in enabled for name in names)
