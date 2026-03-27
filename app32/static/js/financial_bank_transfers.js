(function () {
  const page = document.querySelector('.bank-transfer-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const form = document.getElementById('bank-transfer-form');
  const listEl = document.getElementById('bank-transfer-list');
  const detailCard = document.getElementById('bank-transfer-detail');
  const detailBody = document.getElementById('bank-transfer-detail-body');
  const searchInput = document.getElementById('bank-transfer-search');
  let optionsCache = { bank_accounts: [] };
  let selectedTransferId = null;

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

  const buildOptions = (items, placeholder) => [`<option value="">${placeholder}</option>`]
    .concat((items || []).map((item) => `<option value="${item.id}">${item.code ? `${item.code} - ${item.name}` : (item.name || item.id)}</option>`))
    .join('');

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Falha na operação financeira.');
    return result;
  }

  function ensureDateDefaults({ force = false } = {}) {
    const transferDateInput = $('transfer-date');
    const baseValue = transferDateInput.value || todayDisplay();

    if (force && !transferDateInput.value) {
      transferDateInput.value = baseValue;
    }
  }

  function capturePreservedContext() {
    return {
      originBankAccountId: $('transfer-origin-bank-account').value || '',
      destinationBankAccountId: $('transfer-destination-bank-account').value || '',
      transferDate: $('transfer-date').value || '',
    };
  }

  function restorePreservedContext(context = {}) {
    $('transfer-origin-bank-account').value = context.originBankAccountId || '';
    $('transfer-destination-bank-account').value = context.destinationBankAccountId || '';
    $('transfer-date').value = context.transferDate || '';
    ensureDateDefaults({ force: true });
  }

  function buildPayload() {
    const description = $('transfer-description').value.trim();
    const originBankAccountId = Number($('transfer-origin-bank-account').value || 0);
    const destinationBankAccountId = Number($('transfer-destination-bank-account').value || 0);
    const transferDate = parseDateToIso($('transfer-date').value);
    const amount = parseCurrency($('transfer-amount').value);

    if (!description) throw new Error('Informe o histórico da transferência.');
    if (!originBankAccountId) throw new Error('Selecione a conta de origem.');
    if (!destinationBankAccountId) throw new Error('Selecione a conta de destino.');
    if (originBankAccountId === destinationBankAccountId) throw new Error('Conta de origem e destino devem ser diferentes.');
    if (!transferDate) throw new Error('Informe uma data válida para a transferência.');
    if (!amount || amount <= 0) throw new Error('Informe um valor válido para a transferência.');

    return {
      company_id: companyId,
      description,
      document_number: $('transfer-document-number').value.trim() || null,
      origin_bank_account_id: originBankAccountId,
      destination_bank_account_id: destinationBankAccountId,
      transfer_date: transferDate,
      amount,
      notes: $('transfer-notes').value.trim() || null,
      metadata_json: {},
    };
  }

  function renderTransferList(items = []) {
    if (!items.length) {
      listEl.innerHTML = '<div class="empty-state">Nenhuma transferência bancária encontrada.</div>';
      return;
    }
    listEl.innerHTML = items.map((item) => `
      <button type="button" class="bank-transfer-item ${selectedTransferId === item.id ? 'active' : ''}" data-id="${item.id}">
        <strong>${item.transfer_code}</strong>
        <small>${item.description || 'Sem histórico'}</small>
        <small>${item.origin_bank_account_label || 'Origem'} → ${item.destination_bank_account_label || 'Destino'}</small>
        <div class="bank-transfer-item-meta">
          <span>${item.transfer_date ? new Date(item.transfer_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</span>
          <strong>${Number(item.amount || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
        </div>
      </button>
    `).join('');
  }

  function renderTransferDetail(item) {
    if (!item) {
      detailCard.classList.add('hidden');
      detailBody.innerHTML = '';
      return;
    }
    detailCard.classList.remove('hidden');
    detailBody.innerHTML = `
      <div class="detail-grid">
        <div class="detail-item"><span>Código</span><strong>${item.transfer_code || '-'}</strong></div>
        <div class="detail-item"><span>Status</span><strong><span class="badge badge--${item.transfer_status || 'posted'}">${item.transfer_status || '-'}</span></strong></div>
        <div class="detail-item"><span>Valor</span><strong>${Number(item.amount || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></div>
        <div class="detail-item"><span>Conta de origem</span><strong>${item.origin_bank_account_label || '-'}</strong></div>
        <div class="detail-item"><span>Conta de destino</span><strong>${item.destination_bank_account_label || '-'}</strong></div>
        <div class="detail-item"><span>Data</span><strong>${item.transfer_date ? new Date(item.transfer_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</strong></div>
        <div class="detail-item"><span>Histórico</span><strong>${item.description || '-'}</strong></div>
        <div class="detail-item"><span>Documento</span><strong>${item.document_number || '-'}</strong></div>
        <div class="detail-item"><span>Observações</span><strong>${item.notes || '-'}</strong></div>
      </div>
      <div class="transfer-detail-actions">
        ${item.origin_entry?.id ? `<a class="btn btn-secondary" href="/financial/entries/${item.origin_entry.id}">Abrir débito</a>` : ''}
        ${item.destination_entry?.id ? `<a class="btn btn-secondary" href="/financial/entries/${item.destination_entry.id}">Abrir crédito</a>` : ''}
      </div>
    `;
  }

  async function loadTransferList() {
    const params = new URLSearchParams({ company_id: String(companyId) });
    const query = searchInput.value.trim();
    if (query) params.set('query', query);
    const items = await fetchJson(`/api/financial/bank-transfers?${params.toString()}`);
    renderTransferList(items);
  }

  async function loadTransferDetail(transferId) {
    selectedTransferId = Number(transferId || 0) || null;
    renderTransferList(await fetchJson(`/api/financial/bank-transfers?company_id=${companyId}&query=${encodeURIComponent(searchInput.value.trim())}`));
    if (!selectedTransferId) {
      renderTransferDetail(null);
      return;
    }
    const item = await fetchJson(`/api/financial/bank-transfers/${selectedTransferId}?company_id=${companyId}`);
    renderTransferDetail(item);
  }

  async function loadOptions() {
    optionsCache = await fetchJson(`/api/financial/bank-transfers/options?company_id=${companyId}`);
    const optionsHtml = buildOptions(optionsCache.bank_accounts, 'Selecione...');
    $('transfer-origin-bank-account').innerHTML = optionsHtml;
    $('transfer-destination-bank-account').innerHTML = optionsHtml;
  }

  window.startNewBankTransfer = () => {
    selectedTransferId = null;
    form.reset();
    renderTransferDetail(null);
    renderTransferList([]);
    restorePreservedContext({});
    loadTransferList();
    $('transfer-description').focus();
  };

  window.saveBankTransfer = async (redirectBack) => {
    try {
      const preservedContext = capturePreservedContext();
      const result = await fetchJson(`/api/financial/bank-transfers?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });
      await loadTransferList();
      selectedTransferId = result.id || null;
      renderTransferDetail(result);

      if (redirectBack) {
        window.location.href = '/financial/entries';
        return;
      }

      form.reset();
      restorePreservedContext(preservedContext);
      $('transfer-description').focus();
      alert(`Transferência bancária registrada com sucesso.\nCódigo: ${result.transfer_code || '-'}`);
    } catch (error) {
      alert(error.message);
    }
  };

  $('transfer-amount').addEventListener('input', (event) => {
    event.target.value = formatCurrencyFromDigits(event.target.value);
  });

  ['transfer-date'].forEach((id) => {
    $(id).addEventListener('input', (event) => {
      event.target.value = normalizeDateInput(event.target.value);
    });
  });

  $('transfer-date').addEventListener('blur', () => ensureDateDefaults());

  searchInput.addEventListener('input', () => {
    clearTimeout(searchInput._timer);
    searchInput._timer = setTimeout(() => loadTransferList(), 220);
  });

  listEl.addEventListener('click', async (event) => {
    const item = event.target.closest('.bank-transfer-item');
    if (!item) return;
    await loadTransferDetail(item.dataset.id);
  });

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadOptions();
      ensureDateDefaults({ force: true });
      await loadTransferList();
      $('transfer-description').focus();
    } catch (error) {
      alert(error.message);
    }
  });
})();
