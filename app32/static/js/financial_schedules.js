(function () {
  const page = document.querySelector('.sched-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const initialScheduleId = Number(page.dataset.scheduleId || 0);
  const initialEntryType = String(page.dataset.initialEntryType || '').trim().toLowerCase();
  const isFormMode = page.classList.contains('sched-page--form');
  let schedules = [];
  let selectedSchedule = null;
  let entryTypeLocked = false;
  let optionsCache = {
    counterparties: [],
    chart_accounts: [],
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

  const $ = (id) => document.getElementById(id);
  const form = $('schedule-form');
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
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
  };

  const parseDateToIso = (value) => {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits.length !== 8) return null;
    const [day, month, year] = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)];
    const candidate = new Date(Number(year), Number(month) - 1, Number(day));
    if (candidate.getFullYear() !== Number(year) || candidate.getMonth() + 1 !== Number(month) || candidate.getDate() !== Number(day)) return null;
    return `${year}-${month}-${day}`;
  };

  const formatIso = (value) => {
    if (!value) return '';
    const [year, month, day] = String(value).split('-');
    return year && month && day ? `${day}/${month}/${year}` : value;
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
    form.querySelector('input[name="entry_type"]').value = entryType;
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
    const enabled = $('field-repeat-toggle').value === 'true';
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
    if ($('field-updated-amount')) $('field-updated-amount').value = updatedAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if ($('field-open-balance')) $('field-open-balance').value = openBalance.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getTopAmount() {
    return round2(parseCurrency($('field-amount').value));
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
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Valor total do rateio: ${money(summary.totalAllocated)}</span>`,
      `<span class="rateio-pill ${summary.percentagesOk ? 'is-ok' : 'is-error'}">Faltante percentual: ${formatPercent(summary.remainingPercentage)}%</span>`,
      `<span class="rateio-pill ${summary.valuesOk ? 'is-ok' : 'is-error'}">Faltante valor: ${money(summary.remainingValue)}</span>`
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
      <tr>
        <td class="rateio-cell rateio-cell--chart-account"><select data-index="${index}" data-field="chart_account_id" aria-label="Plano de conta da linha ${index + 1}">${chartOptions}</select></td>
        <td class="rateio-cell rateio-cell--cost-center"><select data-index="${index}" data-field="cost_center_id" aria-label="Centro de resultado da linha ${index + 1}">${costCenterOptions}</select></td>
        <td class="rateio-cell rateio-cell--budget-document"><select data-index="${index}" data-field="budget_document_id" aria-label="NF ou assemelhado da linha ${index + 1}">${budgetDocumentOptions}</select></td>
        <td class="rateio-cell rateio-cell--domain"><select data-index="${index}" data-field="domain_value" aria-label="Projeto ou processo da linha ${index + 1}">${buildDomainOptions(row.domain_value || '')}</select></td>
        <td class="rateio-cell rateio-cell--percentage"><input data-index="${index}" data-field="percentage" value="${row.percentage ?? ''}" inputmode="decimal" placeholder="0,0000" aria-label="Percentual da linha ${index + 1}"></td>
        <td class="rateio-cell rateio-cell--amount"><input data-index="${index}" data-field="allocated_amount_display" value="${row.allocated_amount_display || ''}" inputmode="numeric" placeholder="0,00" aria-label="Valor da linha ${index + 1}"></td>
        <td class="rateio-cell rateio-cell--actions"><div class="rateio-actions"><button type="button" class="btn btn-secondary btn-icon" data-action="duplicate" data-index="${index}" aria-label="Duplicar linha ${index + 1}">+</button><button type="button" class="btn btn-secondary btn-icon" data-action="remove" data-index="${index}" aria-label="Remover linha ${index + 1}">×</button></div></td>
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
      percentage: defaults.percentage ?? '100',
      allocated_amount: defaults.allocated_amount ?? null,
      allocated_amount_display: defaults.allocated_amount_display || '',
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
      percentage: item.percentage != null ? formatPercent(item.percentage) : '',
      allocated_amount: item.allocated_amount != null ? round2(item.allocated_amount) : null,
      allocated_amount_display: item.allocated_amount ? Number(item.allocated_amount).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '',
    }));
    if (!allocationRows.length) {
      allocationRows = [createAllocationRow({ percentage: '100' })];
    }
    recalculateAllRowsFromPercentages();
    renderAllocations();
  }

  function fillForm(schedule) {
    borderoLocked = Boolean(schedule.is_bordero_locked);
    form.schedule_id.value = schedule.id || '';
    form.schedule_code.value = schedule.schedule_code || '';
    form.status.value = schedule.status || 'active';
    applyEntryType(schedule.entry_type || '', { locked: true });
    $('field-description').value = schedule.description || schedule.name || '';
    $('field-document-number').value = schedule.document_number || '';
    $('field-counterparty').value = schedule.counterparty_id || '';
    $('field-amount').value = Number(schedule.template_amount || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    $('field-competence').value = formatIso(schedule.start_date || schedule.first_due_date);
    $('field-due-date').value = formatIso(schedule.first_due_date || schedule.next_due_date);
    $('field-correction-index').value = schedule.correction_index_id || '';
    $('field-discount-rule').value = schedule.discount_rule_id || '';
    $('field-repeat-toggle').value = (schedule.frequency || 'one_time') === 'one_time' ? 'false' : 'true';
    $('field-frequency').value = schedule.frequency === 'monthly' ? 'monthly' : schedule.frequency === 'yearly' ? 'yearly' : 'weekly';
    $('field-interval-value').value = schedule.interval_value || 1;
    $('field-repeat-count').value = schedule.metadata_json?.repeat_count || 1;
    $('field-competence-mode').value = schedule.competence_mode || 'same_as_due';
    clearPendingAttachments();
    hydrateAllocations(schedule);
    renderAttachments(schedule.attachments || []);
    renderBaixas(schedule.related_entries || []);
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
    updateFinancialTotals();
  }

  function validateAllocationSummary() {
    const summary = summarizeAllocations();
    if (!summary.percentagesOk) throw new Error('A soma dos percentuais do rateio deve ser exatamente 100%.');
    if (!summary.valuesOk) throw new Error('A soma dos valores do rateio deve ser igual ao valor informado no agendamento.');
  }

  function buildPayload() {
    if (!form.entry_type.value) {
      throw new Error('Escolha primeiro se o agendamento é de Recebimentos ou Pagamentos.');
    }
    const description = $('field-description').value.trim();
    const counterpartyId = Number($('field-counterparty').value || 0);
    const competenceIso = parseDateToIso($('field-competence').value);
    const dueIso = parseDateToIso($('field-due-date').value);
    const amount = getTopAmount();
    if (!description) throw new Error('Informe o histórico do agendamento.');
    if (!counterpartyId) throw new Error('Selecione um favorecido.');
    if (!competenceIso || !dueIso) throw new Error('Informe datas válidas para competência e vencimento.');
    if (compareIsoDates(dueIso, competenceIso) < 0) {
      throw new Error('O vencimento não pode ser anterior à competência.');
    }
    if (!amount || amount <= 0) throw new Error('Informe um valor válido.');
    validateAllocationSummary();
    const frequency = $('field-repeat-toggle').value === 'true' ? $('field-frequency').value : 'one_time';
    return {
      schedule_code: form.schedule_code.value || undefined,
      name: description.slice(0, 120),
      description,
      memo: null,
      entry_type: form.entry_type.value,
      movement_nature: form.entry_type.value === 'receivable' ? 'credit' : 'debit',
      origin_type: 'manual',
      status: form.status.value || 'active',
      frequency,
      interval_value: Number($('field-interval-value').value || 1),
      start_date: competenceIso,
      first_due_date: dueIso,
      next_due_date: dueIso,
      end_date: null,
      day_of_month: frequency === 'monthly' ? Number(dueIso.split('-')[2]) : null,
      weekday: frequency === 'weekly' ? new Date(`${dueIso}T00:00:00`).getDay() : null,
      template_amount: amount,
      counterparty_id: counterpartyId,
      chart_account_id: Number(allocationRows[0]?.chart_account_id || 0) || null,
      cost_center_id: Number(allocationRows[0]?.cost_center_id || 0) || null,
      document_number_prefix: null,
      generate_advance_days: 0,
      auto_post: false,
      notes: null,
      metadata_json: {
        ...(selectedSchedule?.metadata_json || {}),
        document_number: $('field-document-number').value.trim() || null,
        correction_index_id: Number($('field-correction-index').value || 0) || null,
        discount_rule_id: Number($('field-discount-rule').value || 0) || null,
        competence_mode: $('field-competence-mode').value,
        repeat_count: Number($('field-repeat-count').value || 1),
        attachments: selectedSchedule?.attachments || [],
        counterparty_name: $('field-counterparty').selectedOptions?.[0]?.textContent || null,
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
          allocation_type: row.allocated_amount ? 'amount' : 'percentage',
          percentage: row.percentage !== '' ? round4(parseDecimal(row.percentage)) : null,
          allocated_amount: row.allocated_amount != null ? round2(row.allocated_amount) : null,
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
    $('field-counterparty').innerHTML = buildOptions(optionsCache.counterparties, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('field-correction-index').innerHTML = buildOptions(optionsCache.correction_indexes, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('field-discount-rule').innerHTML = buildOptions(optionsCache.discount_rules, 'Selecione...', (item) => item.display_label || item.name || item.code);
    if (!selectedSchedule) {
      suggestDefaultCorrectionIndex(form.entry_type.value || initialEntryType, { force: true });
    }
    if (allocationRows.length) {
      allocationRows = allocationRows.map((row) => createAllocationRow(row));
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
    selectedSchedule = await fetchJson(`/api/financial/schedules/${scheduleId}?company_id=${companyId}`);
    fillForm(selectedSchedule);
    renderList();
  };

  window.startNewSchedule = (entryType = initialEntryType) => {
    borderoLocked = false;
    selectedSchedule = null;
    form.reset();
    Array.from(form.elements).forEach((field) => {
      if (field) field.disabled = false;
    });
    document.querySelectorAll('.sched-footer-actions button').forEach((button) => {
      button.disabled = false;
    });
    form.schedule_id.value = '';
    form.schedule_code.value = '';
    form.status.value = 'active';
    applyEntryType(entryType || '', { locked: !!entryType });
    clearPendingAttachments();
    allocationRows = [createAllocationRow({ percentage: '100' })];
    recalculateAllRowsFromPercentages();
    renderAllocations();
    renderAttachments([]);
    renderBaixas([]);
    $('baixas-tab-button').classList.add('hidden');
    $('field-frequency').value = 'weekly';
    window.toggleRepeatFields();
    updateFinancialTotals();
    switchTab('agendamento');
    renderList();
  };

  async function saveSchedule() {
    const payload = buildPayload();
    const scheduleId = form.schedule_id.value;
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

  window.handleScheduleAction = async (action) => {
    try {
      if (borderoLocked) throw new Error(`Agendamento bloqueado pelo ${selectedSchedule?.bordero?.code || 'borderô'}.`);
      if (action === 'cancel') return window.location.href = '/financial/schedules';
      const saved = await saveSchedule();
      if (action === 'save_and_new') return window.startNewSchedule(initialEntryType);
      if (action === 'save_and_back') return window.location.href = '/financial/schedules';
      if (action === 'save_and_settle') {
        const result = await fetchJson(`/api/financial/schedules/${saved.id}/create-entry?company_id=${companyId}`, { method: 'POST' });
        if (result.entry?.id) window.location.href = `/financial/entries/${result.entry.id}`;
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
        $('schedule-attachment-input').value = '';
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
      $('schedule-attachment-input').value = '';
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
      $('field-counterparty').value = created.id;
      window.closeCounterpartyModal();
    } catch (error) {
      alert(error.message);
    }
  });

  if (scheduleSearchEl) scheduleSearchEl.addEventListener('input', renderList);

  $('field-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
    recalculateAllRowsFromPercentages();
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
    updateFinancialTotals();
  });

  $('field-competence').addEventListener('blur', () => {
    const competenceIso = parseDateToIso($('field-competence').value);
    const dueIso = parseDateToIso($('field-due-date').value);
    if (competenceIso && dueIso && compareIsoDates(dueIso, competenceIso) < 0) {
      $('field-due-date').setCustomValidity('O vencimento não pode ser anterior à competência.');
      $('field-due-date').reportValidity();
      return;
    }
    $('field-due-date').setCustomValidity('');
  });

  $('field-due-date').addEventListener('blur', () => {
    const competenceIso = parseDateToIso($('field-competence').value);
    const dueIso = parseDateToIso($('field-due-date').value);
    if (competenceIso && dueIso && compareIsoDates(dueIso, competenceIso) < 0) {
      $('field-due-date').setCustomValidity('O vencimento não pode ser anterior à competência.');
      $('field-due-date').reportValidity();
      return;
    }
    $('field-due-date').setCustomValidity('');
  });

  $('field-correction-index').addEventListener('change', () => {
    updateFinancialTotals();
  });

  $('field-discount-rule').addEventListener('change', () => {
    updateFinancialTotals();
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
