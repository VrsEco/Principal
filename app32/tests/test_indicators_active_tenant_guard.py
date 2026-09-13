from pathlib import Path


def test_indicator_routes_require_an_active_company():
    source = (Path(__file__).resolve().parents[1] / 'api' / 'routes' / 'indicators.py').read_text(encoding='utf-8')
    assert '@permission_required(' not in source
    assert source.count('@active_company_permission_required(') >= 16
