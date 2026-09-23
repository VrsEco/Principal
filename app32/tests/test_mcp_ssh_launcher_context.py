"""Inspeciona somente a construção do comando; o trecho SSH nunca é executado."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/start_mcp_prod_ssh.ps1'


@pytest.mark.parametrize('surface', ['user', 'admin', 'analytics'])
@pytest.mark.parametrize('company', ['', '9'])
def test_ssh_context_is_exported_and_shell_quoted(tmp_path, surface, company):
    shell = shutil.which('powershell.exe') or shutil.which('pwsh')
    if not shell:
        pytest.skip('PowerShell necessário para testar o launcher Windows')
    source = SCRIPT.read_text(encoding='utf-8-sig')
    assert source.count('$sshExe = "C:\\Windows') == 1
    prefix = source.split('$sshExe = "C:\\Windows', 1)[0]
    probe = tmp_path / 'probe.ps1'
    probe.write_text(prefix + '\nWrite-Output $remoteCommand\n', encoding='utf-8-sig')
    env = {k: v for k, v in os.environ.items() if not k.startswith('APP32_MCP_')}
    env.update(APP32_MCP_USER_ID='17', APP32_MCP_COMPANY_ID=company,
               APP32_MCP_FALLBACK_ROLE="client'; echo SHOULD_NOT_RUN; '",
               APP32_MCP_PROD_APP_DIR="/tmp/app's folder",
               APP32_MCP_PROD_PYTHON='/tmp/python path/python')
    result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command',
                             '& { ' + prefix + '\nWrite-Output $remoteCommand\n} -Surface ' + surface], env=env, capture_output=True,
                            text=True, check=True, timeout=20)
    args = shlex.split(result.stdout.strip())
    assert args[:4] == ['cd', "/tmp/app's folder", '&&', 'env']
    assert f'APP32_MCP_SURFACE={surface}' in args
    assert 'APP32_MCP_USER_ID=17' in args
    assert "APP32_MCP_FALLBACK_ROLE=client'; echo SHOULD_NOT_RUN; '" in args
    assert 'PYTHONUNBUFFERED=1' in args
    assert ('APP32_MCP_COMPANY_ID=9' in args) == bool(company)
    assert args[-3:-1] == ['/tmp/python path/python', '-c']
    assert 'runpy.run_path' in args[-1]
