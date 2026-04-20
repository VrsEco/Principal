from pathlib import Path


def test_schedule_shortcuts_and_bordero_access_use_unified_baixa_copy():
    schedules_list_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules_list.js").read_text(encoding="utf-8")
    borderos_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_borderos.js").read_text(encoding="utf-8")

    assert 'Abrir borderô' in schedules_list_js
    assert 'Consultar título' in schedules_list_js
    assert '>Baixar</button>' in schedules_list_js
    assert 'open_tab=baixas' in borderos_js
    assert 'data-label="Título financeiro"' in borderos_js
