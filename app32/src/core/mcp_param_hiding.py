"""Parâmetros que o mcp-versus NÃO aceita do cliente em ferramentas compartilhadas com o chat.

Várias ferramentas são funções LangChain usadas pelo chat e expostas ao MCP pelo mesmo objeto. Mudar a
assinatura quebraria o chat. Este adaptador oculta, só no MCP, os parâmetros que carregam identidade ou
confirmação vindas do cliente: o esquema MCP deixa de incluí-los e o valor fixo configurado é injetado.

Regra de uso: só injete valor que NÃO seja uma afirmação de confirmação humana, a não ser que o runtime
já aplique a aprovação persistida àquela ferramenta (``mcp_gate_policy``).
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable

# ferramenta -> {parâmetro oculto: valor injetado}
HIDDEN_CLIENT_PARAMETERS: dict[str, dict[str, Any]] = {
    # O nome do solicitante vem do usuário autenticado (a ferramenta já usa o nome da sessão quando None).
    "request_engineering_suggestion": {"requester_name": None},
}


def adapt_for_mcp(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Devolve ``func`` sem os parâmetros ocultos no esquema e com os valores fixos injetados."""
    hidden = HIDDEN_CLIENT_PARAMETERS.get(str(tool_name))
    if not hidden:
        return func
    signature = inspect.signature(func)
    adapted_signature = signature.replace(
        parameters=[parameter for name, parameter in signature.parameters.items() if name not in hidden]
    )

    @wraps(func)
    def adapted(*args: Any, **kwargs: Any) -> Any:
        for name, value in hidden.items():
            kwargs[name] = value
        return func(*args, **kwargs)

    adapted.__signature__ = adapted_signature  # type: ignore[attr-defined]
    return adapted
