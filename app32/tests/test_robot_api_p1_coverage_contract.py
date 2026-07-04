from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_API_ROUTE_CONTRACTS = [
    ("app32/api/routes/agents.py", "/api/agents/workflow-gaps/metrics", {"GET"}),
    ("app32/api/routes/agents.py", "/api/agents/workflow-usage", {"GET"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/employees/full", {"GET"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/identity/summary", {"GET"}),
    ("app32/api/routes/portfolios.py", "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>/summary-options", {"GET"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/unlinked-employees", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/<string:integration_id>", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/<string:integration_id>", {"PUT", "PATCH"}),
    ("app32/api/routes/integrations.py", "/api/integrations/<string:integration_id>", {"DELETE"}),
    ("app32/api/routes/integrations.py", "/api/integrations/<string:integration_id>/test", {"POST"}),
    ("app32/api/routes/integrations.py", "/api/integrations/catalog/<string:integration_key>", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/requests/<int:request_id>", {"DELETE"}),
    ("app32/api/routes/integrations.py", "/api/integrations/requirements", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/save", {"POST"}),
    ("app32/api/routes/integrations.py", "/api/integrations/status", {"GET"}),
    ("app32/api/routes/integrations.py", "/api/integrations/test/<string:service>", {"POST"}),
    ("app32/api/routes/projects.py", "/api/projects/<int:project_id>/employees", {"GET"}),
    ("app32/api/routes/projects.py", "/api/projects/<int:project_id>/send-owner-summary", {"POST"}),
    ("app32/api/routes/projects.py", "/api/projects/<int:project_id>/summary", {"POST"}),
    ("app32/api/routes/projects.py", "/api/projects/<int:project_id>/summary-options", {"GET"}),
]

GLOBAL_READ_CATALOG_ROUTES = {
    ("app32/api/routes/integrations.py", "/api/integrations/catalog/<string:integration_key>"),
}


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_methods(node: ast.Call) -> set[str]:
    for keyword in node.keywords:
        if keyword.arg != "methods":
            continue
        if isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
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


def test_api_p1_routes_are_registered_with_expected_methods():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    missing = []

    for relative_file, route, expected_methods in P1_API_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
        candidates = [
            (node, body)
            for (registered_route, methods), (node, body) in by_file[relative_file].items()
            if registered_route == route and expected_methods.issubset(set(methods))
        ]
        if not candidates:
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")

    assert missing == []


def test_api_p1_routes_are_authenticated_and_tenant_scoped():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    unguarded = []

    for relative_file, route, expected_methods in P1_API_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
        node, body = next(
            (node, body)
            for (registered_route, methods), (node, body) in by_file[relative_file].items()
            if registered_route == route and expected_methods.issubset(set(methods))
        )
        decorators = _decorator_names(node)
        has_auth_guard = "permission_required" in decorators or "login_required" in decorators
        has_tenant_guard = any(
            marker in body
            for marker in (
                "company_id",
                "active_company_id",
                "active_company",
                "_safe_active_company",
                "_require_integration_admin",
                "_has_operational_full_access",
                "_get_project_page_with_access",
                "has_company_full_access",
                "_ensure_company_access",
            )
        ) or (relative_file, route) in GLOBAL_READ_CATALOG_ROUTES
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not has_tenant_guard:
            unguarded.append(f"{relative_file}:{route}:missing tenant/company scope guard")

    assert unguarded == []
