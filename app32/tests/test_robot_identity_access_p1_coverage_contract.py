from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]

P1_IDENTITY_ACCESS_ROUTE_CONTRACTS = [
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/permission-catalog", {"GET"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/roles/tree", {"GET"}),
    ("app32/api/routes/companies.py", "/api/system-users", {"GET"}),
    ("app32/api/routes/configs.py", "/configs/ai/permissions", {"GET"}),
    ("app32/api/user_employee.py", "/employees/<int:company_id>", {"GET"}),
    ("app32/api/user_employee.py", "/my-activities", {"GET"}),
    ("app32/api/user_employee.py", "/my-companies", {"GET"}),
    ("app32/api/routes/users.py", "/usuarios/cadastrar", {"GET"}),
    ("app32/api/routes/users.py", "/usuarios/editar/<int:user_id>", {"GET"}),
    ("app32/api/routes/users.py", "/usuarios/vincular", {"GET"}),
]

P1_IDENTITY_ACCESS_TEMPLATE_CONTRACTS = [
    "app32/templates/legacy/grv_identity_roles.html",
    "app32/templates/legacy/grv_identity_roles_redirect.html",
]

CONTROL_RE = re.compile(r"<(?:input|select|textarea|button|a|form)\b", re.I)


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _literal_methods(node: ast.Call) -> set[str]:
    for keyword in node.keywords:
        if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            return {value.value.upper() for value in keyword.value.elts if isinstance(value, ast.Constant) and isinstance(value.value, str)}
    return {"GET"}


def _route_functions(path: Path) -> dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    lines = source.splitlines()
    routes = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", None) == "route" and decorator.args:
                route = _literal_string(decorator.args[0])
                if route:
                    routes[(route, tuple(sorted(_literal_methods(decorator))))] = (node, body)
    return routes


def _decorator_names(node: ast.FunctionDef) -> set[str]:
    names = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def test_identity_access_p1_routes_are_registered_authenticated_and_scoped():
    by_file = {}
    missing = []
    unguarded = []
    for relative_file, route, expected_methods in P1_IDENTITY_ACCESS_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
        candidates = [(n, b) for (rr, mm), (n, b) in by_file[relative_file].items() if rr == route and expected_methods.issubset(set(mm))]
        if not candidates:
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")
            continue
        node, body = candidates[0]
        decorators = _decorator_names(node)
        if not ({"permission_required", "login_required", "admin_required"} & decorators):
            unguarded.append(f"{relative_file}:{route}:missing auth/admin guard")
        if not any(marker in body for marker in ("company_id", "active_company", "_ensure_company_access", "current_user", "session", "is_platform_admin", "permission", "User", "Employee")) and not ({"permission_required", "admin_required"} & decorators):
            unguarded.append(f"{relative_file}:{route}:missing tenant/identity scope guard")
    assert missing == []
    assert unguarded == []


def test_identity_access_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []
    for relative_template in P1_IDENTITY_ACCESS_TEMPLATE_CONTRACTS:
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
