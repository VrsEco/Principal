from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_base_template_cache_busts_global_input_formatter():
    source = (REPO_ROOT / "app32/templates/layouts/base.html").read_text(encoding="utf-8")

    assert "filename='js/input_formatters.js', v=static_asset_version('js/input_formatters.js')" in source
