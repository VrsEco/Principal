"""Aplicativo Flask compartilhado pelo runtime MCP (um por processo e configuração).

Cada ``create_app()`` monta um Flask completo e um engine/pool de banco novo (~0,3 s e uma
fila de conexões que só é devolvida na coleta de lixo). Chamá-lo a cada chamada de ferramenta
ou checagem de permissão esgotava conexões (``OperationalError`` na descoberta, lista de
ferramentas vazia) e atrasava respostas (504 / CONNECT_TIMEOUT no cliente).
"""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_apps: dict[Any, tuple[Any, Any]] = {}


def get_mcp_flask_app(config_name: str | None = None) -> Any:
    """Devolve o app do contexto atual, ou um app único por (fábrica, configuração)."""
    from flask import current_app, has_app_context

    if config_name is None and has_app_context():
        return current_app._get_current_object()

    from app import create_app

    # O cache guarda a própria fábrica e compara por identidade: um ``id()`` pode ser reaproveitado
    # depois que uma fábrica de teste é coletada e serviria um app velho.
    entry = _apps.get(config_name)
    if entry is not None and entry[0] is create_app:
        return entry[1]
    with _lock:
        entry = _apps.get(config_name)
        if entry is None or entry[0] is not create_app:
            app = create_app(config_name) if config_name else create_app()
            entry = (create_app, app)
            _apps[config_name] = entry
    return entry[1]
