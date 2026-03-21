(function () {
  const page = document.querySelector('.sched-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const initialScheduleId = Number(page.dataset.scheduleId || 0);
  let schedules = [];
  let selectedSchedule = null;
  let optionsCache = { counterparties: [], chart_accounts: [], cost_centers: [], correction_indexes: [], discount_rules: [], enabled_domains: [] };
  let allocationRows = [];
  let pendingAttachments = [];

  const $ = (id) => document.getElementById(id);
  const form = $('schedule-form');
  const entryTypeBanner = $('entry-type-banner');
  const rateioSummary = $('rateio-summary');

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

  const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
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
    const receivable = entryType === 'receivable';
    entryTypeBanner.textContent = receivable
      ? 'Conta a receber · preenchimento orientado para recebimentos.'
      : 'Conta a pagar · preenchimento orientado para pagamentos.';
  }

  window.setEntryType = (entryType) => {
    form.querySelector('input[name="entry_type"]').value = entryType;
    document.querySelectorAll('.type-chip').forEach((chip) => chip.classList.toggle('active', chip.dataset.entryType === entryType));
    updateEntryTypePresentation(entryType);
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
      body.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum rateio informado.</td></tr>';
      renderAllocationSummary();
      return;
    }

    const chartOptions = buildOptions(analyticChartAccounts(), 'Selecione...', buildChartAccountLabel);
    const costCenterOptions = buildOptions(finalCostCenters(), 'Selecione...', buildCostCenterLabel);

    body.innerHTML = allocationRows.map((row, index) => `
      <tr>
        <td><select data-index="${index}" data-field="chart_account_id">${chartOptions}</select></td>
        <td><select data-index="${index}" data-field="cost_center_id">${costCenterOptions}</select></td>
        <td><select data-index="${index}" data-field="domain_value">${buildDomainOptions(row.domain_value || '')}</select></td>
        <td><input data-index="${index}" data-field="percentage" value="${row.percentage ?? ''}" inputmode="decimal"></td>
        <td><input data-index="${index}" data-field="allocated_amount_display" value="${row.allocated_amount_display || ''}" inputmode="numeric"></td>
        <td><div class="rateio-actions"><button type="button" class="btn btn-secondary btn-icon" data-action="duplicate" data-index="${index}">+</button><button type="button" class="btn btn-secondary btn-icon" data-action="remove" data-index="${index}">×</button></div></td>
      </tr>`).join('');

    allocationRows.forEach((row, index) => {
      body.querySelector(`select[data-field="chart_account_id"][data-index="${index}"]`).value = row.chart_account_id || '';
      body.querySelector(`select[data-field="cost_center_id"][data-index="${index}"]`).value = row.cost_center_id || '';
    });

    renderAllocationSummary();
  }

  function createAllocationRow(defaults = {}) {
    return {
      chart_account_id: defaults.chart_account_id || '',
      cost_center_id: defaults.cost_center_id || '',
      domain_type: defaults.domain_type || null,
      domain_source_id: defaults.domain_source_id || null,
      domain_label: defaults.domain_label || null,
      domain_value: defaults.domain_type && defaults.domain_source_id ? `${defaults.domain_type}:${defaults.domain_source_id}` : '',
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
    const search = ($('schedule-search').value || '').trim().toLowerCase();
    const items = schedules.filter((item) => `${item.schedule_code || ''} ${item.description || item.name || ''} ${item.metadata_json?.counterparty_name || ''}`.toLowerCase().includes(search));
    $('schedule-list').innerHTML = items.length ? items.map((item) => `
      <article class="schedule-item ${selectedSchedule && selectedSchedule.id === item.id ? 'active' : ''}" data-id="${item.id}">
        <strong>${item.description || item.name || 'Sem histórico'}</strong>
        <small>${item.schedule_code || '-'} · ${money(item.template_amount || 0)}</small>
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
        <small>${formatIso(entry.occurred_on || entry.competence_date || entry.due_date)} · ${money(entry.original_amount || 0)}</small>
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
    form.schedule_id.value = schedule.id || '';
    form.schedule_code.value = schedule.schedule_code || '';
    form.status.value = schedule.status || 'active';
    window.setEntryType(schedule.entry_type || 'receivable');
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
    window.toggleRepeatFields();
  }

  function validateAllocationSummary() {
    const summary = summarizeAllocations();
    if (!summary.percentagesOk) throw new Error('A soma dos percentuais do rateio deve ser exatamente 100%.');
    if (!summary.valuesOk) throw new Error('A soma dos valores do rateio deve ser igual ao valor informado no agendamento.');
  }

  function buildPayload() {
    const description = $('field-description').value.trim();
    const counterpartyId = Number($('field-counterparty').value || 0);
    const competenceIso = parseDateToIso($('field-competence').value);
    const dueIso = parseDateToIso($('field-due-date').value);
    const amount = getTopAmount();
    if (!description) throw new Error('Informe o histórico do agendamento.');
    if (!counterpartyId) throw new Error('Selecione um favorecido.');
    if (!competenceIso || !dueIso) throw new Error('Informe datas válidas para competência e vencimento.');
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
  }

  async function loadSchedules() {
    schedules = await fetchJson(`/api/financial/schedules?company_id=${companyId}`);
    renderList();
    if (initialScheduleId && !selectedSchedule) return selectSchedule(initialScheduleId);
    if (!selectedSchedule) window.startNewSchedule();
  }

  window.selectSchedule = async (scheduleId) => {
    selectedSchedule = await fetchJson(`/api/financial/schedules/${scheduleId}?company_id=${companyId}`);
    fillForm(selectedSchedule);
    renderList();
  };

  window.startNewSchedule = () => {
    selectedSchedule = null;
    form.reset();
    form.schedule_id.value = '';
    form.schedule_code.value = '';
    form.status.value = 'active';
    window.setEntryType('receivable');
    clearPendingAttachments();
    allocationRows = [createAllocationRow({ percentage: '100' })];
    recalculateAllRowsFromPercentages();
    renderAllocations();
    renderAttachments([]);
    renderBaixas([]);
    $('baixas-tab-button').classList.add('hidden');
    $('field-frequency').value = 'weekly';
    window.toggleRepeatFields();
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
    await loadSchedules();
    if (saved.id) await window.selectSchedule(saved.id);
    return saved;
  }

  window.handleScheduleAction = async (action) => {
    try {
      if (action === 'cancel') return window.startNewSchedule();
      const saved = await saveSchedule();
      if (action === 'save_and_new') return window.startNewSchedule();
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

  $('schedule-search').addEventListener('input', renderList);

  $('field-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
    recalculateAllRowsFromPercentages();
    renderAllocations();
  });

  $('field-competence').addEventListener('input', (event) => {
    event.target.value = normalizeDateInput(event.target.value);
  });

  $('field-due-date').addEventListener('input', (event) => {
    event.target.value = normalizeDateInput(event.target.value);
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

  $('schedule-list').addEventListener('click', (event) => {
    const item = event.target.closest('.schedule-item[data-id]');
    if (item) window.selectSchedule(Number(item.dataset.id));
  });

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadOptions();
      await loadSchedules();
      window.toggleRepeatFields();
    } catch (error) {
      alert(error.message);
    }
  });
})();
