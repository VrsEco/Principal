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
    const paginationContainer = document.getElementById('bordero-pagination');
    const filters = {
      search: document.getElementById('bordero-filter-search'),
      type: document.getElementById('bordero-filter-type'),
      status: document.getElementById('bordero-filter-status'),
    };

    let borderos = [];
    let borderoPagination = { page: 1, per_page: 50, total: 0, has_more: false };
    let borderoSummary = {};
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
      return borderos;
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
      const openTotal = Number(borderoSummary.signed_open_amount || 0);
      const settledTotal = Number(borderoSummary.signed_settled_amount || 0);
      const itemCount = items.reduce((acc, item) => acc + Number(item.item_count || 0), 0);
      if (kpis[0]) kpis[0].querySelector('strong').textContent = String(borderoPagination.total || 0);
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
        if (paginationContainer) paginationContainer.replaceChildren();
        return;
      }

      tbody.innerHTML = items.map((item) => `
        <tr>
          <td data-label="Status"><span class="bordero-pill bordero-pill--${item.status}">${statusLabel(item.status)}</span></td>
          <td data-label="Código"><span class="entry-code-pill">${item.bordero_code || '-'}</span></td>
          <td data-label="Descrição">
            <div class="bordero-row-title">
              <strong>${item.name || item.description || 'Sem nome'}</strong>
              <small class="cell-muted">${item.description || 'Sem descrição'} · ${item.notes || 'Sem observações'}</small>
            </div>
          </td>
          <td data-label="Tipo"><span class="bordero-pill bordero-pill--${item.bordero_type}">${typeLabel(item.bordero_type)}</span></td>
          <td data-label="Itens">${item.item_count || 0}</td>
          <td data-label="Total">${money(item.signed_total_amount || item.total_amount || 0)}</td>
          <td data-label="Liquidado">${money(item.signed_settled_amount || item.settled_amount || 0)}</td>
          <td data-label="Em aberto">${money(item.signed_open_amount || item.open_amount || 0)}</td>
          <td data-label="Ações">
            <div class="actions-stack">
              <a class="btn btn-secondary btn-sm" href="/financial/borderos/${item.id}?company_id=${companyId}">Editar</a>
              ${item.can_settle
                ? `<a class="btn btn-primary btn-sm" href="/financial/borderos/${item.id}?company_id=${companyId}">Baixar</a>`
                : `<span class="btn btn-primary btn-sm is-disabled">Baixar</span>`}
              <button type="button" class="btn btn-danger btn-sm" data-action="delete" data-id="${item.id}" ${item.can_delete ? '' : 'disabled'}>Excluir</button>
            </div>
          </td>
        </tr>
      `).join('');
      renderPagination();
    }

    function renderPagination() {
      if (!paginationContainer) return;
      paginationContainer.replaceChildren();
      if (!borderoPagination.has_more) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-secondary';
      button.textContent = `Carregar mais (${borderos.length} de ${borderoPagination.total})`;
      button.addEventListener('click', async () => {
        button.disabled = true;
        button.textContent = 'Carregando...';
        try {
          await load({ append: true });
        } catch (error) {
          button.disabled = false;
          button.textContent = error.message || 'Tentar novamente';
        }
      });
      paginationContainer.appendChild(button);
    }

    async function load({ append = false } = {}) {
      const page = append ? borderoPagination.page + 1 : 1;
      const params = new URLSearchParams({
        company_id: String(companyId),
        paginated: 'true',
        page: String(page),
        per_page: '50',
      });
      const search = String(filters.search?.value || '').trim();
      const type = String(filters.type?.value || '').trim();
      const status = String(filters.status?.value || '').trim();
      if (search) params.set('search', search);
      if (type) params.set('bordero_type', type);
      if (status) params.set('status', status);
      const payload = await fetchJson(`/api/financial/borderos?${params.toString()}`);
      if (!Array.isArray(payload.items) || !payload.pagination) {
        throw new Error('Resposta paginada inválida ao carregar borderôs.');
      }
      if (append) {
        const knownIds = new Set(borderos.map((item) => Number(item.id)));
        borderos = borderos.concat(payload.items.filter((item) => !knownIds.has(Number(item.id))));
      } else {
        borderos = payload.items;
      }
      borderoPagination = payload.pagination;
      borderoSummary = payload.summary || {};
      render();
    }

    async function deleteBordero(borderoId) {
      const confirmed = window.confirm('Deseja realmente excluir este borderô?');
      if (!confirmed) return;
      await fetchJson(`/api/financial/borderos/${borderoId}?company_id=${companyId}`, { method: 'DELETE' });
      await load();
    }

    Object.values(filters).forEach((input) => {
      input?.addEventListener('input', updateFilterIndicators);
      input?.addEventListener('change', updateFilterIndicators);
    });

    applyButton?.addEventListener('click', () => load().catch((error) => {
      tbody.innerHTML = `<tr><td colspan="9" class="empty-cell">${error.message}</td></tr>`;
    }));
    clearButton?.addEventListener('click', () => {
      Object.values(filters).forEach((input) => {
        if (input) input.value = '';
      });
      load().catch((error) => {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-cell">${error.message}</td></tr>`;
      });
    });

    tbody?.addEventListener('click', async (event) => {
      const button = event.target.closest('button[data-action="delete"]');
      if (!button) return;
      try {
        await deleteBordero(Number(button.dataset.id));
      } catch (error) {
        alert(error.message);
      }
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
