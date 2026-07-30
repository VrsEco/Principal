from pathlib import Path


def _resolve_sapiens_template_path() -> Path:
    current = Path(__file__).resolve()
    workspace_template = current.parents[1] / "templates" / "sapiens.html"
    if workspace_template.exists():
        return workspace_template

    legacy_template = current.parents[2] / "templates" / "sapiens.html"
    if legacy_template.exists():
        return legacy_template

    raise FileNotFoundError("Template do Sapiens não encontrado no workspace esperado.")


def test_sapiens_template_contains_workflow_catalog_panel():
    template = _resolve_sapiens_template_path().read_text(encoding="utf-8")

    assert 'workflowCatalogPanel' in template
    assert 'Catálogo Operacional de Fluxos' in template
    assert 'opsViewCatalog' in template
    assert 'panel-mode' in template
    assert 'sapiensChatArea' in template
    assert 'workflow-catalog-link' in template
    assert 'compact-meta workflow-card-meta' in template


def test_sapiens_page_initializes_even_after_dom_content_loaded():
    template = _resolve_sapiens_template_path().read_text(encoding="utf-8")

    assert "function initializeSapiensPage()" in template
    assert "if (document.readyState === 'loading')" in template
    assert (
        "document.addEventListener('DOMContentLoaded', initializeSapiensPage, { once: true })"
        in template
    )
    assert "initializeSapiensPage();" in template
