"""Pré-validação das regras de negócio ANTES de pedir ou consumir a aprovação humana.

A aprovação vale só para o conteúdo exato da chamada. Se o conteúdo é recusado depois por uma regra de negócio
(conta bancária ausente, rateio, referências inválidas), a aprovação já foi consumida e se perde. Para as ferramentas
que exigem aprovação e declaram um pré-validador aqui, o runtime roda a validação (sem gravar nada) e devolve o erro
na primeira chamada, antes de abrir a solicitação.

O pré-validador é consultivo: se ele mesmo falhar por exceção, a chamada segue o fluxo normal (o serviço real valida
de novo). Ele nunca autoriza nada; só antecipa a recusa.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

# ferramenta -> "modulo:funcao"; a função recebe os argumentos da chamada e devolve o erro (texto) ou None.
PREVALIDATORS: dict[str, str] = {
    "create_financial_direct_entry": "src.core.mcp_prevalidation:direct_entry",
    "create_financial_entry": "src.core.mcp_prevalidation:financial_entry",
    "replace_financial_allocations": "src.core.mcp_prevalidation:replace_allocations",
    "create_financial_settlement": "src.core.mcp_prevalidation:settlement",
    "create_financial_bordero_settlement": "src.core.mcp_prevalidation:bordero_settlement",
    "reconcile_financial_import_batch": "src.core.mcp_prevalidation:import_batch",
    "match_financial_bank_reconciliation_row": "src.core.mcp_prevalidation:reconciliation_match",
    "create_financial_entry_from_bank_reconciliation_row": "src.core.mcp_prevalidation:reconciliation_new_entry",
    "generate_due_financial_schedules": "src.core.mcp_prevalidation:due_schedules",
}


def _resolve(spec: str) -> Callable[[Mapping[str, Any]], str | None]:
    module_name, _, function_name = spec.partition(":")
    return getattr(importlib.import_module(module_name), function_name)


def prevalidate(tool_name: str, arguments: Mapping[str, Any]) -> str | None:
    """Erro de negócio que recusaria a chamada, ou ``None`` (sem pré-validador, válido ou pré-validador falhou)."""
    spec = PREVALIDATORS.get(str(tool_name))
    if not spec:
        return None
    try:
        return _resolve(spec)(arguments)
    except Exception:  # consultivo: o serviço real valida de novo
        logger.warning("Pré-validação de %s falhou e foi ignorada", tool_name, exc_info=True)
        return None


def direct_entry(arguments: Mapping[str, Any]) -> str | None:
    from src.core.mcp_financial_tools import _bound_payload
    from services.financial_direct_entry_service import FinancialDirectEntryService

    payload, company_error = _bound_payload(arguments.get("company_id"), arguments.get("payload"))
    if company_error:
        return company_error.get("error")
    _data, error = FinancialDirectEntryService.validate_direct_entry(payload=payload)
    return error


def financial_entry(arguments: Mapping[str, Any]) -> str | None:
    """Título a pagar ou a receber: valida o lançamento e o rateio obrigatório sem gravar nada."""
    from src.core.mcp_financial_tools import _bound_payload
    from services.financial_title_rules import requires_allocations, validate_title_creation

    payload, company_error = _bound_payload(arguments.get("company_id"), arguments.get("payload"))
    if company_error:
        return company_error.get("error")
    for forged in ("approved_by_user_id", "approved_at"):
        payload.pop(forged, None)
    if not (requires_allocations(payload.get("entry_type")) or payload.get("allocations")):
        return None
    _clean, _allocations, error = validate_title_creation(company_id=payload["company_id"], payload=payload)
    return error


def replace_allocations(arguments: Mapping[str, Any]) -> str | None:
    from src.core.mcp_financial_tools import _bound_payload
    from services.financial_service import FinancialService

    payload, company_error = _bound_payload(arguments.get("company_id"), arguments.get("payload"))
    if company_error:
        return company_error.get("error")
    _data, _entry, _allocations, error = FinancialService.validate_allocation_batch(payload=payload)
    return error


def settlement(arguments: Mapping[str, Any]) -> str | None:
    from services import financial_prevalidation_rules as rules

    normalized, error = rules.settlement_request_rules(arguments.get("company_id"), arguments.get("payload"))
    if error:
        return error
    return rules.settlement_read_only(normalized)


def bordero_settlement(arguments: Mapping[str, Any]) -> str | None:
    from src.core.mcp_financial_tools import _bound_payload
    from services import financial_prevalidation_rules as rules

    _payload, company_error = _bound_payload(arguments.get("company_id"), arguments.get("payload"))
    if company_error:
        return company_error.get("error")
    return rules.bordero_exists(arguments["company_id"], arguments.get("bordero_id"))


def import_batch(arguments: Mapping[str, Any]) -> str | None:
    from services import financial_prevalidation_rules as rules

    return rules.import_batch_exists(arguments["company_id"], arguments.get("batch_id"))


def reconciliation_match(arguments: Mapping[str, Any]) -> str | None:
    from services import financial_prevalidation_rules as rules

    company_id = arguments["company_id"]
    return rules.import_row_exists(company_id, arguments.get("row_id")) or rules.entry_exists(
        company_id, arguments.get("financial_entry_id")
    )


def reconciliation_new_entry(arguments: Mapping[str, Any]) -> str | None:
    from services import financial_prevalidation_rules as rules

    return rules.import_row_exists(arguments["company_id"], arguments.get("row_id"))


def due_schedules(arguments: Mapping[str, Any]) -> str | None:
    from services import financial_prevalidation_rules as rules

    error = rules.run_until_valid(arguments.get("run_until"))
    if error:
        return error
    schedule_id = arguments.get("schedule_id")
    return rules.schedule_exists(arguments["company_id"], schedule_id) if schedule_id else None
