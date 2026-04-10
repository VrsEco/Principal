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



def test_ai_configuration_items_move_from_finance_base_to_sapiens_ia():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")
    finance_block = sidebar[sidebar.index("Gestão Financeira"):sidebar.index("Sapiens & IA")]
    sapiens_block = sidebar[sidebar.index("Sapiens & IA"):sidebar.index("Sistema")]

    assert ">Classificação IA<" not in finance_block
    assert ">Automação IA<" not in finance_block
    assert "Fila de Classificação IA" in finance_block
    assert "Dashboard IA" in finance_block
    assert "Prestação de contas" in finance_block

    assert "Configurações de IA" in sapiens_block
    assert "Regras de Classificação" in sapiens_block
    assert "Memórias de Classificação" in sapiens_block
    assert "Regras de Automação" in sapiens_block
    assert "Auditoria e Observabilidade" in sapiens_block
    assert "Auditoria Operacional" in sapiens_block
    assert "Auditoria de Automação IA" in sapiens_block



def test_integrations_and_ai_settings_live_under_sapiens_not_system():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")
    sapiens_block = sidebar[sidebar.index("Sapiens & IA"):sidebar.index("Sistema")]
    system_block = sidebar[sidebar.index("Sistema") : sidebar.index("Meu Perfil")]

    assert "/configs/ai" in sapiens_block
    assert "/configs/ai/mcp" in sapiens_block
    assert "Console Operacional IA/MCP" in sapiens_block
    assert "Parâmetros gerais de IA" in sapiens_block
    assert "/integrations" in sapiens_block
    assert "Tools / MCP / Integrações" in sapiens_block
    assert "/integrations" not in system_block
    assert ">Integrações</a>" not in system_block
