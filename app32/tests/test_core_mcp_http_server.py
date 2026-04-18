from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse

import src.core.mcp_http_server as http_server


def test_create_http_app_mounts_expected_surfaces(monkeypatch):
    def fake_surface_app(surface: str):
        app = Starlette()

        async def endpoint(_):
            return JSONResponse({"surface": surface})

        app.add_route("/", endpoint)
        return app

    monkeypatch.setattr(http_server, "build_surface_http_app", fake_surface_app)

    app = http_server.create_http_app()
    paths = {getattr(route, "path", None) for route in app.routes}

    assert "/" in paths
    assert "/healthz" in paths
    assert "/mcp/user" in paths
    assert "/mcp/admin" in paths
    assert "/mcp/analytics" in paths

