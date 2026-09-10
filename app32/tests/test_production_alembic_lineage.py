from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_production_oauth_and_memberships_lineages_converge() -> None:
    app_dir = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option("script_location", str(app_dir / "migrations"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20260910_1000"]
    assert script.get_revision("20260909_1100") is not None