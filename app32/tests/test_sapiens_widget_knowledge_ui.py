from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_global_sapiens_widget_uses_same_knowledge_endpoint_as_full_page():
    template = (ROOT / "templates" / "components" / "sapiens_widget.html").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "static" / "js" / "sapiens_widget.js").read_text(
        encoding="utf-8"
    )

    assert 'data-sapiens-scope="all"' in template
    assert 'data-sapiens-scope="company"' in template
    assert 'data-sapiens-scope="product"' in template
    assert 'href="/sapiens"' in template
    assert "/api/agents/knowledge/answer" in script
    assert "/api/agents/knowledge/feedback" in script
    assert "/api/agents/chat" in script
    assert "knowledge_gap" in script
    assert "company_id" not in script
    assert "interaction_id" in script


def test_global_widget_renders_structured_answer_and_safe_internal_actions():
    script = (ROOT / "static" / "js" / "sapiens_widget.js").read_text(
        encoding="utf-8"
    )

    assert "appendStructured" in script
    assert "appendFeedback" in script
    assert "Certo" in script
    assert "Parcial" in script
    assert "Errado" in script
    assert "document.createTextNode" in script
    assert "safeTarget" in script
    assert "target.startsWith('/')" in script
    assert "innerHTML" not in script


def test_global_widget_has_accessible_launcher_and_dialog_controls():
    template = (ROOT / "templates" / "components" / "sapiens_widget.html").read_text(
        encoding="utf-8"
    )

    assert 'aria-controls="sapiens-widget-panel"' in template
    assert 'aria-expanded="false"' in template
    assert 'aria-label="Fechar Sapiens"' in template
    assert 'aria-live="polite"' in template


def test_global_widget_is_included_in_base_layouts_and_portal():
    classic_base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    modern_base = (ROOT / "templates" / "layouts" / "base.html").read_text(
        encoding="utf-8"
    )
    portal = (ROOT / "templates" / "auth" / "portal.html").read_text(
        encoding="utf-8"
    )

    include = "{% include 'components/sapiens_widget.html' %}"
    assert include in classic_base
    assert include in modern_base
    assert include in portal
