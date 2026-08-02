from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sapiens_exposes_feature_flagged_strategic_tree_scope():
    template = (ROOT / "templates" / "sapiens.html").read_text(encoding="utf-8")

    assert "{% if strategic_tree_enabled %}" in template
    assert 'data-scope="strategic_tree"' in template
    assert 'id="strategicTreeWorkspace"' in template
    assert 'id="strategicTreeNav"' in template
    assert 'id="strategicTreeComposer"' in template
    assert 'data-strategic-tree-csrf=' in template
    assert "strategic_tree.js" in template
    assert "strategic_tree.css" in template


def test_strategic_tree_client_is_tenant_implicit_safe_and_uses_csrf():
    script = (ROOT / "static" / "js" / "strategic_tree.js").read_text(encoding="utf-8")

    assert "/api/knowledge/strategic-trees" in script
    assert "company_id" not in script
    assert "X-CSRF-Token" in script
    assert "Idempotency-Key" in script
    assert "textContent" in script
    assert "innerHTML" not in script


def test_strategic_tree_layout_has_mobile_contract():
    style = (ROOT / "static" / "css" / "strategic_tree.css").read_text(encoding="utf-8")

    assert "grid-template-columns: 280px minmax(0, 1fr)" in style
    assert "@media (max-width: 680px)" in style
    assert ".st-tree-nav { display: flex" in style
    assert ".st-composer" in style


def test_sapiens_dispatches_scope_change_when_scope_is_selected():
    script = (ROOT / "static" / "js" / "sapiens_knowledge.js").read_text(encoding="utf-8")
    event = "root.dispatchEvent(new CustomEvent('sapiens:scope-change'"

    assert script.count(event) == 1
    assert script.index(event) < script.index("function resizeQuestion")
