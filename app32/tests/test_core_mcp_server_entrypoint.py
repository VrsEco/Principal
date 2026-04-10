import os
from unittest.mock import patch

import src.core.mcp_server as mcp_server


def test_run_mcp_server_delegates_to_user_surface():
    with patch.object(mcp_server, "FastMCP", object()):
        with patch("src.core.mcp_server_user.run_user_mcp_server") as run_user:
            with patch.dict(os.environ, {"APP32_MCP_SURFACE": "user"}, clear=False):
                mcp_server.run_mcp_server()

    run_user.assert_called_once_with()


def test_run_mcp_server_delegates_to_admin_surface():
    with patch.object(mcp_server, "FastMCP", object()):
        with patch("src.core.mcp_server_admin.run_admin_mcp_server") as run_admin:
            with patch.dict(os.environ, {"APP32_MCP_SURFACE": "admin"}, clear=False):
                mcp_server.run_mcp_server()

    run_admin.assert_called_once_with()


def test_run_mcp_server_delegates_to_analytics_surface():
    with patch.object(mcp_server, "FastMCP", object()):
        with patch("src.core.mcp_server_analytics.run_analytics_mcp_server") as run_analytics:
            with patch.dict(os.environ, {"APP32_MCP_SURFACE": "analytics"}, clear=False):
                mcp_server.run_mcp_server()

    run_analytics.assert_called_once_with()


def test_run_mcp_server_delegates_to_ops_surface():
    with patch.object(mcp_server, "FastMCP", object()):
        with patch("src.core.mcp_server_ops.run_ops_mcp_server") as run_ops:
            with patch.dict(os.environ, {"APP32_MCP_SURFACE": "ops"}, clear=False):
                mcp_server.run_mcp_server()

    run_ops.assert_called_once_with()


def test_run_mcp_server_defaults_to_user_surface():
    with patch.object(mcp_server, "FastMCP", object()):
        with patch("src.core.mcp_server_user.run_user_mcp_server") as run_user:
            with patch.dict(os.environ, {}, clear=True):
                mcp_server.run_mcp_server()

    run_user.assert_called_once_with()
