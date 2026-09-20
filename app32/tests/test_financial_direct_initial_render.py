"""Isolated rendering contracts: no app/database or financial writes."""
from pathlib import Path
import re
import pytest
from jinja2 import Environment, DictLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('requested,expected', [('receivable','receivable'),('payable','payable'),('','payable'),('invalid','payable')])
def test_initial_type_is_correct_without_javascript(requested, expected):
    source = (ROOT / 'templates/modules/financial/entry_direct.html').read_text(encoding='utf-8')
    env = Environment(loader=DictLoader({
        'entry.html': source,
        'layouts/workspace.html': '<head>{% block head %}{% endblock %}</head><body>{% block workspace_content %}{% endblock %}</body>',
    }), autoescape=select_autoescape())
    html = env.get_template('entry.html').render(
        initial_entry_type=requested, company_id=9,
        url_for=lambda endpoint, filename, **kwargs: '/static/' + filename + '?v=test',
        static_asset_version=lambda filename: 'test',
    )
    assert f'name="entry_type" value="{expected}"' in html
    assert f'data-entry-type="{expected}" data-initial-entry-type=' in html
    assert f'class="type-chip active" data-entry-type="{expected}"' in html
    banner = re.search(r'id="direct-entry-banner"[^>]*>(.*?)</div>', html).group(1)
    assert ('Conta a receber' if expected == 'receivable' else 'Conta a pagar') in banner
    head, body = html.split('</head>', 1)
    assert 'financial_entry_direct.css' in head
    assert 'financial_entry_direct.css' not in body
    assert 'financial_entry_direct.js?v=test' in body


def test_type_initializes_before_options_and_is_not_reset_after_loading():
    source = (ROOT / 'static/js/financial_entry_direct.js').read_text(encoding='utf-8')
    init = source.split("document.addEventListener('DOMContentLoaded', async () => {", 1)[1]
    before, after = init.split('await loadOptions();', 1)
    assert 'window.setDirectEntryType(lockedEntryType)' in before
    assert "window.setDirectEntryType('payable')" in before
    assert 'setDirectEntryType' not in after
    assert "if (lockedEntryType && entryType !== lockedEntryType) return;" in source
    # Suggestions still use options AFTER loading, preserving the financial default.
    assert "suggestDefaultCorrectionIndex(form.querySelector('input[name=\"entry_type\"]').value || lockedEntryType || 'payable', { force: true });" in source

@pytest.mark.parametrize('requested', ['receivable', 'payable'])
def test_real_layout_renders_without_database(requested):
    import importlib.util
    spec = importlib.util.spec_from_file_location('direct_harness', ROOT / 'scripts/qa/direct_entry_browser_harness.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = module.app.test_client()
    response = client.get('/?entry_type=' + requested)
    assert response.status_code == 200
    asset = client.get('/static/js/date_utils.js')
    assert asset.status_code == 200
    assert b'App32DateUtils' in asset.data
    html = response.get_data(as_text=True)
    assert 'layout-workspace' in html
    assert f'data-entry-type="{requested}"' in html
    assert 'financial_entry_direct.css' in html.split('</head>')[0]
    assert client.post('/api/financial/entries/direct', json={}).status_code == 404
