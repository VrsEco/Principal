from pathlib import Path


def test_operations_inteligentes_is_submenu_of_sapiens_ia():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")

    assert 'or \'/operations\' in request.path' in sidebar
    assert 'href="/operations" class="sub-nav-link' in sidebar
    assert 'Operações Inteligentes' in sidebar
    assert 'href="/operations" class="nav-link' not in sidebar

    sapiens_index = sidebar.index("Sapiens")
    operations_index = sidebar.index("Operações Inteligentes")
    assert operations_index > sapiens_index


def test_operations_audit_keeps_sapiens_group_open_and_active():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")

    assert "'/operations' in request.path" in sidebar
    assert "request.path == '/operations' or '/operations/' in request.path" in sidebar



def test_ai_configuration_items_move_from_finance_base_to_sapiens_ia():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")
    finance_block = sidebar[sidebar.index("Gestão Financeira"):sidebar.index("Sapiens")]
    system_block = sidebar[sidebar.index("Sistema"):sidebar.index("Meu Perfil")]

    assert ">Classificação IA<" not in finance_block
    assert ">Automação IA<" not in finance_block
    assert "Fila de Classificação IA" in finance_block
    assert "Dashboard IA" in finance_block
    assert "Prestação de contas" in finance_block

    assert "IA Corporativa" in system_block
    assert "Configurações de Canais" in system_block
    assert "API / MCP" in system_block
    assert "Capacidades de IA" in system_block
    assert "Monitoramento e Auditoria" in system_block



def test_integrations_and_ai_settings_live_under_sapiens_not_system():
    sidebar = Path("templates/partials/sidebar_standard.html").read_text(encoding="utf-8")
    system_block = sidebar[sidebar.index("Sistema") : sidebar.index("Meu Perfil")]

    assert '/ai' in system_block
    assert '/api-mcp' in system_block
    assert '/channels' in system_block
    assert '/tools' in system_block
    assert '/workflow' in system_block
    assert '/ai-capabilities' in system_block
    assert '/ai-monitoring' in system_block
    assert 'Configurações de Canais' in system_block
    assert 'API / MCP' in system_block
