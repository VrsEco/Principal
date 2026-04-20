(function () {
  const page = document.querySelector('.sched-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const initialScheduleId = Number(page.dataset.scheduleId || 0);
  const initialEntryType = String(page.dataset.initialEntryType || '').trim().toLowerCase();
  const pageParams = new URLSearchParams(window.location.search);
  const autoOpenSettlement = pageParams.get('open_settlement') === '1';
  const isFormMode = page.classList.contains('sched-page--form');
  let schedules = [];
  let selectedSchedule = null;
  let entryTypeLocked = false;
  let optionsCache = {
    counterparties: [],
    chart_accounts: [],
    bank_accounts: [],
    cost_centers: [],
    correction_indexes: [],
    discount_rules: [],
    enabled_domains: [],
    budget_versions: [],
    budget_lines: [],
    budget_contracts: [],
    budget_documents: [],
    default_suggestions: {},
  };
  let allocationRows = [];
  let pendingAttachments = [];
  let borderoLocked = false;
  let selectedCalculationLogs = [];
  let settlementSimulation = null;
  let settlementSimulationTimer = null;
  let settlementCompositionHydrating = false;

  const $ = (id) => document.getElementById(id);
  const missingElementMessage = (id) => `A interface de agendamento está desatualizada: campo ${id} não encontrado. Atualize a página e tente novamente.`;
  const requireElement = (id) => {
    const element = $(id);
    if (!element) {
      throw new Error(missingElementMessage(id));
    }
    return element;
  };
  const fieldValue = (id, fallback = '') => {
    const element = $(id);
    return element ? element.value : fallback;
  };
  const requireFieldValue = (id) => requireElement(id).value;
  const setFieldValue = (id, value) => {
    const element = $(id);
    if (element) element.value = value;
  };
  const form = $('schedule-form');
  if (!form) return;
  const entryTypeBanner = $('entry-type-banner');
  const rateioSummary = $('rateio-summary');
  const scheduleListEl = $('schedule-list');
  const scheduleSearchEl = $('schedule-search');

  const revokePendingUrls = () => pendingAttachments.forEach((item) => { try { URL.revokeObjectURL(item.url); } catch (_) {} });
  const clearPendingAttachments = () => { revokePendingUrls(); pendingAttachments = []; };

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

  const normalizeDateInput = (value) => {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 4) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 4)}/${digits.slice(4)}`;
    return `${digits.slice(0, 4)}/${digits.slice(4, 6)}/${digits.slice(6)}`;
  };

  const parseDateToIso = (value) => {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits.length !== 8) return null;
    const [year, month, day] = [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6)];
    const candidate = new Date(Number(year), Number(month) - 1, Number(day));
    if (candidate.getFullYear() !== Number(year) || candidate.getMonth() + 1 !== Number(month) || candidate.getDate() !== Number(day)) return null;
    return `${year}-${month}-${day}`;
  };

  const formatIso = (value) => {
    if (!value) return '';
    const [year, month, day] = String(value).split('-');
    return year && month && day ? `${year}/${month}/${day}` : value;
  };
  const compareIsoDates = (left, right) => {
    if (!left || !right) return 0;
    return left.localeCompare(right);
  };

  const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const signedAmount = (value, movementNature) => {
    const normalized = Math.abs(Number(value || 0));
    return movementNature === 'debit' ? normalized * -1 : normalized;
  };
  const amountClass = (value) => Number(value || 0) < 0 ? 'amount-negative' : 'amount-positive';
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const asMoneyValue = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const toCurrencyInput = (value) => asMoneyValue(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const todayIso = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };
  const statusLabel = (status) => ({ active: 'Ativo', paused: 'Pausado', draft: 'Rascunho', completed: 'Concluído', cancelled: 'Cancelado' }[status] || status || 'Sem status');
  const statusClass = (status) => status === 'active' ? 'badge badge--active' : status === 'completed' ? 'badge badge--completed' : status === 'cancelled' ? 'badge badge--cancelled' : 'badge badge--draft';

  const analyticChartAccounts = () => (optionsCache.chart_accounts || []).filter((item) => !!item.accepts_posting);
  const finalCostCenters = () => {
    const parentIds = new Set((optionsCache.cost_centers || []).filter((item) => item.parent_id).map((item) => Number(item.parent_id)));
    return (optionsCache.cost_centers || []).filter((item) => !parentIds.has(Number(item.id)));
  };

  function switchTab(tab) {
    document.querySelectorAll('.sched-tab').forEach((el) => el.classList.toggle('active', el.dataset.tab === tab));
    document.querySelectorAll('.sched-tab-panel').forEach((el) => el.classList.toggle('active', el.dataset.panel === tab));
  }
  window.switchScheduleTab = switchTab;

  function updateEntryTypePresentation(entryType) {
    page.dataset.entryType = entryType;
    if (!entryTypeBanner) return;
    if (!entryType) {
      entryTypeBanner.textContent = 'Selecione Recebimentos ou Pagamentos para iniciar o agendamento. Após escolher, o tipo fica travado.';
      return;
    }
    const receivable = entryType === 'receivable';
    entryTypeBanner.textContent = receivable
      ? `Recebimentos · tipo travado para este agendamento. Para trocar, cancele e crie um novo.`
      : `Pagamentos · tipo travado para este agendamento. Para trocar, cancele e crie um novo.`;
  }

  function applyEntryType(entryType, { locked = false } = {}) {
    entryTypeLocked = locked;
    const entryTypeInput = form.querySelector('input[name="entry_type"]');
    if (!entryTypeInput) throw new Error(missingElementMessage('entry_type'));
    entryTypeInput.value = entryType;
    document.querySelectorAll('.type-chip').forEach((chip) => {
      const isActive = chip.dataset.entryType === entryType;
      chip.classList.toggle('active', isActive);
      chip.classList.toggle('is-locked', entryTypeLocked && isActive);
      chip.classList.toggle('is-disabled', entryTypeLocked && !isActive);
      chip.disabled = entryTypeLocked;
    });
    updateEntryTypePresentation(entryType);
    if (!selectedSchedule) suggestDefaultCorrectionIndex(entryType);
  }

  window.setEntryType = (entryType) => applyEntryType(entryType, { locked: entryTypeLocked });

  window.chooseEntryType = (entryType) => {
    if (entryTypeLocked) return;
    applyEntryType(entryType, { locked: true });
  };

  window.toggleRepeatFields = () => {
    const enabled = fieldValue('field-repeat-toggle', 'false') === 'true';
    document.querySelectorAll('.repeat-field').forEach((field) => field.classList.toggle('hidden', !enabled));
  };

  const buildOptions = (items, placeholder, formatter) => [`<option value="">${placeholder}</option>`]
    .concat((items || []).map((item) => `<option value="${item.id}">${formatter ? formatter(item) : (item.display_label || item.name || item.code || item.id)}</option>`))
    .join('');

  const buildDomainOptions = (value) => {
    const groups = ['project', 'process'].map((domainType) => {
      const options = optionsCache.enabled_domains
        .filter((item) => item.domain_type === domainType)
        .map((item) => `<option value="${domainType}:${item.source_id}" ${value === `${domainType}:${item.source_id}` ? 'selected' : ''}>${item.display_label}</option>`).join('');
      return options ? `<optgroup label="${domainType === 'project' ? 'Projetos' : 'Processos'}">${options}</optgroup>` : '';
    }).join('');
    return `<option value="">Selecione...</option>${groups}`;
  };

  function buildChartAccountLabel(item) {
    return item.code ? `${item.code} - ${item.name}` : (item.name || item.id);
  }

  function buildCostCenterLabel(item) {
    return item.code ? `${item.code} - ${item.name}` : (item.name || item.id);
  }

  function buildBudgetLabel(item) {
    const code = item.code || '';
    const name = item.name || '';
    return code && name ? `${code} - ${name}` : (code || name || item.id);
  }

  const defaultSuggestions = () => optionsCache.default_suggestions || {};
  const asOptionValue = (value) => (value == null || value === '' ? '' : String(value));
  const getBaseAllocationRows = () => allocationRows.filter((row) => !row.adjustment_kind);
  const getAdjustmentAllocationRows = () => allocationRows.filter((row) => !!row.adjustment_kind);
  const getLastBaseAllocationIndex = () => {
    let lastIndex = -1;
    allocationRows.forEach((row, index) => {
      if (!row.adjustment_kind) lastIndex = index;
    });
    return lastIndex;
  };
  const getConfiguredDiscountAmount = () => round2(parseCurrency($('field-discount-amount')?.value || ''));
  const setDiscountAmountField = (value, { manual = false } = {}) => {
    const field = $('field-discount-amount');
    if (!field) return;
    field.value = formatSignedCurrency(value || 0);
    field.dataset.manualOverride = manual ? '1' : '0';
  };
  const formatSignedCurrency = (value) => {
    const numeric = round2(value);
    const absolute = Math.abs(numeric).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return numeric < 0 ? `-${absolute}` : absolute;
  };
  const sanitizeAllocationAmount = (value) => {
    const numeric = round2(Number(value || 0));
    return Math.abs(numeric) < 0.005 ? 0 : numeric;
  };
  const getDefaultCorrectionIndexIdByEntryType = (entryType) => {
    const suggestions = defaultSuggestions();
    if (entryType === 'receivable') return asOptionValue(suggestions.receivable_correction_index_id || '');
    if (entryType === 'payable') return asOptionValue(suggestions.payable_correction_index_id || '');
    return '';
  };

  function suggestDefaultCorrectionIndex(entryType, { force = false } = {}) {
    const field = $('field-correction-index');
    if (!field) return;
    if (!force && field.value) return;
    field.value = getDefaultCorrectionIndexIdByEntryType(entryType);
  }

  const getSelectedCorrectionIndex = () => (optionsCache.correction_indexes || []).find((item) => String(item.id) === String($('field-correction-index')?.value || ''));
  const getSelectedDiscountRule = () => (optionsCache.discount_rules || []).find((item) => String(item.id) === String($('field-discount-rule')?.value || ''));
  const getAdjustmentChartAccountId = (item) => asOptionValue(item?.metadata_json?.chart_account_id || '');

  function getDaysOverdue() {
    const dueIso = parseDateToIso($('field-due-date')?.value || '');
    if (!dueIso) return 0;
    const dueDate = new Date(`${dueIso}T00:00:00`);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffMs = today.getTime() - dueDate.getTime();
    return diffMs > 0 ? Math.floor(diffMs / 86400000) : 0;
  }

  function calculateCorrectionAmount() {
    const amount = getTopAmount();
    const correction = getSelectedCorrectionIndex();
    if (!amount || !correction) return 0;
    const metadata = correction.metadata_json || {};
    const overdueDays = getDaysOverdue();
    if (!overdueDays) return 0;

    const interestRate = Number(metadata.interest_rate || 0);
    const penaltyRate = Number(metadata.penalty_rate || 0);
    const penaltyLimitRate = Number(metadata.penalty_limit_rate || 0);
    const interestPeriod = String(metadata.interest_period || 'daily').toLowerCase();
    const periods = interestPeriod === 'monthly' ? (overdueDays / 30) : overdueDays;
    const interestAmount = interestRate > 0 ? amount * (interestRate / 100) * periods : 0;
    let effectivePenaltyRate = penaltyRate;
    if (penaltyLimitRate > 0) effectivePenaltyRate = Math.min(effectivePenaltyRate, penaltyLimitRate);
    const penaltyAmount = effectivePenaltyRate > 0 ? amount * (effectivePenaltyRate / 100) : 0;
    return round2(interestAmount + penaltyAmount);
  }

  function calculateDiscountAmount() {
    const discountField = $('field-discount-amount');
    const discountFieldRawValue = String(discountField?.value || '').trim();
    if (discountField?.dataset.manualOverride === '1') {
      return getConfiguredDiscountAmount();
    }
    const amount = getTopAmount();
    const discountRule = getSelectedDiscountRule();
    if (!amount || !discountRule) return 0;
    const metadata = discountRule.metadata_json || {};
    const discountType = String(metadata.discount_type || '').toLowerCase();
    const value = Number(metadata.value || 0);
    if (value <= 0) return 0;
    if (discountType === 'percentage') return round2(amount * (value / 100));
    return round2(value);
  }

  function refreshSuggestedDiscountAmountField() {
    const field = $('field-discount-amount');
    if (!field || field.dataset.manualOverride === '1') return;
    const selectedRule = getSelectedDiscountRule();
    if (!selectedRule) return setDiscountAmountField(0, { manual: false });
    const amount = getTopAmount();
    const metadata = selectedRule.metadata_json || {};
    const discountType = String(metadata.discount_type || '').toLowerCase();
    const value = Number(metadata.value || 0);
    if (value <= 0) return setDiscountAmountField(0, { manual: false });
    const suggestedValue = discountType === 'percentage' ? round2(amount * (value / 100)) : round2(value);
    setDiscountAmountField(suggestedValue, { manual: false });
  }

  function calculateLiquidatedAmount() {
    return round2(
      (selectedSchedule?.related_entries || []).reduce((entryAcc, entry) => (
        entryAcc + (entry.settlements || []).reduce((settAcc, settlement) => (
          settAcc
          + Number(settlement.principal_amount || 0)
          + Number(settlement.interest_amount || 0)
          + Number(settlement.penalty_amount || 0)
          + Number(settlement.fee_amount || 0)
          + Number(settlement.other_adjustments_amount || 0)
          - Number(settlement.discount_amount || 0)
        ), 0)
      ), 0)
    );
  }

  function updateFinancialTotals() {
    const amount = getTopAmount();
    const correctionAmount = calculateCorrectionAmount();
    const discountAmount = calculateDiscountAmount();
    const updatedAmount = round2(amount + correctionAmount - discountAmount);
    const liquidatedAmount = calculateLiquidatedAmount();
    const openBalance = round2(updatedAmount - liquidatedAmount);
    setFieldValue('field-correction-amount', correctionAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    setFieldValue('field-liquidated-amount', liquidatedAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    setFieldValue('field-updated-amount', updatedAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    setFieldValue('field-open-balance', openBalance.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  }

  function getEffectiveScheduleAmount() {
    return round2(getTopAmount() + calculateCorrectionAmount() - calculateDiscountAmount());
  }

  function getTopAmount() {
    return round2(parseCurrency(fieldValue('field-amount')));
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
    allocationRows.forEach((row, index) => {
      if (!row.adjustment_kind) recalculateRowFromPercentage(index);
    });
  }

  function updateAdjustmentAllocationRow(kind, config = {}) {
    const existingIndex = allocationRows.findIndex((row) => row.adjustment_kind === kind);
    const nextAmount = sanitizeAllocationAmount(config.allocated_amount);
    if (!nextAmount) {
      if (existingIndex >= 0) allocationRows.splice(existingIndex, 1);
      return;
    }

    const suggestions = defaultSuggestions();
    const domainType = config.domain_type || suggestions.domain_type || null;
    const domainSourceId = config.domain_source_id || suggestions.domain_source_id || null;
    const defaults = {
      chart_account_id: asOptionValue(config.chart_account_id || ''),
      cost_center_id: asOptionValue(config.cost_center_id || suggestions.cost_center_id || ''),
      budget_version_id: '',
      budget_version_code: null,
      budget_line_id: '',
      budget_line_code: null,
      budget_contract_id: '',
      budget_contract_code: null,
      budget_document_id: '',
      budget_document_code: null,
      domain_type: domainType,
      domain_source_id: domainSourceId,
      domain_label: config.domain_label || suggestions.domain_label || null,
      domain_value: domainType && domainSourceId ? `${domainType}:${domainSourceId}` : '',
      adjustment_kind: kind,
      adjustment_label: config.adjustment_label || null,
      notes: config.notes || null,
      percentage: '',
      allocated_amount: nextAmount,
      allocated_amount_display: formatSignedCurrency(nextAmount),
    };

    if (existingIndex >= 0) {
      const current = allocationRows[existingIndex];
      allocationRows[existingIndex] = {
        ...current,
        ...defaults,
        chart_account_id: current.chart_account_id || defaults.chart_account_id,
        cost_center_id: current.cost_center_id || defaults.cost_center_id,
        domain_type: current.domain_type || defaults.domain_type,
        domain_source_id: current.domain_source_id || defaults.domain_source_id,
        domain_label: current.domain_label || defaults.domain_label,
        domain_value: current.domain_value || defaults.domain_value,
      };
      return;
    }

    allocationRows.push(createAllocationRow(defaults));
  }

  function syncAdjustmentAllocationRows() {
    const correction = getSelectedCorrectionIndex();
    const discountRule = getSelectedDiscountRule();
    updateAdjustmentAllocationRow('correction', {
      adjustment_label: 'Correção Financeira',
      chart_account_id: getAdjustmentChartAccountId(correction),
      allocated_amount: calculateCorrectionAmount(),
      notes: correction ? `Correção Financeira: ${correction.display_label || correction.name || correction.code || correction.id}` : 'Correção Financeira',
    });
    updateAdjustmentAllocationRow('discount', {
      adjustment_label: 'Desconto',
      chart_account_id: getAdjustmentChartAccountId(discountRule),
      allocated_amount: calculateDiscountAmount() * -1,
      notes: discountRule ? `Desconto: ${discountRule.display_label || discountRule.name || discountRule.code || discountRule.id}` : 'Desconto',
    });
  }

  function summarizeAllocations() {
    const totalAmount = getEffectiveScheduleAmount();
    const totalPercentage = round4(getBaseAllocationRows().reduce((acc, row) => acc + parseDecimal(row.percentage), 0));
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
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Valor total do rateio: ${money(summary.totalAllocated)}</span>`,
      `<span class="rateio-pill ${summary.percentagesOk ? 'is-ok' : 'is-error'}">Faltante percentual: ${formatPercent(summary.remainingPercentage)}%</span>`,
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Faltante valor: ${money(summary.remainingValue)}</span>`
    ].join('');
    return summary;
  }

  function ensureRemainingRow(indexChanged) {
    if (indexChanged !== getLastBaseAllocationIndex()) return false;
    const summary = summarizeAllocations();
    if (summary.remainingPercentage <= 0.01 || summary.remainingPercentage >= 100) return false;
    allocationRows.push({
      chart_account_id: '',
      cost_center_id: '',
      domain_type: null,
      domain_source_id: null,
      domain_label: null,
      domain_value: '',
      adjustment_kind: null,
      adjustment_label: null,
      notes: null,
      percentage: formatPercent(summary.remainingPercentage),
      allocated_amount: round2(summary.remainingValue),
      allocated_amount_display: summary.remainingValue ? summary.remainingValue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '',
    });
    return true;
  }

  function syncAllocationRowInputs(index) {
    const percentageInput = $('allocations-body').querySelector(`input[data-field="percentage"][data-index="${index}"]`);
    const amountInput = $('allocations-body').querySelector(`input[data-field="allocated_amount_display"][data-index="${index}"]`);
    if (percentageInput) percentageInput.value = allocationRows[index].percentage || '';
    if (amountInput) amountInput.value = allocationRows[index].allocated_amount_display || '';
    renderAllocationSummary();
  }

  function renderAllocations() {
    const body = $('allocations-body');
    if (!allocationRows.length) {
      body.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhum rateio informado.</td></tr>';
      renderAllocationSummary();
      return;
    }

    const chartOptions = buildOptions(analyticChartAccounts(), 'Selecione...', buildChartAccountLabel);
    const costCenterOptions = buildOptions(finalCostCenters(), 'Selecione...', buildCostCenterLabel);
    const budgetDocumentOptions = buildOptions(optionsCache.budget_documents, 'Selecione...', buildBudgetLabel);

    body.innerHTML = allocationRows.map((row, index) => `
      <tr class="${row.adjustment_kind ? 'rateio-row--adjustment' : ''}">
        <td class="rateio-cell rateio-cell--chart-account"><select data-index="${index}" data-field="chart_account_id" aria-label="Plano de conta da linha ${index + 1}">${chartOptions}</select></td>
        <td class="rateio-cell rateio-cell--cost-center"><select data-index="${index}" data-field="cost_center_id" aria-label="Centro de resultado da linha ${index + 1}">${costCenterOptions}</select></td>
        <td class="rateio-cell rateio-cell--budget-document"><select data-index="${index}" data-field="budget_document_id" aria-label="NF ou assemelhado da linha ${index + 1}">${budgetDocumentOptions}</select></td>
        <td class="rateio-cell rateio-cell--domain"><select data-index="${index}" data-field="domain_value" aria-label="Projeto ou processo da linha ${index + 1}">${buildDomainOptions(row.domain_value || '')}</select></td>
        <td class="rateio-cell rateio-cell--percentage"><input data-index="${index}" data-field="percentage" value="${row.percentage ?? ''}" inputmode="decimal" placeholder="0,0000" aria-label="Percentual da linha ${index + 1}" ${row.adjustment_kind ? 'readonly tabindex="-1"' : ''}></td>
        <td class="rateio-cell rateio-cell--amount"><input data-index="${index}" data-field="allocated_amount_display" value="${row.allocated_amount_display || ''}" inputmode="numeric" placeholder="0,00" aria-label="Valor da linha ${index + 1}" ${row.adjustment_kind ? 'readonly tabindex="-1"' : ''}></td>
        <td class="rateio-cell rateio-cell--actions"><div class="rateio-actions">${row.adjustment_kind ? `<span class="rateio-adjustment-tag">${row.adjustment_label || 'Ajuste'}</span>` : `<button type="button" class="btn btn-secondary btn-icon" data-action="duplicate" data-index="${index}" aria-label="Duplicar linha ${index + 1}">+</button><button type="button" class="btn btn-secondary btn-icon" data-action="remove" data-index="${index}" aria-label="Remover linha ${index + 1}">×</button>`}</div></td>
      </tr>`).join('');

    allocationRows.forEach((row, index) => {
      body.querySelector(`select[data-field="chart_account_id"][data-index="${index}"]`).value = row.chart_account_id || '';
      body.querySelector(`select[data-field="cost_center_id"][data-index="${index}"]`).value = row.cost_center_id || '';
      body.querySelector(`select[data-field="budget_document_id"][data-index="${index}"]`).value = row.budget_document_id || '';
    });

    renderAllocationSummary();
  }

  function createAllocationRow(defaults = {}) {
    const suggestions = defaultSuggestions();
    const domainType = defaults.domain_type || suggestions.domain_type || null;
    const domainSourceId = defaults.domain_source_id || suggestions.domain_source_id || null;
    return {
      chart_account_id: defaults.chart_account_id || '',
      cost_center_id: asOptionValue(defaults.cost_center_id || suggestions.cost_center_id || ''),
      budget_version_id: asOptionValue(defaults.budget_version_id || suggestions.budget_version_id || ''),
      budget_version_code: defaults.budget_version_code || null,
      budget_line_id: asOptionValue(defaults.budget_line_id || suggestions.budget_line_id || ''),
      budget_line_code: defaults.budget_line_code || null,
      budget_contract_id: asOptionValue(defaults.budget_contract_id || suggestions.budget_contract_id || ''),
      budget_contract_code: defaults.budget_contract_code || null,
      budget_document_id: asOptionValue(defaults.budget_document_id || suggestions.budget_document_id || ''),
      budget_document_code: defaults.budget_document_code || null,
      domain_type: domainType,
      domain_source_id: domainSourceId,
      domain_label: defaults.domain_label || suggestions.domain_label || null,
      domain_value: domainType && domainSourceId ? `${domainType}:${domainSourceId}` : '',
      adjustment_kind: defaults.adjustment_kind || null,
      adjustment_label: defaults.adjustment_label || null,
      percentage: defaults.percentage ?? '100',
      allocated_amount: defaults.allocated_amount ?? null,
      allocated_amount_display: defaults.allocated_amount_display || '',
      notes: defaults.notes || null,
    };
  }

  window.addAllocationRow = (defaults = {}) => {
    allocationRows.push(createAllocationRow(defaults));
    renderAllocations();
  };

  function renderList() {
    if (!scheduleListEl || !scheduleSearchEl) return;
    const search = (scheduleSearchEl.value || '').trim().toLowerCase();
    const items = schedules.filter((item) => `${item.schedule_code || ''} ${item.description || item.name || ''} ${item.metadata_json?.counterparty_name || ''}`.toLowerCase().includes(search));
    scheduleListEl.innerHTML = items.length ? items.map((item) => `
      <article class="schedule-item ${selectedSchedule && selectedSchedule.id === item.id ? 'active' : ''}" data-id="${item.id}">
        <strong>${item.description || item.name || 'Sem histórico'}</strong>
        <small>${item.schedule_code || '-'} · <span class="${amountClass(item.signed_template_amount ?? 0)}">${money(item.signed_template_amount ?? item.template_amount ?? 0)}</span></small>
        <div class="schedule-item-meta"><span class="${statusClass(item.status)}">${statusLabel(item.status)}</span><small>${formatIso(item.next_due_date || item.first_due_date)}</small></div>
      </article>`).join('') : '<div class="empty-state">Nenhum agendamento encontrado.</div>';
  }

  function renderAttachments(savedAttachments) {
    const merged = [
      ...pendingAttachments.map((item) => ({ ...item, is_pending: true })),
      ...(savedAttachments || []),
    ];
    $('attachments-empty').classList.toggle('hidden', merged.length > 0);
    $('attachments-list').innerHTML = merged.length ? merged.map((item) => `
      <article class="attachment-item ${item.is_pending ? 'is-pending' : ''}">
        <button type="button" class="attachment-preview-trigger" data-attachment-preview="${item.url}" data-attachment-name="${item.name}">
          <span class="attachment-meta"><strong>${item.name}</strong><small>${item.content_type || 'Arquivo'}</small>${item.is_pending ? '<span class="attachment-state">Na fila</span>' : ''}</span>
        </button>
        <div class="rateio-actions"><button type="button" class="btn btn-secondary" data-attachment-preview="${item.url}" data-attachment-name="${item.name}">Visualizar</button>${item.is_pending ? `<button type="button" class="btn btn-secondary" data-pending-attachment-delete="${item.id}">Remover</button>` : `<button type="button" class="btn btn-secondary" data-attachment-delete="${item.id}">Excluir</button>`}</div>
      </article>`).join('') : '<div class="empty-state">Nenhum anexo selecionado ou vinculado.</div>';
  }

  async function flushPendingAttachments(scheduleId) {
    if (!scheduleId || !pendingAttachments.length) return;
    const queue = [...pendingAttachments];
    for (const item of queue) {
      const formData = new FormData();
      formData.append('file', item.file);
      await fetchJson(`/api/financial/schedules/${scheduleId}/attachments?company_id=${companyId}`, { method: 'POST', body: formData });
    }
    clearPendingAttachments();
  }

  function renderBaixas(entries) {
    $('baixas-empty').classList.toggle('hidden', !!entries.length);
    $('baixas-list').innerHTML = entries.map((entry, index) => `
      <article class="baixa-card">
        <strong>${index + 1}. ${entry.description || 'Baixa sem histórico'}</strong>
        <small>${formatIso(entry.occurred_on || entry.competence_date || entry.due_date)} · <span class="${amountClass(entry.signed_amount ?? 0)}">${money(entry.signed_amount ?? signedAmount(entry.original_amount, entry.movement_nature))}</span></small>
        <table class="settlement-table">
          <thead><tr><th>Seq.</th><th>Data</th><th>Tipo</th><th>Valor</th><th>Multa</th><th>Juros</th><th>Desconto</th></tr></thead>
          <tbody>${(entry.settlements || []).length ? entry.settlements.map((settlement, idx) => `<tr><td>${idx + 1}</td><td>${formatIso(settlement.settlement_date)}</td><td>${settlement.settlement_type || '-'}</td><td>${money(settlement.principal_amount || 0)}</td><td>${money(settlement.penalty_amount || 0)}</td><td>${money(settlement.interest_amount || 0)}</td><td>${money(settlement.discount_amount || 0)}</td></tr>`).join('') : '<tr><td colspan="7">Sem liquidações registradas.</td></tr>'}</tbody>
        </table>
      </article>`).join('');
  }

  async function loadCalculationLogs(scheduleId) {
    if (!scheduleId) return [];
    const payload = await fetchJson(`/api/financial/schedules/${scheduleId}/calculation-logs?company_id=${companyId}&limit=50`);
    return Array.isArray(payload.logs) ? payload.logs : [];
  }

  function eventLabel(eventType) {
    return ({
      settlement_posted: 'Baixa registrada',
      settlement_updated: 'Baixa atualizada',
      settlement_deleted: 'Baixa removida',
      adjustment_released: 'Ajuste liberado',
      recalculation: 'Recálculo',
    }[eventType] || eventType || 'Evento financeiro');
  }

  function renderTitleBalance(schedule) {
    const panelEl = $('title-balance-panel');
    if (!panelEl) return;
    const hasSchedule = Boolean(schedule?.id);
    panelEl.classList.toggle('hidden', !hasSchedule);
    if (!hasSchedule) {
      panelEl.innerHTML = '';
      return;
    }

    const summary = schedule.summary || {};
    const nature = schedule.movement_nature;
    const principalAmount = asMoneyValue(summary.principal_amount ?? summary.template_amount ?? schedule.template_amount);
    const principalOpen = asMoneyValue(summary.principal_open ?? summary.open_principal ?? schedule.template_amount);
    const adjustmentsGenerated = asMoneyValue(summary.adjustments_generated ?? summary.correction_amount ?? 0);
    const adjustmentsSettled = asMoneyValue(summary.adjustments_settled ?? 0);
    const adjustmentsOpen = asMoneyValue(summary.adjustments_open ?? Math.max(adjustmentsGenerated - adjustmentsSettled, 0));
    const discountsOpen = asMoneyValue(summary.discounts_open ?? summary.discount_amount ?? 0);
    const totalOpen = asMoneyValue(summary.total_open ?? (principalOpen + adjustmentsOpen - discountsOpen));
    const settledTotal = asMoneyValue(summary.principal_settled ?? summary.liquidated_amount ?? 0);

    panelEl.innerHTML = `
      <header class="title-balance-head">
        <div>
          <span>Saldo analítico do título</span>
          <h3>${escapeHtml(schedule.schedule_code || `Título ${schedule.id}`)} · ${escapeHtml(schedule.description || schedule.name || 'Sem histórico')}</h3>
          <p>Composição operacional do principal, correções financeiras, descontos e saldo ainda alterável.</p>
        </div>
        <strong class="${amountClass(signedAmount(totalOpen, nature))}">${money(signedAmount(totalOpen, nature))}</strong>
      </header>
      <div class="title-balance-grid">
        <article class="title-balance-card title-balance-card--principal">
          <span>Principal original</span>
          <strong>${money(signedAmount(principalAmount, nature))}</strong>
          <small>Valor base do título financeiro.</small>
        </article>
        <article class="title-balance-card">
          <span>Principal em aberto</span>
          <strong>${money(signedAmount(principalOpen, nature))}</strong>
          <small>Parcela do principal ainda pendente.</small>
        </article>
        <article class="title-balance-card title-balance-card--adjustment">
          <span>Ajustes em aberto</span>
          <strong>${money(signedAmount(adjustmentsOpen, nature))}</strong>
          <small>Correções/descontos ainda não baixados.</small>
        </article>
        <article class="title-balance-card">
          <span>Principal baixado</span>
          <strong>${money(signedAmount(settledTotal, nature))}</strong>
          <small>Principal liquidado até o momento.</small>
        </article>
      </div>
    `;
  }

  function ledgerMetric(label, value, movementNature, { invert = false } = {}) {
    const numeric = asMoneyValue(value) * (invert ? -1 : 1);
    const signed = signedAmount(numeric, movementNature);
    return `<div class="ledger-component"><span>${label}</span><strong class="${amountClass(signed)}">${money(signed)}</strong></div>`;
  }

  function ledgerStep(title, subtitle, metrics, tone = '') {
    return `
      <section class="ledger-step ${tone}">
        <header><span>${title}</span><small>${subtitle}</small></header>
        <div class="ledger-components">${metrics.join('')}</div>
      </section>
    `;
  }

  function renderCalculationLogs(schedule, logs) {
    const emptyEl = $('calculation-log-empty');
    const shellEl = $('calculation-log-shell');
    const summaryEl = $('calculation-log-summary');
    const listEl = $('calculation-log-list');
    const tabButton = $('calculation-log-tab-button');
    const hasSchedule = Boolean(schedule?.id);
    const normalizedLogs = Array.isArray(logs) ? logs : [];
    selectedCalculationLogs = normalizedLogs;

    renderTitleBalance(schedule);
    tabButton?.classList.toggle('hidden', !hasSchedule);
    emptyEl?.classList.toggle('hidden', normalizedLogs.length > 0 || !hasSchedule);
    shellEl?.classList.toggle('hidden', !hasSchedule || !normalizedLogs.length);

    if (!hasSchedule) {
      if (summaryEl) summaryEl.innerHTML = '';
      if (listEl) listEl.innerHTML = '';
      return;
    }

    const latest = normalizedLogs[0] || null;
    const summary = schedule.summary || {};
    const signedTotalOpen = signedAmount(summary.total_open ?? latest?.total_due_after ?? latest?.open_principal_after ?? 0, schedule?.movement_nature);
    const signedAdjustmentsOpen = signedAmount(summary.adjustments_open ?? latest?.adjustments_open_after ?? 0, schedule?.movement_nature);

    if (summaryEl) {
      summaryEl.innerHTML = latest ? [
        `<article class="calc-log-kpi"><span>Último evento</span><strong>${formatIso(latest.calculation_date)}</strong><small>${eventLabel(latest.event_type)}</small></article>`,
        `<article class="calc-log-kpi"><span>Total em aberto</span><strong class="${amountClass(signedTotalOpen)}">${money(signedTotalOpen)}</strong><small>Principal + ajustes pendentes</small></article>`,
        `<article class="calc-log-kpi"><span>Ajustes em aberto</span><strong class="${amountClass(signedAdjustmentsOpen)}">${money(signedAdjustmentsOpen)}</strong><small>Correção financeira/descontos a liquidar</small></article>`,
        `<article class="calc-log-kpi"><span>Eventos</span><strong>${normalizedLogs.length}</strong><small>Memórias estruturadas registradas</small></article>`,
      ].join('') : '';
    }

    if (listEl) {
      listEl.innerHTML = normalizedLogs.map((log, index) => {
        const meta = log.metadata_json || {};
        const snapshot = log.snapshot_json || meta.snapshot || {};
        const settlementCode = meta.settlement_code || snapshot.settlement_code || '-';
        const entryCode = snapshot.entry_code || '-';
        const beforeTotal = log.total_due_before ?? ((log.principal_before || 0) + (log.adjustments_open_before || 0));
        const afterTotal = log.total_due_after ?? ((log.principal_after || 0) + (log.adjustments_open_after || 0));
        return `
          <article class="calc-log-card calc-log-card--ledger">
            <header class="calc-log-card__head">
              <div>
                <span class="calc-log-step">Evento ${index + 1}</span>
                <h3>${formatIso(log.calculation_date)} · ${escapeHtml(eventLabel(log.event_type))}</h3>
                <p>Título ${escapeHtml(schedule.schedule_code || schedule.id || '-')} · Baixa ${escapeHtml(settlementCode)} · Lançamento ${escapeHtml(entryCode)}</p>
              </div>
              <div class="calc-log-card__badges">
                <span class="calc-log-badge">Principal ${money(signedAmount(log.principal_settled_now ?? log.settled_principal_current ?? 0, schedule?.movement_nature))}</span>
                <span class="calc-log-badge">Ajustes ${money(signedAmount(log.adjustments_settled_now ?? log.correction_amount ?? 0, schedule?.movement_nature))}</span>
              </div>
            </header>
            <div class="ledger-flow">
              ${ledgerStep('Antes', 'Saldo calculado antes da baixa', [
                ledgerMetric('Principal aberto', log.principal_before ?? log.template_amount ?? 0, schedule?.movement_nature),
                ledgerMetric('Ajustes abertos', log.adjustments_open_before ?? log.correction_amount ?? 0, schedule?.movement_nature),
                ledgerMetric('Total devido', beforeTotal, schedule?.movement_nature),
              ], 'ledger-step--before')}
              ${ledgerStep('Agora', 'Composição realizada neste evento', [
                ledgerMetric('Principal baixado', log.principal_settled_now ?? log.settled_principal_current ?? 0, schedule?.movement_nature),
                ledgerMetric('Ajustes baixados', log.adjustments_settled_now ?? 0, schedule?.movement_nature),
                ledgerMetric('Desconto liberado', log.discount_now ?? log.discount_amount ?? 0, schedule?.movement_nature, { invert: true }),
              ], 'ledger-step--current')}
              ${ledgerStep('Depois', 'Saldo remanescente editável do título', [
                ledgerMetric('Principal aberto', log.principal_after ?? log.open_principal_after ?? 0, schedule?.movement_nature),
                ledgerMetric('Ajustes abertos', log.adjustments_open_after ?? 0, schedule?.movement_nature),
                ledgerMetric('Total devido', afterTotal, schedule?.movement_nature),
              ], 'ledger-step--after')}
            </div>
            <details class="calc-log-snapshot">
              <summary>Ver snapshot técnico do cálculo</summary>
              <pre>${escapeHtml(JSON.stringify(snapshot || {}, null, 2))}</pre>
            </details>
          </article>
        `;
      }).join('');
    }
  }

  function hydrateAllocations(schedule) {
    allocationRows = (schedule.allocations || []).map((item) => createAllocationRow({
      chart_account_id: item.chart_account_id || '',
      cost_center_id: item.cost_center_id || '',
      budget_version_id: item.budget_version_id || item.metadata_json?.budget_version_id || '',
      budget_version_code: item.budget_version_code || item.metadata_json?.budget_version_code || null,
      budget_line_id: item.budget_line_id || item.metadata_json?.budget_line_id || '',
      budget_line_code: item.budget_line_code || item.metadata_json?.budget_line_code || null,
      budget_contract_id: item.budget_contract_id || item.metadata_json?.budget_contract_id || '',
      budget_contract_code: item.budget_contract_code || item.metadata_json?.budget_contract_code || null,
      budget_document_id: item.budget_document_id || item.metadata_json?.budget_document_id || '',
      budget_document_code: item.budget_document_code || item.metadata_json?.budget_document_code || null,
      domain_type: item.domain_type || null,
      domain_source_id: item.domain_source_id || null,
      domain_label: item.domain_label || null,
      adjustment_kind: item.metadata_json?.adjustment_kind || null,
      adjustment_label: item.metadata_json?.adjustment_label || null,
      notes: item.notes || null,
      percentage: item.percentage != null ? formatPercent(item.percentage) : '',
      allocated_amount: item.allocated_amount != null ? round2(item.allocated_amount) : null,
      allocated_amount_display: item.allocated_amount != null ? formatSignedCurrency(item.allocated_amount) : '',
    }));
    if (!allocationRows.length) {
      allocationRows = [createAllocationRow({ percentage: '100' })];
    }
    recalculateAllRowsFromPercentages();
    syncAdjustmentAllocationRows();
    renderAllocations();
  }

  function fillForm(schedule) {
    borderoLocked = Boolean(schedule.is_bordero_locked);
    form.schedule_id.value = schedule.id || '';
    form.schedule_code.value = schedule.schedule_code || '';
    form.status.value = schedule.status || 'active';
    applyEntryType(schedule.entry_type || '', { locked: true });
    setFieldValue('field-description', schedule.description || schedule.name || '');
    setFieldValue('field-document-number', schedule.document_number || '');
    setFieldValue('field-counterparty', schedule.counterparty_id || '');
    setFieldValue('field-amount', Number(schedule.template_amount || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    setFieldValue('field-competence', formatIso(schedule.competence_date || schedule.start_date || schedule.first_due_date));
    setFieldValue('field-due-date', formatIso(schedule.first_due_date || schedule.next_due_date));
    setFieldValue('field-correction-index', schedule.correction_index_id || '');
    setFieldValue('field-discount-rule', schedule.discount_rule_id || '');
    if (Number(schedule.metadata_json?.discount_amount_override || 0) > 0) {
      setDiscountAmountField(schedule.metadata_json?.discount_amount_override || 0, { manual: true });
    } else {
      setDiscountAmountField(0, { manual: false });
    }
    setFieldValue('field-repeat-toggle', (schedule.frequency || 'one_time') === 'one_time' ? 'false' : 'true');
    setFieldValue('field-frequency', schedule.frequency === 'monthly' ? 'monthly' : schedule.frequency === 'yearly' ? 'yearly' : 'weekly');
    setFieldValue('field-interval-value', schedule.interval_value || 1);
    setFieldValue('field-repeat-count', schedule.metadata_json?.repeat_count || 1);
    clearPendingAttachments();
    hydrateAllocations(schedule);
    renderAttachments(schedule.attachments || []);
    renderBaixas(schedule.related_entries || []);
    renderCalculationLogs(schedule, selectedCalculationLogs);
    $('baixas-tab-button').classList.toggle('hidden', !(schedule.related_entries || []).length);
    Array.from(form.elements).forEach((field) => {
      if (!field || ['schedule_id', 'schedule_code'].includes(field.name)) return;
      field.disabled = borderoLocked;
    });
    document.querySelectorAll('.sched-footer-actions button').forEach((button) => {
      if (button.textContent.includes('Cancelar')) return;
      button.disabled = borderoLocked;
    });
    if (borderoLocked && entryTypeBanner) {
      const code = schedule.bordero?.code || schedule.summary?.bordero_code || 'Borderô';
      entryTypeBanner.textContent = `Agendamento bloqueado pelo ${code}. Consulta liberada; edição e baixa direta indisponíveis.`;
    }
    window.toggleRepeatFields();
    refreshSuggestedDiscountAmountField();
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  }

  function validateAllocationSummary() {
    const summary = summarizeAllocations();
    if (!summary.percentagesOk) throw new Error('A soma dos percentuais do rateio deve ser exatamente 100%.');
    if (!summary.valuesOk) throw new Error('A soma dos valores do rateio deve ser igual ao valor atualizado do agendamento.');
  }

  function buildPayload() {
    const entryType = form.entry_type?.value || '';
    if (!entryType) {
      throw new Error('Escolha primeiro se o agendamento é de Recebimentos ou Pagamentos.');
    }
    const description = requireFieldValue('field-description').trim();
    const counterpartyId = Number(requireFieldValue('field-counterparty') || 0);
    const competenceIso = parseDateToIso(requireFieldValue('field-competence'));
    const dueIso = parseDateToIso(requireFieldValue('field-due-date'));
    const amount = getTopAmount();
    if (!description) throw new Error('Informe o histórico do agendamento.');
    if (!counterpartyId) throw new Error('Selecione um favorecido.');
    if (!competenceIso || !dueIso) throw new Error('Informe datas válidas para competência e vencimento.');
    if (compareIsoDates(dueIso, competenceIso) < 0) {
      throw new Error('O vencimento não pode ser anterior à competência.');
    }
    if (!amount || amount <= 0) throw new Error('Informe um valor válido.');
    syncAdjustmentAllocationRows();
    validateAllocationSummary();
    const frequency = fieldValue('field-repeat-toggle', 'false') === 'true' ? fieldValue('field-frequency', 'weekly') : 'one_time';
    const primaryAllocation = getBaseAllocationRows()[0] || allocationRows[0] || {};
    const isUpdate = Boolean(form.schedule_id?.value);
    return {
      schedule_code: isUpdate ? undefined : (form.schedule_code?.value || undefined),
      name: description.slice(0, 120),
      description,
      memo: null,
      entry_type: entryType,
      movement_nature: entryType === 'receivable' ? 'credit' : 'debit',
      origin_type: 'manual',
      status: form.status?.value || 'active',
      frequency,
      interval_value: Number(fieldValue('field-interval-value', '1') || 1),
      start_date: competenceIso,
      competence_date: competenceIso,
      first_due_date: dueIso,
      next_due_date: dueIso,
      end_date: null,
      day_of_month: frequency === 'monthly' ? Number(dueIso.split('-')[2]) : null,
      weekday: frequency === 'weekly' ? new Date(`${dueIso}T00:00:00`).getDay() : null,
      template_amount: amount,
      counterparty_id: counterpartyId,
      chart_account_id: Number(primaryAllocation.chart_account_id || 0) || null,
      cost_center_id: Number(primaryAllocation.cost_center_id || 0) || null,
      document_number_prefix: null,
      generate_advance_days: 0,
      auto_post: false,
      notes: null,
      metadata_json: {
        ...(selectedSchedule?.metadata_json || {}),
        document_number: fieldValue('field-document-number').trim() || null,
        correction_index_id: Number(fieldValue('field-correction-index') || 0) || null,
        discount_rule_id: Number(fieldValue('field-discount-rule') || 0) || null,
        discount_amount_override: $('field-discount-amount')?.dataset.manualOverride === '1' ? (getConfiguredDiscountAmount() || 0) : 0,
        repeat_count: Number(fieldValue('field-repeat-count', '1') || 1),
        attachments: selectedSchedule?.attachments || [],
        counterparty_name: $('field-counterparty')?.selectedOptions?.[0]?.textContent || null,
        allocations: allocationRows.map((row) => ({
          chart_account_id: Number(row.chart_account_id || 0) || null,
          cost_center_id: Number(row.cost_center_id || 0) || null,
          budget_version_id: Number(row.budget_version_id || 0) || null,
          budget_version_code: row.budget_version_code || null,
          budget_line_id: Number(row.budget_line_id || 0) || null,
          budget_line_code: row.budget_line_code || null,
          budget_contract_id: Number(row.budget_contract_id || 0) || null,
          budget_contract_code: row.budget_contract_code || null,
          budget_document_id: Number(row.budget_document_id || 0) || null,
          budget_document_code: row.budget_document_code || null,
          domain_type: row.domain_type || null,
          domain_source_id: row.domain_source_id || null,
          domain_label: row.domain_label || null,
          allocation_type: 'amount',
          percentage: row.percentage !== '' ? round4(parseDecimal(row.percentage)) : null,
          allocated_amount: row.allocated_amount != null ? round2(row.allocated_amount) : null,
          notes: row.notes || null,
          metadata_json: {
            adjustment_kind: row.adjustment_kind || null,
            adjustment_label: row.adjustment_label || null,
          },
        })),
      },
    };
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Falha na operação financeira.');
    return result;
  }

  async function loadOptions() {
    optionsCache = await fetchJson(`/api/financial/schedules/options?company_id=${companyId}`);
    const counterpartyField = requireElement('field-counterparty');
    const correctionIndexField = requireElement('field-correction-index');
    const discountRuleField = requireElement('field-discount-rule');
    const settlementBankAccountField = $('settlement-bank-account');
    counterpartyField.innerHTML = buildOptions(optionsCache.counterparties, 'Selecione...', (item) => item.display_label || item.name || item.code);
    correctionIndexField.innerHTML = buildOptions(optionsCache.correction_indexes, 'Selecione...', (item) => item.display_label || item.name || item.code);
    discountRuleField.innerHTML = buildOptions(optionsCache.discount_rules, 'Selecione...', (item) => item.display_label || item.name || item.code);
    if (settlementBankAccountField) {
      settlementBankAccountField.innerHTML = buildOptions(optionsCache.bank_accounts, 'Selecione a conta...', (item) => item.display_label || item.name || item.code);
    }
    if (!selectedSchedule) {
      suggestDefaultCorrectionIndex(form.entry_type?.value || initialEntryType, { force: true });
    }
    refreshSuggestedDiscountAmountField();
    if (allocationRows.length) {
      allocationRows = allocationRows.map((row) => createAllocationRow(row));
      syncAdjustmentAllocationRows();
      renderAllocations();
    }
  }

  async function loadSchedules() {
    schedules = await fetchJson(`/api/financial/schedules?company_id=${companyId}`);
    renderList();
    if (initialScheduleId && !selectedSchedule) return selectSchedule(initialScheduleId);
    if (!selectedSchedule) window.startNewSchedule(initialEntryType);
  }

  window.selectSchedule = async (scheduleId) => {
    const [schedule, calculationLogs] = await Promise.all([
      fetchJson(`/api/financial/schedules/${scheduleId}?company_id=${companyId}`),
      loadCalculationLogs(scheduleId),
    ]);
    selectedSchedule = schedule;
    selectedCalculationLogs = calculationLogs;
    fillForm(selectedSchedule);
    renderList();
  };

  window.startNewSchedule = (entryType = initialEntryType) => {
    borderoLocked = false;
    selectedSchedule = null;
    selectedCalculationLogs = [];
    form.reset();
    Array.from(form.elements).forEach((field) => {
      if (field) field.disabled = false;
    });
    document.querySelectorAll('.sched-footer-actions button').forEach((button) => {
      button.disabled = false;
    });
    if (form.schedule_id) form.schedule_id.value = '';
    if (form.schedule_code) form.schedule_code.value = '';
    if (form.status) form.status.value = 'active';
    applyEntryType(entryType || '', { locked: !!entryType });
    clearPendingAttachments();
    allocationRows = [createAllocationRow({ percentage: '100' })];
    recalculateAllRowsFromPercentages();
    renderAllocations();
    renderAttachments([]);
    renderBaixas([]);
    renderCalculationLogs(null, []);
    $('baixas-tab-button')?.classList.add('hidden');
    $('calculation-log-tab-button')?.classList.add('hidden');
    setFieldValue('field-frequency', 'weekly');
    setDiscountAmountField(0, { manual: false });
    window.toggleRepeatFields();
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
    switchTab('agendamento');
    renderList();
  };

  async function saveSchedule() {
    const payload = buildPayload();
    const scheduleId = form.schedule_id?.value || '';
    const saved = await fetchJson(scheduleId ? `/api/financial/schedules/${scheduleId}?company_id=${companyId}` : `/api/financial/schedules?company_id=${companyId}`, {
      method: scheduleId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (saved.id && pendingAttachments.length) {
      await flushPendingAttachments(saved.id);
    }
    selectedSchedule = saved;
    if (isFormMode) {
      if (saved.id) await window.selectSchedule(saved.id);
    } else {
      await loadSchedules();
      if (saved.id) await window.selectSchedule(saved.id);
    }
    return saved;
  }

  function calculateSettlementGross(composition = getSettlementCompositionFromForm()) {
    return round2(Number(composition.principal || 0) + Number(composition.financial_correction || 0) - Number(composition.discount || 0));
  }

  function refreshSettlementGrossField(composition = getSettlementCompositionFromForm()) {
    setFieldValue('settlement-component-gross', toCurrencyInput(calculateSettlementGross(composition)));
  }

  function getSettlementCompositionFromForm() {
    const result = { principal: 0, financial_correction: 0, discount: 0 };
    document.querySelectorAll('[data-settlement-component]').forEach((input) => {
      result[input.dataset.settlementComponent] = round2(parseCurrency(input.value));
    });
    result.gross_amount = calculateSettlementGross(result);
    return result;
  }

  function getDefaultSettlementComposition(schedule = selectedSchedule) {
    const summary = schedule?.summary || {};
    const principalOpen = summary.principal_open ?? summary.open_total ?? getTopAmount();
    const backendAdjustments = Number(summary.adjustments_open || 0);
    const financialCorrection = backendAdjustments > 0 ? backendAdjustments : calculateCorrectionAmount();
    const backendDiscount = Number(summary.discounts_open || 0);
    const discount = backendDiscount > 0 ? backendDiscount : calculateDiscountAmount();
    const composition = {
      principal: round2(principalOpen || 0),
      financial_correction: round2(financialCorrection || 0),
      discount: round2(discount || 0),
    };
    composition.gross_amount = calculateSettlementGross(composition);
    return composition;
  }

  function setSettlementComponentInputs(composition = {}) {
    settlementCompositionHydrating = true;
    const normalized = {
      principal: composition.principal || 0,
      financial_correction: composition.financial_correction
        ?? composition.correction_financial
        ?? composition.correction
        ?? round2(
          Number(composition.monetary_correction || 0)
          + Number(composition.interest || 0)
          + Number(composition.fine || 0)
          + Number(composition.manual_adjustment || 0)
        ),
      discount: composition.discount || 0,
    };
    const mapping = {
      principal: 'settlement-component-principal',
      financial_correction: 'settlement-component-financial-correction',
      discount: 'settlement-component-discount',
    };
    Object.entries(mapping).forEach(([key, elementId]) => {
      const input = $(elementId);
      if (input) input.value = toCurrencyInput(normalized[key] || 0);
    });
    refreshSettlementGrossField(normalized);
    settlementCompositionHydrating = false;
  }

  function settlementPayload({ explicit = true } = {}) {
    const bankAccountId = Number(fieldValue('settlement-bank-account') || 0);
    const payload = {
      settlement_date: $('settlement-date')?.value || todayIso(),
      bank_account_id: bankAccountId || null,
      metadata_json: { source_context: 'schedule_assisted_settlement_modal' },
    };
    if (explicit) {
      payload.composition = getSettlementCompositionFromForm();
    } else {
      payload.composition = getDefaultSettlementComposition();
    }
    return payload;
  }

  function renderSettlementSimulation(simulation) {
    settlementSimulation = simulation || null;
    const statusEl = $('settlement-simulation-status');
    const summaryEl = $('settlement-simulation-summary');
    const afterEl = $('settlement-after-summary');
    const confirmButton = $('settlement-confirm-button');
    if (!simulation) {
      if (statusEl) statusEl.textContent = 'Informe a composição para simular a baixa.';
      if (summaryEl) summaryEl.innerHTML = '';
      if (afterEl) afterEl.innerHTML = '';
      if (confirmButton) confirmButton.disabled = true;
      return;
    }

    const composition = simulation.composition || {};
    const before = simulation.before || {};
    const after = simulation.after || {};
    const errors = simulation.errors || [];
    if (statusEl) {
      statusEl.textContent = simulation.valid ? 'Composição válida para baixa.' : errors.join(' ');
      statusEl.classList.toggle('is-invalid', !simulation.valid);
      statusEl.classList.toggle('is-valid', !!simulation.valid);
    }
    if (confirmButton) confirmButton.disabled = !simulation.valid;
    if (summaryEl) {
      summaryEl.innerHTML = [
        ['Principal antes', before.principal_open],
        ['Correção Financeira antes', before.adjustments_open],
        ['Total devido antes', before.total_due],
        ['Valor da Baixa', composition.gross_amount],
      ].map(([label, value]) => `<article><span>${label}</span><strong>${money(signedAmount(value || 0, selectedSchedule?.movement_nature))}</strong></article>`).join('');
    }
    if (afterEl) {
      afterEl.innerHTML = `
        <article><span>Principal após</span><strong>${money(signedAmount(after.principal_open || 0, selectedSchedule?.movement_nature))}</strong></article>
        <article><span>Correção Financeira após</span><strong>${money(signedAmount(after.adjustments_open || 0, selectedSchedule?.movement_nature))}</strong></article>
        <article><span>Total em aberto após</span><strong>${money(signedAmount(after.total_open || 0, selectedSchedule?.movement_nature))}</strong></article>
      `;
    }
  }

  async function simulateSettlementComposition({ explicit = true, hydrate = false } = {}) {
    const scheduleId = Number($('settlement-schedule-id')?.value || selectedSchedule?.id || 0);
    if (!scheduleId) return;
    const statusEl = $('settlement-simulation-status');
    if (statusEl) {
      statusEl.textContent = 'Simulando composição...';
      statusEl.classList.remove('is-invalid', 'is-valid');
    }
    const simulation = await fetchJson(`/api/financial/schedules/${scheduleId}/settlements/simulate?company_id=${companyId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settlementPayload({ explicit })),
    });
    if (hydrate) setSettlementComponentInputs(simulation.composition || {});
    renderSettlementSimulation(simulation);
  }

  function scheduleSettlementSimulation() {
    if (settlementCompositionHydrating) return;
    window.clearTimeout(settlementSimulationTimer);
    settlementSimulationTimer = window.setTimeout(() => {
      simulateSettlementComposition({ explicit: true }).catch((error) => {
        renderSettlementSimulation({ valid: false, errors: [error.message], composition: getSettlementCompositionFromForm() });
      });
    }, 350);
  }

  async function openSettlementCompositionModal(schedule) {
    if (!schedule?.id) throw new Error('Salve o título financeiro antes de baixar.');
    const modalEl = requireElement('settlement-composition-modal');
    requireElement('settlement-schedule-id').value = schedule.id;
    requireElement('settlement-date').value = todayIso();
    setFieldValue('settlement-bank-account', schedule.bank_account_id || selectedSchedule?.bank_account_id || '');
    requireElement('settlement-modal-subtitle').textContent = `${schedule.schedule_code || `Título ${schedule.id}`} · ${schedule.description || schedule.name || 'Sem histórico'}`;
    setSettlementComponentInputs({});
    renderSettlementSimulation(null);
    modalEl.classList.remove('hidden');
    modalEl.setAttribute('aria-hidden', 'false');
    await simulateSettlementComposition({ explicit: false, hydrate: true });
    if (autoOpenSettlement && window.history?.replaceState) {
      const nextParams = new URLSearchParams(window.location.search);
      nextParams.delete('open_settlement');
      const nextQuery = nextParams.toString();
      const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash || ''}`;
      window.history.replaceState({}, document.title, nextUrl);
    }
    window.setTimeout(() => $('settlement-date')?.focus(), 0);
  }

  window.closeSettlementCompositionModal = () => {
    window.clearTimeout(settlementSimulationTimer);
    const modalEl = $('settlement-composition-modal');
    if (!modalEl) return;
    modalEl.classList.add('hidden');
    modalEl.setAttribute('aria-hidden', 'true');
  };

  window.confirmAssistedSettlement = async () => {
    try {
      const scheduleId = Number($('settlement-schedule-id')?.value || selectedSchedule?.id || 0);
      if (!scheduleId) return;
      if (!Number(fieldValue('settlement-bank-account') || 0)) {
        throw new Error('Selecione a conta da baixa antes de confirmar.');
      }
      await fetchJson(`/api/financial/schedules/${scheduleId}/settlements/assisted?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settlementPayload({ explicit: true })),
      });
      window.location.href = '/financial/schedules';
    } catch (error) {
      alert(error.message);
    }
  };

  window.handleScheduleAction = async (action) => {
    try {
      if (borderoLocked) throw new Error(`Agendamento bloqueado pelo ${selectedSchedule?.bordero?.code || 'borderô'}.`);
      if (action === 'cancel') return window.location.href = '/financial/schedules';
      const saved = await saveSchedule();
      if (action === 'save_and_new') return window.startNewSchedule(initialEntryType);
      if (action === 'save_and_back') return window.location.href = '/financial/schedules';
      if (action === 'save_and_settle') {
        await openSettlementCompositionModal(saved);
      }
    } catch (error) {
      alert(error.message);
    }
  };

  window.generateDueSchedules = async () => {
    try {
      const result = await fetchJson(`/api/financial/schedules/generate-due?company_id=${companyId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      alert(`Geração concluída. ${result.generated_count || 0} lançamento(s) criado(s).`);
      await loadSchedules();
    } catch (error) {
      alert(error.message);
    }
  };

  window.uploadSelectedAttachments = async () => {
    try {
      const files = Array.from($('schedule-attachment-input').files || []);
      if (!files.length) throw new Error('Selecione pelo menos um arquivo.');
      if (selectedSchedule?.id) {
        for (const file of files) {
          const formData = new FormData();
          formData.append('file', file);
          await fetchJson(`/api/financial/schedules/${selectedSchedule.id}/attachments?company_id=${companyId}`, { method: 'POST', body: formData });
        }
        setFieldValue('schedule-attachment-input', '');
        await window.selectSchedule(selectedSchedule.id);
        switchTab('anexos');
        return;
      }
      files.forEach((file, idx) => {
        pendingAttachments.push({
          id: `pending-${Date.now()}-${idx}`,
          name: file.name,
          content_type: file.type || 'Arquivo',
          file,
          url: URL.createObjectURL(file),
        });
      });
      setFieldValue('schedule-attachment-input', '');
      renderAttachments(selectedSchedule?.attachments || []);
      switchTab('anexos');
    } catch (error) {
      alert(error.message);
    }
  };

  async function deleteAttachment(attachmentId) {

    try {
      if (!selectedSchedule?.id) return;
      await fetchJson(`/api/financial/schedules/${selectedSchedule.id}/attachments/${attachmentId}?company_id=${companyId}`, { method: 'DELETE' });
      await window.selectSchedule(selectedSchedule.id);
      switchTab('anexos');
    } catch (error) {
      alert(error.message);
    }
  }

  window.openAttachmentPreview = (url, name) => {
    $('attachment-preview-title').textContent = name || 'Visualizar anexo';
    $('attachment-preview-frame').src = url || '';
    $('attachment-preview-modal').classList.remove('hidden');
    $('attachment-preview-modal').setAttribute('aria-hidden', 'false');
  };

  window.closeAttachmentPreview = () => {
    $('attachment-preview-frame').src = '';
    $('attachment-preview-modal').classList.add('hidden');
    $('attachment-preview-modal').setAttribute('aria-hidden', 'true');
  };

  window.openCounterpartyModal = () => {
    $('counterparty-modal').classList.remove('hidden');
    $('counterparty-modal').setAttribute('aria-hidden', 'false');
  };

  window.closeCounterpartyModal = () => {
    $('counterparty-modal').classList.add('hidden');
    $('counterparty-modal').setAttribute('aria-hidden', 'true');
    $('counterparty-form').reset();
  };

  $('counterparty-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const formData = new FormData(event.currentTarget);
      const payload = {
        code: null,
        name: formData.get('name'),
        legal_name: formData.get('legal_name') || null,
        document_number: String(formData.get('document_number') || '').replace(/\D/g, '') || null,
        is_active: true,
        metadata_json: {},
      };
      const created = await fetchJson(`/api/financial/catalogs/counterparties?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      await loadOptions();
      setFieldValue('field-counterparty', created.id);
      window.closeCounterpartyModal();
    } catch (error) {
      alert(error.message);
    }
  });

  if (scheduleSearchEl) scheduleSearchEl.addEventListener('input', renderList);

  $('field-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
    refreshSuggestedDiscountAmountField();
    recalculateAllRowsFromPercentages();
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  });

  $('field-competence').addEventListener('input', (event) => {
    event.target.value = normalizeDateInput(event.target.value);
    $('field-due-date').setCustomValidity('');
  });

  $('field-due-date').addEventListener('input', (event) => {
    event.target.value = normalizeDateInput(event.target.value);
    event.target.setCustomValidity('');
    refreshSuggestedDiscountAmountField();
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  });

  $('field-competence').addEventListener('blur', () => {
    const competenceIso = parseDateToIso(fieldValue('field-competence'));
    const dueIso = parseDateToIso(fieldValue('field-due-date'));
    if (competenceIso && dueIso && compareIsoDates(dueIso, competenceIso) < 0) {
      $('field-due-date').setCustomValidity('O vencimento não pode ser anterior à competência.');
      $('field-due-date').reportValidity();
      return;
    }
    $('field-due-date').setCustomValidity('');
  });

  $('field-due-date').addEventListener('blur', () => {
    const competenceIso = parseDateToIso(fieldValue('field-competence'));
    const dueIso = parseDateToIso(fieldValue('field-due-date'));
    if (competenceIso && dueIso && compareIsoDates(dueIso, competenceIso) < 0) {
      $('field-due-date').setCustomValidity('O vencimento não pode ser anterior à competência.');
      $('field-due-date').reportValidity();
      return;
    }
    $('field-due-date').setCustomValidity('');
  });

  $('field-correction-index').addEventListener('change', () => {
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  });

  $('field-discount-rule').addEventListener('change', () => {
    const selectedRule = getSelectedDiscountRule();
    if (selectedRule) {
      const metadata = selectedRule.metadata_json || {};
      const suggestedValue = (() => {
        const amount = getTopAmount();
        const discountType = String(metadata.discount_type || '').toLowerCase();
        const value = Number(metadata.value || 0);
        if (value <= 0) return 0;
        if (discountType === 'percentage') return round2(amount * (value / 100));
        return round2(value);
      })();
      setDiscountAmountField(suggestedValue, { manual: false });
    } else {
      setDiscountAmountField(0, { manual: false });
    }
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  });

  $('field-discount-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
    event.target.dataset.manualOverride = '1';
    syncAdjustmentAllocationRows();
    renderAllocations();
    updateFinancialTotals();
  });

  document.querySelectorAll('[data-settlement-component]').forEach((input) => {
    input.addEventListener('input', (event) => {
      event.target.value = formatCurrencyFromDigits(event.target.value);
      refreshSettlementGrossField();
      scheduleSettlementSimulation();
    });
  });

  if ($('settlement-date')) {
    $('settlement-date').addEventListener('change', scheduleSettlementSimulation);
  }
  if ($('settlement-bank-account')) {
    $('settlement-bank-account').addEventListener('change', scheduleSettlementSimulation);
  }

  if ($('settlement-composition-form')) {
    $('settlement-composition-form').addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      const activeId = document.activeElement?.id || '';
      if (activeId !== 'settlement-confirm-button') {
        event.preventDefault();
      }
    });
    $('settlement-composition-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      await window.confirmAssistedSettlement();
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const modalEl = $('settlement-composition-modal');
    if (!modalEl || modalEl.classList.contains('hidden')) return;
    window.closeSettlementCompositionModal();
  });

  $('counterparty-document').addEventListener('input', (event) => {
    const digits = String(event.target.value || '').replace(/\D/g, '').slice(0, 14);
    event.target.value = digits.length <= 11
      ? digits.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2')
      : digits.replace(/(\d{2})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1/$2').replace(/(\d{4})(\d{1,2})$/, '$1-$2');
  });

  $('allocations-body').addEventListener('input', (event) => {
    const field = event.target.dataset.field;
    const index = Number(event.target.dataset.index || -1);
    if (index < 0 || !field || !allocationRows[index]) return;
    if (allocationRows[index].adjustment_kind) return;

    if (field === 'percentage') {
      allocationRows[index].percentage = event.target.value;
      recalculateRowFromPercentage(index);
      const added = ensureRemainingRow(index);
      if (added) {
        renderAllocations();
      } else {
        syncAllocationRowInputs(index);
      }
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

  $('allocations-body').addEventListener('change', (event) => {
    const field = event.target.dataset.field;
    const index = Number(event.target.dataset.index || -1);
    if (index < 0 || !field || !allocationRows[index]) return;
    if (allocationRows[index].adjustment_kind && ['percentage', 'allocated_amount_display'].includes(field)) return;
    if (field === 'budget_document_id') {
      const value = event.target.value;
      const item = (optionsCache.budget_documents || []).find((candidate) => String(candidate.id) === String(value));
      if (!value || !item) {
        allocationRows[index].budget_version_id = '';
        allocationRows[index].budget_version_code = null;
        allocationRows[index].budget_line_id = '';
        allocationRows[index].budget_line_code = null;
        allocationRows[index].budget_contract_id = '';
        allocationRows[index].budget_contract_code = null;
        allocationRows[index].budget_document_id = '';
        allocationRows[index].budget_document_code = null;
        return;
      }
      allocationRows[index].budget_document_id = value;
      allocationRows[index].budget_document_code = item?.code || null;
      const contract = (optionsCache.budget_contracts || []).find((candidate) => String(candidate.id) === String(item.budget_contract_id || ''));
      const line = (optionsCache.budget_lines || []).find((candidate) => String(candidate.id) === String(contract?.budget_line_id || ''));
      const version = (optionsCache.budget_versions || []).find((candidate) => String(candidate.id) === String(line?.budget_version_id || ''));
      allocationRows[index].budget_contract_id = contract ? String(contract.id) : '';
      allocationRows[index].budget_contract_code = contract?.code || null;
      allocationRows[index].budget_line_id = line ? String(line.id) : '';
      allocationRows[index].budget_line_code = line?.code || null;
      allocationRows[index].budget_version_id = version ? String(version.id) : '';
      allocationRows[index].budget_version_code = version?.code || null;
      return;
    }
    if (field === 'domain_value') {
      const value = event.target.value;
      allocationRows[index].domain_value = value;
      if (!value) {
        allocationRows[index].domain_type = null;
        allocationRows[index].domain_source_id = null;
        allocationRows[index].domain_label = null;
        return;
      }
      const [domainType, sourceId] = value.split(':');
      const item = optionsCache.enabled_domains.find((candidate) => candidate.domain_type === domainType && String(candidate.source_id) === String(sourceId));
      allocationRows[index].domain_type = domainType;
      allocationRows[index].domain_source_id = Number(sourceId);
      allocationRows[index].domain_label = item?.display_label || null;
      return;
    }
    allocationRows[index][field] = event.target.value;
  });

  $('allocations-body').addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const index = Number(button.dataset.index || -1);
    if (allocationRows[index]?.adjustment_kind) return;
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

  $('attachments-list').addEventListener('click', (event) => {
    const preview = event.target.closest('[data-attachment-preview]');
    if (preview) {
      return window.openAttachmentPreview(preview.dataset.attachmentPreview, preview.dataset.attachmentName);
    }
    const pendingButton = event.target.closest('button[data-pending-attachment-delete]');
    if (pendingButton) {
      const pendingId = pendingButton.dataset.pendingAttachmentDelete;
      const item = pendingAttachments.find((candidate) => candidate.id === pendingId);
      if (item) { try { URL.revokeObjectURL(item.url); } catch (_) {} }
      pendingAttachments = pendingAttachments.filter((candidate) => candidate.id !== pendingId);
      renderAttachments(selectedSchedule?.attachments || []);
      return;
    }
    const button = event.target.closest('button[data-attachment-delete]');
    if (button) deleteAttachment(button.dataset.attachmentDelete);
  });

  if (scheduleListEl) {
    scheduleListEl.addEventListener('click', (event) => {
      const item = event.target.closest('.schedule-item[data-id]');
      if (item) window.selectSchedule(Number(item.dataset.id));
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadOptions();
      if (isFormMode) {
        if (initialScheduleId) {
          await window.selectSchedule(initialScheduleId);
          if (autoOpenSettlement && selectedSchedule?.id) {
            await openSettlementCompositionModal(selectedSchedule);
          }
        } else {
          window.startNewSchedule(initialEntryType);
        }
      } else {
        await loadSchedules();
      }
      window.toggleRepeatFields();
      updateFinancialTotals();
    } catch (error) {
      alert(error.message);
    }
  });
})();
