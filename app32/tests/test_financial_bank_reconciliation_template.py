from pathlib import Path


def test_bank_reconciliation_template_contains_three_column_workspace():
    template = Path(
        r"C:\GestaoVersus\app32\app32\templates\modules\financial\bank_reconciliation.html"
    ).read_text(encoding="utf-8")

    assert "Upload prático do extrato" in template
    assert 'accept=".ofx,.xlsx,.xls,.csv"' in template
    assert 'id="bank-rows-list"' in template
    assert 'id="system-rows-list"' in template
    assert 'id="workbench-panel"' in template
    assert "Painel de decisão" in template
    assert "Conciliado 1:N" in template
    assert "Cancelar conciliação" in template
    assert "Criar lançamento no sistema" in template
    assert "selectBankAccountCard(" in template
    assert "document.getElementById('upload-bank-account').addEventListener('change'" in template
