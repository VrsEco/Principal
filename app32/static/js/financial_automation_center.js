(function () {
  const root = document.querySelector('.fa-page');
  if (!root) return;
  const companyId = Number(root.dataset.companyId || 0);
  const recordsBody = document.getElementById('fa-records-body');
  const importDialog = document.getElementById('fa-import-dialog');
  const documentDialog = document.getElementById('fa-document-dialog');
  const documentBody = document.getElementById('fa-document-body');
  const state = { options: null, records: [] };
  const statusLabels = { imported: 'Importada', validated: 'Validada', generated: 'Gerada', excluded: 'Excluída' };
  const originLabels = {
    accountability: 'Prestação de contas',
    csv: 'CSV',
    xlsx: 'Planilha',
    ofx: 'OFX',
    api: 'API',
    mcp: 'MCP',
    manual_upload: 'Upload manual',
    integration: 'Integração',
  };

  const byId = (id) => document.getElementById(id);
  const selectedIds = () => Array.from(document.querySelectorAll('.fa-record-select:checked')).map((el) => Number(el.value));
  const badge = (status) => `<span class="fa-badge fa-badge--${status}">${statusLabels[status] || status || '-'}</span>`;

  async function api(url, options = {}) {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'Falha na operação.');
    return payload;
  }

  function optionLabel(item) {
    return `${item.code ? `${item.code} · ` : ''}${item.name || item.display_label || item.label || item.source_name || ''}`;
  }

  function domainLabel(record) {
    if (!record.domain_type || !record.domain_source_id) return '';
    return `${record.domain_type}:${record.domain_source_id}`;
  }

  function selectHtml(items, selectedValue, placeholder, valueGetter = (item) => item.id, labelGetter = optionLabel, fieldName = '') {
    const options = [`<option value="">${placeholder}</option>`]
      .concat((items || []).map((item) => {
        const value = valueGetter(item);
        const selected = String(value) === String(selectedValue) ? 'selected' : '';
        return `<option value="${value}" ${selected}>${labelGetter(item)}</option>`;
      }));
    return `<select data-field="${fieldName}">${options.join('')}</select>`;
  }

  function render() {
    if (!state.records.length) {
      recordsBody.innerHTML = '<tr><td colspan="16" class="fa-empty">Nenhum registro encontrado.</td></tr>';
      return;
    }
    recordsBody.innerHTML = state.records.map((record) => `
      <tr data-record-id="${record.id}">
        <td><input type="checkbox" class="fa-record-select" value="${record.id}"></td>
        <td>${badge(record.status)}</td>
        <td>${record.batch?.source_label || originLabels[record.batch?.origin_type] || record.document?.mime_type || record.document?.file_name || '-'}</td>
        <td>${selectHtml([{id:'payable',name:'Pagar'},{id:'receivable',name:'Receber'}], record.entry_direction, 'Tipo', (item) => item.id, optionLabel, 'entry_direction')}</td>
        <td>${selectHtml([{id:'settled',name:'Já pago/recebido'},{id:'open',name:'Em aberto'}], record.settlement_state, 'Situação', (item) => item.id, optionLabel, 'settlement_state')}</td>
        <td><input type="text" value="${record.description || ''}" data-field="description"></td>
        <td>${selectHtml(state.options?.counterparties, record.counterparty_id, 'Favorecido', (item) => item.id, optionLabel, 'counterparty_id')}</td>
        <td><input type="number" step="0.01" value="${record.amount || 0}" data-field="amount"></td>
        <td><input type="date" value="${record.competence_date || ''}" data-field="competence_date"></td>
        <td><input type="date" value="${record.due_date || ''}" data-field="due_date"></td>
        <td>${selectHtml(state.options?.bank_accounts, record.bank_account_id, 'Conta', (item) => item.id, optionLabel, 'bank_account_id')}</td>
        <td>${selectHtml(state.options?.chart_accounts, record.chart_account_id, 'Conta contábil', (item) => item.id, optionLabel, 'chart_account_id')}</td>
        <td>${selectHtml(state.options?.cost_centers, record.cost_center_id, 'Centro', (item) => item.id, optionLabel, 'cost_center_id')}</td>
        <td>${selectHtml(state.options?.domain_options, domainLabel(record), 'Projeto/Processo', (item) => `${item.domain_type}:${item.source_id}`, (item) => item.label, 'domain_link')}</td>
        <td>${record.confidence_score ?? '-'}</td>
        <td>
          <div class="fa-inline">
            <button type="button" class="fa-btn fa-btn--ghost" data-action="save">Salvar</button>
            <button type="button" class="fa-btn fa-btn--secondary" data-action="origin">Ver origem</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  function rowPayload(row) {
    const id = Number(row.dataset.recordId);
    const payload = {};
    row.querySelectorAll('[data-field]').forEach((el) => {
      const field = el.dataset.field;
      if (!field) return;
      if (field === 'domain_link') {
        if (el.value) {
          const [domain_type, source_id] = el.value.split(':');
          payload.domain_type = domain_type;
          payload.domain_source_id = Number(source_id);
        } else {
          payload.domain_type = null;
          payload.domain_source_id = null;
        }
        return;
      }
      if (['counterparty_id', 'bank_account_id', 'chart_account_id', 'cost_center_id'].includes(field)) {
        payload[field] = el.value ? Number(el.value) : null;
        return;
      }
      if (field === 'amount') {
        payload.amount = el.value ? Number(el.value) : 0;
        return;
      }
      payload[field] = el.value || null;
    });
    return { id, payload };
  }

  async function loadOptions() {
    state.options = await api(`/api/financial/automation/options?company_id=${companyId}`);
    const originFilter = byId('filter-origin');
    originFilter.innerHTML = '<option value="">Todas</option>' + ['accountability','csv','xlsx','ofx','api','mcp','manual_upload','integration']
      .map((item) => `<option value="${item}">${originLabels[item] || item}</option>`).join('');
  }

  async function loadRecords() {
    const query = new URLSearchParams({ company_id: companyId });
    [['status', 'filter-status'], ['origin_type', 'filter-origin'], ['competence_date_from', 'filter-competence-from'], ['competence_date_to', 'filter-competence-to'], ['due_date_from', 'filter-due-from'], ['due_date_to', 'filter-due-to']]
      .forEach(([key, id]) => { const value = byId(id).value; if (value) query.set(key, value); });
    state.records = await api(`/api/financial/automation/records?${query.toString()}`);
    render();
  }

  async function saveRow(row) {
    const { id, payload } = rowPayload(row);
    await api(`/api/financial/automation/records/${id}?company_id=${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    await loadRecords();
  }

  async function showOrigin(row) {
    const recordId = Number(row.dataset.recordId);
    const record = state.records.find((item) => item.id === recordId);
    if (!record?.document?.id) {
      documentBody.innerHTML = '<p class="fa-muted">Este registro não possui documento/origem estruturada.</p>';
      documentDialog.showModal();
      return;
    }
    const payload = await api(`/api/financial/automation/documents/${record.document.id}?company_id=${companyId}`);
    const publicUrl = payload.public_url ? `<p><a href="${payload.public_url}" target="_blank" rel="noopener">Abrir arquivo</a></p>` : '';
    documentBody.innerHTML = `
      <div class="fa-doc-preview">
        <div>
          <h4>Metadados</h4>
          <pre>${JSON.stringify(payload, null, 2)}</pre>
        </div>
        <div>
          <h4>Texto extraído</h4>
          <pre>${payload.extracted_text || '(sem texto extraído)'}</pre>
          ${publicUrl}
        </div>
      </div>
    `;
    documentDialog.showModal();
  }

  async function bulkStatus(status) {
    const ids = selectedIds();
    if (!ids.length) return alert('Selecione ao menos um registro.');
    await api(`/api/financial/automation/records/bulk-status?company_id=${companyId}`, {
      method: 'POST',
      body: JSON.stringify({ record_ids: ids, status }),
    });
    await loadRecords();
  }

  async function generateSelected() {
    const ids = selectedIds();
    await api(`/api/financial/automation/generate?company_id=${companyId}`, {
      method: 'POST',
      body: JSON.stringify({ record_ids: ids.length ? ids : null }),
    });
    await loadRecords();
  }

  async function createBatch() {
    try {
      const body = {
        origin_type: byId('fa-import-origin').value,
        source_label: byId('fa-import-source-label').value || null,
        documents: byId('fa-import-documents').value ? JSON.parse(byId('fa-import-documents').value) : [],
        records: byId('fa-import-records').value ? JSON.parse(byId('fa-import-records').value) : [],
      };
      await api(`/api/financial/automation/batches?company_id=${companyId}`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      importDialog.close();
      byId('fa-import-documents').value = '';
      byId('fa-import-records').value = '';
      await loadRecords();
    } catch (error) {
      alert(error.message);
    }
  }

  byId('fa-open-import').addEventListener('click', () => importDialog.showModal());
  byId('fa-refresh').addEventListener('click', loadRecords);
  byId('fa-submit-import').addEventListener('click', createBatch);
  byId('fa-mark-validated').addEventListener('click', () => bulkStatus('validated'));
  byId('fa-mark-excluded').addEventListener('click', () => bulkStatus('excluded'));
  byId('fa-generate').addEventListener('click', generateSelected);
  byId('fa-select-all').addEventListener('change', (event) => {
    document.querySelectorAll('.fa-record-select').forEach((el) => { el.checked = event.target.checked; });
  });
  byId('fa-filters').addEventListener('change', loadRecords);
  recordsBody.addEventListener('click', async (event) => {
    const action = event.target.dataset.action;
    const row = event.target.closest('tr');
    if (!action || !row) return;
    if (action === 'save') await saveRow(row);
    if (action === 'origin') await showOrigin(row);
  });

  (async function init() {
    try {
      await loadOptions();
      await loadRecords();
    } catch (error) {
      recordsBody.innerHTML = `<tr><td colspan="16" class="fa-empty">${error.message}</td></tr>`;
    }
  })();
})();
