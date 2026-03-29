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
  };

  const $ = (id) => document.getElementById(id);
  const createSection = $('bordero-create-section');
  const detailSection = $('bordero-detail-section');
  const createButton = $('bordero-create-button');
  const settlementButton = $('bordero-settlement-button');
  const banner = $('bordero-banner');
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

  function bankAccountLabel(item) {
    return item.display_label || item.name || item.code || `Conta ${item.id}`;
  }

  function renderBankAccountOptions() {
    const html = ['<option value="">Selecione...</option>']
      .concat(state.bankAccounts.map((item) => `<option value="${item.id}">${bankAccountLabel(item)}</option>`))
      .join('');
    $('bordero-bank-account').innerHTML = html;
    $('settlement-bank-account').innerHTML = html;
  }

  function applyType(type) {
    state.selectedType = type;
    document.querySelectorAll('.bordero-type-chip').forEach((button) => {
      const active = button.dataset.type === type;
      button.classList.toggle('btn-primary', active);
      button.classList.toggle('btn-secondary', !active);
      if (borderoId) button.disabled = true;
    });
    if (!type) {
      banner.textContent = 'Selecione o tipo do borderô e os agendamentos elegíveis.';
      $('bordero-schedule-body').innerHTML = '<tr><td colspan="6" class="empty-state">Selecione um tipo para carregar os agendamentos.</td></tr>';
      renderSelectionSummary();
      return;
    }
    banner.textContent = `${typeLabel(type)} · somente agendamentos com saldo aberto e sem outro borderô ativo ficam elegíveis para agrupamento.`;
    renderEligibleSchedules();
  }

  function eligibleSchedules() {
    const search = String($('bordero-schedule-search')?.value || '').trim().toLowerCase();
    return state.schedules.filter((item) => {
      const summary = item.summary || {};
      const openTotal = Number(summary.open_total || 0);
      const locked = Boolean(item.is_bordero_locked || summary.is_bordero_locked);
      const haystack = `${item.schedule_code || ''} ${item.description || ''} ${summary.counterparty_name || ''}`.toLowerCase();
      if (!state.selectedType || item.entry_type !== state.selectedType) return false;
      if (locked || openTotal <= 0) return false;
      if (search && !haystack.includes(search)) return false;
      return true;
    });
  }

  function renderSelectionSummary() {
    const rows = Array.from(document.querySelectorAll('.bordero-schedule-selector:checked'));
    const count = rows.length;
    const total = rows.reduce((acc, input) => acc + parseCurrency(input.closest('tr').querySelector('.bordero-amount-input')?.value || 0), 0);
    $('bordero-create-summary').innerHTML = [
      `<span>Títulos selecionados: ${count}</span>`,
      `<span>Total do borderô: ${money(total)}</span>`,
    ].join('');
  }

  function renderEligibleSchedules() {
    const tbody = $('bordero-schedule-body');
    const items = eligibleSchedules();
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum agendamento elegível para este tipo.</td></tr>';
      renderSelectionSummary();
      return;
    }

    tbody.innerHTML = items.map((item) => {
      const summary = item.summary || {};
      const openTotal = Number(summary.open_total || 0);
      const counterparty = summary.counterparty_name || item.metadata_json?.counterparty_name || '-';
      return `
        <tr data-schedule-id="${item.id}">
          <td><input type="checkbox" class="bordero-schedule-selector"></td>
          <td>
            <div class="bordero-row-title">
              <strong>${item.description || 'Sem histórico'}</strong>
              <small>${item.schedule_code || '-'} · ${item.status || '-'}</small>
            </div>
          </td>
          <td>${counterparty}</td>
          <td>${formatDate(item.next_due_date || item.first_due_date)}</td>
          <td>${money(openTotal)}</td>
          <td><input class="bordero-amount-input" inputmode="numeric" value="${formatCurrencyFromDigits(Math.round(openTotal * 100))}" data-open-amount="${openTotal}"></td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.bordero-schedule-selector').forEach((input) => input.addEventListener('change', renderSelectionSummary));
    tbody.querySelectorAll('.bordero-amount-input').forEach((input) => {
      input.addEventListener('input', (event) => {
        event.target.value = formatCurrencyFromDigits(event.target.value);
        renderSelectionSummary();
      });
    });
    renderSelectionSummary();
  }

  function selectedItemsPayload() {
    return Array.from(document.querySelectorAll('.bordero-schedule-selector:checked')).map((input) => {
      const row = input.closest('tr');
      const amountInput = row.querySelector('.bordero-amount-input');
      const openAmount = Number(amountInput.dataset.openAmount || 0);
      const selectedAmount = parseCurrency(amountInput.value);
      if (selectedAmount <= 0 || selectedAmount > openAmount + 0.001) {
        throw new Error('Revise os valores selecionados. Cada valor do borderô deve ser maior que zero e menor ou igual ao saldo aberto.');
      }
      return {
        financial_schedule_id: Number(row.dataset.scheduleId || 0),
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
    renderBankAccountOptions();
  }

  function renderDetail(bordero) {
    state.bordero = bordero;
    $('bordero-title').textContent = `${bordero.bordero_code} · ${bordero.description || 'Borderô financeiro'}`;
    banner.textContent = `${typeLabel(bordero.bordero_type)} · ${statusLabel(bordero.status)} · os títulos permanecem congelados e a baixa acontece somente no nível do borderô.`;
    $('detail-code').textContent = bordero.bordero_code || '-';
    $('detail-status').textContent = statusLabel(bordero.status);
    $('detail-total').textContent = money(bordero.signed_total_amount || bordero.total_amount || 0);
    $('detail-open').textContent = money(bordero.signed_open_amount || bordero.open_amount || 0);
    $('bordero-description').value = bordero.description || '';
    $('bordero-notes').value = bordero.notes || '';
    $('bordero-bank-account').value = bordero.bank_account_id || '';
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
            <td>${item.item_code || '-'}</td>
            <td>
              <div class="bordero-row-title">
                <strong>${snap.description || 'Sem histórico'}</strong>
                <small>${snap.schedule_code || summary.schedule_code || '-'} · agendamento ${item.financial_schedule_id}</small>
              </div>
            </td>
            <td>${summary.counterparty_name || snap.metadata_json?.counterparty_name || '-'}</td>
            <td>${money(item.selected_amount || 0)}</td>
            <td>${money(item.settled_amount || 0)}</td>
            <td>${money(item.open_amount || 0)}</td>
          </tr>
        `;
      }).join('');
    }

    const settlementsBody = $('bordero-settlements-body');
    const settlements = bordero.settlements || [];
    if (!settlements.length) {
      settlementsBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhuma baixa registrada.</td></tr>';
    } else {
      settlementsBody.innerHTML = settlements.map((item) => `
        <tr>
          <td>${item.settlement_code || '-'}</td>
          <td>${formatDate(item.settlement_date)}</td>
          <td>${money(item.gross_amount || 0)}</td>
          <td>${money(item.allocated_amount || 0)}</td>
          <td>${money(item.variance_amount || 0)}</td>
          <td>${settlementStatusLabel(item.settlement_status)}</td>
        </tr>
      `).join('');
    }

    createSection.classList.add('hidden');
    detailSection.classList.remove('hidden');
    document.querySelectorAll('.bordero-type-chip').forEach((button) => button.disabled = true);
    $('bordero-description').disabled = true;
    $('bordero-notes').disabled = true;
    $('bordero-bank-account').disabled = true;
    const openAmount = Number(bordero.open_amount || 0);
    const canSettle = bordero.status !== 'cancelled' && openAmount > 0;
    $('settlement-date').value = new Date().toISOString().slice(0, 10);
    $('settlement-amount').value = formatCurrencyFromDigits(Math.round(openAmount * 100));
    settlementButton.disabled = !canSettle;
  }

  async function loadDetail() {
    const bordero = await fetchJson(`/api/financial/borderos/${borderoId}?company_id=${companyId}`);
    renderDetail(bordero);
  }

  async function createBordero() {
    const items = selectedItemsPayload();
    if (!state.selectedType) throw new Error('Selecione o tipo do borderô.');
    if (!items.length) throw new Error('Selecione ao menos um agendamento.');
    const payload = {
      bordero_type: state.selectedType,
      description: $('bordero-description').value.trim(),
      bank_account_id: Number($('bordero-bank-account').value || 0) || null,
      notes: $('bordero-notes').value.trim() || null,
      items,
    };
    const created = await fetchJson(`/api/financial/borderos?company_id=${companyId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    window.location.href = `/financial/borderos/${created.id}`;
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

  async function init() {
    try {
      await Promise.all([loadBankAccounts(), loadSchedules()]);
      document.querySelectorAll('.bordero-type-chip').forEach((button) => {
        button.addEventListener('click', () => applyType(button.dataset.type));
      });
      $('bordero-schedule-search')?.addEventListener('input', renderEligibleSchedules);
      $('bordero-refresh-schedules')?.addEventListener('click', loadSchedules);
      $('settlement-amount')?.addEventListener('input', (event) => {
        event.target.value = formatCurrencyFromDigits(event.target.value);
      });
      createButton?.addEventListener('click', async () => {
        try { await createBordero(); } catch (error) { alert(error.message); }
      });
      settlementButton?.addEventListener('click', async () => {
        try { await createSettlement(); } catch (error) { alert(error.message); }
      });

      if (borderoId) {
        await loadDetail();
      } else {
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
