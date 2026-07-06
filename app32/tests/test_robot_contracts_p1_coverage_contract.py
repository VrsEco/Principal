from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]

P1_CONTRACTS_ROUTE_CONTRACTS = [
    ("app32/api/routes/contracts.py", "/contracts/<int:contract_id>", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/catalogs/items", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/customers", {"GET"}),
    ("app32/api/routes/contracts.py", "/contracts/customers/portfolio", {"GET"}),
    ("app32/api/routes/contracts.py", "/contracts/dashboard", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/legal-entities", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/new", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/parties", {"GET"}),
    ("app32/api/routes/contracts.py", "/contracts/parties/<int:party_id>", {"GET", "POST"}),
    ("app32/api/routes/contracts.py", "/contracts/parties/new", {"GET", "POST"}),
]

P1_CONTRACTS_TEMPLATE_CONTRACTS = [
    "app32/templates/modules/contracts/_contract_tab_content.html",
    "app32/templates/modules/contracts/contract_create.html",
    "app32/templates/modules/contracts/contract_manage.html",
    "app32/templates/modules/contracts/contracts_items_catalog.html",
    "app32/templates/modules/contracts/contracts_items_catalog_items.html",
    "app32/templates/modules/contracts/contracts_items_catalog_structure.html",
    "app32/templates/modules/contracts/contracts_workspace.html",
    "app32/templates/modules/contracts/customers_portfolio.html",
    "app32/templates/modules/contracts/legal_entities.html",
    "app32/templates/modules/contracts/parties_list.html",
    "app32/templates/modules/contracts/party_manage.html",
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


def test_contracts_p1_routes_are_registered_authenticated_and_scoped():
    by_file = {}
    missing = []
    unguarded = []
    for relative_file, route, expected_methods in P1_CONTRACTS_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
        candidates = [(n, b) for (rr, mm), (n, b) in by_file[relative_file].items() if rr == route and expected_methods.issubset(set(mm))]
        if not candidates:
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")
            continue
        node, body = candidates[0]
        decorators = _decorator_names(node)
        if not ({"permission_required", "login_required"} & decorators):
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not any(marker in body for marker in ("company_id", "active_company", "session", "current_user", "has_company_full_access", "permission_required", "Contract")) and "permission_required" not in decorators:
            unguarded.append(f"{relative_file}:{route}:missing tenant/domain scope guard")
    assert missing == []
    assert unguarded == []


def test_contracts_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []
    for relative_template in P1_CONTRACTS_TEMPLATE_CONTRACTS:
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


def test_contracts_p1_human_gate_controls_are_structurally_covered():
    critical_controls = {
        "app32/templates/modules/contracts/_contract_tab_content.html": [
            'name="delete_retention_id"',
            'type="submit"',
        ],
        "app32/templates/modules/contracts/contracts_items_catalog.html": [
            "<form",
            'method="post"',
        ],
        "app32/templates/modules/contracts/contracts_items_catalog_items.html": [
            "<form",
            'method="post"',
        ],
        "app32/templates/modules/contracts/contracts_items_catalog_structure.html": [
            "<form",
            'method="post"',
        ],
        "app32/templates/modules/contracts/contracts_list.html": [
            'name="form_action"',
            'value="activate_contract"',
            'value="suspend_contract"',
            'value="close_contract"',
            'value="delete_contract"',
            "confirm(",
        ],
    }
    missing = []
    for relative_template, markers in critical_controls.items():
        source = (REPO_ROOT / relative_template).read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in source:
                missing.append(f"{relative_template}:{marker}")
    assert missing == []
