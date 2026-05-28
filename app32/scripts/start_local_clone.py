"""Launcher local resiliente para APP32 em clone PostgreSQL.

Objetivo:
- garantir sys.path compatível com o layout do repositório
- aplicar defaults seguros para DEV local/E2E
- subir o Flask sem reloader e sem bootstrap pesado por padrão
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _setdefault(name: str, value: str) -> None:
    if not os.environ.get(name):
        os.environ[name] = value


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "app32"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PACKAGE_ROOT))

_setdefault("FLASK_CONFIG", "development")
_setdefault("FLASK_ENV", "development")
_setdefault("DEBUG", "false")
_setdefault("PORT", "5032")
_setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
_setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
_setdefault("SECRET_KEY", "gv-e2e-dev-secret-20260528")

from app import create_app  # noqa: E402


app = create_app(os.environ.get("FLASK_CONFIG", "development"))
port = int(os.environ.get("PORT", "5032"))
debug = os.environ.get("DEBUG", "false").lower() == "true"

print(f"Starting APP32 local clone launcher on http://127.0.0.1:{port}")
app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
