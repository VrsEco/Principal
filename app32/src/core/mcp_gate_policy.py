"""Quando uma mutação do mcp-versus exige aprovação humana persistida (decisão D6, opção B).

Antes: o flag ``human_gate`` do catálogo era só declarativo. O runtime só pedia aprovação quando a
política negava (risco alto/crítico, ação destrutiva, matriz do overlay), então 39 das 66 ferramentas
com ``human_gate=True`` rodavam sem aprovação. Agora a regra é uma só, explícita e testada:

* exigem aprovação: destrutivas (delete/remove/cancel/reset/archive), aprovações e rejeições,
  publicação/envio a terceiros (publish/resume/send), mutações de risco alto ou crítico, e as
  financeiras que lançam ou baixam valor, mais o fim de vida de contrato (listadas abaixo);
* não exigem: criar e editar de risco médio (seguem só com RBAC por empresa e auditoria).

O que o cliente envia nunca é aprovação: a aprovação é um registro persistido no APP32, vinculado ao
principal, à empresa, à ferramenta e ao payload exato, consumido uma única vez.
"""

from __future__ import annotations

from typing import Any

APPROVAL_VERBS = frozenset(
    {"delete", "remove", "cancel", "reset", "archive", "approve", "reject", "publish", "resume", "send"}
)

# Financeiras que lançam, baixam ou materializam valor, e fim de vida de contrato comercial.
APPROVAL_TOOLS = frozenset(
    {
        "create_financial_entry",
        "create_financial_direct_entry",
        "create_financial_settlement",
        "create_financial_bordero_settlement",
        "create_financial_entry_from_bank_reconciliation_row",
        "match_financial_bank_reconciliation_row",
        "review_financial_reconciliation_match",
        "reconcile_financial_import_batch",
        "convert_financial_ingestion_record",
        "generate_due_financial_schedules",
        "apply_financial_automation_to_instance",
        "process_financial_import_batch",
        "replace_financial_allocations",
        "generate_commercial_billing_batch",
        "generate_commercial_financial_titles_for_billing",
        "close_commercial_contract",
        "suspend_commercial_contract",
    }
)

_READ_PREFIXES = ("get_", "list_", "search_", "describe_")


def _risk(capability: Any) -> str:
    return str(getattr(getattr(capability, "risk", None), "value", getattr(capability, "risk", None)) or "medium")


def requires_persisted_approval(tool_name: str, capability: Any = None) -> bool:
    """True quando a chamada só pode executar depois de uma aprovação humana persistida."""
    name = str(tool_name or "").strip().lower()
    if not name or name.startswith(_READ_PREFIXES):
        return False
    if name in APPROVAL_TOOLS:
        return True
    if name.split("_")[0] in APPROVAL_VERBS:
        return True
    return _risk(capability) in {"high", "critical"} and bool(getattr(capability, "human_gate", False))
