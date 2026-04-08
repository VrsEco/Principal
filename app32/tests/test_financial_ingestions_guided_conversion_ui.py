from pathlib import Path


def test_financial_ingestions_template_contains_guided_conversion_section():
    template = Path(r"C:\GestaoVersus\app32\templates\modules\financial\ingestions.html").read_text(encoding="utf-8")

    assert "Conversão guiada" in template
    assert "Salvar + converter" in template
    assert 'id="guided-target-type"' in template
    assert 'id="guided-domain"' in template


def test_financial_ingestions_js_supports_persist_and_convert_guided_flow():
    script = Path(r"C:\GestaoVersus\app32\static\js\financial_ingestions.js").read_text(encoding="utf-8")

    assert "persistGuidedChanges" in script
    assert "/api/financial/schedules/options" in script
    assert "guided.targetType" in script
    assert "window.convertIngestion" in script
