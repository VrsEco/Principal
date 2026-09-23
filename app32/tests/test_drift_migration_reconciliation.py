"""Offline migration graph checks: no Flask runtime or database connection."""
import ast
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[1]


def graph():
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return ScriptDirectory.from_config(config)


def test_preserves_deployed_parent_and_merges_both_heads():
    scripts = graph()
    assert scripts.get_revision("20260919_0001").down_revision == "20260916_1000"
    assert scripts.get_heads() == ["20260923_1200"]
    assert set(scripts.get_revision("20260923_1200").down_revision) == {
        "20260922_1100", "20260917_1000"
    }


@pytest.mark.parametrize("current", [
    ("20260922_1100", "20260917_1000"),
    ("20260922_1100",),
    ("20260917_1000",),
    (),
])
def test_upgrade_path_resolves_without_rewriting_history(current):
    steps = graph()._upgrade_revs("heads", current)
    revisions = [step.revision.revision for step in steps]
    assert revisions[-1] == "20260923_1200"
    assert not set(current).intersection(revisions)
    if len(current) == 2:
        assert revisions == ["20260923_1200"]


def test_merge_revision_has_no_schema_or_data_operations():
    path = ROOT / "migrations/versions/20260923_1200_merge_identity_and_audit_heads.py"
    module = ast.parse(path.read_text(encoding="utf-8"))
    operations = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    assert {node.name for node in operations} == {"upgrade", "downgrade"}
    assert all(len(node.body) == 1 and isinstance(node.body[0], ast.Pass) for node in operations)


def test_postgres_helper_diagnostics_do_not_write_to_mcp_stdout():
    module = ast.parse((ROOT / "database/postgres_helper.py").read_text(encoding="utf-8-sig"))
    prints = [node for node in ast.walk(module)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "print"]
    assert prints
    assert all(any(keyword.arg == "file" and ast.unparse(keyword.value) == "sys.stderr"
                   for keyword in node.keywords) for node in prints)
