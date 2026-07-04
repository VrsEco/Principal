from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P1_PROCESSES_ROUTE_CONTRACTS = [
    ("app32/api/routes/agents.py", "/agents/processos", {"GET"}),
    ("app32/api/routes/agents.py", "/api/cadastro-agent/empresa/processar", {"POST"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-portal", {"GET"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-portal/processes/<int:process_id>", {"GET"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-portal/strategic-management", {"GET"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-routines/analysis", {"GET"}),
    ("app32/api/routes/processes.py", "/api/processes/upload-flow", {"POST"}),
    ("app32/api/routes/processes.py", "/api/routines/<int:routine_id>/collaborators", {"GET"}),
    ("app32/api/routes/processes.py", "/api/routines/<int:routine_id>/collaborators", {"POST"}),
    ("app32/api/routes/processes.py", "/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>", {"PUT"}),
    ("app32/api/routes/processes.py", "/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>", {"DELETE"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/bpms-analysis", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-instances", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-occurrences", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-portal", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-portal/processes/<int:process_id>", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-portal/strategic-management", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/process-routines", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/processes/<int:process_id>/bpms-analysis", {"GET"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/routines/<routine_id>", {"GET"}),
    ("app32/api/routes/processes.py", "/macro-processes/<int:macro_id>/book", {"GET"}),
    ("app32/api/routes/processes.py", "/process-map/compact", {"GET"}),
    ("app32/api/routes/processes.py", "/processes/<int:process_id>/book", {"GET"}),
]

P1_PROCESSES_TEMPLATE_CONTRACTS = [
    "app32/templates/legacy/grv_process_analysis.html",
    "app32/templates/legacy/grv_process_detail.html",
    "app32/templates/legacy/grv_process_instance_manage.html",
    "app32/templates/legacy/grv_process_instances.html",
    "app32/templates/legacy/grv_process_map.html",
    "app32/templates/legacy/grv_process_modeling.html",
    "app32/templates/legacy/processes_sidebar.html",
    "app32/templates/modules/processes/bpmn_modeler.html",
    "app32/templates/modules/processes/bpms_analysis.html",
    "app32/templates/modules/processes/process_details_v2.html",
    "app32/templates/modules/processes/process_instance_v2.html",
    "app32/templates/modules/processes/process_map_compact_view.html",
    "app32/templates/modules/processes/process_map_v2.html",
    "app32/templates/modules/processes/process_occurrences_list.html",
    "app32/templates/modules/processes/process_portal_compact.html",
    "app32/templates/modules/processes/process_portal_process_detail.html",
    "app32/templates/modules/processes/processes_v2.html",
    "app32/templates/pdf/grv_process_map_print.html",
    "app32/templates/reports/macro_process_book_v1.html",
    "app32/templates/reports/process_book_v2.html",
]

P1_PROCESSES_JS_ENDPOINT_CONTRACTS = [
    ("app32/static/js/processes.js", "/api/process-areas"),
    ("static/js/processes.js", "/api/process-areas"),
]

WRAPPER_ONLY_ROUTES = {
    ("app32/api/routes/agents.py", "/agents/processos"),
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


def test_processes_p1_routes_are_registered_authenticated_and_scoped():
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    missing = []
    unguarded = []

    for relative_file, route, expected_methods in P1_PROCESSES_ROUTE_CONTRACTS:
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
                "_has_operational_full_access",
                "permission_required",
                "Process.query.filter_by",
                "Routine.query.filter_by",
                "MacroProcess.query.filter_by",
            )
        ) or (relative_file, route) in WRAPPER_ONLY_ROUTES
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not has_scope_guard:
            unguarded.append(f"{relative_file}:{route}:missing tenant/user scope guard")

    assert missing == []
    assert unguarded == []


def test_processes_p1_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P1_PROCESSES_TEMPLATE_CONTRACTS:
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


def test_processes_p1_js_endpoints_are_declared_in_bundles():
    missing = []
    for relative_file, endpoint in P1_PROCESSES_JS_ENDPOINT_CONTRACTS:
        path = REPO_ROOT / relative_file
        if not path.exists():
            missing.append(f"{relative_file}:missing file")
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        if endpoint not in source:
            missing.append(f"{relative_file}:missing endpoint {endpoint}")

    assert missing == []
