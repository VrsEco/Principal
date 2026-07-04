from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_ADMIN_CONFIG_ROUTE_CONTRACTS = [
    ("app32/api/routes/configs.py", "/api/ai-monitoring/report.pdf", {"GET"}),
    ("app32/api/routes/configs.py", "/api/ai-monitoring/requests", {"GET"}),
    ("app32/api/routes/configs.py", "/api/ai-monitoring/requests", {"POST"}),
    ("app32/api/routes/configs.py", "/api/configs/ai/agents", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/ai/agents/<string:agent_id>", {"PUT"}),
    ("app32/api/routes/configs.py", "/api/configs/ai/logs", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/automation-registry", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/executions/<string:execution_id>", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/runs/<string:run_id>", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/runs/<string:run_id>/artifacts/<int:artifact_index>", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/runs/<string:run_id>/backlog-candidates", {"GET"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/runs/<string:run_id>/backlog-sync", {"POST"}),
    ("app32/api/routes/configs.py", "/api/configs/qa/e2e/runs/<string:run_id>/manifest", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/configs", {"GET"}),
    ("app32/api/routes/configs.py", "/api/qa/robot-tests/areas/<string:area_id>/latest", {"GET"}),
    ("app32/api/routes/configs.py", "/api/qa/robot-tests/areas/latest", {"GET"}),
    ("app32/api/routes/configs.py", "/api/qa/robot-tests/errors", {"GET"}),
    ("app32/api/routes/configs.py", "/api/qa/robot-tests/errors/<string:error_id>/actions", {"POST"}),
    ("app32/api/routes/configs.py", "/api/qa/robot-tests/overview", {"GET"}),
    ("app32/api/routes/configs.py", "/configs/ai", {"GET"}),
    ("app32/api/routes/configs.py", "/configs/ai/monitoring", {"GET"}),
    ("app32/api/routes/configs.py", "/configs/system", {"GET"}),
    ("app32/api/routes/integrations.py", "/integrations/admin", {"GET"}),
]

P1_ADMIN_CONFIG_TEMPLATE_CONTRACTS = [
    "app32/templates/configs_system.html",
    "app32/templates/configs_system_audit.html",
    "app32/templates/configurations.html",
    "app32/templates/configurations_ai.html",
    "app32/templates/integrations_admin.html",
]

LEGACY_REDIRECT_ROUTES = {
    ("app32/api/routes/configs.py", "/configs/ai"),
    ("app32/api/routes/configs.py", "/configs/ai/monitoring"),
    ("app32/api/routes/integrations.py", "/integrations/admin"),
}

CONTROL_RE = re.compile(r"<(?:input|select|textarea|button|a|form)\b", re.I)


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _literal_methods(node: ast.Call) -> set[str]:
    for keyword in node.keywords:
        if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            return {
                value.value.upper()
                for value in keyword.value.elts
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            }
    return {"GET"}


def _route_functions(path: Path) -> dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    lines = source.splitlines()
    routes: dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if getattr(decorator.func, "attr", None) != "route" or not decorator.args:
                continue
            route = _literal_string(decorator.args[0])
            if route:
                routes[(route, tuple(sorted(_literal_methods(decorator))))] = (node, body)
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


def test_admin_config_p1_routes_are_registered_authenticated_and_admin_scoped():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    missing = []
    unguarded = []

    for relative_file, route, expected_methods in P1_ADMIN_CONFIG_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
        candidates = [
            (node, body)
            for (registered_route, methods), (node, body) in by_file[relative_file].items()
            if registered_route == route and expected_methods.issubset(set(methods))
        ]
        if not candidates:
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")
            continue
        node, body = candidates[0]
        decorators = _decorator_names(node)
        has_auth_guard = (
            "permission_required" in decorators
            or "login_required" in decorators
            or "admin_required" in decorators
        )
        has_admin_or_tenant_scope = any(
            marker in body
            for marker in (
                "company_id",
                "active_company",
                "_safe_active_company",
                "_require_integration_admin",
                "_require_admin",
                "is_platform_admin",
                "permission_required",
                "current_user",
                "session",
            )
        ) or bool({"permission_required", "admin_required"} & decorators) or (relative_file, route) in LEGACY_REDIRECT_ROUTES
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/admin guard")
        if not has_admin_or_tenant_scope:
            unguarded.append(f"{relative_file}:{route}:missing admin/tenant scope guard")

    assert missing == []
    assert unguarded == []


def test_admin_config_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P1_ADMIN_CONFIG_TEMPLATE_CONTRACTS:
        path = REPO_ROOT / relative_template
        if not path.exists():
            missing.append(relative_template)
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            env.parse(source)
        except Exception as exc:  # pragma: no cover
            invalid.append(f"{relative_template}: {exc}")
        if not CONTROL_RE.search(source):
            without_controls.append(relative_template)

    assert missing == []
    assert invalid == []
    assert without_controls == []
