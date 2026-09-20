from __future__ import annotations

"""Entrypoint stdio da surface financeira canônica.

Mantém o mesmo registry utilizado pelo transporte HTTPS/OAuth; não cria
catálogo paralelo para o cliente local.
"""

from src.core.mcp_surface_registry import build_oauth_finance_mcp_server, run_finance_mcp_server

__all__ = ["build_oauth_finance_mcp_server", "run_finance_mcp_server"]


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    run_finance_mcp_server()
