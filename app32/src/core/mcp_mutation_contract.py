"""Contrato automático das MUTAÇÕES do mcp-versus (onda 2), em modo relatório com catraca.

Equivalente ao contrato das leituras (``mcp_cohort_contract``): nenhuma mutação entra numa coorte
publicada sem passar. Enquanto o trabalho de correção acontece, o contrato roda em **modo relatório**:
mede as violações por ferramenta, e um arquivo de linha de base só deixa o número **diminuir**
(violação nova reprova a CI; violação corrigida exige remover a linha de base).

Códigos de violação (SPEC onda2_mutacoes_mcp_versus_v1, seção 4):

* M1 sem ``company_id``/``company_ref`` de primeiro nível;
* M2 parâmetro de identidade/rastreio vindo do cliente (``user_id``, ``approver_*``, ``actor_*`` ...);
* M3 verbo de escrita declarado como risco baixo;
* M4 exige gate humano (destrutiva, aprovação, publicação externa, alto/crítico) e não tem;
* M5 financeira sem ``idempotency_key``;
* M6 importa módulo inexistente;
* M7 sem escopo alcançável pelo token ou sem permissão declarada;
* M8 captura ampla de exceção que pode engolir a negação de permissão.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.core import mcp_read_cohorts
from src.core.mcp_cohort_contract import ToolProbe, missing_imported_modules

WRITE_VERBS = frozenset(
    {
        "create", "update", "delete", "save", "upsert", "toggle", "approve", "complete", "log", "request",
        "restore", "add", "apply", "register", "publish", "configure", "confirm", "pause", "resume", "start",
        "finish", "send", "schedule", "sync", "close", "dispatch", "generate", "import", "process", "review",
        "duplicate", "replace", "match", "reconcile", "classify", "convert", "correct", "cancel", "move",
        "lock", "unlock", "escalate", "attach", "draft", "reject", "archive", "reopen", "assign", "link",
        "unlink", "set", "remove", "reset",
    }
)
DESTRUCTIVE_VERBS = frozenset({"delete", "remove", "cancel", "reset", "archive"})
GATED_VERBS = DESTRUCTIVE_VERBS | {"approve", "publish", "reject"}
IDEMPOTENT_VERBS = frozenset({"create", "upsert", "generate", "import", "replace", "reconcile", "match"})

IDENTITY_PARAM = re.compile(
    r"^(user_id|request_id|trace_id|actor\w*|\w*_user_id|approver\w*|created_by\w*|requested_by\w*|reviewer\w*)$"
)
_COMPANY_PARAMS = ("company_id", "company_ref")
_BROAD_EXCEPT = re.compile(r"except\s+(Exception|BaseException)\b")
_PERMISSION_EXCEPT = re.compile(r"except\s+\(?[^:\n]*PermissionError")

# tool -> {codigo: motivo}. Exceções só com revisão do código da tool.
REVIEWED_MUTATION_EXCEPTIONS: dict[str, dict[str, str]] = {}


def is_mutation(name: str) -> bool:
    verb = name.split("_")[0]
    return verb in WRITE_VERBS and not name.startswith(("get_", "list_"))


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str


def _risk(capability: Any) -> str:
    return str(getattr(getattr(capability, "risk", None), "value", getattr(capability, "risk", None)))


def audit_mutation_tool(name: str, *, capability: Any, probe: ToolProbe | None) -> list[Violation]:
    """Lista as violações do contrato de mutações (vazia = pronta para uma coorte da onda 2)."""
    if capability is None:
        return [Violation("M7", "ausente do catálogo de capabilities")]
    if probe is None or probe.schema is None:
        return [Violation("M7", "não está registrada como ferramenta MCP")]

    verb = name.split("_")[0]
    params = tuple((probe.schema or {}).get("properties", {}).keys())
    risk = _risk(capability)
    gate = bool(getattr(capability, "human_gate", False))
    found: list[Violation] = []

    if not any(p in params for p in _COMPANY_PARAMS):
        found.append(Violation("M1", "sem company_id/company_ref de primeiro nível"))

    for param in params:
        if IDENTITY_PARAM.match(param):
            found.append(Violation("M2", f"parâmetro de identidade vindo do cliente: {param}"))

    if risk == "low":
        found.append(Violation("M3", f"verbo de escrita '{verb}' declarado como risco baixo"))

    if not gate and (verb in GATED_VERBS or risk in {"high", "critical"}):
        reason = "destrutiva/aprovação/publicação" if verb in GATED_VERBS else f"risco {risk}"
        found.append(Violation("M4", f"exige gate humano ({reason}) e não tem"))

    is_financial = getattr(capability, "domain", None) == "finance" or "financial" in name
    if is_financial and verb in IDEMPOTENT_VERBS and "idempotency_key" not in params:
        found.append(Violation("M5", "financeira sem idempotency_key"))

    for module in missing_imported_modules(probe.source):
        found.append(Violation("M6", f"importa módulo inexistente '{module}'"))

    if mcp_read_cohorts.token_scope_for(capability) is None:
        found.append(Violation("M7", "sem escopo alcançável pelo token (mcp_user, mcp_analytics ou mcp_finance)"))
    if not tuple(getattr(capability, "permissions", ()) or ()):
        found.append(Violation("M7", "sem permissão declarada"))

    source = probe.source or ""
    if _BROAD_EXCEPT.search(source) and not _PERMISSION_EXCEPT.search(source):
        found.append(Violation("M8", "captura exceção ampla sem repassar PermissionError"))

    excused = REVIEWED_MUTATION_EXCEPTIONS.get(name, {})
    return [v for v in found if v.code not in excused]


def survey_mutations(probes: dict[str, ToolProbe], capabilities: list[Any]) -> dict[str, list[Violation]]:
    """Violações por mutação do catálogo (inclui as sem violação, com lista vazia)."""
    report: dict[str, list[Violation]] = {}
    for capability in capabilities:
        name = capability.name
        if is_mutation(name):
            report[name] = audit_mutation_tool(name, capability=capability, probe=probes.get(name))
    return report


def as_codes(report: dict[str, list[Violation]]) -> dict[str, list[str]]:
    return {name: sorted({v.code for v in found}) for name, found in sorted(report.items()) if found}
