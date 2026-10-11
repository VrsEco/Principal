"""Política de idempotência das mutações financeiras do mcp-versus (SPEC onda 2, seção 10).

* ``required``: criam, geram, importam, conciliam ou casam valor; repetir duplicaria. Exigem ``idempotency_key``.
* ``optional``: ``upsert``/``replace`` e a geração de relatório; repetir regrava o mesmo estado. Aceitam a chave.

O cliente só vê o parâmetro ``idempotency_key``; o runtime (``mcp_runtime``) aplica a regra.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Optional

IDEMPOTENCY_PARAM = "idempotency_key"
IDEMPOTENCY_KEY_MAX_LENGTH = 128

REQUIRED_TOOLS = frozenset(
    {
        "create_financial_automation_rule",
        "create_financial_bordero",
        "create_financial_bordero_settlement",
        "create_financial_budget_contract",
        "create_financial_budget_document",
        "create_financial_budget_document_schedules",
        "create_financial_budget_line",
        "create_financial_budget_version",
        "create_financial_catalog_item",
        "create_financial_classification_rule",
        "create_financial_closing",
        "create_financial_direct_entry",
        "create_financial_entry",
        "create_financial_entry_from_bank_reconciliation_row",
        "create_financial_import_batch",
        "create_financial_ingestion_record",
        "create_financial_schedule",
        "create_financial_settlement",
        "generate_commercial_billing_batch",
        "generate_commercial_financial_titles_for_billing",
        "generate_due_financial_schedules",
        "import_financial_budget_matrix",
        "match_financial_bank_reconciliation_row",
        "reconcile_financial_import_batch",
    }
)
OPTIONAL_TOOLS = frozenset(
    {
        "generate_financial_report",
        "replace_financial_allocations",
        "upsert_commercial_contract_financial_terms",
        "upsert_commercial_contract_fiscal_terms",
        "upsert_financial_budget_matrix",
        "upsert_financial_domain_enablement",
    }
)


def idempotency_mode(tool_name: str) -> Optional[str]:
    """``'required'``, ``'optional'`` ou ``None`` (ferramenta sem idempotência)."""
    name = str(tool_name or "")
    if name in REQUIRED_TOOLS:
        return "required"
    if name in OPTIONAL_TOOLS:
        return "optional"
    return None


def with_idempotency_param(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Acrescenta ``idempotency_key`` ao esquema MCP; o valor é consumido pelo runtime e não chega à ferramenta."""
    mode = idempotency_mode(tool_name)
    if not mode:
        return func
    signature = inspect.signature(func)
    if IDEMPOTENCY_PARAM in signature.parameters:
        return func
    param = inspect.Parameter(
        IDEMPOTENCY_PARAM,
        inspect.Parameter.KEYWORD_ONLY,
        default=None,
        annotation=Optional[str],
    )
    parameters = [p for p in signature.parameters.values() if p.kind is not inspect.Parameter.VAR_KEYWORD]
    parameters.append(param)
    parameters.extend(p for p in signature.parameters.values() if p.kind is inspect.Parameter.VAR_KEYWORD)

    @wraps(func)
    def adapted(*args: Any, **kwargs: Any) -> Any:
        kwargs.pop(IDEMPOTENCY_PARAM, None)
        return func(*args, **kwargs)

    adapted.__signature__ = signature.replace(parameters=parameters)  # type: ignore[attr-defined]
    return adapted
