from pathlib import Path


TEMPLATE_PATH = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\bank_reconciliation.html")


def test_reconciliation_template_uses_standard_right_sidebar_filters():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "{% block sidebar_right %}" in content
    assert 'workspace-bank-account' in content
    assert 'batch-select' in content
    assert 'reconciliation-amount-filter' in content
    assert 'reconciliation-movement-filter' in content
    assert 'data-format="currency"' in content
    assert 'Compara o valor absoluto' in content
    assert 'onclick="applyWorkspaceFilters()"' in content
    assert 'openFilterDrawer()' not in content
    assert 'id="recon-filter-drawer"' not in content
    assert 'Abrir filtros' not in content


def test_reconciliation_template_exposes_bulk_cancel_controls_for_reconciled_tab():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert 'id="bank-column-actions"' in content
    assert "function renderBankColumnActions()" in content
    assert "function toggleSelectAllVisibleReconciledRows()" in content
    assert "function cancelSelectedReconciliations()" in content
    assert "/api/financial/reconciliation/rows/cancel-batch" in content
    assert "Selecionar todos" in content
    assert "Cancelar conciliação" in content


def test_reconciliation_template_uses_requested_workbench_card_order():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert 'id="selected-bank-strip"' in content
    assert "function renderSelectedBankStrip()" in content
    assert "Registros bancários selecionados" not in content

    order = [
        "Conciliação em conjunto",
        "Baixa de título em aberto",
        "Criar título e baixar",
        "Sugestões automáticas da linha em foco",
    ]

    positions = [content.index(label) for label in order]
    assert positions == sorted(positions)


def test_reconciliation_template_uses_compact_money_without_currency_symbol():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "style:'currency'" not in content
    assert "currency:'BRL'" not in content
    assert "R$" not in content


def test_reconciliation_template_exposes_entry_and_exit_tags_for_bank_and_system_rows():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "function movementNatureBadge(movementNature)" in content
    assert "badge('Entrada', 'info')" in content
    assert "badge('Saída', 'danger')" in content
    assert "${movementNatureBadge(row.movement_nature)}" in content
    assert "${movementNatureBadge(item.movement_nature)}" in content
    assert content.count("${movementNatureBadge(item.movement_nature)}") >= 2


def test_reconciliation_template_submits_amount_and_movement_filters_to_workspace_api():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "amountFilter" in content
    assert "movementNatureFilter" in content
    assert "amount: state.amountFilter || null" in content
    assert "movement_nature: state.movementNatureFilter || null" in content
    assert "formatCurrencyInputValue" in content
