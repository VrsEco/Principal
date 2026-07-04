from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


P0_FINANCE_ROUTE_CONTRACTS = [
    ("app32/api/routes/real_estate_auctions.py", "/api/real-estate-auctions/properties/<int:property_id>/financial-sheet"),
    ("app32/api/routes/contracts.py", "/contracts/billing/done"),
    ("app32/api/routes/financial.py", "/financial/automation-audit"),
    ("app32/api/routes/financial.py", "/financial/borderos/<int:bordero_id>"),
    ("app32/api/routes/financial.py", "/financial/budget"),
    ("app32/api/routes/financial.py", "/financial/budget-template"),
    ("app32/api/routes/financial.py", "/financial/budget/execution"),
    ("app32/api/routes/financial.py", "/financial/budget/workspace"),
    ("app32/api/routes/financial.py", "/financial/budgets"),
    ("app32/api/routes/financial.py", "/financial/budgets/workspace"),
    ("app32/api/routes/financial.py", "/financial/catalogs/<string:catalog_slug>"),
    ("app32/api/routes/financial.py", "/financial/classification-dashboard"),
    ("app32/api/routes/financial.py", "/financial/classification-memories"),
    ("app32/api/routes/financial.py", "/financial/classification-queue"),
    ("app32/api/routes/financial.py", "/financial/dashboard"),
    ("app32/api/routes/financial.py", "/financial/domain-enablements"),
    ("app32/api/routes/financial.py", "/financial/entries"),
    ("app32/api/routes/financial.py", "/financial/entries/<int:entry_id>"),
    ("app32/api/routes/financial.py", "/financial/entries/direct"),
    ("app32/api/routes/financial.py", "/financial/import-template"),
    ("app32/api/routes/financial.py", "/financial/imports/<int:batch_id>"),
    ("app32/api/routes/financial.py", "/financial/ingestions"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/drilldown"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/export-pdf"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/export-xlsx"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/export.pdf"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/export.xlsx"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/layout-test"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/projected-titles"),
    ("app32/api/routes/financial_reports.py", "/financial/reports/<report_slug>/view"),
    ("app32/api/routes/financial.py", "/financial/schedules/<int:schedule_id>/settle"),
    ("app32/api/routes/financial.py", "/financial/schedules/new"),
    ("app32/api/routes/real_estate_auctions.py", "/real-estate-auctions/properties/<int:property_id>/financial-sheet"),
]

P0_FINANCE_TEMPLATE_CONTRACTS = [
    "app32/templates/modules/financial/automation_audit.html",
    "app32/templates/modules/financial/automation_rules.html",
    "app32/templates/modules/financial/borderos_list.html",
    "app32/templates/modules/financial/budget_cycles_list.html",
    "app32/templates/modules/financial/budget_execution.html",
    "app32/templates/modules/financial/budget_matrix.html",
    "app32/templates/modules/financial/catalog_detail.html",
    "app32/templates/modules/financial/classification_memories.html",
    "app32/templates/modules/financial/classification_rules.html",
    "app32/templates/modules/financial/counterparties_workspace.html",
    "app32/templates/modules/financial/domain_enablements.html",
    "app32/templates/modules/financial/entries_list.html",
    "app32/templates/modules/financial/entry_direct.html",
    "app32/templates/modules/financial/import_batch_manage.html",
    "app32/templates/modules/financial/partials/_budget_matrix_actions.html",
    "app32/templates/modules/financial/partials/_budget_matrix_filters.html",
    "app32/templates/modules/financial/partials/_budget_matrix_header.html",
    "app32/templates/modules/financial/partials/_budget_matrix_side.html",
    "app32/templates/modules/financial/partials/_dashboard_filters.html",
    "app32/templates/modules/financial/partials/report_filters_bank_statement_page.html",
    "app32/templates/modules/financial/partials/report_filters_bank_statement_sidebar.html",
    "app32/templates/modules/financial/partials/report_filters_cash_flow_sidebar.html",
    "app32/templates/modules/financial/partials/report_filters_income_statement_2_sidebar.html",
    "app32/templates/modules/financial/partials/report_filters_income_statement_page.html",
    "app32/templates/modules/financial/partials/report_filters_income_statement_sidebar.html",
    "app32/templates/modules/financial/partials/report_filters_ledger_page.html",
    "app32/templates/modules/financial/partials/report_filters_ledger_sidebar.html",
    "app32/templates/modules/financial/partials/report_filters_schedule_page.html",
    "app32/templates/modules/financial/partials/report_filters_schedule_sidebar.html",
    "app32/templates/modules/financial/partials/report_view_cash_flow.html",
    "app32/templates/modules/financial/partials/report_view_income_statement.html",
    "app32/templates/modules/financial/partials/report_view_working_capital.html",
    "app32/templates/modules/financial/report_filters.html",
    "app32/templates/modules/financial/report_layout_bank_statement_dossier_landscape_test.html",
    "app32/templates/modules/financial/report_view.html",
]

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
                body = "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
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


def test_finance_p0_routes_are_registered_and_permission_guarded():
    by_file: dict[str, dict[str, tuple[ast.FunctionDef, str]]] = {}
    for relative_file, _route in P0_FINANCE_ROUTE_CONTRACTS:
        by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))

    missing = []
    unguarded = []
    for relative_file, route in P0_FINANCE_ROUTE_CONTRACTS:
        route_map = by_file[relative_file]
        if route not in route_map:
            missing.append(f"{relative_file}:{route}")
            continue
        node, body = route_map[route]
        decorators = _decorator_names(node)
        if "permission_required" not in decorators and "login_required" not in decorators:
            unguarded.append(f"{relative_file}:{route}:missing permission_required")
        has_tenant_context = "permission_required" in decorators or any(
            token in body
            for token in (
                "company_id",
                "get_active_company",
                "_resolve_financial_company",
                "_resolve_contracts_company",
                "_resolve_active_company",
                "_resolve_company",
                "_build_financial_report_or_abort",
                "_build_financial_report_with_definition_or_abort",
                "get_accessible_company_ids",
                "permission_required",
            )
        )
        if not has_tenant_context:
            unguarded.append(f"{relative_file}:{route}:missing tenant/company context")

    assert missing == []
    assert unguarded == []


def test_finance_p0_templates_have_parseable_ui_contracts():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []

    for relative_template in P0_FINANCE_TEMPLATE_CONTRACTS:
        path = REPO_ROOT / relative_template
        if not path.exists():
            missing.append(relative_template)
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            env.parse(source)
        except Exception as exc:  # pragma: no cover - falha explicitada no assert
            invalid.append(f"{relative_template}: {exc}")
        if not CONTROL_RE.search(source):
            without_controls.append(relative_template)

    assert missing == []
    assert invalid == []
    assert without_controls == []
