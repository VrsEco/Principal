from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_REAL_ESTATE_ROUTE_CONTRACTS = [
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>", {"PATCH"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>", {"DELETE"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/attachments", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/attachments/<int:attachment_id>", {"DELETE"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/due-diligence", {"PUT"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/events", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>", {"PATCH"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>", {"DELETE"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/settings", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/settings", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/sources", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/sources", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/sources/<int:source_id>", {"PATCH"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/sources/<int:source_id>", {"DELETE"}),
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/workspace", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/archive", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/attachments", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/attachments/<int:attachment_id>/delete", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/due-diligence", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/edit", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/events", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>/delete", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/new", {"GET"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/settings", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/sources", {"POST"}),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/sources/<int:source_id>/delete", {"POST"}),
]

P1_REAL_ESTATE_TEMPLATE_CONTRACTS = [
    "app32/templates/modules/real_estate_auctions/property_detail.html",
    "app32/templates/modules/real_estate_auctions/property_form.html",
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


def test_real_estate_p1_routes_are_registered_authenticated_and_scoped():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    missing = []
    unguarded = []

    for relative_file, route, expected_methods in P1_REAL_ESTATE_ROUTE_CONTRACTS:
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
        has_auth_guard = "permission_required" in decorators or "login_required" in decorators
        has_scope_guard = any(
            marker in body
            for marker in (
                "company_id",
                "active_company",
                "session",
                "current_user",
                "has_company_full_access",
                "RealEstateAuction",
                "real_estate",
                "permission_required",
            )
        )
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not has_scope_guard:
            unguarded.append(f"{relative_file}:{route}:missing tenant/domain scope guard")

    assert missing == []
    assert unguarded == []


def test_real_estate_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P1_REAL_ESTATE_TEMPLATE_CONTRACTS:
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
