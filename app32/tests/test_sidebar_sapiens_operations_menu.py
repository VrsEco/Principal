from pathlib import Path


def test_operations_inteligentes_is_submenu_of_sapiens_ia():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")

    assert 'or \'/operations\' in request.path' in sidebar
    assert 'href="/operations" class="sub-nav-link' in sidebar
    assert 'Operações Inteligentes' in sidebar
    assert 'href="/operations" class="nav-link' not in sidebar

    sapiens_index = sidebar.index("Sapiens & IA")
    operations_index = sidebar.index("Operações Inteligentes")
    assert operations_index > sapiens_index


def test_operations_audit_keeps_sapiens_group_open_and_active():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")

    assert "'/operations' in request.path" in sidebar
    assert "request.path == '/operations' or '/operations/' in request.path" in sidebar
