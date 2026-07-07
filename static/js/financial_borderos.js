(function () {
  const page = document.querySelector('.bordero-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const borderoId = Number(page.dataset.borderoId || 0);
  const initialType = String(page.dataset.initialBorderoType || '').trim().toLowerCase();

  const state = {
    bordero: null,
    schedules: [],
    bankAccounts: [],
    selectedType: initialType || '',
    editingSettlementId: null,
    selectedScheduleIds: new Set(),
    scheduleAmounts: new Map(),
  };

  const $ = (id) => document.getElementById(id);
  const createSection = $('bordero-create-section');
  const detailSection = $('bordero-detail-section');
  const createButton = $('bordero-create-button');
  const saveButton = $('bordero-save-button');
  const deleteButton = $('bordero-delete-button');
  const settlementButton = $('bordero-settlement-button');
  const settlementCancelWrap = $('bordero-settlement-cancel-wrap');
  const settlementCancelButton = $('bordero-settlement-cancel-button');
  const banner = $('bordero-banner');
  const typeInfo = $('bordero-type-info');
  const selectAllSchedules = $('bordero-select-all-schedules');
  const visibleSelectionChip = $('bordero-visible-selection-chip');
  const scheduleFilterCount = $('bordero-schedule-filters-count');
  const applyScheduleFiltersButton = $('bordero-apply-schedule-filters');
  const clearScheduleFiltersButton = $('bordero-clear-schedule-filters');
  const scheduleFilters = {
    counterparty: $('bordero-filter-counterparty'),
    dueFrom: $('bordero-filter-due-from'),
    dueTo: $('bordero-filter-due-to'),
    minAmount: $('bordero-filter-min-amount'),
    maxAmount: $('bordero-filter-max-amount'),
  };
  const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const formatDate = (value) => {
    if (!value) return '-';
    const [year, month, day] = String(value).split('-');
    return year && month && day ? `${day}/${month}/${year}` : value;
  };
  const typeLabel = (value) => value === 'payable' ? 'Pagamento' : 'Recebimento';
  const statusLabel = (value) => ({ open: 'Aberto', partially_settled: 'Parcialmente liquidado', settled: 'Liquidado', cancelled: 'Cancelado', draft: 'Rascunho' }[value] || value || '-');
  const settlementStatusLabel = (value) => ({ posted: 'Postado', cancelled: 'Cancelado' }[value] || value || '-');

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Falha na operação de borderô.');
    return payload;
  }

  function formatCurrencyFromDigits(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return '';
    const cents = digits.padStart(3, '0');
    const intPart = cents.slice(0, -2).replace(/^0+/, '') || '0';
    return `${intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents.slice(-2)}`;
  }

  function parseCurrency(value) {
    const normalized = String(value || '').replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, '');
    return normalized ? Number(normalized) : 0;
  }

  function scheduleCounterparty(item) {
    const summary = item.summary || {};
    return summary.counterparty_name || item.metadata_json?.counterparty_name || '';
  }

  function scheduleDueDate(item) {
    return String(item.next_due_date || item.first_due_date || '').slice(0, 10);
  }

  function scheduleOpenTotal(item) {
    return Number((item.summary || {}).open_total || 0);
  }

  function defaultScheduleAmount(item) {
    return formatCurrencyFromDigits(Math.round(scheduleOpenTotal(item) * 100));
  }

  function getScheduleAmount(scheduleId, fallbackItem) {
    const key = Number(scheduleId || 0);
    return state.scheduleAmounts.get(key) || defaultScheduleAmount(fallbackItem);
  }

  function setScheduleAmount(scheduleId, value) {
    const key = Number(scheduleId || 0);
    if (!key) return;
    state.scheduleAmounts.set(key, value);
  }

  function syncVisibleSelectionState() {
    document.querySelectorAll('#bordero-schedule-body tr[data-schedule-id]').forEach((row) => {
      const scheduleId = Number(row.dataset.scheduleId || 0);
      const selector = row.querySelector('.bordero-schedule-selector');
      const amountInput = row.querySelector('.bordero-amount-input');
      if (!scheduleId) return;
      if (amountInput) setScheduleAmount(scheduleId, amountInput.value);
      if (selector?.checked) state.selectedScheduleIds.add(scheduleId);
      else state.selectedScheduleIds.delete(scheduleId);
    });
  }

  function bankAccountLabel(item) {
    return item.display_label || item.name || item.code || `Conta ${item.id}`;
  }

  function renderSettlementBankAccountOptions() {
    const html = ['<option value="">Selecione...</option>']
      .concat(state.bankAccounts.map((item) => `<option value="${item.id}">${bankAccountLabel(item)}</option>`))
      .join('');
    $('settlement-bank-account').innerHTML = html;
  }

  function ensureCreatedDateValue(value) {
    const normalized = String(value || '').trim();
    if (normalized) {
      $('bordero-created-date').value = normalized.slice(0, 10);
      return;
    }
    $('bordero-created-date').value = new Date().toISOString().slice(0, 10);
  }

  function applyType(type) {
    state.selectedType = type;
    page.dataset.borderoType = type || '';
    typeInfo.textContent = type ? typeLabel(type) : 'Tipo não definido';
    if (!type) {
      banner.textContent = 'Selecione o tipo do borderô e os títulos financeiros elegíveis.';
      $('bordero-schedule-body').innerHTML = '<tr><td colspan="6" class="empty-state">Selecione um tipo para carregar os títulos financeiros.</td></tr>';
      renderSelectionSummary();
      return;
    }
    banner.textContent = `${typeLabel(type)} · somente títulos financeiros com saldo aberto e sem outro borderô ativo ficam elegíveis para agrupamento.`;
    renderEligibleSchedules();
  }

  function eligibleSchedules() {
    const search = String($('bordero-schedule-search')?.value || '').trim().toLowerCase();
    const counterpartyFilter = String(scheduleFilters.counterparty?.value || '').trim().toLowerCase();
    const dueFrom = String(scheduleFilters.dueFrom?.value || '').trim();
    const dueTo = String(scheduleFilters.dueTo?.value || '').trim();
    const minAmount = parseCurrency(scheduleFilters.minAmount?.value);
    const maxAmount = parseCurrency(scheduleFilters.maxAmount?.value);
    return state.schedules.filter((item) => {
      const summary = item.summary || {};
      const openTotal = scheduleOpenTotal(item);
      const locked = Boolean(item.is_bordero_locked || summary.is_bordero_locked);
      const counterparty = scheduleCounterparty(item);
      const dueDate = scheduleDueDate(item);
      const haystack = `${item.schedule_code || ''} ${item.description || ''} ${counterparty}`.toLowerCase();
      if (!state.selectedType || item.entry_type !== state.selectedType) return false;
      if (locked || openTotal <= 0) return false;
      if (search && !haystack.includes(search)) return false;
      if (counterpartyFilter && !counterparty.toLowerCase().includes(counterpartyFilter)) return false;
      if (dueFrom && (!dueDate || dueDate < dueFrom)) return false;
      if (dueTo && (!dueDate || dueDate > dueTo)) return false;
      if (minAmount > 0 && openTotal < minAmount) return false;
      if (maxAmount > 0 && openTotal > maxAmount) return false;
      return true;
    });
  }

  function renderSelectionSummary() {
    syncVisibleSelectionState();
    const visibleRows = Array.from(document.querySelectorAll('#bordero-schedule-body tr[data-schedule-id]'));
    const visibleCount = visibleRows.length;
    const visibleSelectedCount = visibleRows.filter((row) => state.selectedScheduleIds.has(Number(row.dataset.scheduleId || 0))).length;
    const hiddenSelectedCount = Array.from(state.selectedScheduleIds).filter((scheduleId) => !visibleRows.some((row) => Number(row.dataset.scheduleId || 0) === scheduleId)).length;
    const count = state.selectedScheduleIds.size;
    const total = Array.from(state.selectedScheduleIds).reduce((acc, scheduleId) => {
      const item = state.schedules.find((schedule) => Number(schedule.id) === Number(scheduleId));
      if (!item) return acc;
      return acc + parseCurrency(getScheduleAmount(scheduleId, item));
    }, 0);
    $('bordero-create-summary').innerHTML = [
      `<span>Títulos selecionados: ${count}</span>`,
      `<span>Total do borderô: ${money(total)}</span>`,
      hiddenSelectedCount ? `<span>${hiddenSelectedCount} selecionado(s) fora do filtro atual</span>` : '',
    ].join('');
    if (visibleSelectionChip) visibleSelectionChip.textContent = `${visibleSelectedCount}/${visibleCount} títulos visíveis selecionados`;
    if (selectAllSchedules) {
      selectAllSchedules.checked = visibleCount > 0 && visibleSelectedCount === visibleCount;
      selectAllSchedules.indeterminate = visibleSelectedCount > 0 && visibleSelectedCount < visibleCount;
      selectAllSchedules.disabled = visibleCount === 0;
    }
    updateScheduleFilterIndicators();
  }

  function getActiveScheduleFilters() {
    return Object.values(scheduleFilters).filter((input) => String(input?.value || '').trim());
  }

  function updateScheduleFilterIndicators() {
    const activeCount = getActiveScheduleFilters().length;
    if (scheduleFilterCount) scheduleFilterCount.textContent = String(activeCount);
  }

  function renderEligibleSchedules() {
    syncVisibleSelectionState();
    const tbody = $('bordero-schedule-body');
    const items = eligibleSchedules();
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum título financeiro elegível para este tipo.</td></tr>';
      renderSelectionSummary();
      return;
    }

    tbody.innerHTML = items.map((item) => {
      const summary = item.summary || {};
      const openTotal = scheduleOpenTotal(item);
      const counterparty = scheduleCounterparty(item) || '-';
      const checked = state.selectedScheduleIds.has(Number(item.id)) ? 'checked' : '';
      const amountValue = getScheduleAmount(item.id, item);
      return `
        <tr data-schedule-id="${item.id}">
          <td data-label="Selecionar"><input type="checkbox" class="bordero-schedule-selector" ${checked}></td>
          <td data-label="Título financeiro">
            <div class="bordero-row-title">
              <strong>${item.description || 'Sem histórico'}</strong>
              <small><a href="/financial/schedules/${item.id}?company_id=${companyId}">${item.schedule_code || '-'}</a> · ${item.status || '-'}</small>
            </div>
          </td>
          <td data-label="Favorecido">${counterparty}</td>
          <td data-label="Vencimento">${formatDate(item.next_due_date || item.first_due_date)}</td>
          <td data-label="Saldo aberto">${money(openTotal)}</td>
          <td data-label="Valor no borderô"><input class="bordero-amount-input" inputmode="numeric" value="${amountValue}" data-open-amount="${openTotal}"></td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.bordero-schedule-selector').forEach((input) => input.addEventListener('change', (event) => {
      const row = event.target.closest('tr');
      const scheduleId = Number(row?.dataset.scheduleId || 0);
      if (event.target.checked) state.selectedScheduleIds.add(scheduleId);
      else state.selectedScheduleIds.delete(scheduleId);
      renderSelectionSummary();
    }));
    tbody.querySelectorAll('.bordero-amount-input').forEach((input) => {
      input.addEventListener('input', (event) => {
        event.target.value = formatCurrencyFromDigits(event.target.value);
        const row = event.target.closest('tr');
        setScheduleAmount(Number(row?.dataset.scheduleId || 0), event.target.value);
        renderSelectionSummary();
      });
    });
    renderSelectionSummary();
  }

  function selectedItemsPayload() {
    syncVisibleSelectionState();
    return Array.from(state.selectedScheduleIds).map((scheduleId) => {
      const schedule = state.schedules.find((item) => Number(item.id) === Number(scheduleId));
      if (!schedule) throw new Error('Um dos títulos selecionados não está mais disponível. Atualize a lista e tente novamente.');
      const openAmount = scheduleOpenTotal(schedule);
      const selectedAmount = parseCurrency(getScheduleAmount(scheduleId, schedule));
      if (selectedAmount <= 0 || selectedAmount > openAmount + 0.001) {
        throw new Error('Revise os valores selecionados. Cada valor do borderô deve ser maior que zero e menor ou igual ao saldo aberto.');
      }
      return {
        financial_schedule_id: Number(scheduleId || 0),
        selected_amount: selectedAmount,
      };
    });
  }

  async function loadSchedules() {
    state.schedules = await fetchJson(`/api/financial/schedules?company_id=${companyId}&status=active`);
    if (!borderoId) renderEligibleSchedules();
  }

  async function loadBankAccounts() {
    state.bankAccounts = await fetchJson(`/api/financial/catalogs/bank_accounts?company_id=${companyId}`);
    renderSettlementBankAccountOptions();
  }

  function resetSettlementForm(bordero = state.bordero) {
    state.editingSettlementId = null;
    settlementButton.textContent = 'Registrar baixa';
    settlementCancelWrap?.classList.add('hidden');
    const openAmount = Number(bordero?.open_amount || 0);
    $('settlement-date').value = new Date().toISOString().slice(0, 10);
    $('settlement-amount').value = formatCurrencyFromDigits(Math.round(openAmount * 100));
    $('settlement-bank-account').value = bordero?.bank_account_id || '';
    $('settlement-notes').value = '';
    settlementButton.disabled = !(bordero && bordero.status !== 'cancelled' && openAmount > 0);
  }

  function startSettlementEdit(settlement) {
    if (!settlement) return;
    state.editingSettlementId = Number(settlement.id || 0) || null;
    $('settlement-date').value = settlement.settlement_date || new Date().toISOString().slice(0, 10);
    $('settlement-amount').value = formatCurrencyFromDigits(Math.round(Number(settlement.gross_amount || 0) * 100));
    $('settlement-bank-account').value = settlement.bank_account_id || state.bordero?.bank_account_id || '';
    $('settlement-notes').value = settlement.notes || '';
    settlementButton.textContent = 'Salvar edição';
    settlementCancelWrap?.classList.remove('hidden');
    settlementButton.disabled = false;
  }

  function renderDetail(bordero) {
    state.bordero = bordero;
    page.dataset.borderoType = bordero.bordero_type || '';
    $('bordero-title').textContent = `${bordero.bordero_code} · ${bordero.name || bordero.description || 'Borderô financeiro'}`;
    banner.textContent = `${typeLabel(bordero.bordero_type)} · ${statusLabel(bordero.status)} · os títulos permanecem congelados e a baixa do borderô liquida cada Título Financeiro pelo fluxo oficial.`;
    $('detail-code').textContent = bordero.bordero_code || '-';
    $('detail-status').textContent = statusLabel(bordero.status);
    $('detail-total').textContent = money(bordero.signed_total_amount || bordero.total_amount || 0);
    $('detail-open').textContent = money(bordero.signed_open_amount || bordero.open_amount || 0);
    $('bordero-name').value = bordero.name || '';
    $('bordero-description').value = bordero.description || bordero.notes || '';
    ensureCreatedDateValue(bordero.created_date || bordero.created_at);
    $('settlement-bank-account').value = bordero.bank_account_id || '';

    const itemsBody = $('bordero-items-body');
    const items = bordero.items || [];
    if (!items.length) {
      itemsBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum item no borderô.</td></tr>';
    } else {
      itemsBody.innerHTML = items.map((item) => {
        const snap = item.snapshot_json || {};
        const summary = snap.summary || {};
        return `
          <tr>
            <td data-label="Item">${item.item_code || '-'}</td>
            <td data-label="Título financeiro">
              <div class="bordero-row-title">
                <strong>${snap.description || 'Sem histórico'}</strong>
                <small><a href="/financial/schedules/${item.financial_schedule_id}?company_id=${companyId}&open_tab=baixas">${snap.schedule_code || summary.schedule_code || '-'}</a> · título ${item.financial_schedule_id}</small>
              </div>
            </td>
            <td data-label="Favorecido">${summary.counterparty_name || snap.metadata_json?.counterparty_name || '-'}</td>
            <td data-label="Selecionado">${money(item.selected_amount || 0)}</td>
            <td data-label="Liquidado">${money(item.settled_amount || 0)}</td>
            <td data-label="Em aberto">${money(item.open_amount || 0)}</td>
          </tr>
        `;
      }).join('');
    }

    const settlementsBody = $('bordero-settlements-body');
    const settlements = bordero.settlements || [];
    if (!settlements.length) {
      settlementsBody.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhuma baixa registrada.</td></tr>';
    } else {
      settlementsBody.innerHTML = settlements.map((item) => `
        <tr>
          <td data-label="Código">${item.settlement_code || '-'}</td>
          <td data-label="Data">${formatDate(item.settlement_date)}</td>
          <td data-label="Valor bruto">${money(item.gross_amount || 0)}</td>
          <td data-label="Alocado">${money(item.allocated_amount || 0)}</td>
          <td data-label="Variação">${money(item.variance_amount || 0)}</td>
          <td data-label="Status">${settlementStatusLabel(item.settlement_status)}</td>
          <td data-label="Ações">
            <div class="bordero-table-actions">
              <button type="button" class="btn btn-secondary btn-xs" data-bordero-settlement-edit="${item.id}">Editar</button>
              <button type="button" class="btn btn-danger btn-xs" data-bordero-settlement-delete="${item.id}">Excluir</button>
            </div>
          </td>
        </tr>
      `).join('');
    }

    createSection.classList.add('hidden');
    detailSection.classList.remove('hidden');
    saveButton?.classList.remove('hidden');
    const openAmount = Number(bordero.open_amount || 0);
    $('settlement-date').value = new Date().toISOString().slice(0, 10);
    deleteButton?.classList.toggle('hidden', !bordero.can_delete);
    deleteButton && (deleteButton.disabled = !bordero.can_delete);
    resetSettlementForm(bordero);
  }

  async function loadDetail() {
    const bordero = await fetchJson(`/api/financial/borderos/${borderoId}?company_id=${companyId}`);
    renderDetail(bordero);
  }

  async function createBordero() {
    const items = selectedItemsPayload();
    if (!state.selectedType) throw new Error('Selecione o tipo do borderô.');
    const name = $('bordero-name').value.trim();
    if (!name) throw new Error('Informe o nome do borderô.');
    if (!items.length) throw new Error('Selecione ao menos um título financeiro.');
    const payload = {
      bordero_type: state.selectedType,
      name,
      description: $('bordero-description').value.trim() || null,
      created_date: $('bordero-created-date').value || null,
      notes: $('bordero-description').value.trim() || null,
      items,
    };
    const created = await fetchJson(`/api/financial/borderos?company_id=${companyId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    window.location.href = `/financial/borderos/${created.id}?company_id=${companyId}`;
  }

  async function saveBordero() {
    if (!borderoId) return;
    const payload = {
      name: $('bordero-name').value.trim(),
      description: $('bordero-description').value.trim() || null,
      created_date: $('bordero-created-date').value || null,
      notes: $('bordero-description').value.trim() || null,
    };
    if (!payload.name) throw new Error('Informe o nome do borderô.');
    const updated = await fetchJson(`/api/financial/borderos/${borderoId}?company_id=${companyId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    renderDetail(updated);
  }

  async function createSettlement() {
    const amount = parseCurrency($('settlement-amount').value);
    if (amount <= 0) throw new Error('Informe um valor válido para a baixa do borderô.');
    const payload = {
      settlement_date: $('settlement-date').value,
      gross_amount: amount,
      bank_account_id: Number($('settlement-bank-account').value || 0) || null,
      notes: $('settlement-notes').value.trim() || null,
    };
    await fetchJson(`/api/financial/borderos/${borderoId}/settlements?company_id=${companyId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    await loadDetail();
  }

  async function updateSettlement() {
    if (!state.editingSettlementId) throw new Error('Selecione uma baixa do borderô para editar.');
    const amount = parseCurrency($('settlement-amount').value);
    if (amount <= 0) throw new Error('Informe um valor válido para a baixa do borderô.');
    const payload = {
      settlement_date: $('settlement-date').value,
      gross_amount: amount,
      bank_account_id: Number($('settlement-bank-account').value || 0) || null,
      notes: $('settlement-notes').value.trim() || null,
    };
    await fetchJson(`/api/financial/borderos/${borderoId}/settlements/${state.editingSettlementId}?company_id=${companyId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    await loadDetail();
  }

  async function deleteSettlement(settlementId) {
    if (!settlementId) return;
    if (!window.confirm('Excluir esta baixa do borderô? Os títulos voltarão a ficar disponíveis conforme o saldo reaberto.')) return;
    await fetchJson(`/api/financial/borderos/${borderoId}/settlements/${settlementId}?company_id=${companyId}`, {
      method: 'DELETE',
    });
    await loadDetail();
  }

  async function deleteBordero() {
    if (!borderoId) return;
    if (!window.confirm('Excluir este borderô? Esta ação só é permitida quando não existirem baixas ativas.')) return;
    await fetchJson(`/api/financial/borderos/${borderoId}?company_id=${companyId}`, {
      method: 'DELETE',
    });
    window.location.href = '/financial/borderos';
  }

  async function init() {
    try {
      await Promise.all([loadBankAccounts(), loadSchedules()]);
      $('bordero-schedule-search')?.addEventListener('input', renderEligibleSchedules);
      $('bordero-refresh-schedules')?.addEventListener('click', loadSchedules);
      selectAllSchedules?.addEventListener('change', (event) => {
        const shouldSelect = Boolean(event.target.checked);
        document.querySelectorAll('#bordero-schedule-body tr[data-schedule-id]').forEach((row) => {
          const scheduleId = Number(row.dataset.scheduleId || 0);
          const selector = row.querySelector('.bordero-schedule-selector');
          const amountInput = row.querySelector('.bordero-amount-input');
          if (selector) selector.checked = shouldSelect;
          if (amountInput) setScheduleAmount(scheduleId, amountInput.value);
          if (shouldSelect) state.selectedScheduleIds.add(scheduleId);
          else state.selectedScheduleIds.delete(scheduleId);
        });
        renderEligibleSchedules();
      });
      Object.values(scheduleFilters).forEach((input) => {
        input?.addEventListener('input', updateScheduleFilterIndicators);
        input?.addEventListener('change', updateScheduleFilterIndicators);
      });
      [scheduleFilters.minAmount, scheduleFilters.maxAmount].forEach((input) => {
        input?.addEventListener('input', (event) => {
          event.target.value = formatCurrencyFromDigits(event.target.value);
        });
      });
      applyScheduleFiltersButton?.addEventListener('click', renderEligibleSchedules);
      clearScheduleFiltersButton?.addEventListener('click', () => {
        Object.values(scheduleFilters).forEach((input) => {
          if (input) input.value = '';
        });
        renderEligibleSchedules();
      });
      $('settlement-amount')?.addEventListener('input', (event) => {
        event.target.value = formatCurrencyFromDigits(event.target.value);
      });
      saveButton?.addEventListener('click', async () => {
        try { await saveBordero(); alert('Borderô atualizado com sucesso.'); } catch (error) { alert(error.message); }
      });
      createButton?.addEventListener('click', async () => {
        try { await createBordero(); } catch (error) { alert(error.message); }
      });
      settlementButton?.addEventListener('click', async () => {
        try {
          if (state.editingSettlementId) await updateSettlement();
          else await createSettlement();
        } catch (error) { alert(error.message); }
      });
      settlementCancelButton?.addEventListener('click', () => resetSettlementForm());
      deleteButton?.addEventListener('click', async () => {
        try { await deleteBordero(); } catch (error) { alert(error.message); }
      });
      $('bordero-settlements-body')?.addEventListener('click', async (event) => {
        const editButton = event.target.closest('button[data-bordero-settlement-edit]');
        if (editButton) {
          const settlement = (state.bordero?.settlements || []).find((item) => Number(item.id) === Number(editButton.dataset.borderoSettlementEdit));
          startSettlementEdit(settlement);
          return;
        }
        const deleteSettlementButton = event.target.closest('button[data-bordero-settlement-delete]');
        if (deleteSettlementButton) {
          try { await deleteSettlement(Number(deleteSettlementButton.dataset.borderoSettlementDelete)); } catch (error) { alert(error.message); }
        }
      });

      if (borderoId) {
        await loadDetail();
      } else {
        ensureCreatedDateValue();
        applyType(state.selectedType || '');
      }
    } catch (error) {
      banner.textContent = error.message;
      if (!borderoId) $('bordero-schedule-body').innerHTML = `<tr><td colspan="6" class="empty-state">${error.message}</td></tr>`;
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
