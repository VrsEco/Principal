(function () {
  async function init() {
    const page = document.querySelector('.sched-list-page');
    if (!page) return;

    const companyId = Number(page.dataset.companyId || 0);
    const userId = Number(page.dataset.userId || 0);
    const tbody = document.getElementById('schedule-table-body');
    const kpis = Array.from(document.querySelectorAll('#schedule-kpis .sched-kpi'));
    const filtersCount = document.getElementById('schedule-filters-count');
    const clearFiltersButton = document.getElementById('schedule-clear-filters');
    const sidebarClearFiltersButton = document.getElementById('schedule-sidebar-clear-filters');
    const filters = {
      search: document.getElementById('schedule-filter-search'),
      type: document.getElementById('schedule-filter-type'),
      settlement: document.getElementById('schedule-filter-settlement'),
      bordero: document.getElementById('schedule-filter-bordero'),
      counterparty: document.getElementById('schedule-filter-counterparty'),
      dueDateFrom: document.getElementById('schedule-filter-due-date-from'),
      dueDateTo: document.getElementById('schedule-filter-due-date-to'),
      competenceDateFrom: document.getElementById('schedule-filter-competence-date-from'),
      competenceDateTo: document.getElementById('schedule-filter-competence-date-to'),
      titleAmount: document.getElementById('schedule-filter-title-amount'),
    };

    if (!tbody || !filters.search) return;

    const storageKey = `gestao_versus:financial_schedules:list_filters:v2:user:${userId || 'none'}:company:${companyId || 'none'}:path:${window.location.pathname}`;
    const persistableFilters = Object.entries(filters).filter(([, input]) => Boolean(input));
    const filterQueryNames = {
      search: 'search',
      type: 'type',
      settlement: 'settlement',
      bordero: 'bordero',
      counterparty: 'counterparty',
      dueDateFrom: 'due_date_from',
      dueDateTo: 'due_date_to',
      competenceDateFrom: 'competence_date_from',
      competenceDateTo: 'competence_date_to',
      titleAmount: 'title_amount',
    };

    function readFilterValue(input) {
      if (!input) return '';
      if (input.multiple) {
        return Array.from(input.selectedOptions || []).map((option) => option.value);
      }
      return input.value || '';
    }

    function writeFilterValue(input, value) {
      if (!input) return;
      if (input.multiple) {
        const values = Array.isArray(value) ? value.map(String) : [];
        Array.from(input.options || []).forEach((option) => {
          option.selected = values.includes(String(option.value));
        });
        return;
      }
      input.value = value == null ? '' : String(value);
    }

    function saveFiltersState() {
      try {
        const payload = persistableFilters.reduce((acc, [name, input]) => {
          acc[name] = readFilterValue(input);
          return acc;
        }, {});
        window.localStorage.setItem(storageKey, JSON.stringify(payload));
      } catch (error) {
        console.warn('Não foi possível persistir filtros de títulos financeiros.', error);
      }
    }

    function restoreFiltersState() {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) return false;
        const payload = JSON.parse(raw);
        persistableFilters.forEach(([name, input]) => writeFilterValue(input, payload[name]));
        return true;
      } catch (error) {
        console.warn('Não foi possível restaurar filtros de títulos financeiros.', error);
        return false;
      }
    }

    function restoreFiltersFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const hasExplicitFilters = Object.values(filterQueryNames).some((name) => params.has(name));
      if (!hasExplicitFilters) return false;

      persistableFilters.forEach(([name, input]) => {
        writeFilterValue(input, params.get(filterQueryNames[name]) || '');
      });
      return true;
    }

    function formatLocalIsoDate(value) {
      const year = value.getFullYear();
      const month = String(value.getMonth() + 1).padStart(2, '0');
      const day = String(value.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }

    function applyCurrentMonthDueDateRange() {
      const now = new Date();
      writeFilterValue(filters.dueDateFrom, formatLocalIsoDate(new Date(now.getFullYear(), now.getMonth(), 1)));
      writeFilterValue(filters.dueDateTo, formatLocalIsoDate(new Date(now.getFullYear(), now.getMonth() + 1, 0)));
    }

    function syncFiltersToUrl() {
      const url = new URL(window.location.href);
      persistableFilters.forEach(([name, input]) => {
        const queryName = filterQueryNames[name];
        const value = readFilterValue(input);
        if (Array.isArray(value) ? value.length : String(value || '').trim()) {
          url.searchParams.set(queryName, Array.isArray(value) ? value.join(',') : value);
        } else {
          url.searchParams.delete(queryName);
        }
      });
      window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
    }

    function clearFiltersState() {
      try {
        window.localStorage.removeItem(storageKey);
      } catch (error) {
        console.warn('Não foi possível limpar filtros persistidos de títulos financeiros.', error);
      }
    }

    let schedules = [];
    let borderos = [];
    let scheduleItems = [];

    const formatDate = (value) => {
      if (!value) return '-';
      const [year, month, day] = String(value).split('-');
      return year && month && day ? `${day}/${month}/${year}` : value;
    };

    const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const amountClass = (value) => Number(value || 0) < 0 ? 'sched-amount sched-amount--negative' : 'sched-amount sched-amount--positive';
    const typeLabel = (entryType) => entryType === 'payable' ? 'Pagamento' : 'Recebimento';
    const typeClass = (entryType) => entryType === 'payable' ? 'sched-pill--payable' : 'sched-pill--receivable';
    const resolveScheduleState = (summary = {}, item = {}) => {
      if (item.is_bordero_virtual) return 'bordero';
      if (item.bordero && !item.is_bordero_virtual) return 'bordero_item';
      return summary.operational_state || summary.settlement_state || 'open';
    };
    const settlementLabel = (state, item) => {
      if (state === 'bordero_item' && item?.bordero?.code) return `Bord. - ${item.bordero.code}`;
      if (state === 'bordero') return 'Borderô';
      if (item?.summary?.operational_state_label) return item.summary.operational_state_label;
      return ({ draft: 'Rascunho', forecast: 'Projetado', open: 'Em aberto', partial: 'Baixado parcial', settled: 'Baixado', cancelled: 'Cancelado' }[state] || 'Em aberto');
    };
    const settlementClass = (state) => ({ draft: 'sched-pill--open', forecast: 'sched-pill--partial', open: 'sched-pill--open', partial: 'sched-pill--partial', settled: 'sched-pill--settled', cancelled: 'sched-pill--bordero-item', bordero_item: 'sched-pill--bordero-item', bordero: 'sched-pill--bordero' }[state] || 'sched-pill--open');

    const numberMatches = (filterValue, targetValue) => {
      if (filterValue === '' || filterValue == null) return true;
      const normalizedFilter = Number(filterValue);
      const normalizedTarget = Number(targetValue || 0);
      if (!Number.isFinite(normalizedFilter)) return true;
      return Math.abs(normalizedTarget - normalizedFilter) < 0.01;
    };

    const dateGte = (filterValue, targetValue) => {
      if (!filterValue) return true;
      if (!targetValue) return false;
      return String(targetValue) >= String(filterValue);
    };

    const dateLte = (filterValue, targetValue) => {
      if (!filterValue) return true;
      if (!targetValue) return false;
      return String(targetValue) <= String(filterValue);
    };

    function updateFiltersCount() {
      const activeCount = Object.values(filters).reduce((count, input) => {
        if (!input) return count;
        return String(input.value || '').trim() ? count + 1 : count;
      }, 0);

      if (filtersCount) filtersCount.textContent = String(activeCount);
    }

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Falha ao carregar títulos financeiros.');
      return payload;
    }

    function getFilteredItems() {
      const search = String(filters.search.value || '').trim().toLowerCase();
      const type = String(filters.type.value || '').trim();
      const settlement = String(filters.settlement.value || '').trim();
      const borderoFilter = String(filters.bordero.value || '').trim();
      const counterparty = String(filters.counterparty.value || '').trim().toLowerCase();
      const dueDateFrom = String(filters.dueDateFrom.value || '').trim();
      const dueDateTo = String(filters.dueDateTo.value || '').trim();
      const competenceDateFrom = String(filters.competenceDateFrom.value || '').trim();
      const competenceDateTo = String(filters.competenceDateTo.value || '').trim();
      const titleAmount = String(filters.titleAmount.value || '').trim();

      return scheduleItems.filter((item) => {
        const summary = item.summary || {};
        const effectiveState = resolveScheduleState(summary, item);
        const itemCounterparty = String(summary.counterparty_name || item.metadata_json?.counterparty_name || '').trim().toLowerCase();
        const itemCompetence = item.start_date || item.first_due_date || item.created_date || '';
        const itemDueDate = item.next_due_date || item.first_due_date || item.created_date || '';
        const haystack = `${item.schedule_code || ''} ${item.description || item.name || ''} ${itemCounterparty}`.toLowerCase();
        if (search && !haystack.includes(search)) return false;
        if (type && item.entry_type !== type) return false;
        if (settlement && effectiveState !== settlement) return false;
        if (borderoFilter === 'bordero' && !item.is_bordero_virtual) return false;
        if (borderoFilter === 'item' && (!item.bordero || item.is_bordero_virtual)) return false;
        if (borderoFilter === 'free' && (item.bordero || item.is_bordero_virtual)) return false;
        if (counterparty && !itemCounterparty.includes(counterparty)) return false;
        if (!dateGte(dueDateFrom, itemDueDate)) return false;
        if (!dateLte(dueDateTo, itemDueDate)) return false;
        if (!dateGte(competenceDateFrom, itemCompetence)) return false;
        if (!dateLte(competenceDateTo, itemCompetence)) return false;
        if (!numberMatches(titleAmount, Math.abs(Number(item.template_amount || 0)))) return false;
        return true;
      });
    }

    function renderKpis(items) {
      const receivableTotal = items
        .filter((item) => item.entry_type === 'receivable')
        .reduce((acc, item) => acc + Number(item.summary?.signed_open_total ?? item.signed_template_amount ?? 0), 0);
      const payableTotal = items
        .filter((item) => item.entry_type === 'payable')
        .reduce((acc, item) => acc + Number(item.summary?.signed_open_total ?? item.signed_template_amount ?? 0), 0);
      const openCount = items.filter((item) => {
        const effectiveState = resolveScheduleState(item.summary || {}, item);
        return !['settled', 'cancelled', 'draft'].includes(effectiveState);
      }).length;

      if (kpis[0]) {
        kpis[0].querySelector('strong').textContent = String(items.length);
      }
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
      if (kpis[3]) {
        kpis[3].querySelector('strong').textContent = String(openCount);
      }
    }

    function renderTable() {
      const items = getFilteredItems();
      renderKpis(items);

      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-state">Nenhum Título Financeiro encontrado para os filtros informados.</td></tr>';
        return;
      }

      tbody.innerHTML = items.map((item) => {
        const summary = item.summary || {};
        const settlementState = resolveScheduleState(summary, item);
        const hasOpenBalance = summary.has_open_balance != null
          ? Boolean(summary.has_open_balance)
          : Number(summary.open_total || 0) > 0;
        const borderoCode = item.bordero?.code || summary.bordero_code || '';
        const isBorderoLocked = Boolean(item.is_bordero_locked || summary.is_bordero_locked);
        const isBorderoVirtual = Boolean(item.is_bordero_virtual);
        const actionsHtml = isBorderoVirtual
          ? `<div class="sched-row-actions">
              <a class="btn btn-primary" href="/financial/borderos/${item.bordero_id}?company_id=${companyId}">Abrir borderô</a>
            </div>`
          : isBorderoLocked
            ? `<div class="sched-row-actions">
                <a class="btn btn-primary" href="/financial/borderos/${item.bordero?.id || item.bordero_id}?company_id=${companyId}">Abrir borderô</a>
                <a class="btn btn-secondary" href="/financial/schedules/${item.id}?company_id=${companyId}">Consultar título</a>
              </div>`
            : `<div class="sched-row-actions">
                <button type="button" class="btn btn-primary" data-action="settle" data-id="${item.id}" ${(hasOpenBalance && !isBorderoLocked) ? '' : 'disabled'}>Baixar</button>
                <a class="btn btn-secondary" href="/financial/schedules/${item.id}?company_id=${companyId}">Editar</a>
                <button type="button" class="btn btn-danger" data-action="delete" data-id="${item.id}" ${isBorderoLocked ? 'disabled' : ''}>Excluir</button>
              </div>`;

        return `
        <tr>
          <td><span class="sched-pill ${settlementClass(settlementState)}">${settlementLabel(settlementState, item)}</span></td>
          <td>${isBorderoVirtual ? (item.bordero_code || item.schedule_code || '-') : item.id}</td>
          <td class="sched-history">
            <strong>${item.name || item.description || 'Sem histórico'}</strong>
            <small>${item.schedule_code || '-'} · ${item.status || '-'}${borderoCode && !isBorderoVirtual ? ` · ${borderoCode}` : ''}</small>
          </td>
          <td><span class="sched-pill ${typeClass(item.entry_type)}">${typeLabel(item.entry_type)}</span></td>
          <td><span class="${amountClass(item.signed_template_amount ?? 0)}">${money(item.signed_template_amount ?? item.template_amount ?? 0)}</span></td>
          <td><span class="${amountClass(summary.signed_open_total ?? item.signed_template_amount ?? 0)}">${money(summary.signed_open_total ?? item.signed_template_amount ?? item.template_amount ?? 0)}</span></td>
          <td>${summary.counterparty_name || item.metadata_json?.counterparty_name || '-'}</td>
          <td>${formatDate(item.start_date || item.first_due_date || item.created_date)}</td>
          <td>${formatDate(item.next_due_date || item.first_due_date || item.created_date)}</td>
          <td>${actionsHtml}</td>
        </tr>
      `;
      }).join('');
    }

    function buildVirtualBorderoItems() {
      return borderos.map((item) => ({
        id: `bordero-${item.id}`,
        bordero_id: item.id,
        bordero_code: item.bordero_code,
        schedule_code: item.bordero_code,
        name: item.name || item.description || item.bordero_code,
        description: item.description || item.name || item.bordero_code,
        entry_type: item.bordero_type,
        template_amount: item.total_amount || 0,
        signed_template_amount: item.signed_total_amount || item.total_amount || 0,
        created_date: item.created_date || String(item.created_at || '').slice(0, 10),
        status: item.status,
        metadata_json: { bordero_code: item.bordero_code },
        is_bordero_virtual: true,
        summary: {
          settlement_state: item.status === 'settled' ? 'settled' : (item.status === 'partially_settled' ? 'partial' : 'open'),
          counterparty_name: '-',
          open_total: item.open_amount || 0,
          signed_open_total: item.signed_open_amount || item.open_amount || 0,
        },
        bordero: {
          id: item.id,
          code: item.bordero_code,
          status: item.status,
          type: item.bordero_type,
          locked: false,
        },
      }));
    }

    function rebuildScheduleItems() {
      scheduleItems = [...buildVirtualBorderoItems(), ...schedules];
    }

    async function loadSchedules() {
      const scheduleParams = new URLSearchParams({ company_id: String(companyId) });
      const dueDateFrom = String(filters.dueDateFrom?.value || '').trim();
      const dueDateTo = String(filters.dueDateTo?.value || '').trim();
      if (dueDateFrom) scheduleParams.set('due_date_from', dueDateFrom);
      if (dueDateTo) scheduleParams.set('due_date_to', dueDateTo);

      schedules = await fetchJson(`/api/financial/schedules?${scheduleParams.toString()}`);
      borderos = await fetchJson(`/api/financial/borderos?company_id=${companyId}`);
      rebuildScheduleItems();
      renderTable();
    }

    async function liquidateSchedule(scheduleId) {
      window.location.href = `/financial/schedules/${scheduleId}?company_id=${companyId}&open_settlement=1`;
    }

    async function deleteSchedule(scheduleId) {
      const confirmed = window.confirm('Deseja realmente excluir este título financeiro?');
      if (!confirmed) return;
      await fetchJson(`/api/financial/schedules/${scheduleId}?company_id=${companyId}`, { method: 'DELETE' });
      await loadSchedules();
    }

    persistableFilters.forEach(([, input]) => input?.addEventListener('input', () => {
      updateFiltersCount();
      saveFiltersState();
      syncFiltersToUrl();
      renderTable();
    }));
    persistableFilters.forEach(([name, input]) => input?.addEventListener('change', async () => {
      updateFiltersCount();
      saveFiltersState();
      syncFiltersToUrl();
      if (name === 'dueDateFrom' || name === 'dueDateTo') {
        try {
          await loadSchedules();
        } catch (error) {
          tbody.innerHTML = `<tr><td colspan="10" class="empty-state">${error.message}</td></tr>`;
        }
      } else {
        renderTable();
      }
    }));

    const clearAllFilters = () => {
      persistableFilters.forEach(([, input]) => {
        writeFilterValue(input, '');
      });
      applyCurrentMonthDueDateRange();
      clearFiltersState();
      updateFiltersCount();
      syncFiltersToUrl();
      loadSchedules().catch((error) => {
        tbody.innerHTML = `<tr><td colspan="10" class="empty-state">${error.message}</td></tr>`;
      });
    };

    clearFiltersButton?.addEventListener('click', clearAllFilters);
    sidebarClearFiltersButton?.addEventListener('click', clearAllFilters);

    tbody.addEventListener('click', async (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      try {
        if (button.dataset.action === 'settle') {
          await liquidateSchedule(Number(button.dataset.id));
        }
        if (button.dataset.action === 'delete') {
          await deleteSchedule(Number(button.dataset.id));
        }
      } catch (error) {
        alert(error.message);
      }
    });

    try {
      const restoredFromUrl = restoreFiltersFromUrl();
      const restoredFromStorage = restoredFromUrl ? false : restoreFiltersState();
      if (!restoredFromUrl && !restoredFromStorage) applyCurrentMonthDueDateRange();
      if (restoredFromUrl) saveFiltersState();
      updateFiltersCount();
      await loadSchedules();
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="10" class="empty-state">${error.message}</td></tr>`;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
