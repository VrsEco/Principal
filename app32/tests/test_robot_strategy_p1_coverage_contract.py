from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_STRATEGY_ROUTE_CONTRACTS = [
    ("app32/api/routes/indicators.py", "/api/indicators/<int:indicator_id>", {"DELETE"}),
    ("app32/api/routes/indicators.py", "/api/indicators/<int:indicator_id>/toggle-active", {"POST"}),
    ("app32/api/routes/indicator_analysis_safe.py", "/incentives/comparative", {"GET"}),
    ("app32/api/routes/incentives.py", "/incentives/indicators", {"GET"}),
    ("app32/api/routes/incentives.py", "/incentives/indicators/<int:indicator_id>/edit", {"GET", "POST"}),
    ("app32/api/routes/incentives.py", "/incentives/indicators/new", {"POST"}),
    ("app32/api/routes/indicators.py", "/indicators", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/<int:indicator_id>", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/<int:indicator_id>/edit", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/analysis", {"GET"}),
    ("app32/api/routes/indicator_analysis_safe.py", "/indicators/analysis", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/data", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/link-map", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/measurement-routines", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/new", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/routine-execution/<int:routine_id>", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/tree", {"GET"}),
    ("app32/api/routes/indicators.py", "/indicators/tree/<int:node_id>/delete", {"POST"}),
    ("app32/api/routes/indicators.py", "/indicators/tree/<int:node_id>/edit", {"GET", "POST"}),
    ("app32/api/routes/indicators.py", "/indicators/tree/new", {"GET", "POST"}),
]

P1_STRATEGY_TEMPLATE_CONTRACTS = [
    "app32/templates/implantacao/execution_estruturas.html",
    "app32/templates/implantacao/modelo_canvas_proposta_valor.html",
    "app32/templates/implantacao/modelo_modefin.html",
    "app32/templates/implantacao/modelo_produtos.html",
    "app32/templates/implantacao/modelo_produtos_v2.html",
    "app32/templates/legacy/grv_indicator_data_form.html",
    "app32/templates/legacy/grv_indicator_form.html",
    "app32/templates/legacy/grv_indicator_goal_form.html",
    "app32/templates/legacy/grv_indicator_group_form.html",
    "app32/templates/legacy/grv_indicators_analysis.html",
    "app32/templates/legacy/grv_indicators_data.html",
    "app32/templates/legacy/grv_indicators_goals.html",
    "app32/templates/legacy/grv_indicators_list.html",
    "app32/templates/legacy/grv_indicators_tree.html",
    "app32/templates/legacy/indicators_sidebar.html",
    "app32/templates/legacy/plan_company.html",
    "app32/templates/legacy/plan_drivers.html",
    "app32/templates/legacy/plan_drivers_backup.html",
    "app32/templates/legacy/plan_indicator_sidebar.html",
    "app32/templates/legacy/plan_okr_area.html",
    "app32/templates/legacy/plan_okr_global.html",
    "app32/templates/legacy/plan_participants.html",
    "app32/templates/legacy/plan_projects.html",
    "app32/templates/legacy/plan_selector.html",
    "app32/templates/legacy/plan_selector_compact.html",
    "app32/templates/modules/incentives/indicator_edit.html",
    "app32/templates/modules/incentives/indicator_list.html",
    "app32/templates/modules/incentives/plan_manage.html",
    "app32/templates/modules/indicators/comparative_analysis.html",
    "app32/templates/modules/indicators/indicator_batch_entry.html",
    "app32/templates/modules/indicators/indicator_data_list.html",
    "app32/templates/modules/indicators/indicator_details_v2.html",
    "app32/templates/modules/indicators/indicator_form_v2.html",
    "app32/templates/modules/indicators/indicator_link_map.html",
    "app32/templates/modules/indicators/indicator_tree.html",
    "app32/templates/modules/indicators/indicator_tree_form.html",
    "app32/templates/modules/indicators/indicators_v2.html",
    "app32/templates/modules/indicators/measurement_routines.html",
    "app32/templates/modules/plans/growth_okrs_area.html",
    "app32/templates/modules/plans/growth_okrs_global.html",
    "app32/templates/modules/plans/growth_projects.html",
    "app32/templates/modules/plans/implantation_alignment.html",
    "app32/templates/modules/plans/implantation_execution.html",
    "app32/templates/modules/plans/implantation_model.html",
]

P1_STRATEGY_JS_ENDPOINT_CONTRACTS = [
    ("app32/static/js/indicators.js", "/api/indicator-groups"),
    ("static/js/indicators.js", "/api/indicator-groups"),
    ("app32/static/js/indicators.js", "/api/plans"),
    ("static/js/indicators.js", "/api/plans"),
]

REDIRECT_ONLY_ROUTES = {
    ("app32/api/routes/indicator_analysis_safe.py", "/incentives/comparative"),
    ("app32/api/routes/incentives.py", "/incentives/indicators"),
}

CONTROL_RE = re.compile(r"<(?:input|select|textarea|button|a|form)\b", re.I)


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


def test_strategy_p1_routes_are_registered_authenticated_and_scoped():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    missing = []
    unguarded = []

    for relative_file, route, expected_methods in P1_STRATEGY_ROUTE_CONTRACTS:
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
                "_get_project_page_with_access",
                "permission_required",
            )
        ) or (relative_file, route) in REDIRECT_ONLY_ROUTES
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not has_scope_guard:
            unguarded.append(f"{relative_file}:{route}:missing tenant/user scope guard")

    assert missing == []
    assert unguarded == []


def test_strategy_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P1_STRATEGY_TEMPLATE_CONTRACTS:
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


def test_strategy_p1_js_endpoints_are_declared_in_bundles():
    missing = []
    for relative_file, endpoint in P1_STRATEGY_JS_ENDPOINT_CONTRACTS:
        path = REPO_ROOT / relative_file
        if not path.exists():
            missing.append(f"{relative_file}:missing file")
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        if endpoint not in source:
            missing.append(f"{relative_file}:missing endpoint {endpoint}")

    assert missing == []
