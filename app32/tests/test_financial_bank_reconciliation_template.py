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
    assert "function resolveCompanyId()" in template
    assert "window.companyId" in template
    assert "function companyQuery" in template
    assert "renderAccountsError" in template
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
