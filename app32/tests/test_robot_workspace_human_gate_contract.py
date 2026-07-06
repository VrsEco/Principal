from __future__ import annotations

import ast
from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[2]


def _route_functions(path: Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    routes: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if getattr(decorator.func, "attr", None) != "route" or not decorator.args:
                continue
            first = decorator.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                routes[first.value] = node
    return routes


def test_workspace_main_route_is_registered_and_scoped_by_session():
    routes = _route_functions(REPO_ROOT / "app32/api/routes/main.py")
    assert "/main" in routes
    source = ast.get_source_segment(
        (REPO_ROOT / "app32/api/routes/main.py").read_text(encoding="utf-8", errors="ignore"),
        routes["/main"],
    ) or ""
    assert "render_template('notation.html')" in source or 'render_template("notation.html")' in source


def test_workspace_notation_delete_action_has_human_gate_contract():
    template = REPO_ROOT / "app32/templates/notation.html"
    source = template.read_text(encoding="utf-8", errors="ignore")
    Environment().parse(source)

    assert 'id="action-delete"' in source
    assert "disabled" in source
    assert 'id="noteBoard"' in source
    assert 'id="action-create"' in source
    assert 'id="action-edit"' in source
