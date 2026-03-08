from pathlib import Path


def test_sapiens_template_contains_workflow_catalog_panel():
    template = Path(r"C:\GestaoVersus\app32\templates\sapiens.html").read_text(encoding="utf-8")

    assert 'workflowCatalogPanel' in template
    assert 'Catálogo Operacional de Fluxos' in template
    assert 'opsViewCatalog' in template
    assert 'panel-mode' in template
    assert 'sapiensChatArea' in template
    assert 'workflow-catalog-link' in template
    assert 'compact-meta workflow-card-meta' in template
