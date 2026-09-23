"""As cópias públicas versionadas não podem divergir dos assets desta release."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('name', [
    'financial_borderos.js', 'financial_entry_direct.js', 'financial_schedules.js',
])
def test_financial_public_asset_matches_canonical(name):
    assert (ROOT / 'static/js' / name).read_bytes() == (
        ROOT / 'app32/static/js' / name
    ).read_bytes()
