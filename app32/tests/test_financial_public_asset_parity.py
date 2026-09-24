"""Os assets financeiros públicos devem estar presentes na release."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('name', [
    'financial_borderos.js', 'financial_entry_direct.js', 'financial_schedules.js',
])
def test_financial_public_asset_is_versioned(name):
    assert (ROOT / 'static/js' / name).is_file()
