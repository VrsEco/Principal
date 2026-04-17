from __future__ import annotations

from src.core.mcp_surface_registry import get_surface_manifest


def test_project_task_secure_tools_are_scoped_per_surface():
    user_manifest = get_surface_manifest("user", domain="projects", include_tools=True)
    admin_manifest = get_surface_manifest("admin", domain="projects", include_tools=True)
    analytics_manifest = get_surface_manifest("analytics", domain="projects", include_tools=True)

    user_tools = {tool["name"] for tool in user_manifest["tools"]}
    admin_tools = {tool["name"] for tool in admin_manifest["tools"]}
    analytics_tools = {tool["name"] for tool in analytics_manifest["tools"]}

    assert {"list_project_tasks_secure", "create_project_task_secure", "update_project_task_secure"} <= user_tools
    assert "delete_project_task_secure" not in user_tools
    assert "restore_project_task_secure" not in user_tools

    assert {"delete_project_task_secure", "restore_project_task_secure", "get_project_task_analytics_report"} <= admin_tools
    assert "get_project_task_analytics_report" in analytics_tools
    assert "delete_project_task_secure" not in analytics_tools

