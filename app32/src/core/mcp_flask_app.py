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
_apps: dict[Any, Any] = {}


def get_mcp_flask_app(config_name: str | None = None) -> Any:
    """Devolve o app do contexto atual, ou um app único por (fábrica, configuração)."""
    from flask import current_app, has_app_context

    if config_name is None and has_app_context():
        return current_app._get_current_object()

    from app import create_app

    key = (id(create_app), config_name)
    app = _apps.get(key)
    if app is None:
        with _lock:
            app = _apps.get(key)
            if app is None:
                app = create_app(config_name) if config_name else create_app()
                _apps[key] = app
    return app
