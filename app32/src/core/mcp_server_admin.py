from __future__ import annotations

from src.core.mcp_surface_registry import build_admin_mcp_server, run_admin_mcp_server

__all__ = ["build_admin_mcp_server", "run_admin_mcp_server"]


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    run_admin_mcp_server()

