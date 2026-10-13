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
    # Exclusões e restauração: a confirmação NÃO é uma afirmação do cliente. O runtime exige aprovação humana persistida
    # (mcp_gate_policy: verbo delete, ou risco alto com gate) e só então a ferramenta roda; o valor fixo satisfaz a
    # confirmação interna da ferramenta compartilhada com o chat.
    "delete_project": {"confirm": True},
    "delete_project_task_secure": {"confirm": True},
    "restore_project_task_secure": {"confirm": True},
    "delete_meeting_secure": {"confirm": True},
}


def description_for_mcp(tool_name: str, description: str | None) -> str | None:
    """Descrição da ferramenta sem as linhas ``:param <oculto>:`` dos parâmetros que o MCP não expõe."""
    hidden = HIDDEN_CLIENT_PARAMETERS.get(str(tool_name))
    if not hidden or not description:
        return description
    kept = [
        line
        for line in description.splitlines()
        if not any(line.strip().startswith(f":param {name}:") for name in hidden)
    ]
    return "\n".join(kept)


def adapt_for_mcp(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Devolve ``func`` sem os parâmetros ocultos no esquema e com os valores fixos injetados.

    Nas mutações financeiras com idempotência (``mcp_idempotency_policy``) acrescenta ``idempotency_key``.
    """
    from src.core.mcp_idempotency_policy import with_idempotency_param

    func = with_idempotency_param(str(tool_name), func)
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
