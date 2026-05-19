(function () {
  const page = document.querySelector('.direct-entry-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const form = document.getElementById('direct-entry-form');
  const body = document.getElementById('direct-allocations-body');
  const banner = document.getElementById('direct-entry-banner');
  const rateioSummary = document.getElementById('direct-rateio-summary');
  const entryTypeSwitch = document.getElementById('direct-entry-type-switch');
  let optionsCache = {
    counterparties: [],
    bank_accounts: [],
    chart_accounts: [],
    cost_centers: [],
    correction_indexes: [],
    discount_rules: [],
    enabled_domains: [],
    default_suggestions: {},
    budget_versions: [],
    budget_lines: [],
    budget_contracts: [],
    budget_documents: [],
  };
  let allocationRows = [];

  const $ = (id) => document.getElementById(id);

  const formatCurrencyFromDigits = (value) => {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return '';
    const cents = digits.padStart(3, '0');
    const intPart = cents.slice(0, -2).replace(/^0+/, '') || '0';
    return `${intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents.slice(-2)}`;
  };

  const parseCurrency = (value) => {
    const normalized = String(value || '').replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, '');
    return normalized ? Number(normalized) : 0;
  };

  const parseDecimal = (value) => {
    const normalized = String(value ?? '').trim().replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, '');
    return normalized ? Number(normalized) : 0;
  };

  const formatPercent = (value) => {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric)) return '';
    return numeric.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
  };

  const round2 = (value) => Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100;
  const round4 = (value) => Math.round((Number(value || 0) + Number.EPSILON) * 10000) / 10000;
  const todayDisplay = () => new Date().toLocaleDateString('pt-BR');

  const normalizeDateInput = (value) => {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
  };

  const parseDateToIso = (value) => {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits.length !== 8) return null;
    return `${digits.slice(4)}-${digits.slice(2, 4)}-${digits.slice(0, 2)}`;
  };

  const analyticChartAccounts = () => (optionsCache.chart_accounts || []).filter((item) => !!item.accepts_posting);
  const finalCostCenters = () => {
    const parentIds = new Set((optionsCache.cost_centers || []).filter((item) => item.parent_id).map((item) => Number(item.parent_id)));
    return (optionsCache.cost_centers || []).filter((item) => !parentIds.has(Number(item.id)));
  };

  function updateEntryTypePresentation(entryType) {
    page.dataset.entryType = entryType;
    if (!banner) return;
    const receivable = entryType === 'receivable';
    banner.textContent = receivable
      ? 'Conta a receber · preenchimento orientado para recebimentos imediatos.'
      : 'Conta a pagar · preenchimento orientado para pagamentos imediatos.';
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Falha na operação financeira.');
    return result;
  }

  const buildOptions = (items, placeholder, formatter) => [`<option value="">${placeholder}</option>`]
    .concat((items || []).map((item) => `<option value="${item.id}">${formatter ? formatter(item) : (item.display_label || item.name || item.code || item.id)}</option>`))
    .join('');

  const buildDomainOptions = (value) => {
    const groups = ['project', 'process'].map((domainType) => {
      const options = optionsCache.enabled_domains
        .filter((item) => item.domain_type === domainType)
        .map((item) => {
          const optionValue = item.domain_value || `${item.source_kind || 'routine'}:${domainType}:${item.source_id}`;
          return `<option value="${optionValue}" ${value === optionValue ? 'selected' : ''}>${item.display_label}</option>`;
        }).join('');
      return options ? `<optgroup label="${domainType === 'project' ? 'Projetos' : 'Processos'}">${options}</optgroup>` : '';
    }).join('');
    return `<option value="">Selecione...</option>${groups}`;
  };

  const buildChartAccountLabel = (item) => item.code ? `${item.code} - ${item.name}` : (item.name || item.id);
  const buildCostCenterLabel = (item) => item.code ? `${item.code} - ${item.name}` : (item.name || item.id);
  const buildBudgetLabel = (item) => {
    const code = item.code || '';
    const name = item.name || '';
    return code && name ? `${code} - ${name}` : (code || name || item.id);
  };
  const normalizeSearchTerm = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
  const cloneAllocationRows = () => allocationRows.map((row) => ({ ...row }));
  const defaultSuggestions = () => optionsCache.default_suggestions || {};
  const asOptionValue = (value) => (value == null || value === '' ? '' : String(value));
  const getDefaultCorrectionIndexIdByEntryType = (entryType) => {
    const suggestions = defaultSuggestions();
    if (entryType === 'receivable') return asOptionValue(suggestions.receivable_correction_index_id || '');
    if (entryType === 'payable') return asOptionValue(suggestions.payable_correction_index_id || '');
    return '';
  };
  const lockedEntryType = ['payable', 'receivable'].includes(String(page.dataset.initialEntryType || '').trim().toLowerCase())
    ? String(page.dataset.initialEntryType || '').trim().toLowerCase()
    : '';

  function suggestDefaultCorrectionIndex(entryType, { force = false } = {}) {
    const field = $('direct-correction-index');
    if (!field) return;
    if (!force && field.value) return;
    field.value = getDefaultCorrectionIndexIdByEntryType(entryType);
  }

  function getTopAmount() {
    return round2(parseCurrency($('direct-amount').value));
  }

  function recalculateRowFromPercentage(index) {
    const total = getTopAmount();
    const row = allocationRows[index];
    const percentage = round4(parseDecimal(row.percentage));
    row.percentage = percentage ? formatPercent(percentage) : '';
    const allocated = total > 0 ? round2(total * percentage / 100) : 0;
    row.allocated_amount = allocated;
    row.allocated_amount_display = allocated ? allocated.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '';
  }

  function recalculateRowFromAmount(index) {
    const total = getTopAmount();
    const row = allocationRows[index];
    const allocated = round2(parseCurrency(row.allocated_amount_display));
    row.allocated_amount = allocated;
    const percentage = total > 0 ? round4((allocated / total) * 100) : 0;
    row.percentage = percentage ? formatPercent(percentage) : '';
  }

  function recalculateAllRowsFromPercentages() {
    allocationRows.forEach((_, index) => recalculateRowFromPercentage(index));
  }

  function summarizeAllocations() {
    const totalAmount = getTopAmount();
    const totalPercentage = round4(allocationRows.reduce((acc, row) => acc + parseDecimal(row.percentage), 0));
    const totalAllocated = round2(allocationRows.reduce((acc, row) => acc + round2(row.allocated_amount), 0));
    const remainingPercentage = round4(100 - totalPercentage);
    const remainingValue = round2(totalAmount - totalAllocated);
    const percentagesOk = Math.abs(totalPercentage - 100) <= 0.01;
    const valuesOk = Math.abs(totalAllocated - totalAmount) <= 0.01;
    return { totalAmount, totalPercentage, totalAllocated, remainingPercentage, remainingValue, percentagesOk, valuesOk };
  }

  function renderAllocationSummary() {
    const summary = summarizeAllocations();
    rateioSummary.innerHTML = [
      `<span class="rateio-pill ${summary.percentagesOk ? 'is-ok' : 'is-error'}">Percentual total: ${formatPercent(summary.totalPercentage)}%</span>`,
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Valor total do rateio: ${summary.totalAllocated.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>`,
      `<span class="rateio-pill ${summary.percentagesOk ? 'is-ok' : 'is-error'}">Faltante percentual: ${formatPercent(summary.remainingPercentage)}%</span>`,
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Faltante valor: ${summary.remainingValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>`
    ].join('');
    return summary;
  }

  function ensureRemainingRow(indexChanged) {
    if (indexChanged !== allocationRows.length - 1) return false;
    const summary = summarizeAllocations();
    if (summary.remainingPercentage <= 0.01 || summary.remainingPercentage >= 100) return false;
    allocationRows.push({
      chart_account_id: '',
      cost_center_id: '',
      domain_source_kind: 'routine',
      domain_type: null,
      domain_source_id: null,
      domain_label: null,
      domain_value: '',
      percentage: formatPercent(summary.remainingPercentage),
      allocated_amount: round2(summary.remainingValue),
      allocated_amount_display: summary.remainingValue ? summary.remainingValue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '',
    });
    return true;
  }

  function syncAllocationRowInputs(index) {
    const percentageInput = body.querySelector(`input[data-field="percentage"][data-index="${index}"]`);
    const amountInput = body.querySelector(`input[data-field="allocated_amount_display"][data-index="${index}"]`);
    if (percentageInput) percentageInput.value = allocationRows[index].percentage || '';
    if (amountInput) amountInput.value = allocationRows[index].allocated_amount_display || '';
    renderAllocationSummary();
  }

  function createAllocationRow(defaults = {}) {
    const suggestions = defaultSuggestions();
    const domainSourceKind = defaults.domain_source_kind || suggestions.domain_source_kind || 'routine';
    const domainType = defaults.domain_type || suggestions.domain_type || null;
    const domainSourceId = defaults.domain_source_id || suggestions.domain_source_id || null;
    return {
      chart_account_id: defaults.chart_account_id || '',
      cost_center_id: asOptionValue(defaults.cost_center_id || suggestions.cost_center_id || ''),
      budget_version_id: asOptionValue(defaults.budget_version_id || suggestions.budget_version_id || ''),
      budget_line_id: asOptionValue(defaults.budget_line_id || suggestions.budget_line_id || ''),
      budget_contract_id: asOptionValue(defaults.budget_contract_id || suggestions.budget_contract_id || ''),
      budget_document_id: asOptionValue(defaults.budget_document_id || suggestions.budget_document_id || ''),
      domain_source_kind: domainSourceKind,
      domain_type: domainType,
      domain_source_id: domainSourceId,
      domain_label: defaults.domain_label || suggestions.domain_label || null,
      domain_value: domainType && domainSourceId ? `${domainSourceKind}:${domainType}:${domainSourceId}` : '',
      percentage: defaults.percentage ?? '100',
      allocated_amount: defaults.allocated_amount ?? null,
      allocated_amount_display: defaults.allocated_amount_display || '',
    };
  }

  function applyCounterpartyDefaults(counterpartyId, { force = false } = {}) {
    const selectedId = Number(counterpartyId || 0);
    if (!selectedId || allocationRows.length !== 1) return;
    const counterparty = (optionsCache.counterparties || []).find((item) => Number(item.id) === selectedId);
    if (!counterparty) return;

    const row = allocationRows[0];
    let changed = false;
    if ((force || !row.chart_account_id) && counterparty.default_chart_account_id) {
      row.chart_account_id = String(counterparty.default_chart_account_id);
      changed = true;
    }
    if ((force || !row.cost_center_id) && counterparty.default_cost_center_id) {
      row.cost_center_id = String(counterparty.default_cost_center_id);
      changed = true;
    }
    if (changed) renderAllocations();
  }

  function buildSearchableSelectItems(field) {
    if (field === 'chart_account_id') {
      return analyticChartAccounts().map((item) => ({
        value: asOptionValue(item.id),
        label: buildChartAccountLabel(item),
        search: normalizeSearchTerm([item.code, item.name, item.display_label, item.id].filter(Boolean).join(' ')),
      }));
    }
    if (field === 'cost_center_id') {
      return finalCostCenters().map((item) => ({
        value: asOptionValue(item.id),
        label: buildCostCenterLabel(item),
        search: normalizeSearchTerm([item.code, item.name, item.display_label, item.id].filter(Boolean).join(' ')),
      }));
    }
    if (field === 'domain_value') {
      return (optionsCache.enabled_domains || []).map((item) => {
        const value = item.domain_value || `${item.source_kind || 'routine'}:${item.domain_type}:${item.source_id}`;
        const group = item.domain_type === 'process' ? 'Processo' : 'Projeto';
        return {
          value,
          label: item.display_label || item.name || item.code || value,
          group,
          search: normalizeSearchTerm([
            item.display_label,
            item.name,
            item.code,
            item.domain_type,
            item.source_id,
            value,
          ].filter(Boolean).join(' ')),
        };
      });
    }
    return [];
  }

  function searchableSelectPlaceholder(field) {
    return ({
      chart_account_id: 'Selecione ou busque...',
      cost_center_id: 'Selecione ou busque...',
      domain_value: 'Selecione projeto ou processo...',
    }[field] || 'Selecione...');
  }

  function selectedSearchableItemLabel(field, value) {
    if (!value) return searchableSelectPlaceholder(field);
    const item = buildSearchableSelectItems(field).find((candidate) => candidate.value === String(value));
    return item?.label || searchableSelectPlaceholder(field);
  }

  function renderSearchableSelect(field, index, value) {
    const selectedLabel = selectedSearchableItemLabel(field, value);
    const placeholder = searchableSelectPlaceholder(field);
    return `
      <div class="search-select" data-search-select data-field="${field}" data-index="${index}">
        <select class="search-select__native" data-index="${index}" data-field="${field}" tabindex="-1" aria-hidden="true"></select>
        <input type="text" class="search-select__display" data-search-select-display value="${value ? selectedLabel : ''}" placeholder="${placeholder}" autocomplete="off" spellcheck="false" aria-autocomplete="list" aria-haspopup="listbox" aria-expanded="false">
        <div class="search-select__popover hidden" data-search-select-popover>
          <div class="search-select__options" data-search-select-options role="listbox" aria-label="${placeholder}"></div>
        </div>
      </div>`;
  }

  function closeSearchableSelect(container) {
    if (!container) return;
    container.classList.remove('is-open');
    container.querySelector('[data-search-select-display]')?.setAttribute('aria-expanded', 'false');
    container.querySelector('[data-search-select-popover]')?.classList.add('hidden');
  }

  function closeAllSearchableSelects(except = null) {
    body?.querySelectorAll('[data-search-select]').forEach((container) => {
      if (container !== except) closeSearchableSelect(container);
    });
  }

  function fillNativeSearchableSelect(select) {
    if (!select) return;
    const field = select.dataset.field;
    const currentValue = String(select.value || select.dataset.currentValue || '');
    const placeholder = searchableSelectPlaceholder(field);
    const items = buildSearchableSelectItems(field);
    select.innerHTML = [`<option value="">${placeholder}</option>`]
      .concat(items.map((item) => `<option value="${item.value}">${item.label}</option>`))
      .join('');
    select.value = currentValue;
  }

  function resolveSearchableItems(container) {
    const field = container?.dataset.field;
    const rawSearch = container?.querySelector('[data-search-select-display]')?.value || '';
    const search = normalizeSearchTerm(rawSearch);
    const currentValue = String(container?.querySelector('.search-select__native')?.value || '');
    const items = buildSearchableSelectItems(field)
      .filter((item) => !search || item.search.includes(search) || normalizeSearchTerm(item.label).includes(search))
      .slice(0, 12);
    return { rawSearch, currentValue, items };
  }

  function positionSearchablePopover(container) {
    if (!container) return;
    const input = container.querySelector('[data-search-select-display]');
    const popover = container.querySelector('[data-search-select-popover]');
    if (!input || !popover || popover.classList.contains('hidden')) return;
    const rect = input.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
    const estimatedHeight = Math.min(220, Math.max(120, popover.scrollHeight || 0));
    const spaceBelow = viewportHeight - rect.bottom;
    const spaceAbove = rect.top;
    const openAbove = spaceBelow < estimatedHeight && spaceAbove > spaceBelow;
    const top = openAbove
      ? Math.max(8, rect.top - estimatedHeight - 6)
      : Math.min(viewportHeight - estimatedHeight - 8, rect.bottom + 6);
    const maxWidth = Math.max(220, viewportWidth - rect.left - 12);
    popover.style.top = `${top}px`;
    popover.style.left = `${Math.max(8, rect.left)}px`;
    popover.style.width = `${Math.min(rect.width, maxWidth)}px`;
    popover.style.maxHeight = `${Math.min(220, openAbove ? Math.max(120, spaceAbove - 12) : Math.max(120, spaceBelow - 12))}px`;
  }

  function refreshSearchableSelectOptions(container) {
    if (!container) return;
    const { currentValue, items, rawSearch } = resolveSearchableItems(container);
    const host = container.querySelector('[data-search-select-options]');
    if (!host) return;
    if (!String(rawSearch || '').trim()) {
      host.innerHTML = '';
      closeSearchableSelect(container);
      return;
    }
    if (!items.length) {
      host.innerHTML = '<div class="search-select__empty">Nenhum item encontrado.</div>';
      container.classList.add('is-open');
      container.querySelector('[data-search-select-display]')?.setAttribute('aria-expanded', 'true');
      container.querySelector('[data-search-select-popover]')?.classList.remove('hidden');
      return;
    }
    host.innerHTML = items.map((item) => `
      <button type="button" class="search-select__option ${item.value === currentValue ? 'is-selected' : ''}" data-search-option-value="${item.value}" role="option" aria-selected="${item.value === currentValue ? 'true' : 'false'}">
        ${item.group ? `<span class="search-select__option-group">${item.group}</span>` : ''}
        <span>${item.label}</span>
      </button>`).join('');
    container.classList.add('is-open');
    container.querySelector('[data-search-select-display]')?.setAttribute('aria-expanded', 'true');
    container.querySelector('[data-search-select-popover]')?.classList.remove('hidden');
    positionSearchablePopover(container);
  }

  function syncSearchableSelectLabel(container) {
    if (!container) return;
    const field = container.dataset.field;
    const select = container.querySelector('.search-select__native');
    const input = container.querySelector('[data-search-select-display]');
    if (!input) return;
    input.value = select?.value ? selectedSearchableItemLabel(field, select.value) : '';
  }

  function applySearchableSelection(container, nextValue) {
    if (!container) return;
    const select = container.querySelector('.search-select__native');
    if (!select) return;
    select.value = nextValue || '';
    syncSearchableSelectLabel(container);
    select.dispatchEvent(new Event('change', { bubbles: true }));
    closeSearchableSelect(container);
  }

  function reconcileSearchableInput(container) {
    if (!container) return;
    const { items, rawSearch } = resolveSearchableItems(container);
    const normalizedRaw = normalizeSearchTerm(rawSearch);
    if (!normalizedRaw) {
      applySearchableSelection(container, '');
      return;
    }
    const exactMatch = items.find((item) => normalizeSearchTerm(item.label) === normalizedRaw);
    if (exactMatch) {
      applySearchableSelection(container, exactMatch.value);
      return;
    }
    if (items.length === 1) {
      applySearchableSelection(container, items[0].value);
      return;
    }
    syncSearchableSelectLabel(container);
    closeSearchableSelect(container);
  }

  function initializeAllocationSearchableSelects() {
    body?.querySelectorAll('[data-search-select]').forEach((container) => {
      const select = container.querySelector('.search-select__native');
      if (!select) return;
      fillNativeSearchableSelect(select);
      syncSearchableSelectLabel(container);
    });
  }

  function renderAllocations() {
    const budgetDocumentOptions = buildOptions(optionsCache.budget_documents, 'Selecione...', buildBudgetLabel);
    body.innerHTML = allocationRows.length ? allocationRows.map((row, index) => `
      <tr>
        <td>${renderSearchableSelect('chart_account_id', index, row.chart_account_id || '')}</td>
        <td>${renderSearchableSelect('cost_center_id', index, row.cost_center_id || '')}</td>
        <td><select data-index="${index}" data-field="budget_document_id">${budgetDocumentOptions}</select></td>
        <td>${renderSearchableSelect('domain_value', index, row.domain_value || '')}</td>
        <td><input data-index="${index}" data-field="percentage" value="${row.percentage ?? ''}" inputmode="decimal"></td>
        <td><input data-index="${index}" data-field="allocated_amount_display" value="${row.allocated_amount_display || ''}" inputmode="numeric"></td>
        <td><div class="rateio-actions"><button type="button" class="btn btn-secondary" data-action="duplicate" data-index="${index}">+</button><button type="button" class="btn btn-secondary" data-action="remove" data-index="${index}">×</button></div></td>
      </tr>`).join('') : '<tr><td colspan="7" class="empty-state">Nenhum rateio informado.</td></tr>';

    allocationRows.forEach((row, index) => {
      const chartSelect = body.querySelector(`.search-select__native[data-field="chart_account_id"][data-index="${index}"]`);
      const centerSelect = body.querySelector(`.search-select__native[data-field="cost_center_id"][data-index="${index}"]`);
      const domainSelect = body.querySelector(`.search-select__native[data-field="domain_value"][data-index="${index}"]`);
      const budgetDocumentSelect = body.querySelector(`select[data-field="budget_document_id"][data-index="${index}"]`);
      if (chartSelect) {
        chartSelect.dataset.currentValue = row.chart_account_id || '';
        fillNativeSearchableSelect(chartSelect);
        chartSelect.value = row.chart_account_id || '';
      }
      if (centerSelect) {
        centerSelect.dataset.currentValue = row.cost_center_id || '';
        fillNativeSearchableSelect(centerSelect);
        centerSelect.value = row.cost_center_id || '';
      }
      if (domainSelect) {
        domainSelect.dataset.currentValue = row.domain_value || '';
        fillNativeSearchableSelect(domainSelect);
        domainSelect.value = row.domain_value || '';
      }
      if (budgetDocumentSelect) budgetDocumentSelect.value = row.budget_document_id || '';
    });

    initializeAllocationSearchableSelects();
    renderAllocationSummary();
  }

  window.addDirectAllocationRow = (defaults = {}) => {
    allocationRows.push(createAllocationRow(defaults));
    renderAllocations();
  };

  window.setDirectEntryType = (entryType) => {
    if (lockedEntryType && entryType !== lockedEntryType) return;
    form.querySelector('input[name="entry_type"]').value = entryType;
    document.querySelectorAll('.type-chip').forEach((chip) => chip.classList.toggle('active', chip.dataset.entryType === entryType));
    updateEntryTypePresentation(entryType);
    suggestDefaultCorrectionIndex(entryType);
  };

  function validateAllocationSummary() {
    const summary = summarizeAllocations();
    if (!summary.percentagesOk) throw new Error('A soma dos percentuais do rateio deve ser exatamente 100%.');
    if (!summary.valuesOk) throw new Error('A soma dos valores do rateio deve ser igual ao valor informado no lançamento rápido.');
  }

  function ensureDateDefaults({ force = false } = {}) {
    const occurredOnInput = $('direct-occurred-on');
    const competenceInput = $('direct-competence-date');
    const dueDateInput = $('direct-due-date');
    const sourceValue = occurredOnInput.value || todayDisplay();

    if (force && !occurredOnInput.value) {
      occurredOnInput.value = sourceValue;
    }
    if (force && !competenceInput.value) {
      competenceInput.value = sourceValue;
    }
    if (force && !dueDateInput.value) {
      dueDateInput.value = sourceValue;
    }
    if (!competenceInput.value && occurredOnInput.value) {
      competenceInput.value = occurredOnInput.value;
    }
    if (!dueDateInput.value && occurredOnInput.value) {
      dueDateInput.value = occurredOnInput.value;
    }
  }

  function capturePreservedContext() {
    return {
      entryType: form.querySelector('input[name="entry_type"]').value || 'payable',
      counterpartyId: $('direct-counterparty').value || '',
      bankAccountId: $('direct-bank-account').value || '',
      competenceDate: $('direct-competence-date').value || '',
      occurredOn: $('direct-occurred-on').value || '',
      dueDate: $('direct-due-date').value || '',
      correctionIndexId: $('direct-correction-index').value || '',
      discountRuleId: $('direct-discount-rule').value || '',
      allocations: cloneAllocationRows(),
    };
  }

  function restorePreservedContext(context = {}) {
    window.setDirectEntryType(context.entryType || 'payable');
    $('direct-counterparty').value = context.counterpartyId || '';
    $('direct-bank-account').value = context.bankAccountId || '';
    $('direct-competence-date').value = context.competenceDate || '';
    $('direct-occurred-on').value = context.occurredOn || '';
    $('direct-due-date').value = context.dueDate || '';
    $('direct-correction-index').value = context.correctionIndexId || '';
    $('direct-discount-rule').value = context.discountRuleId || '';
    allocationRows = (context.allocations || []).length
      ? context.allocations.map((row) => createAllocationRow(row))
      : [createAllocationRow({ percentage: '100' })];
    if ($('direct-counterparty').value) {
      applyCounterpartyDefaults($('direct-counterparty').value);
    }
    ensureDateDefaults({ force: true });
  }

  function buildPayload() {
    const description = $('direct-description').value.trim();
    const original_amount = getTopAmount();
    const competence_date = parseDateToIso($('direct-competence-date').value);
    const occurred_on = parseDateToIso($('direct-occurred-on').value);
    const due_date = parseDateToIso($('direct-due-date').value);
    if (!description) throw new Error('Informe o histórico do lançamento.');
    if (!Number($('direct-counterparty').value || 0)) throw new Error('Selecione um favorecido.');
    if (!Number($('direct-bank-account').value || 0)) throw new Error('Selecione a conta bancária do lançamento rápido.');
    if (!competence_date || !occurred_on) throw new Error('Informe datas válidas para competência e lançamento.');
    if (!original_amount || original_amount <= 0) throw new Error('Informe um valor válido.');
    validateAllocationSummary();
    return {
      company_id: companyId,
      entry_type: form.querySelector('input[name="entry_type"]').value,
      description,
      document_number: $('direct-document-number').value.trim() || null,
      counterparty_id: Number($('direct-counterparty').value),
      bank_account_id: Number($('direct-bank-account').value || 0) || null,
      competence_date,
      occurred_on,
      due_date,
      original_amount,
      correction_index_id: Number($('direct-correction-index').value || 0) || null,
      discount_rule_id: Number($('direct-discount-rule').value || 0) || null,
      notes: $('direct-notes').value.trim() || null,
      allocations: allocationRows.map((row) => ({
        chart_account_id: Number(row.chart_account_id || 0) || null,
        cost_center_id: Number(row.cost_center_id || 0) || null,
        budget_version_id: Number(row.budget_version_id || 0) || null,
        budget_line_id: Number(row.budget_line_id || 0) || null,
        budget_contract_id: Number(row.budget_contract_id || 0) || null,
        budget_document_id: Number(row.budget_document_id || 0) || null,
        domain_source_kind: row.domain_source_kind || 'routine',
        domain_type: row.domain_type || null,
        domain_source_id: row.domain_source_id || null,
        domain_label: row.domain_label || null,
        allocation_type: row.allocated_amount ? 'amount' : 'percentage',
        percentage: row.percentage !== '' ? round4(parseDecimal(row.percentage)) : null,
        allocated_amount: row.allocated_amount != null ? round2(row.allocated_amount) : null,
        metadata_json: {},
      })),
    };
  }

  window.saveDirectEntry = async (openEntry) => {
    try {
      const preservedContext = capturePreservedContext();
      const result = await fetchJson(`/api/financial/entries/direct?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });
      if (openEntry && result.entry?.id) {
        window.location.href = `/financial/entries/${result.entry.id}`;
        return;
      }
      form.reset();
      restorePreservedContext(preservedContext);
      recalculateAllRowsFromPercentages();
      renderAllocations();
      $('direct-description').focus();
      const scheduleLabel = result.schedule?.schedule_code || `#${result.schedule?.id || '-'}`;
      const entryLabel = result.entry?.entry_code || `#${result.entry?.id || '-'}`;
      alert(`Lançamento rápido registrado com sucesso.\nAgendamento: ${scheduleLabel}\nLançamento: ${entryLabel}`);
    } catch (error) {
      alert(error.message);
    }
  };

  async function loadOptions() {
    optionsCache = await fetchJson(`/api/financial/entries/direct/options?company_id=${companyId}`);
    $('direct-counterparty').innerHTML = buildOptions(optionsCache.counterparties, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('direct-bank-account').innerHTML = buildOptions(optionsCache.bank_accounts, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('direct-correction-index').innerHTML = buildOptions(optionsCache.correction_indexes, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('direct-discount-rule').innerHTML = buildOptions(optionsCache.discount_rules, 'Selecione...', (item) => item.display_label || item.name || item.code);
    suggestDefaultCorrectionIndex(form.querySelector('input[name="entry_type"]').value || lockedEntryType || 'payable', { force: true });
    if (allocationRows.length) {
      allocationRows = allocationRows.map((row) => createAllocationRow(row));
    }
    renderAllocations();
  }

  window.openDirectCounterpartyModal = () => {
    $('direct-counterparty-modal').classList.remove('hidden');
    $('direct-counterparty-modal').setAttribute('aria-hidden', 'false');
  };

  window.closeDirectCounterpartyModal = () => {
    $('direct-counterparty-modal').classList.add('hidden');
    $('direct-counterparty-modal').setAttribute('aria-hidden', 'true');
    $('direct-counterparty-form').reset();
  };

  $('direct-counterparty-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const fd = new FormData(event.currentTarget);
      const payload = {
        code: null,
        name: fd.get('name'),
        legal_name: fd.get('legal_name') || null,
        document_number: String(fd.get('document_number') || '').replace(/\D/g, '') || null,
        is_active: true,
        metadata_json: {},
      };
      const created = await fetchJson(`/api/financial/catalogs/counterparties?company_id=${companyId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      await loadOptions();
      $('direct-counterparty').value = created.id;
      applyCounterpartyDefaults(created.id);
      window.closeDirectCounterpartyModal();
    } catch (error) {
      alert(error.message);
    }
  });

  $('direct-counterparty').addEventListener('change', (event) => {
    applyCounterpartyDefaults(event.target.value);
  });

  $('direct-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
    recalculateAllRowsFromPercentages();
    renderAllocations();
  });

  ['direct-competence-date', 'direct-occurred-on', 'direct-due-date'].forEach((id) => {
    $(id).addEventListener('input', (event) => { event.target.value = normalizeDateInput(event.target.value); });
  });

  $('direct-occurred-on').addEventListener('blur', () => ensureDateDefaults());
  $('direct-competence-date').addEventListener('blur', () => ensureDateDefaults());
  $('direct-due-date').addEventListener('blur', () => ensureDateDefaults());

  $('direct-counterparty-document').addEventListener('input', (event) => {
    const digits = String(event.target.value || '').replace(/\D/g, '').slice(0, 14);
    event.target.value = digits.length <= 11
      ? digits.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2')
      : digits.replace(/(\d{2})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1/$2').replace(/(\d{4})(\d{1,2})$/, '$1-$2');
  });

  body.addEventListener('input', (event) => {
    if (event.target.matches('[data-search-select-display]')) {
      const container = event.target.closest('[data-search-select]');
      closeAllSearchableSelects(container);
      refreshSearchableSelectOptions(container);
      return;
    }
    const field = event.target.dataset.field;
    const index = Number(event.target.dataset.index || -1);
    if (index < 0 || !field || !allocationRows[index]) return;
    if (field === 'percentage') {
      allocationRows[index].percentage = event.target.value;
      recalculateRowFromPercentage(index);
      const added = ensureRemainingRow(index);
      if (added) renderAllocations(); else syncAllocationRowInputs(index);
      return;
    }
    if (field === 'allocated_amount_display') {
      event.target.value = formatCurrencyFromDigits(event.target.value);
      allocationRows[index].allocated_amount_display = event.target.value;
      recalculateRowFromAmount(index);
      syncAllocationRowInputs(index);
      return;
    }
    allocationRows[index][field] = event.target.value;
  });

  body.addEventListener('change', (event) => {
    const field = event.target.dataset.field;
    const index = Number(event.target.dataset.index || -1);
    if (index < 0 || !field || !allocationRows[index]) return;
    if (field === 'budget_document_id') {
      const value = event.target.value;
      const item = (optionsCache.budget_documents || []).find((candidate) => String(candidate.id) === String(value));
      if (!value || !item) {
        allocationRows[index].budget_version_id = '';
        allocationRows[index].budget_line_id = '';
        allocationRows[index].budget_contract_id = '';
        allocationRows[index].budget_document_id = '';
        return;
      }
      const contract = (optionsCache.budget_contracts || []).find((candidate) => String(candidate.id) === String(item.budget_contract_id || ''));
      const line = (optionsCache.budget_lines || []).find((candidate) => String(candidate.id) === String(contract?.budget_line_id || ''));
      const version = (optionsCache.budget_versions || []).find((candidate) => String(candidate.id) === String(line?.budget_version_id || ''));
      allocationRows[index].budget_document_id = String(item.id);
      allocationRows[index].budget_contract_id = contract ? String(contract.id) : '';
      allocationRows[index].budget_line_id = line ? String(line.id) : '';
      allocationRows[index].budget_version_id = version ? String(version.id) : '';
      return;
    }
    if (field === 'domain_value') {
      const value = event.target.value;
      allocationRows[index].domain_value = value;
      if (!value) {
        allocationRows[index].domain_source_kind = 'routine';
        allocationRows[index].domain_type = null;
        allocationRows[index].domain_source_id = null;
        allocationRows[index].domain_label = null;
        if (event.target.matches('.search-select__native')) {
          syncSearchableSelectLabel(event.target.closest('[data-search-select]'));
        }
        return;
      }
      const [sourceKind, domainType, sourceId] = value.split(':');
      const item = optionsCache.enabled_domains.find((candidate) => (candidate.domain_value || `${candidate.source_kind || 'routine'}:${candidate.domain_type}:${candidate.source_id}`) === value);
      allocationRows[index].domain_source_kind = sourceKind || 'routine';
      allocationRows[index].domain_type = domainType;
      allocationRows[index].domain_source_id = Number(sourceId);
      allocationRows[index].domain_label = item?.display_label || null;
      if (event.target.matches('.search-select__native')) {
        syncSearchableSelectLabel(event.target.closest('[data-search-select]'));
      }
      return;
    }
    allocationRows[index][field] = event.target.value;
    if (event.target.matches('.search-select__native')) {
      syncSearchableSelectLabel(event.target.closest('[data-search-select]'));
    }
  });

  body.addEventListener('click', (event) => {
    const optionButton = event.target.closest('[data-search-option-value]');
    if (optionButton) {
      event.preventDefault();
      const container = optionButton.closest('[data-search-select]');
      applySearchableSelection(container, optionButton.dataset.searchOptionValue || '');
      return;
    }
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const index = Number(button.dataset.index || -1);
    if (button.dataset.action === 'duplicate' && allocationRows[index]) {
      allocationRows.splice(index + 1, 0, createAllocationRow({ ...allocationRows[index] }));
      renderAllocations();
      return;
    }
    if (button.dataset.action === 'remove') {
      allocationRows.splice(index, 1);
      if (!allocationRows.length) allocationRows = [createAllocationRow({ percentage: '100' })];
      recalculateAllRowsFromPercentages();
      renderAllocations();
    }
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('[data-search-select]')) {
      closeAllSearchableSelects();
    }
  });

  window.addEventListener('resize', () => {
    body?.querySelectorAll('[data-search-select].is-open').forEach((container) => positionSearchablePopover(container));
  });

  window.addEventListener('scroll', () => {
    body?.querySelectorAll('[data-search-select].is-open').forEach((container) => positionSearchablePopover(container));
  }, true);

  body.addEventListener('focusin', (event) => {
    if (!event.target.matches('[data-search-select-display]')) return;
    const container = event.target.closest('[data-search-select]');
    const select = container?.querySelector('.search-select__native');
    const selectedLabel = select?.value
      ? selectedSearchableItemLabel(container?.dataset.field, select.value)
      : '';
    closeAllSearchableSelects(container);
    if (selectedLabel && String(event.target.value || '') === selectedLabel) {
      event.target.select();
      return;
    }
    if ((event.target.value || '').trim()) {
      refreshSearchableSelectOptions(container);
    }
  });

  body.addEventListener('focusout', (event) => {
    if (!event.target.matches('[data-search-select-display]')) return;
    const container = event.target.closest('[data-search-select]');
    window.setTimeout(() => {
      if (!container?.contains(document.activeElement)) {
        reconcileSearchableInput(container);
      }
    }, 120);
  });

  body.addEventListener('keydown', (event) => {
    if (!event.target.matches('[data-search-select-display]')) return;
    const container = event.target.closest('[data-search-select]');
    if (event.key === 'Escape') {
      event.preventDefault();
      syncSearchableSelectLabel(container);
      closeSearchableSelect(container);
      return;
    }
    if (event.key === 'Enter') {
      const firstOption = container?.querySelector('[data-search-option-value]');
      if (firstOption) {
        event.preventDefault();
        applySearchableSelection(container, firstOption.dataset.searchOptionValue || '');
      }
    }
  });

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      allocationRows = [createAllocationRow({ percentage: '100' })];
      await loadOptions();
      ensureDateDefaults({ force: true });
      recalculateAllRowsFromPercentages();
      renderAllocations();
      if (lockedEntryType) {
        entryTypeSwitch?.classList.add('is-locked');
        window.setDirectEntryType(lockedEntryType);
      } else {
        window.setDirectEntryType('payable');
      }
      $('direct-description').focus();
    } catch (error) {
      alert(error.message);
    }
  });
})();
