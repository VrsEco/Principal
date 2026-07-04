from __future__ import annotations

import ast
import re
from pathlib import Path

from jinja2 import Environment

REPO_ROOT = Path(__file__).resolve().parents[2]

P2_RESIDUAL_ROUTE_CONTRACTS = [
    ('app32/api/notes.py', '/<int:note_id>', {'DELETE'}),
    ('app32/api/notes.py', '/<int:note_id>', {'PUT'}),
    ('app32/api/routes/urgent_business_review.py', '/consultive/cockpit/fronts/<front_key>', {'GET'}),
    ('app32/api/routes/dev.py', '/debug/routes', {'GET'}),
    ('app32/api/webhooks/email_webhook.py', '/email', {'POST'}),
    ('app32/api/routes/health.py', '/health/live', {'GET'}),
    ('app32/api/routes/health.py', '/health/ready', {'GET'}),
    ('app32/api/routes/health.py', '/health', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/calculate/run', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/closing/<int:calc_id>', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/closing/<int:calc_id>/<action>', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/harvest/run', {'POST'}),
    ('app32/api/routes/incentives.py', '/incentives/participants/<int:participant_id>', {'DELETE', 'PATCH'}),
    ('app32/api/routes/incentives.py', '/incentives/reports', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/rules/<int:rule_set_id>', {'PATCH'}),
    ('app32/api/routes/incentives.py', '/incentives/rules/<int:rule_set_id>', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/rules/<int:rule_set_id>/participants', {'POST'}),
    ('app32/api/routes/incentives.py', '/incentives/rules/<int:rule_set_id>/vetores', {'POST'}),
    ('app32/api/routes/incentives.py', '/incentives/rules/new', {'POST', 'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/seed-mock', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/spider-web', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/statement', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/statement/<int:calc_id>/<int:employee_id>', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/validation', {'GET'}),
    ('app32/api/routes/incentives.py', '/incentives/vetores/<int:vetor_id>', {'DELETE', 'PATCH'}),
    ('app32/api/routes/incentives.py', '/incentives/vetores/<int:vetor_id>/range', {'PATCH'}),
    ('app32/api/routes/incentives.py', '/incentives', {'GET'}),
    ('app32/api/routes/internal_audit.py', '/internal-audit', {'GET'}),
    ('app32/api/routes/main.py', '/main', {'GET'}),
    ('app32/api/routes/okr.py', '/okrs/new', {'GET'}),
    ('app32/api/routes/okr.py', '/okrs', {'GET'}),
    ('app32/api/routes/dev.py', '/ping/dependencies', {'GET'}),
    ('app32/api/routes/dev.py', '/seed-demo', {'GET'}),
    ('app32/api/webhooks/telegram_webhook.py', '/telegram', {'POST'}),
    ('app32/api/routes/dev.py', '/trigger-proactive', {'GET'}),
]

P2_RESIDUAL_TEMPLATE_CONTRACTS = [
    'app32/templates/agent_surface_wrapper.html',
    'app32/templates/modules/operations/ai_tools_catalog.html',
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


def _find_route(by_file, relative_file: str, route: str, expected_methods: set[str]):
    by_file.setdefault(relative_file, _route_functions(REPO_ROOT / relative_file))
    return [
        (node, body)
        for (registered_route, methods), (node, body) in by_file[relative_file].items()
        if registered_route == route and expected_methods.issubset(set(methods))
    ]


def test_residual_p2_routes_are_registered_with_expected_methods():
    by_file = {}
    missing = []
    for relative_file, route, expected_methods in P2_RESIDUAL_ROUTE_CONTRACTS:
        if not _find_route(by_file, relative_file, route, expected_methods):
            missing.append(f"{relative_file}:{route}:{','.join(sorted(expected_methods))}")
    assert missing == []


def test_residual_p2_routes_keep_auth_scope_or_public_operational_markers():
    by_file = {}
    unguarded = []
    operational_markers = (
        "company_id",
        "active_company",
        "active_company_id",
        "current_user",
        "session",
        "permission_required",
        "login_required",
        "admin_required",
        "request.get_json",
        "request.args",
        "jsonify",
        "render_template",
        "redirect",
        "health",
        "dependencies",
        "webhook",
        "signature",
        "token",
        "Incentive",
        "OKR",
        "Note",
        "Audit",
        "_safe_active_company",
        "_require_",
    )
    for relative_file, route, expected_methods in P2_RESIDUAL_ROUTE_CONTRACTS:
        node, body = _find_route(by_file, relative_file, route, expected_methods)[0]
        decorators = _decorator_names(node)
        has_guard = {"permission_required", "login_required", "admin_required"} & decorators
        has_marker = any(marker in body for marker in operational_markers)
        if not has_guard and not has_marker:
            unguarded.append(f"{relative_file}:{route}:missing auth/scope/public-operational marker")
    assert unguarded == []


def test_residual_p2_templates_are_parseable_and_have_ui_controls():
    env = Environment()
    missing = []
    invalid = []
    without_controls = []
    for relative_template in P2_RESIDUAL_TEMPLATE_CONTRACTS:
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
