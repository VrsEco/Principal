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
