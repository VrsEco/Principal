"""Valida apenas o bootstrap de paths; não importa serviços nem inicia MCP."""
import ast
import sys
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / 'src/core/mcp_server.py'
ROOT = str(ENTRYPOINT.parents[2])


@pytest.mark.parametrize('paths', [
    ['venv-packages'],
    ['venv-packages', ROOT],
    [ROOT, 'venv-packages', ROOT],
])
def test_project_root_has_precedence_without_duplicates(monkeypatch, paths, capsys):
    tree = ast.parse(ENTRYPOINT.read_text(encoding='utf-8'))
    bootstrap = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'src.intelligence.tool_catalog':
            break
        bootstrap.append(node)
    monkeypatch.setattr(sys, 'path', list(paths) + [p for p in sys.path if p != ROOT])
    exec(compile(ast.Module(body=bootstrap, type_ignores=[]), str(ENTRYPOINT), 'exec'),
         {'__file__': str(ENTRYPOINT)})
    assert sys.path[0] == ROOT
    assert sys.path.count(ROOT) == 1
    assert 'venv-packages' in sys.path
    assert capsys.readouterr().out == ''
