from pathlib import Path


def test_ai_monitoring_ui_declares_expected_contracts():
    template = Path('templates/modules/operations/ai_config_simple_page.html').read_text(encoding='utf-8')
    script = Path('static/js/ai_monitoring_page.js').read_text(encoding='utf-8')
    css = Path('static/css/ai_monitoring_page.css').read_text(encoding='utf-8')

    assert 'data-monitoring-page="true"' in template
    assert 'id="aiMonitoringSummaryGrid"' in template
    assert 'id="aiMonitoringEvents"' in template
    assert 'id="aiMonitoringRequestList"' in template
    assert 'id="aiMonitoringOpenRequest"' in template
    assert '/api/ai-monitoring/panel' in script or 'panelEndpoint' in script
    assert 'aiMonitoringRequestForm' in script
    assert 'aiMonitoringExportPdf' in script
    assert '.ai-monitoring-shell' in css
    assert '.ai-monitoring-summary-grid' in css
    assert '.ai-monitoring-panel' in css
