"""O runtime de produção não pode escrever assets dentro do worktree Git."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_static_root_is_the_only_versioned_static_source():
    assert (ROOT / "static/vendor/chartjs/chart.umd.min.js").is_file()
    assert (ROOT / "static/vendor/chartjs/chartjs-adapter-date-fns.bundle.min.js").is_file()
    assert not any((ROOT / "app32/static").rglob("*"))


def test_application_uses_public_static_root_without_runtime_synchronization():
    content = (ROOT / "app32/app.py").read_text(encoding="utf-8")

    assert 'Flask(__name__, static_folder="../static")' in content
    assert "_sync_public_static_assets" not in content
