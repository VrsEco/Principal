from pathlib import Path


def test_financial_schedules_list_filters_are_persistent_and_tenant_scoped():
    source = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules_list.js").read_text(encoding="utf-8")

    assert "financial_schedules:list_filters:v1" in source
    assert "company:${companyId || 'none'}" in source
    assert "window.localStorage.setItem(storageKey" in source
    assert "window.localStorage.getItem(storageKey" in source
    assert "window.localStorage.removeItem(storageKey" in source
    assert "restoreFiltersState();" in source


def test_financial_schedules_list_js_cache_buster_was_updated():
    source = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules_list.html").read_text(encoding="utf-8")

    assert "financial_schedules_list.js', v='20260612a'" in source
