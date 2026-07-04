from __future__ import annotations

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_CATALOG = REPO_ROOT / "app32/src/intelligence/tool_catalog.py"


P0_MCP_SAPIENS_TOOLS = [
    "analyze_process_flow_copilot_tool",
    "archive_real_estate_auction_property_tool",
    "create_real_estate_auction_attachment_tool",
    "create_real_estate_auction_event_tool",
    "create_work_calendar_event_tool",
    "create_work_journey_manual_task_tool",
    "delete_real_estate_auction_attachment_tool",
    "delete_real_estate_auction_event_tool",
    "delete_real_estate_auction_source_tool",
    "delete_work_calendar_event_tool",
    "generate_work_journey_agenda_tool",
    "get_efficiency_collaborators_analysis_tool",
    "get_process_routines_analysis_tool",
    "get_real_estate_auction_property_tool",
    "get_work_journey_agenda_tool",
    "get_work_journey_board_tool",
    "get_work_journey_capacity_report_tool",
    "list_employee_process_routines_for_journey_tool",
    "list_routine_journey_bindings_tool",
    "list_work_calendar_events_tool",
    "list_work_journey_blocks_tool",
    "list_work_journey_manual_tasks_tool",
    "list_work_journey_rules_tool",
    "list_work_journey_task_inventory_tool",
    "lock_work_journey_agenda_tool",
    "move_work_journey_agenda_item_tool",
    "save_routine_journey_binding_tool",
    "save_work_journey_block_tool",
    "save_work_journey_rule_tool",
    "suggest_process_flow_activity_automation_tool",
    "unlock_work_journey_agenda_tool",
    "update_real_estate_auction_event_tool",
    "update_real_estate_auction_property_tool",
    "update_real_estate_auction_source_tool",
    "update_work_calendar_event_tool",
    "update_work_journey_item_tool",
    "upsert_real_estate_auction_due_diligence_tool",
]

P0_MCP_SAPIENS_ROUTES = [
    ("app32/api/routes/configs.py", "/api/configs/ai/mcp/instruction-registry/entries"),
    ("app32/api/routes/configs.py", "/api/configs/ai/mcp/instruction-registry/invalidate"),
    ("app32/api/routes/auth.py", "/auth/profile/mcp-token/config"),
    ("app32/api/routes/auth.py", "/auth/profile/mcp-token/generate"),
    ("app32/api/routes/auth.py", "/auth/profile/mcp-token/renew"),
    ("app32/api/routes/auth.py", "/auth/profile/mcp-token/revoke"),
    ("app32/api/routes/auth.py", "/auth/profile/mcp-token/status"),
    ("app32/api/routes/auth.py", "/profile/mcp-token/renew"),
]


def _catalog_tool_names() -> set[str]:
    source = TOOL_CATALOG.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"name=[\"']([a-zA-Z0-9_]+)[\"']", source))


def _literal_route(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _route_functions(path: Path) -> dict[str, tuple[ast.FunctionDef, str]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    lines = source.splitlines()
    routes: dict[str, tuple[ast.FunctionDef, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if getattr(decorator.func, "attr", None) != "route" or not decorator.args:
                continue
            route = _literal_route(decorator.args[0])
            if route:
                routes[route] = (node, "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)]))
    return routes


def _decorator_names(node: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def test_p0_mcp_sapiens_tools_are_registered_in_single_catalog():
    names = _catalog_tool_names()
    missing = [tool for tool in P0_MCP_SAPIENS_TOOLS if tool not in names]

    assert missing == []


def test_p0_mcp_sapiens_mutating_tools_are_explicitly_traceable():
    mutating_prefixes = ("create_", "update_", "delete_", "archive_", "save_", "lock_", "unlock_", "move_", "upsert_", "generate_")
    mutating_tools = [tool for tool in P0_MCP_SAPIENS_TOOLS if tool.startswith(mutating_prefixes)]
    catalog_source = TOOL_CATALOG.read_text(encoding="utf-8", errors="ignore")

    assert mutating_tools
    for tool in mutating_tools:
        assert tool in catalog_source


def test_p0_mcp_sapiens_routes_are_registered_and_guarded():
    by_file: dict[str, dict[str, tuple[ast.FunctionDef, str]]] = {}
    for relative_file, _route in P0_MCP_SAPIENS_ROUTES:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))

    missing = []
    unguarded = []
    for relative_file, route in P0_MCP_SAPIENS_ROUTES:
        route_map = by_file[relative_file]
        if route not in route_map:
            missing.append(f"{relative_file}:{route}")
            continue
        node, body = route_map[route]
        decorators = _decorator_names(node)
        if "login_required" not in decorators:
            unguarded.append(f"{relative_file}:{route}:missing login_required")
        if "configs.py" in relative_file and "_require_ai_admin_access" not in body:
            unguarded.append(f"{relative_file}:{route}:missing ai-admin gate")
        if "auth.py" in relative_file and "user_mcp_token_service" not in body:
            unguarded.append(f"{relative_file}:{route}:missing token service")
        if "company_id" not in body and "status" not in route and "revoke" not in route:
            unguarded.append(f"{relative_file}:{route}:missing tenant/company context")

    assert missing == []
    assert unguarded == []
