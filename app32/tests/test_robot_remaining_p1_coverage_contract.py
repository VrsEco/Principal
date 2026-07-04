from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]

P1_REMAINING_ROUTE_CONTRACTS = [
    ("app32/api/routes/companies.py", "/companies/<int:company_id>/identity", {"GET"}),
    ("app32/api/routes/portfolios.py", "/companies/<int:company_id>/project-portfolios", {"GET"}),
    ("app32/api/routes/integrations.py", "/integrations/workflows", {"GET"}),
    ("app32/api/routes/meetings.py", "/company/<int:company_id>/meeting/<int:meeting_id>/report", {"GET"}),
    ("app32/api/routes/projects.py", "/projects/<int:project_id>/manage", {"GET"}),
    ("app32/api/routes/projects.py", "/projects/new", {"GET"}),
]

P1_REMAINING_TEMPLATE_CONTRACTS = [
    "app32/templates/modules/contracts/contracts_billing.html",
    "app32/templates/modules/contracts/contracts_billing_done.html",
    "app32/templates/modules/contracts/contracts_billing_review.html",
    "app32/templates/modules/contracts/contracts_fiscal_invoices.html",
    "app32/templates/legacy/meeting_form.html",
    "app32/templates/meetings_manage_v2.html",
    "app32/templates/meetings_sidebar.html",
]

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


def test_remaining_p1_routes_are_registered_authenticated_and_scoped():
    by_file = {}
    missing = []
    unguarded = []
    for relative_file, route, expected_methods in P1_REMAINING_ROUTE_CONTRACTS:
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
        if not ({"permission_required", "login_required", "admin_required"} & decorators):
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not any(
            marker in body
            for marker in (
                "company_id",
                "active_company",
                "session",
                "current_user",
                "has_company_full_access",
                "_get_project_page_with_access",
                "permission_required",
                "url_for",
                "Meeting",
                "Project",
            )
        ) and not ({"permission_required", "admin_required"} & decorators):
            unguarded.append(f"{relative_file}:{route}:missing tenant/domain scope guard")
    assert missing == []
    assert unguarded == []


def test_remaining_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []
    for relative_template in P1_REMAINING_TEMPLATE_CONTRACTS:
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
