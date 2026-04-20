from pathlib import Path


def test_schedule_js_keeps_legacy_tab_aliases_pointing_to_canonical_tabs():
    content = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")
    assert "const normalizeScheduleTab" in content
    assert "settlements: 'baixas'" in content
    assert "liquidacao: 'baixas'" in content
    assert "'memoria-calculo': 'memoria-calculo'" in content
    assert "switchTab('memoria-calculo')" in content


def test_financial_borderos_and_entries_remove_legacy_agendamento_copy():
    borderos_html = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\borderos.html").read_text(encoding="utf-8")
    borderos_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_borderos.js").read_text(encoding="utf-8")
    entries_html = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\entries_list.html").read_text(encoding="utf-8")
    assert 'Títulos Financeiros elegíveis' in borderos_html
    assert 'títulos financeiros elegíveis' in borderos_js
    assert 'Selecione ao menos um título financeiro.' in borderos_js
    assert '>Título financeiro</a>' in entries_html
