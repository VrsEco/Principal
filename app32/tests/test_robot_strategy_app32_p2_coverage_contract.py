from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment

REPO_ROOT = Path(__file__).resolve().parents[2]

P2_STRATEGY_APP32_ROUTE_CONTRACTS = [
    ('app32/api/routes/plans.py', '/<int:plan_id>/delete', {'POST'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/growth', {'GET'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/growth/<section>', {'GET'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/implantation', {'GET'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/implantation/<section>', {'GET'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/sections/<section_key>/complete', {'POST'}),
    ('app32/api/routes/plans.py', '/<int:plan_id>/update', {'POST'}),
    ('app32/api/routes/strategy_alignment.py', '/api/strategy-alignment-n1/maturation', {'GET'}),
    ('app32/api/routes/strategy_alignment.py', '/api/strategy-alignment-n1/maturation/<int:item_id>/review', {'POST'}),
    ('app32/api/routes/strategy_alignment.py', '/strategy/alignment-n1/maturation', {'GET'}),
]

P2_STRATEGY_APP32_TEMPLATE_CONTRACTS = [
    'app32/templates/404.html',
    'app32/templates/agent_logs.html',
    'app32/templates/ai_board.html',
    'app32/templates/board_interface.html',
    'app32/templates/cadastro_agent.html',
    'app32/templates/cadastro_analise.html',
    'app32/templates/cadastro_form.html',
    'app32/templates/cadastros_list.html',
    'app32/templates/company_logos_manager.html',
    'app32/templates/components/global_activity_button.html',
    'app32/templates/efficiency_analysis.html',
    'app32/templates/engineering_board.html',
    'app32/templates/identity_sidebar.html',
    'app32/templates/legacy/agents_cadastro.html',
    'app32/templates/legacy/agents_sidebar.html',
    'app32/templates/legacy/grv_dashboard.html',
    'app32/templates/legacy/grv_identity_mvv.html',
    'app32/templates/legacy/grv_identity_mvv_redirect.html',
    'app32/templates/legacy/grv_identity_org_chart.html',
    'app32/templates/legacy/grv_routine_activities.html',
    'app32/templates/legacy/grv_routine_capacity.html',
    'app32/templates/legacy/grv_routine_efficiency.html',
    'app32/templates/legacy/grv_sidebar.html',
    'app32/templates/legacy/routine_dashboard.html',
    'app32/templates/legacy/routine_selector.html',
    'app32/templates/legacy/routine_tasks.html',
    'app32/templates/modules/companies/companies_v2.html',
    'app32/templates/modules/consultive/business_review_cockpit.html',
    'app32/templates/modules/dashboard_v2.html',
    'app32/templates/modules/incentives/closings_list.html',
    'app32/templates/modules/incentives/comparative_placeholder.html',
    'app32/templates/modules/incentives/reports_selector.html',
    'app32/templates/modules/incentives/rules_manage.html',
    'app32/templates/modules/incentives/validation_panel.html',
    'app32/templates/modules/okrs/okr_form_v2.html',
    'app32/templates/modules/okrs/okrs_v2.html',
    'app32/templates/notation.html',
    'app32/templates/report_pdf.html',
    'app32/templates/reports/formal_report.html',
    'app32/templates/routines_sidebar.html',
    'app32/templates/styleguide.html',
    'app32/templates/test_routines_modal.html',
    'app32/templates/implantacao/alinhamento_canvas_expectativas.html',
    'app32/templates/implantacao/entrega_relatorio_final.html',
    'app32/templates/implantacao/execution_intro.html',
    'app32/templates/implantacao/modelo_mapa_persona.html',
    'app32/templates/implantacao/modelo_matriz_diferenciais.html',
    'app32/templates/implantacao/relatorios/relatorio_1_capa_resumo.html',
    'app32/templates/legacy/plan_dashboard.html',
    'app32/templates/legacy/plan_implantacao.html',
    'app32/templates/legacy/plan_reports.html',
    'app32/templates/legacy/plan_sidebar.html',
    'app32/templates/modules/incentives/plan_new.html',
    'app32/templates/modules/plans/base_planning.html',
    'app32/templates/modules/plans/growth_dashboard.html',
    'app32/templates/modules/plans/growth_drivers.html',
    'app32/templates/modules/plans/growth_participants.html',
    'app32/templates/modules/plans/growth_report.html',
    'app32/templates/modules/plans/implantation_dashboard.html',
    'app32/templates/modules/plans/implantation_market.html',
    'app32/templates/modules/plans/implantation_report.html',
    'app32/templates/modules/plans/plans_list.html',
    'app32/templates/modules/strategy/alignment_n1_maturation.html',
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


def test_strategy_app32_p2_routes_are_registered_and_scoped():
    by_file = {}
    missing = []
    unguarded = []
    scope_markers = (
        "company_id",
        "active_company_id",
        "active_company",
        "current_user",
        "session",
        "permission_required",
        "login_required",
        "admin_required",
        "Plan",
        "Strategic",
        "Maturation",
        "request.get_json",
        "redirect",
        "render_template",
    )
    for relative_file, route, expected_methods in P2_STRATEGY_APP32_ROUTE_CONTRACTS:
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
        has_auth_guard = {"permission_required", "login_required", "admin_required"} & decorators
        has_scope_marker = any(marker in body for marker in scope_markers)
        if not has_auth_guard and not has_scope_marker:
            unguarded.append(f"{relative_file}:{route}:missing auth/scope marker")
    assert missing == []
    assert unguarded == []


def test_strategy_app32_p2_templates_are_parseable_and_have_controls():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []
    for relative_template in P2_STRATEGY_APP32_TEMPLATE_CONTRACTS:
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
