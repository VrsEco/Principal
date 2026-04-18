from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def test_financial_operations_menu_prioritizes_automation_center():
    sidebar = (BASE_DIR / "templates" / "partials" / "sidebar_standard.html").read_text(encoding="utf-8")

    operation_marker = """<button class="subgroup-button" onclick="return toggleSidebarGroup(this, event)">
                    Operação"""
    operation_start = sidebar.index(operation_marker)
    operation_end = sidebar.index("<div class=\"sidebar-subgroup {{ 'open' if request.path == '/financial'", operation_start)
    operation_block = sidebar[operation_start:operation_end]

    assert "/financial/automation" in operation_block
    assert "Central de Automação" in operation_block
    assert "request.path == '/financial/automation'" in operation_block
    assert operation_block.index("Central de Automação") < operation_block.index("Agendamentos")
