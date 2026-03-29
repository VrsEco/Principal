(function () {
  async function init() {
    const page = document.querySelector('.sched-page');
    if (!page) return;

    const companyId = Number(page.dataset.companyId || 0);
    const list = document.getElementById('schedule-list-results');
    const kpis = Array.from(document.querySelectorAll('#schedule-kpis .sched-kpi'));
    const filtersCount = document.getElementById('schedule-filters-count');
    const resultsPill = document.getElementById('schedule-results-pill');
    const clearFiltersButton = document.getElementById('schedule-clear-filters');
    const sidebarClearFiltersButton = document.getElementById('schedule-sidebar-clear-filters');
    const actionSettle = document.getElementById('schedule-action-settle');
    const actionEdit = document.getElementById('schedule-action-edit');
    const actionDelete = document.getElementById('schedule-action-delete');
    const filters = {
      search: document.getElementById('schedule-filter-search'),
      type: document.getElementById('schedule-filter-type'),
      settlement: document.getElementById('schedule-filter-settlement'),
      counterparty: document.getElementById('schedule-filter-counterparty'),
      dueDateFrom: document.getElementById('schedule-filter-due-date-from'),
      dueDateTo: document.getElementById('schedule-filter-due-date-to'),
      competenceDateFrom: document.getElementById('schedule-filter-competence-date-from'),
      competenceDateTo: document.getElementById('schedule-filter-competence-date-to'),
      titleAmount: document.getElementById('schedule-filter-title-amount'),
    };

    if (!list || !filters.search) return;

    const state = {
      schedules: [],
      selectedId: null,
    };

    const byId = (id) => document.getElementById(id);
    const formatDate = (value) => {
      if (!value) return '-';
      const [year, month, day] = String(value).split('-');
      return year && month && day ? `${day}/${month}/${year}` : value;
    };
    const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const amountClass = (value) => Number(value || 0) < 0 ? 'sched-amount sched-amount--negative' : 'sched-amount sched-amount--positive';
    const typeLabel = (entryType) => entryType === 'payable' ? 'Pagamento' : 'Recebimento';
    const typeClass = (entryType) => entryType === 'payable' ? 'sched-pill--payable' : 'sched-pill--receivable';
    const settlementLabel = (value) => ({ open: 'Em aberto', partial: 'Liquidado parcial', settled: 'Liquidado' }[value] || 'Em aberto');
    const settlementClass = (value) => ({ open: 'sched-pill--open', partial: 'sched-pill--partial', settled: 'sched-pill--settled' }[value] || 'sched-pill--open');

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Falha ao carregar agendamentos.');
      return payload;
    }

    function numberMatches(filterValue, targetValue) {
      if (filterValue === '' || filterValue == null) return true;
      const normalizedFilter = Number(filterValue);
      const normalizedTarget = Number(targetValue || 0);
      if (!Number.isFinite(normalizedFilter)) return true;
      return Math.abs(normalizedTarget - normalizedFilter) < 0.01;
    }

    function dateGte(filterValue, targetValue) {
      if (!filterValue) return true;
      if (!targetValue) return false;
      return String(targetValue) >= String(filterValue);
    }

    function dateLte(filterValue, targetValue) {
      if (!filterValue) return true;
      if (!targetValue) return false;
      return String(targetValue) <= String(filterValue);
    }

    function getFilteredItems() {
      const search = String(filters.search.value || '').trim().toLowerCase();
      const type = String(filters.type.value || '').trim();
      const settlement = String(filters.settlement.value || '').trim();
      const counterparty = String(filters.counterparty.value || '').trim().toLowerCase();
      const dueDateFrom = String(filters.dueDateFrom.value || '').trim();
      const dueDateTo = String(filters.dueDateTo.value || '').trim();
      const competenceDateFrom = String(filters.competenceDateFrom.value || '').trim();
      const competenceDateTo = String(filters.competenceDateTo.value || '').trim();
      const titleAmount = String(filters.titleAmount.value || '').trim();

      return state.schedules.filter((item) => {
        const summary = item.summary || {};
        const itemCounterparty = String(summary.counterparty_name || item.metadata_json?.counterparty_name || '').trim().toLowerCase();
        const itemCompetence = item.start_date || item.first_due_date || '';
        const itemDueDate = item.next_due_date || item.first_due_date || '';
        const haystack = `${item.schedule_code || ''} ${item.description || item.name || ''} ${itemCounterparty}`.toLowerCase();
        if (search && !haystack.includes(search)) return false;
        if (type && item.entry_type !== type) return false;
        if (settlement && (summary.settlement_state || 'open') !== settlement) return false;
        if (counterparty && !itemCounterparty.includes(counterparty)) return false;
        if (!dateGte(dueDateFrom, itemDueDate)) return false;
        if (!dateLte(dueDateTo, itemDueDate)) return false;
        if (!dateGte(competenceDateFrom, itemCompetence)) return false;
        if (!dateLte(competenceDateTo, itemCompetence)) return false;
        if (!numberMatches(titleAmount, Math.abs(Number(item.template_amount || 0)))) return false;
        return true;
      });
    }

    function updateFiltersCount() {
      const activeCount = Object.values(filters).reduce((count, input) => {
        if (!input) return count;
        return String(input.value || '').trim() ? count + 1 : count;
      }, 0);
      if (filtersCount) filtersCount.textContent = String(activeCount);
    }

    function renderKpis(items) {
      const receivableTotal = items
        .filter((item) => item.entry_type === 'receivable')
        .reduce((acc, item) => acc + Number(item.summary?.signed_open_total ?? item.signed_template_amount ?? 0), 0);
      const payableTotal = items
        .filter((item) => item.entry_type === 'payable')
        .reduce((acc, item) => acc + Number(item.summary?.signed_open_total ?? item.signed_template_amount ?? 0), 0);
      const openCount = items.filter((item) => (item.summary?.settlement_state || 'open') !== 'settled').length;

      if (kpis[0]) kpis[0].querySelector('strong').textContent = String(items.length);
      if (kpis[1]) {
        const target = kpis[1].querySelector('strong');
        target.textContent = money(receivableTotal);
        target.className = amountClass(receivableTotal);
      }
      if (kpis[2]) {
        const target = kpis[2].querySelector('strong');
        target.textContent = money(payableTotal);
        target.className = amountClass(payableTotal);
      }
      if (kpis[3]) kpis[3].querySelector('strong').textContent = String(openCount);
      if (resultsPill) resultsPill.textContent = `${items.length} registros`;
    }

    function ensureSelection(items) {
      if (!items.length) {
        state.selectedId = null;
        return;
      }
      const hasSelected = items.some((item) => Number(item.id) === Number(state.selectedId));
      if (!hasSelected) {
        state.selectedId = Number(items[0].id);
      }
    }

    function renderList(items) {
      ensureSelection(items);
      if (!items.length) {
        list.innerHTML = '<div class="sched-empty">Nenhum agendamento encontrado para os filtros informados.</div>';
        renderDetail(null);
        return;
      }

      list.innerHTML = items.map((item) => {
        const summary = item.summary || {};
        const settlementState = summary.settlement_state || 'open';
        const isSelected = Number(item.id) === Number(state.selectedId);
        const counterparty = summary.counterparty_name || item.metadata_json?.counterparty_name || '-';
        const signedTitle = item.signed_template_amount ?? item.template_amount ?? 0;
        const signedOpen = summary.signed_open_total ?? signedTitle;
        return `
          <article class="sched-item sched-item--${item.entry_type || 'receivable'} ${isSelected ? 'is-selected' : ''}" data-id="${item.id}">
            <div class="sched-item-head">
              <div>
                <div class="sched-item-code">${item.schedule_code || `AG.${item.id}`}</div>
                <div class="sched-item-title">${item.description || item.name || 'Sem histórico'}</div>
                <div class="sched-item-subtitle">${counterparty}</div>
              </div>
              <div class="sched-item-meta">
                <span class="sched-pill ${typeClass(item.entry_type)}">${typeLabel(item.entry_type)}</span>
                <span class="sched-pill ${settlementClass(settlementState)}">${settlementLabel(settlementState)}</span>
              </div>
            </div>
            <div class="sched-item-metrics">
              <div class="sched-metric"><span>Valor título</span><strong class="${amountClass(signedTitle)}">${money(signedTitle)}</strong></div>
              <div class="sched-metric"><span>Saldo</span><strong class="${amountClass(signedOpen)}">${money(signedOpen)}</strong></div>
              <div class="sched-metric"><span>Competência</span><strong>${formatDate(item.start_date || item.first_due_date)}</strong></div>
              <div class="sched-metric"><span>Vencimento</span><strong>${formatDate(item.next_due_date || item.first_due_date)}</strong></div>
            </div>
            <div class="sched-item-foot">
              <span class="sched-muted">${item.status || '-'}${item.budget_document_id ? ` · NF/Equiv. #${item.budget_document_id}` : ''}</span>
              <strong>${item.id}</strong>
            </div>
          </article>
        `;
      }).join('');

      const selected = items.find((item) => Number(item.id) === Number(state.selectedId)) || items[0];
      renderDetail(selected);
    }

    function renderDetail(item) {
      if (!item) {
        byId('schedule-detail-title').textContent = 'Selecione um agendamento';
        byId('schedule-detail-subtitle').textContent = 'Os dados consolidados do registro aparecerão aqui.';
        byId('schedule-detail-state').textContent = 'Sem seleção';
        byId('schedule-detail-context').innerHTML = '';
        byId('schedule-detail-summary').textContent = 'Escolha um registro na fila operacional para visualizar detalhes.';
        byId('detail-code').textContent = '-';
        byId('detail-type').textContent = '-';
        byId('detail-counterparty').textContent = '-';
        byId('detail-status').textContent = '-';
        byId('detail-competence').textContent = '-';
        byId('detail-due-date').textContent = '-';
        byId('detail-title-amount').textContent = money(0);
        byId('detail-open-amount').textContent = money(0);
        byId('detail-description').textContent = '-';
        byId('detail-links').textContent = '-';
        actionSettle.disabled = true;
        actionDelete.disabled = true;
        actionEdit.href = '/financial/schedules/new';
        return;
      }

      const summary = item.summary || {};
      const settlementState = summary.settlement_state || 'open';
      const counterparty = summary.counterparty_name || item.metadata_json?.counterparty_name || '-';
      const signedTitle = item.signed_template_amount ?? item.template_amount ?? 0;
      const signedOpen = summary.signed_open_total ?? signedTitle;
      const isBorderoLocked = Boolean(item.is_bordero_locked || summary.is_bordero_locked);
      const borderoCode = item.bordero?.code || summary.bordero_code || '';
      const context = [
        `<span class="sched-context-chip"><b>Tipo:</b> ${typeLabel(item.entry_type)}</span>`,
        `<span class="sched-context-chip"><b>Liquidação:</b> ${settlementLabel(settlementState)}</span>`,
        `<span class="sched-context-chip"><b>ID:</b> ${item.id}</span>`,
      ];
      if (borderoCode) context.push(`<span class="sched-context-chip"><b>Borderô:</b> ${borderoCode}</span>`);
      if (item.budget_document_id) context.push(`<span class="sched-context-chip"><b>NF/Equiv.:</b> #${item.budget_document_id}</span>`);

      byId('schedule-detail-title').textContent = item.description || item.name || 'Sem histórico';
      byId('schedule-detail-subtitle').textContent = `${item.schedule_code || `AG.${item.id}`} · ${counterparty}`;
      byId('schedule-detail-state').textContent = settlementLabel(settlementState);
      byId('schedule-detail-context').innerHTML = context.join('');
      byId('schedule-detail-summary').innerHTML = `<strong>${item.schedule_code || `AG.${item.id}`}</strong><br>${counterparty}<br>Valor título: ${money(signedTitle)} · Saldo aberto: ${money(signedOpen)} · Vencimento: ${formatDate(item.next_due_date || item.first_due_date)}`;
      byId('detail-code').textContent = item.schedule_code || `AG.${item.id}`;
      byId('detail-type').textContent = typeLabel(item.entry_type);
      byId('detail-counterparty').textContent = counterparty;
      byId('detail-status').textContent = item.status || '-';
      byId('detail-competence').textContent = formatDate(item.start_date || item.first_due_date);
      byId('detail-due-date').textContent = formatDate(item.next_due_date || item.first_due_date);
      byId('detail-title-amount').textContent = money(signedTitle);
      byId('detail-open-amount').textContent = money(signedOpen);
      byId('detail-description').textContent = item.description || item.name || '-';
      byId('detail-links').textContent = [
        item.budget_document_id ? `NF/Equiv. #${item.budget_document_id}` : null,
        borderoCode ? `Borderô ${borderoCode}` : null,
        item.document_number_prefix ? `Doc. ${item.document_number_prefix}` : null,
      ].filter(Boolean).join(' · ') || '-';

      actionSettle.disabled = !(Number(summary.open_total || 0) > 0) || isBorderoLocked;
      actionDelete.disabled = isBorderoLocked;
      actionSettle.dataset.id = String(item.id);
      actionDelete.dataset.id = String(item.id);
      actionEdit.href = `/financial/schedules/${item.id}`;
      actionEdit.textContent = isBorderoLocked ? 'Consultar' : 'Editar';
      actionSettle.textContent = isBorderoLocked ? 'No borderô' : 'Liquidar';
    }

    function render() {
      const items = getFilteredItems();
      renderKpis(items);
      renderList(items);
    }

    async function loadSchedules() {
      state.schedules = await fetchJson(`/api/financial/schedules?company_id=${companyId}`);
      render();
    }

    async function liquidateSchedule(scheduleId) {
      window.location.href = `/financial/schedules/${scheduleId}/settle?company_id=${companyId}`;
    }

    async function deleteSchedule(scheduleId) {
      const confirmed = window.confirm('Deseja realmente excluir este agendamento?');
      if (!confirmed) return;
      await fetchJson(`/api/financial/schedules/${scheduleId}?company_id=${companyId}`, { method: 'DELETE' });
      await loadSchedules();
    }

    function clearFilters() {
      Object.values(filters).forEach((input) => {
        if (input) input.value = '';
      });
      updateFiltersCount();
      render();
    }

    Object.values(filters).forEach((input) => input?.addEventListener('input', () => {
      updateFiltersCount();
      render();
    }));
    Object.values(filters).forEach((input) => input?.addEventListener('change', () => {
      updateFiltersCount();
      render();
    }));

    clearFiltersButton?.addEventListener('click', clearFilters);
    sidebarClearFiltersButton?.addEventListener('click', clearFilters);

    list.addEventListener('click', (event) => {
      const card = event.target.closest('.sched-item[data-id]');
      if (!card) return;
      state.selectedId = Number(card.dataset.id);
      render();
    });

    actionSettle?.addEventListener('click', async () => {
      try {
        const scheduleId = Number(actionSettle.dataset.id || 0);
        if (scheduleId) await liquidateSchedule(scheduleId);
      } catch (error) {
        alert(error.message);
      }
    });

    actionDelete?.addEventListener('click', async () => {
      try {
        const scheduleId = Number(actionDelete.dataset.id || 0);
        if (scheduleId) await deleteSchedule(scheduleId);
      } catch (error) {
        alert(error.message);
      }
    });

    try {
      updateFiltersCount();
      await loadSchedules();
    } catch (error) {
      list.innerHTML = `<div class="sched-empty">${error.message}</div>`;
      renderDetail(null);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
