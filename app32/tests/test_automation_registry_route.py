from pathlib import Path


def test_automation_registry_page_route_is_registered():
    source = Path(r"C:\GestaoVersus\app32\app32\api\routes\configs.py").read_text(encoding="utf-8")

    assert "@configs_bp.route('/ai-automation-mesh')" in source
    assert "modules/operations/automation_registry.html" in source
