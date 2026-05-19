from pathlib import Path


def test_schedule_templates_use_titulo_financeiro_copy():
    schedule_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")
    list_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules_list.html").read_text(encoding="utf-8")

    assert "Títulos Financeiros" in schedule_template
    assert "Novo Título Financeiro" in schedule_template
    assert "Títulos Financeiros" in list_template
    assert "Criar título a pagar" in list_template


def test_schedule_javascript_uses_titulo_financeiro_copy():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")
    list_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules_list.js").read_text(encoding="utf-8")

    assert "A interface de títulos financeiros está desatualizada" in schedule_js
    assert "Informe o histórico do título financeiro." in schedule_js
    assert "Falha ao carregar títulos financeiros." in list_js
    assert "Deseja realmente excluir este título financeiro?" in list_js


def test_settlement_delete_button_is_bound_to_baixas_list():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "data-settlement-delete" in schedule_js
    assert "data-direct-entry-delete" in schedule_js
    assert "const baixasListEl = $('baixas-list');" in schedule_js
    assert "baixasListEl.addEventListener('click'" in schedule_js


def test_direct_entry_schedule_uses_whole_delete_copy():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "Excluir lançamento rápido" in schedule_js
    assert "remove o título e a baixa juntos" in schedule_js


def test_settlement_delete_button_is_not_disabled_by_title_lock():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "field.matches?.('[data-settlement-delete]')" in schedule_js
    assert "button[data-settlement-delete]" in schedule_js
    assert "button.disabled = false" in schedule_js


def test_schedule_allocation_excludes_financial_adjustments_from_rateio():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "updateAdjustmentAllocationRow('correction'" not in schedule_js
    assert "updateAdjustmentAllocationRow('discount'" not in schedule_js
    assert "allocationRows = getBaseAllocationRows().map((row) => createAllocationRow({" in schedule_js
    assert "const totalAmount = getTopAmount();" in schedule_js
    assert "const totalAllocated = round2(getBaseAllocationRows().reduce" in schedule_js
    assert "valor principal do título financeiro" in schedule_js
    assert "allocations: getBaseAllocationRows().map((row) => ({" in schedule_js
    assert "metadata_json: {}" in schedule_js


def test_schedule_recurrence_competence_mode_field_is_available():
    schedule_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "field-competence-mode" in schedule_template
    assert "Mesma data de competência do título base" in schedule_template
    assert "Competência conforme vencimento de cada título" in schedule_template
    assert "normalizeCompetenceMode" in schedule_js
    assert "competence_mode: frequency === 'one_time' ? 'same_competence' : competenceMode" in schedule_js


def test_schedule_rateio_search_field_selects_current_label_before_new_search():
    schedule_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")

    assert "const selectedLabel = select?.value"[:28] in schedule_js
    assert "selectedSearchableItemLabel(container?.dataset.field, select.value)" in schedule_js
    assert "event.target.select();" in schedule_js
