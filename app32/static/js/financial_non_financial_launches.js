(function () {
  const page = document.querySelector('.non-financial-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const form = document.getElementById('non-financial-form');
  const listEl = document.getElementById('non-financial-list');
  const detailCard = document.getElementById('non-financial-detail');
  const detailBody = document.getElementById('non-financial-detail-body');
  const searchInput = document.getElementById('non-financial-search');

  let optionsCache = { counterparties: [], chart_accounts: [], cost_centers: [], enabled_domains: [] };
  let selectedLaunchId = null;

  const $ = (id) => document.getElementById(id);

  const todayDisplay = () => new Date().toLocaleDateString('pt-BR');

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

  const buildOptions = (items, placeholder, formatter) => [`<option value="">${placeholder}</option>`]
    .concat((items || []).map((item) => `<option value="${item.id}">${formatter ? formatter(item) : (item.display_label || item.name || item.code || item.id)}</option>`))
    .join('');

  const buildDomainOptions = (value) => {
    const groups = ['project', 'process'].map((domainType) => {
      const options = (optionsCache.enabled_domains || [])
        .filter((item) => item.domain_type === domainType)
        .map((item) => `<option value="${domainType}:${item.source_id}" ${value === `${domainType}:${item.source_id}` ? 'selected' : ''}>${item.display_label}</option>`)
        .join('');
      return options ? `<optgroup label="${domainType === 'project' ? 'Projetos' : 'Processos'}">${options}</optgroup>` : '';
    }).join('');
    return `<option value="">Selecione...</option>${groups}`;
  };

  const toDomainPayload = (rawValue) => {
    if (!rawValue) return { domain_type: null, domain_source_id: null };
    const [domainType, sourceId] = String(rawValue).split(':');
    const numericId = Number(sourceId || 0);
    if (!domainType || !numericId) return { domain_type: null, domain_source_id: null };
    return { domain_type: domainType, domain_source_id: numericId };
  };

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Falha na operação financeira.');
    return result;
  }

  function ensureDateDefaults({ force = false } = {}) {
    const launchDateInput = $('non-financial-launch-date');
    if (force && !launchDateInput.value) {
      launchDateInput.value = todayDisplay();
    }
  }

  function capturePreservedContext() {
    return {
      counterpartyId: $('non-financial-counterparty').value || '',
      launchDate: $('non-financial-launch-date').value || '',
      debitChartAccountId: $('non-financial-debit-chart-account').value || '',
      debitCostCenterId: $('non-financial-debit-cost-center').value || '',
      debitDomain: $('non-financial-debit-domain').value || '',
      creditChartAccountId: $('non-financial-credit-chart-account').value || '',
      creditCostCenterId: $('non-financial-credit-cost-center').value || '',
      creditDomain: $('non-financial-credit-domain').value || '',
    };
  }

  function restorePreservedContext(context = {}) {
    $('non-financial-counterparty').value = context.counterpartyId || '';
    $('non-financial-launch-date').value = context.launchDate || '';
    $('non-financial-debit-chart-account').value = context.debitChartAccountId || '';
    $('non-financial-debit-cost-center').value = context.debitCostCenterId || '';
    $('non-financial-debit-domain').value = context.debitDomain || '';
    $('non-financial-credit-chart-account').value = context.creditChartAccountId || '';
    $('non-financial-credit-cost-center').value = context.creditCostCenterId || '';
    $('non-financial-credit-domain').value = context.creditDomain || '';
    ensureDateDefaults({ force: true });
  }

  function buildPayload() {
    const description = $('non-financial-description').value.trim();
    const counterpartyId = Number($('non-financial-counterparty').value || 0);
    const launchDate = parseDateToIso($('non-financial-launch-date').value);
    const amount = parseCurrency($('non-financial-amount').value);
    const debitChartAccountId = Number($('non-financial-debit-chart-account').value || 0);
    const debitCostCenterId = Number($('non-financial-debit-cost-center').value || 0);
    const creditChartAccountId = Number($('non-financial-credit-chart-account').value || 0);
    const creditCostCenterId = Number($('non-financial-credit-cost-center').value || 0);

    if (!description) throw new Error('Informe o histórico do lançamento não financeiro.');
    if (!counterpartyId) throw new Error('Selecione o favorecido.');
    if (!launchDate) throw new Error('Informe uma data válida para o lançamento.');
    if (!amount || amount <= 0) throw new Error('Informe um valor válido para o lançamento.');
    if (!debitChartAccountId || !debitCostCenterId) throw new Error('Preencha o lado débito com plano de conta e centro de resultado.');
    if (!creditChartAccountId || !creditCostCenterId) throw new Error('Preencha o lado crédito com plano de conta e centro de resultado.');

    const debitDomain = toDomainPayload($('non-financial-debit-domain').value);
    const creditDomain = toDomainPayload($('non-financial-credit-domain').value);

    return {
      company_id: companyId,
      description,
      counterparty_id: counterpartyId,
      launch_date: launchDate,
      amount,
      title_number: $('non-financial-title-number').value.trim() || null,
      installment_number: $('non-financial-installment-number').value.trim() || null,
      debit_chart_account_id: debitChartAccountId,
      debit_cost_center_id: debitCostCenterId,
      debit_domain_type: debitDomain.domain_type,
      debit_domain_source_id: debitDomain.domain_source_id,
      credit_chart_account_id: creditChartAccountId,
      credit_cost_center_id: creditCostCenterId,
      credit_domain_type: creditDomain.domain_type,
      credit_domain_source_id: creditDomain.domain_source_id,
      notes: $('non-financial-notes').value.trim() || null,
      metadata_json: {},
    };
  }

  function renderLaunchList(items = []) {
    if (!items.length) {
      listEl.innerHTML = '<div class="empty-state">Nenhum lançamento não financeiro encontrado.</div>';
      return;
    }
    listEl.innerHTML = items.map((item) => `
      <button type="button" class="non-financial-item ${selectedLaunchId === item.id ? 'active' : ''}" data-id="${item.id}">
        <strong>${item.launch_code}</strong>
        <small>${item.description || 'Sem histórico'}</small>
        <small>${item.counterparty_label || 'Sem favorecido'}</small>
        <div class="non-financial-item-meta">
          <span>${item.launch_date ? new Date(item.launch_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</span>
          <strong>${Number(item.amount || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
        </div>
      </button>
    `).join('');
  }

  function renderLaunchDetail(item) {
    if (!item) {
      detailCard.classList.add('hidden');
      detailBody.innerHTML = '';
      return;
    }
    detailCard.classList.remove('hidden');
    detailBody.innerHTML = `
      <div class="detail-grid">
        <div class="detail-item"><span>Código</span><strong>${item.launch_code || '-'}</strong></div>
        <div class="detail-item"><span>Status</span><strong><span class="status-badge">${item.launch_status || '-'}</span></strong></div>
        <div class="detail-item"><span>Valor</span><strong>${Number(item.amount || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></div>
        <div class="detail-item"><span>Data</span><strong>${item.launch_date ? new Date(item.launch_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</strong></div>
        <div class="detail-item"><span>Favorecido</span><strong>${item.counterparty_label || '-'}</strong></div>
        <div class="detail-item"><span>Número / Parcela</span><strong>${item.title_installment_label || '-'}</strong></div>
        <div class="detail-item"><span>Histórico</span><strong>${item.description || '-'}</strong></div>
        <div class="detail-item"><span>Observações</span><strong>${item.notes || '-'}</strong></div>
      </div>
      <div class="entry-sides-grid">
        <section class="entry-side debit">
          <h3>Débito</h3>
          <dl>
            <div><dt>Plano de Conta</dt><dd>${item.debit_chart_account_label || '-'}</dd></div>
            <div><dt>Centro de Resultado</dt><dd>${item.debit_cost_center_label || '-'}</dd></div>
            <div><dt>Projeto / Processo</dt><dd>${item.debit_domain_label || '-'}</dd></div>
          </dl>
          <div class="entry-side-links">
            ${item.debit_entry?.id ? `<a class="btn btn-secondary" href="/financial/entries/${item.debit_entry.id}">Abrir débito</a>` : ''}
          </div>
        </section>
        <section class="entry-side credit">
          <h3>Crédito</h3>
          <dl>
            <div><dt>Plano de Conta</dt><dd>${item.credit_chart_account_label || '-'}</dd></div>
            <div><dt>Centro de Resultado</dt><dd>${item.credit_cost_center_label || '-'}</dd></div>
            <div><dt>Projeto / Processo</dt><dd>${item.credit_domain_label || '-'}</dd></div>
          </dl>
          <div class="entry-side-links">
            ${item.credit_entry?.id ? `<a class="btn btn-secondary" href="/financial/entries/${item.credit_entry.id}">Abrir crédito</a>` : ''}
          </div>
        </section>
      </div>
    `;
  }

  async function loadList() {
    const params = new URLSearchParams({ company_id: String(companyId) });
    const query = searchInput.value.trim();
    if (query) params.set('query', query);
    const items = await fetchJson(`/api/financial/non-financial-entries?${params.toString()}`);
    renderLaunchList(items);
  }

  async function loadDetail(launchId) {
    selectedLaunchId = Number(launchId || 0) || null;
    await loadList();
    if (!selectedLaunchId) {
      renderLaunchDetail(null);
      return;
    }
    const item = await fetchJson(`/api/financial/non-financial-entries/${selectedLaunchId}?company_id=${companyId}`);
    renderLaunchDetail(item);
  }

  async function loadOptions() {
    optionsCache = await fetchJson(`/api/financial/non-financial-entries/options?company_id=${companyId}`);
    $('non-financial-counterparty').innerHTML = buildOptions(optionsCache.counterparties, 'Selecione...', (item) => item.display_label || item.name || item.code);
    const chartOptions = buildOptions(optionsCache.chart_accounts, 'Selecione...', (item) => item.display_label || item.name || item.code);
    const centerOptions = buildOptions(optionsCache.cost_centers, 'Selecione...', (item) => item.display_label || item.name || item.code);
    $('non-financial-debit-chart-account').innerHTML = chartOptions;
    $('non-financial-credit-chart-account').innerHTML = chartOptions;
    $('non-financial-debit-cost-center').innerHTML = centerOptions;
    $('non-financial-credit-cost-center').innerHTML = centerOptions;
    $('non-financial-debit-domain').innerHTML = buildDomainOptions('');
    $('non-financial-credit-domain').innerHTML = buildDomainOptions('');
  }

  window.startNewNonFinancialLaunch = () => {
    selectedLaunchId = null;
    form.reset();
    renderLaunchDetail(null);
    ensureDateDefaults({ force: true });
    loadList();
    $('non-financial-description').focus();
  };

  window.saveNonFinancialLaunch = async (keepSelected) => {
    try {
      const preservedContext = capturePreservedContext();
      const result = await fetchJson(`/api/financial/non-financial-entries?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });

      await loadList();
      if (keepSelected) {
        selectedLaunchId = result.id || null;
        renderLaunchDetail(result);
      } else {
        selectedLaunchId = null;
        form.reset();
        restorePreservedContext(preservedContext);
        renderLaunchDetail(null);
        await loadList();
      }

      $('non-financial-description').focus();
      alert(`Lançamento não financeiro registrado com sucesso.\nCódigo: ${result.launch_code || '-'}`);
    } catch (error) {
      alert(error.message);
    }
  };

  window.openNonFinancialCounterpartyModal = () => {
    $('non-financial-counterparty-modal').classList.remove('hidden');
    $('non-financial-counterparty-modal').setAttribute('aria-hidden', 'false');
  };

  window.closeNonFinancialCounterpartyModal = () => {
    $('non-financial-counterparty-modal').classList.add('hidden');
    $('non-financial-counterparty-modal').setAttribute('aria-hidden', 'true');
    $('non-financial-counterparty-form').reset();
  };

  $('non-financial-counterparty-form').addEventListener('submit', async (event) => {
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
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      await loadOptions();
      $('non-financial-counterparty').value = created.id;
      window.closeNonFinancialCounterpartyModal();
    } catch (error) {
      alert(error.message);
    }
  });

  $('non-financial-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
  });

  $('non-financial-launch-date').addEventListener('input', (event) => {
    event.target.value = normalizeDateInput(event.target.value);
  });

  searchInput.addEventListener('input', () => {
    clearTimeout(searchInput._timer);
    searchInput._timer = setTimeout(() => loadList(), 220);
  });

  listEl.addEventListener('click', async (event) => {
    const item = event.target.closest('.non-financial-item');
    if (!item) return;
    await loadDetail(item.dataset.id);
  });

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadOptions();
      ensureDateDefaults({ force: true });
      await loadList();
      $('non-financial-description').focus();
    } catch (error) {
      alert(error.message);
    }
  });
})();
