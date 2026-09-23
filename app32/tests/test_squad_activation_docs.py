from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['codex-squad-engenharia', 'claude-squad-cliente', 'antigravity-squad-versus']

@pytest.mark.parametrize('name', NAMES)
def test_standard_prompt_preserves_guards_and_lab_separation(name):
    text = (ROOT / '.ai' / (name + '.md')).read_text(encoding='utf-8')
    for term in ['company_id', 'RBAC', 'MCP', 'Sem autorização explícita', 'AA.J.16']:
        assert term in text
    assert 'company_id=10' not in text
    lab = (ROOT / '.ai' / (name + '-laboratorio.md')).read_text(encoding='utf-8')
    assert 'Escopo restrito' in lab
    assert name + '.md' in lab

@pytest.mark.parametrize('name', NAMES[1:])
def test_client_prompts_do_not_equate_activation_with_authentication(name):
    text = (ROOT / '.ai' / (name + '.md')).read_text(encoding='utf-8')
    assert 'não autentica nem instala' in text
    assert 'mcp-versus' in text
    assert 'Não exija instalar o código APP32' in text
