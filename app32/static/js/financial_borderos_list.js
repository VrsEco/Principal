(function () {
  async function init() {
    const page = document.querySelector('.bordero-list-page');
    if (!page) return;

    const companyId = Number(page.dataset.companyId || 0);
    const tbody = document.getElementById('bordero-table-body');
    const kpis = Array.from(document.querySelectorAll('#bordero-kpis .bordero-kpi'));
    const filterCount = document.getElementById('borderos-filters-count');
    const activeFiltersChip = document.getElementById('bordero-active-filters-chip');
    const applyButton = document.getElementById('borderos-apply-filters');
    const clearButton = document.getElementById('borderos-clear-filters');
    const filters = {
      search: document.getElementById('bordero-filter-search'),
      type: document.getElementById('bordero-filter-type'),
      status: document.getElementById('bordero-filter-status'),
    };

    let borderos = [];
    const money = (value) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const typeLabel = (value) => value === 'payable' ? 'Pagamento' : 'Recebimento';
    const statusLabel = (value) => ({ open: 'Aberto', partially_settled: 'Parcial', settled: 'Liquidado', cancelled: 'Cancelado', draft: 'Rascunho' }[value] || value || '-');
    const getActiveFilters = () => Object.values(filters).filter((input) => String(input?.value || '').trim());

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Falha ao carregar borderôs.');
      return payload;
    }

    function getFiltered() {
      const search = String(filters.search?.value || '').trim().toLowerCase();
      const type = String(filters.type?.value || '').trim();
      const status = String(filters.status?.value || '').trim();
      return borderos.filter((item) => {
        const haystack = `${item.bordero_code || ''} ${item.description || ''} ${item.notes || ''}`.toLowerCase();
        if (search && !haystack.includes(search)) return false;
        if (type && item.bordero_type !== type) return false;
        if (status && item.status !== status) return false;
        return true;
      });
    }

    function updateFilterIndicators() {
      const activeCount = getActiveFilters().length;
      if (filterCount) filterCount.textContent = String(activeCount);

      if (!activeFiltersChip) return;
      if (!activeCount) {
        activeFiltersChip.textContent = 'Sem filtros ativos';
        return;
      }

      const labels = [];
      const search = String(filters.search?.value || '').trim();
      const type = String(filters.type?.value || '').trim();
      const status = String(filters.status?.value || '').trim();
      if (search) labels.push(`Busca: ${search}`);
      if (type) labels.push(`Tipo: ${typeLabel(type)}`);
      if (status) labels.push(`Status: ${statusLabel(status)}`);
      activeFiltersChip.textContent = labels.join(' · ');
    }

    function renderKpis(items) {
      const openTotal = items.reduce((acc, item) => acc + Number(item.signed_open_amount || 0), 0);
      const settledTotal = items.reduce((acc, item) => acc + Number(item.signed_settled_amount || 0), 0);
      const itemCount = items.reduce((acc, item) => acc + Number(item.item_count || 0), 0);
      if (kpis[0]) kpis[0].querySelector('strong').textContent = String(items.length);
      if (kpis[1]) kpis[1].querySelector('strong').textContent = money(openTotal);
      if (kpis[2]) kpis[2].querySelector('strong').textContent = money(settledTotal);
      if (kpis[3]) kpis[3].querySelector('strong').textContent = String(itemCount);
    }

    function render() {
      const items = getFiltered();
      updateFilterIndicators();
      renderKpis(items);
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-cell">Nenhum borderô encontrado para os filtros aplicados.</td></tr>';
        return;
      }

      tbody.innerHTML = items.map((item) => `
        <tr>
          <td><span class="bordero-pill bordero-pill--${item.status}">${statusLabel(item.status)}</span></td>
          <td><span class="entry-code-pill">${item.bordero_code || '-'}</span></td>
          <td>
            <div class="bordero-row-title">
              <strong>${item.description || 'Sem descrição'}</strong>
              <small class="cell-muted">ID ${item.id} · ${item.notes || 'Sem observações'}</small>
            </div>
          </td>
          <td><span class="bordero-pill bordero-pill--${item.bordero_type}">${typeLabel(item.bordero_type)}</span></td>
          <td>${item.item_count || 0}</td>
          <td>${money(item.signed_total_amount || item.total_amount || 0)}</td>
          <td>${money(item.signed_settled_amount || item.settled_amount || 0)}</td>
          <td>${money(item.signed_open_amount || item.open_amount || 0)}</td>
          <td>
            <div class="actions-stack">
              <a class="btn btn-secondary btn-sm" href="/financial/borderos/${item.id}">Abrir</a>
            </div>
          </td>
        </tr>
      `).join('');
    }

    async function load() {
      borderos = await fetchJson(`/api/financial/borderos?company_id=${companyId}`);
      render();
    }

    Object.values(filters).forEach((input) => {
      input?.addEventListener('input', updateFilterIndicators);
      input?.addEventListener('change', updateFilterIndicators);
    });

    applyButton?.addEventListener('click', render);
    clearButton?.addEventListener('click', () => {
      Object.values(filters).forEach((input) => {
        if (input) input.value = '';
      });
      render();
    });

    try {
      await load();
    } catch (error) {
      updateFilterIndicators();
      tbody.innerHTML = `<tr><td colspan="9" class="empty-cell">${error.message}</td></tr>`;
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
