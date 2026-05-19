from pathlib import Path


def test_direct_entry_rateio_uses_searchable_selects():
    content = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_entry_direct.js").read_text(encoding="utf-8")

    assert "renderSearchableSelect('chart_account_id'" in content
    assert "renderSearchableSelect('cost_center_id'" in content
    assert "renderSearchableSelect('domain_value'" in content
    assert "event.target.select();" in content


def test_automation_center_has_search_inputs_for_financial_dimensions():
    template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\automation_center.html").read_text(encoding="utf-8")
    script = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_automation_center.js").read_text(encoding="utf-8")

    assert 'data-select-filter-target="fa-review-chart-account"' in template
    assert 'data-select-filter-target="fa-review-cost-center"' in template
    assert 'data-select-filter-target="fa-review-domain-link"' in template
    assert "filterSelectOptions(targetId, '')" in script


def test_report_sidebars_have_search_inputs_for_financial_dimensions():
    ledger = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_ledger_sidebar.html").read_text(encoding="utf-8")
    cash_flow = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_cash_flow_sidebar.html").read_text(encoding="utf-8")
    workspace_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_report_workspace.js").read_text(encoding="utf-8")

    assert 'data-select-filter-target="ledger-chart-accounts"' in ledger
    assert 'data-select-filter-target="ledger-cost-centers"' in ledger
    assert 'data-select-filter-target="ledger-projects"' in ledger
    assert 'data-select-filter-target="ledger-processes"' in ledger
    assert 'data-select-filter-target="cash-flow-chart-accounts"' in cash_flow
    assert 'data-select-filter-target="cash-flow-cost-centers"' in cash_flow
    assert 'data-select-filter-target="cash-flow-projects"' in cash_flow
    assert 'data-select-filter-target="cash-flow-processes"' in cash_flow
    assert 'data-select-filter-target="cash-flow-title-chart"' in cash_flow
    assert 'data-select-filter-target="cash-flow-title-center"' in cash_flow
    assert "form.querySelectorAll('[data-select-filter-target]')" in workspace_js


def test_budget_forms_filter_chart_accounts_and_cost_centers():
    workspace = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\budget_workspace.html").read_text(encoding="utf-8")
    matrix = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\budget_matrix.html").read_text(encoding="utf-8")

    assert 'data-select-filter-target="line-chart-account"' in workspace
    assert 'data-select-filter-target="line-cost-center"' in workspace
    assert "analyticChartAccounts()" in workspace
    assert "analyticCostCenters()" in workspace
    assert 'data-select-filter-target="line-chart-account"' in matrix
    assert 'data-select-filter-target="line-cost-center"' in matrix
    assert "const analyticChartAccounts = (options.chart_accounts || []).filter" in matrix
    assert "const analyticCostCenters = (options.cost_centers || []).filter" in matrix


def test_backend_enforces_analytic_catalogs_and_enabled_domains():
    catalog_service = Path(r"C:\GestaoVersus\app32\app32\services\financial_catalog_service.py").read_text(encoding="utf-8")
    automation_service = Path(r"C:\GestaoVersus\app32\app32\services\financial_automation_service.py").read_text(encoding="utf-8")
    report_service = Path(r"C:\GestaoVersus\app32\app32\services\financial_report_service.py").read_text(encoding="utf-8")

    assert "Selecione uma conta analítica do plano de contas." in catalog_service
    assert "Selecione um centro de resultado analítico." in catalog_service
    assert "_analytic_chart_accounts()" in automation_service
    assert "_analytic_cost_centers()" in automation_service
    assert "não está habilitado no Financeiro" in automation_service
    assert "_flat_list_from_enabled(Project, enabled_project_ids)" in report_service
    assert "_flat_list_from_enabled(Process, enabled_process_ids)" in report_service


def test_served_financial_static_assets_match_app32_versions():
    mirrored_assets = [
        ("financial_schedules.js", "js"),
        ("financial_entry_direct.js", "js"),
        ("financial_automation_center.js", "js"),
        ("financial_report_workspace.js", "js"),
    ]

    for filename, folder in mirrored_assets:
        app32_asset = Path(fr"C:\GestaoVersus\app32\app32\static\{folder}\{filename}").read_text(encoding="utf-8")
        served_asset = Path(fr"C:\GestaoVersus\app32\static\{folder}\{filename}").read_text(encoding="utf-8")
        assert served_asset == app32_asset, f"Asset servido divergente: {filename}"
