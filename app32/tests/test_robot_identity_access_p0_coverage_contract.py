from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P0_IDENTITY_ACCESS_ROUTE_CONTRACTS = [
    ("app32/api/user_employee.py", "/add-to-company"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/link-user"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/role-permission-presets"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/role-permission-presets/<int:preset_id>"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/roles"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/roles/<int:role_id>"),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/users"),
    ("app32/api/routes/users.py", "/api/usuarios/<int:user_id>"),
    ("app32/api/routes/users.py", "/api/usuarios/<int:user_id>/test-channel"),
    ("app32/api/routes/auth.py", "/auth/change-password"),
    ("app32/api/auth.py", "/current-user"),
    ("app32/api/user_employee.py", "/employee/<int:employee_id>"),
    ("app32/api/user_employee.py", "/employee/<int:employee_id>/link-user"),
    ("app32/api/auth.py", "/logout"),
    ("app32/api/routes/auth.py", "/logout"),
    ("app32/api/auth.py", "/register"),
    ("app32/api/user_employee.py", "/register"),
    ("app32/api/auth.py", "/users"),
    ("app32/api/auth.py", "/users/<int:user_id>"),
    ("app32/api/auth.py", "/users/<int:user_id>/link-companies"),
    ("app32/api/auth.py", "/users/<int:user_id>/link-company"),
    ("app32/api/auth.py", "/users/<int:user_id>/status"),
    ("app32/api/auth.py", "/users/<int:user_id>/unlink-company/<int:employee_id>"),
    ("app32/api/auth.py", "/users/companies"),
    ("app32/api/auth.py", "/users/page"),
    ("app32/api/routes/users.py", "/usuarios/api/delete/<int:user_id>"),
]

P0_IDENTITY_ACCESS_TEMPLATE_CONTRACTS = [
    "app32/templates/auth/login_v2.html",
    "app32/templates/auth/select_company_v2.html",
]

PUBLIC_ALLOWED_ROUTES = {
    ("app32/api/auth.py", "/register"),
    ("app32/api/user_employee.py", "/register"),
}

SESSION_ONLY_ROUTES = {
    ("app32/api/auth.py", "/logout"),
    ("app32/api/routes/auth.py", "/logout"),
}

CONTROL_RE = re.compile(r"<(?:input|select|textarea|button|a|form)\b", re.I)


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
                current = routes.get(route)
                body = "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
                if current:
                    previous_node, previous_body = current
                    body = previous_body + "\n" + body
                    routes[route] = (previous_node, body)
                else:
                    routes[route] = (node, body)
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


def test_identity_access_p0_routes_are_registered_and_guarded():
    by_file: dict[str, dict[str, tuple[ast.FunctionDef, str]]] = {}
    for relative_file, _route in P0_IDENTITY_ACCESS_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))

    missing = []
    unguarded = []
    for relative_file, route in P0_IDENTITY_ACCESS_ROUTE_CONTRACTS:
        route_map = by_file[relative_file]
        if route not in route_map:
            missing.append(f"{relative_file}:{route}")
            continue
        node, body = route_map[route]
        decorators = _decorator_names(node)
        route_key = (relative_file, route)
        is_public_allowed = route_key in PUBLIC_ALLOWED_ROUTES
        has_auth_guard = (
            is_public_allowed
            or "login_required" in decorators
            or "permission_required" in decorators
            or "current_user" in body
            or "is_platform_admin" in body
        )
        has_tenant_or_scope_guard = (
            is_public_allowed
            or route_key in SESSION_ONLY_ROUTES
            or "admin_required" in decorators
            or "company_id" in body
            or "can_access_company" in body
            or "has_company_full_access" in body
            or "is_platform_admin" in body
            or "current_user" in body
            or "permission" in body.lower()
        )
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth guard")
        if not has_tenant_or_scope_guard:
            unguarded.append(f"{relative_file}:{route}:missing tenant/scope guard")

    assert missing == []
    assert unguarded == []


def test_identity_access_p0_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P0_IDENTITY_ACCESS_TEMPLATE_CONTRACTS:
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
