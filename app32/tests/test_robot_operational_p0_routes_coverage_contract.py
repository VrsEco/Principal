from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


P0_API_ROUTE_CONTRACTS = [
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/employees", {"POST"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/employees/<int:employee_id>", {"GET", "PUT"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/employees/<int:employee_id>", {"DELETE"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/employees/<int:employee_id>/access", {"DELETE"}),
    ("app32/api/routes/companies.py", "/api/companies/<int:company_id>/logo", {"POST"}),
    ("app32/api/routes/portfolios.py", "/api/companies/<int:company_id>/portfolios", {"POST"}),
    ("app32/api/routes/portfolios.py", "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>", {"PUT"}),
    ("app32/api/routes/portfolios.py", "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>", {"DELETE"}),
    ("app32/api/routes/portfolios.py", "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>/summary", {"POST"}),
]

P0_PROCESSES_ROUTE_CONTRACTS = [
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-routines", {"POST"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-routines/<int:routine_id>", {"PUT"}),
    ("app32/api/routes/processes.py", "/api/companies/<int:company_id>/process-routines/<int:routine_id>", {"DELETE"}),
    ("app32/api/routes/processes.py", "/companies/<int:company_id>/bpms-analysis/save", {"POST"}),
]

P0_ROUTINE_ROUTE_CONTRACTS = [
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/absences", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/absences/<int:request_id>/approve", {"POST"}),
    ("app32/api/routes/work_journey_agendas.py", "/api/companies/<int:company_id>/work-journey/agendas/<int:agenda_id>/lock", {"POST"}),
    ("app32/api/routes/work_journey_agendas.py", "/api/companies/<int:company_id>/work-journey/agendas/<int:agenda_id>/unlock", {"POST"}),
    ("app32/api/routes/work_journey_agendas.py", "/api/companies/<int:company_id>/work-journey/agendas/generate", {"POST"}),
    ("app32/api/routes/work_journey_agendas.py", "/api/companies/<int:company_id>/work-journey/agendas/items/<int:agenda_item_id>", {"PATCH"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/blocks", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/blocks/<int:block_id>", {"PUT"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/blocks/<int:block_id>", {"DELETE"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/calendar/events", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/calendar/events/<int:event_id>", {"PATCH"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/calendar/events/<int:event_id>", {"DELETE"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/items/<int:item_id>/transfer", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/process-routines/<int:routine_id>/binding", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/rules", {"POST"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/rules/<int:rule_id>", {"PUT"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/rules/<int:rule_id>", {"DELETE"}),
    ("app32/api/routes/work_journey.py", "/api/companies/<int:company_id>/work-journey/transfers/<int:request_id>/approve", {"POST"}),
]


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


def _assert_route_contracts(contracts: list[tuple[str, str, set[str]]]) -> None:
    by_file: dict[str, dict[tuple[str, tuple[str, ...]], tuple[ast.FunctionDef, str]]] = {}
    for relative_file, _route, _methods in contracts:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))

    missing = []
    unguarded = []
    for relative_file, route, expected_methods in contracts:
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
        has_company_scope = (
            "company_id" in [arg.arg for arg in node.args.args]
            and (
                "company_id" in body
                or "has_company_full_access" in body
                or "_ensure_company_access" in body
                or "can_access_company" in body
            )
        )
        if not has_auth_guard:
            unguarded.append(f"{relative_file}:{route}:missing auth/permission guard")
        if not has_company_scope:
            unguarded.append(f"{relative_file}:{route}:missing company_id tenant guard")

    assert missing == []
    assert unguarded == []


def test_api_company_and_portfolio_p0_routes_are_registered_and_tenant_guarded():
    _assert_route_contracts(P0_API_ROUTE_CONTRACTS)


def test_processes_and_routine_p0_routes_are_registered_and_tenant_guarded():
    _assert_route_contracts(P0_PROCESSES_ROUTE_CONTRACTS + P0_ROUTINE_ROUTE_CONTRACTS)
