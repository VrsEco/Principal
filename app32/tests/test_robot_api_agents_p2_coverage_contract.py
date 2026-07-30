from __future__ import annotations
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

P2_API_AGENTS_ROUTE_CONTRACTS = [
    ('app32/api/routes/agents.py', '/agents/board', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/cadastro', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/estrategico', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/factory', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/logs', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/performance', {'GET'}),
    ('app32/api/routes/agents.py', '/agents/rotina', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents/<string:agent_id>/test', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/actions/approve/<int:action_id>', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/actions/pending', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents/actions/reject/<int:action_id>', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/actions/revalidate/<int:action_id>', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/actions/rollback/<int:action_id>', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/diagnostics', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents/history', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents/menu/options', {'GET'}),
    ('app32/api/routes/agents.py', '/api/agents/menu/options', {'POST'}),
    ('app32/api/routes/agents.py', '/api/agents/menu/options/<int:option_id>', {'PATCH', 'PUT'}),
    ('app32/api/routes/ai_board.py', '/api/ai/board/resume', {'POST'}),
    ('app32/api/routes/ai_board.py', '/api/ai/board/start', {'POST'}),
    ('app32/api/routes/agents.py', '/api/cadastro-agent/empresa/finalizar', {'POST'}),
    ('app32/api/routes/agents.py', '/api/cadastro-agent/empresa/iniciar', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/business-reviews', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/business-reviews', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/business-reviews/<int:review_id>/decision', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/assisted-analyses/<int:analysis_id>/decision', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/assisted-analyses/<int:analysis_id>/validations', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/fronts/<front_key>/assisted-analyses', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/fronts/<front_key>/assisted-analyses', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/fronts/<front_key>/protocol', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/cockpit/structural-fronts/<front_key>/analysis', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/structural-learning-links', {'GET'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/structural-learning-links', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/structural-learning-links/<int:learning_link_id>/decision', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/urgent-needs/<int:urgent_need_id>/decision', {'POST'}),
    ('app32/api/routes/urgent_business_review.py', '/api/consultive/urgent-needs/<int:urgent_need_id>/status', {'POST'}),
    ('app32/api/routes/main.py', '/api/dashboard/stats', {'GET'}),
    ('app32/api/routes/diag.py', '/api/debug-session', {'GET'}),
    ('app32/api/routes/diag.py', '/api/diag/data-health', {'GET'}),
    ('app32/api/route_audit.py', '/api/entity/<entity_type>/disable', {'POST'}),
    ('app32/api/route_audit.py', '/api/entity/<entity_type>/enable', {'POST'}),
    ('app32/api/route_audit.py', '/api/export-report', {'GET'}),
    ('app32/api/routes/incentives.py', '/api/incentive-rule-sets/<int:rule_set_id>', {'DELETE'}),
    ('app32/api/routes/incentives.py', '/api/incentive-rule-sets/<int:rule_set_id>/protected-delete', {'DELETE'}),
    ('app32/api/routes/incentives.py', '/api/incentives/closings/<int:calc_id>', {'PATCH', 'DELETE'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/areas', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/auditors', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/checklists/<int:checklist_id>', {'GET'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/execution-items/<int:execution_item_id>', {'PATCH', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/evidence-links', {'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/executions', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/executions/<int:execution_id>', {'GET'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/findings', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/findings/<int:finding_id>', {'GET', 'PATCH', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/follow-ups', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/options', {'GET'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/points', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/points/<int:point_id>', {'GET', 'PATCH', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/reports', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/reports/<int:report_id>', {'GET', 'PATCH', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/reports/<int:report_id>/issue', {'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/summary', {'GET'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/workpapers', {'GET', 'POST'}),
    ('app32/api/routes/internal_audit.py', '/api/internal-audit/workpapers/<int:workpaper_id>', {'GET'}),
    ('app32/api/routes/onboarding.py', '/api/onboarding/status', {'GET'}),
    ('app32/api/route_audit.py', '/api/routes', {'GET'}),
    ('app32/api/route_audit.py', '/api/routes/<path:endpoint>/details', {'GET'}),
    ('app32/api/route_audit.py', '/api/routes/without-logging', {'GET'}),
    ('app32/api/route_audit.py', '/api/summary', {'GET'}),
    ('app32/api/routes/incentives.py', '/api/v1/incentives/facts/<int:fact_id>', {'PATCH'}),
    ('app32/api/routes/incentives.py', '/api/v1/incentives/facts/<int:fact_id>/verify', {'POST'}),
    ('app32/api/routes/incentives.py', '/api/v1/incentives/facts/webhook', {'POST'}),
]

P2_API_AGENTS_JS_ENDPOINTS = [
    ('app32/static/js/companies.js', '/api/companies?all=true'),
    ('static/js/companies.js', '/api/companies?all=true'),
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


def _find_route(by_file, relative_file: str, route: str, expected_methods: set[str]):
    by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
    return [
        (node, body)
        for (registered_route, methods), (node, body) in by_file[relative_file].items()
        if registered_route == route and expected_methods.issubset(set(methods))
    ]


def test_api_agents_p2_routes_are_registered_with_expected_methods():
    by_file = {}
    missing = []
    for relative_file, route, expected_methods in P2_API_AGENTS_ROUTE_CONTRACTS:
        if not _find_route(by_file, relative_file, route, expected_methods):
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")
    assert missing == []


def test_api_agents_p2_routes_keep_security_or_operational_markers():
    by_file = {}
    unguarded = []
    security_markers = (
        "company_id",
        "active_company_id",
        "active_company",
        "current_user",
        "session",
        "permission_required",
        "admin_required",
        "login_required",
        "_safe_active_company",
        "_get_active_company",
        "_require_",
        "has_company_full_access",
        "request.get_json",
        "request.args",
        "jsonify",
        "redirect",
        "render_template",
    )
    for relative_file, route, expected_methods in P2_API_AGENTS_ROUTE_CONTRACTS:
        node, body = _find_route(by_file, relative_file, route, expected_methods)[0]
        decorators = _decorator_names(node)
        has_auth_guard = {"permission_required", "login_required", "admin_required"} & decorators
        has_operational_marker = any(marker in body for marker in security_markers)
        if not has_auth_guard and not has_operational_marker:
            unguarded.append(f"{relative_file}:{route}:missing auth/scope/operational marker")
    assert unguarded == []


def test_api_agents_p2_js_endpoints_are_declared_in_frontend_sources():
    missing = []
    for relative_file, endpoint in P2_API_AGENTS_JS_ENDPOINTS:
        source = (REPO_ROOT / relative_file).read_text(encoding="utf-8", errors="ignore")
        if endpoint not in source:
            missing.append(f"{relative_file}:{endpoint}")
    assert missing == []
