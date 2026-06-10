from pathlib import Path
import re
import shutil
import subprocess

import pytest


TEMPLATE_PATH = Path(
    r"C:\GestaoVersus\app32\app32\templates\modules\financial\bank_reconciliation.html"
)


def test_bank_reconciliation_template_contains_three_column_workspace():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "Upload de Arquivos - OFX, CSV, etc" in template
    assert "Upload de Arquivos - OFX, XLS, XLSX e CSV" not in template
    assert "Upload prático do extrato" not in template
    assert "O fluxo aceita arquivos OFX, XLS, XLSX e CSV" not in template
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
    assert "function resolveCompanyId()" in template
    assert "window.companyId" in template
    assert "function companyQuery" in template
    assert "renderAccountsError" in template
    assert 'id="recon-hero-panel"' in template
    assert 'aria-controls="recon-hero-panel-body"' in template
    assert 'class="recon-top-grid"' in template
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in template
    assert ".recon-top-card.panel--collapsed .panel-header{min-height:62px}" in template
    assert ".recon-top-card h1,.recon-top-card h2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:.98rem" in template
    assert 'id="recon-page-title"' in template
    assert "`Conciliação Bancária — ${selected.bank_account.name}`" in template
    assert "Gestão Financeira · Conciliação operacional" not in template
    assert "Importe OFX, XLS, XLSX ou CSV" not in template
    assert "Importar novo extrato" not in template
    assert 'class="recon-overview-grid recon-overview-grid--hero"' in template
    assert "handlePanelToggleClick(event, 'recon-hero-panel')" in template
    assert 'id="workspace-overview-panel"' not in template
    assert 'id="workspace-title"' not in template
    assert 'class="panel workspace-board-panel"' in template
    assert "margin:.85rem 1rem;border:1px solid var(--border);border-radius:14px;background:var(--surface-secondary)" in template
    assert "Operação assistida" not in template
    assert 'id="workspace-subtitle"' not in template
    assert "Nenhum lote vinculado a esta conta." not in template
    assert "handlePanelToggleClick(event, 'workspace-panel')" not in template
    assert "Indicadores operacionais" not in template
    assert "Resumo do lote e da conciliação" not in template
    assert 'class="summary-grid summary-grid--compact"' in template
    assert "function handleSystemRowCardClick(entryId, event)" in template
    assert 'onclick="handleSystemRowCardClick(${item.id}, event)"' in template
    assert 'onclick="event.stopPropagation(); toggleEntrySelection(${item.id})"' in template
    assert "? 'Remover' : 'Selecionar'" in template
    assert 'id="bank-date-from"' in template
    assert 'id="bank-date-to"' in template
    assert 'id="settlement-date-from"' in template
    assert 'id="settlement-date-to"' in template
    assert "Data inicial do extrato" in template
    assert "Data inicial da baixa" in template
    assert "company_id=${companyId}" not in template
    assert "?? remaining ||" not in template


def test_bank_reconciliation_upload_has_guided_submit_flow():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert '<form id="upload-form" class="upload-grid" novalidate>' in template
    assert 'id="upload-batch-code"' in template
    assert 'id="upload-file"' in template
    assert 'id="upload-status"' in template
    assert 'id="upload-submit-button"' in template
    assert "function generateBatchCode()" in template
    assert "function detectSourceFromFileName" in template
    assert "<small>Linhas vindas do extrato selecionado.</small>" not in template
    assert "<small>Itens ainda sem vínculo confirmado.</small>" not in template
    assert "function showUploadStatus" in template
    assert "setUploadBusy(true)" in template
    assert "catch(error)" in template
    assert "Selecione uma conta bancária antes de enviar o extrato." in template
    assert "Selecione um arquivo OFX, XLS, XLSX ou CSV" in template


def test_bank_reconciliation_inline_script_has_valid_javascript_syntax(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js indisponível para validar sintaxe do script inline")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", template, flags=re.S)
    assert scripts

    script_file = tmp_path / "bank_reconciliation_inline.js"
    script_file.write_text("\n".join(scripts), encoding="utf-8")

    result = subprocess.run(
        ["node", "--check", str(script_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
