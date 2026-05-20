from pathlib import Path


TEMPLATE_PATH = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\bank_reconciliation.html")


def test_reconciliation_template_exposes_filter_sidebar_and_apply_action():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert 'openFilterDrawer()' in content
    assert 'id="recon-filter-drawer"' in content
    assert 'Atualizar' in content
    assert 'workspace-bank-account' in content
    assert 'batch-select' in content
    assert 'Abrir filtros' not in content


def test_reconciliation_template_uses_requested_workbench_card_order():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    order = [
        "Registros bancários selecionados",
        "Baixa de título em aberto",
        "Criar título e baixar",
        "Conciliação em conjunto",
        "Sugestões automáticas da linha em foco",
    ]

    positions = [content.index(label) for label in order]
    assert positions == sorted(positions)
