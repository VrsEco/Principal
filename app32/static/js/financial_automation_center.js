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
  const documentTypeLabels = {
    nfe_xml: 'NFe XML',
    nfce_xml: 'NFCe XML',
    cte_xml: 'CTe XML',
    danfe_pdf: 'DANFE PDF',
    dacte_pdf: 'DACTE PDF',
    receipt_pdf: 'Recibo PDF',
    receipt_image: 'Recibo imagem',
    spreadsheet: 'Planilha',
    ofx: 'OFX',
    unknown_document: 'Documento',
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

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function documentLabel(record) {
    const type = record.document_type || record.document?.document_type;
    return documentTypeLabels[type] || type || 'Documento';
  }

  function partiesLabel(record) {
    const issuer = record.issuer_name || record.extracted_fields_json?.issuer_name;
    const recipient = record.recipient_name || record.extracted_fields_json?.recipient_name;
    return [issuer, recipient].filter(Boolean).join(' → ') || '-';
  }

  function keyLabel(record) {
    const number = record.external_document_number || record.extracted_fields_json?.document_number;
    const key = record.document_key || record.extracted_fields_json?.document_key;
    const parts = [];
    if (number) parts.push(`Nº ${number}`);
    if (key) parts.push(key);
    return parts.join('<br>') || '-';
  }

  function pendingLabel(record) {
    const flags = record.review_flags_json || [];
    if (!flags.length) return '<span class="fa-muted">Sem pendências</span>';
    return flags.map((flag) => `<span class="fa-badge fa-badge--excluded">${escapeHtml(flag)}</span>`).join(' ');
  }

  function originLabel(record) {
    const sourceLabel = record.batch?.source_label || originLabels[record.batch?.origin_type];
    const fileName = record.document?.file_name;
    return [sourceLabel, fileName].filter(Boolean).join('<br>') || '-';
  }

  function render() {
    if (!state.records.length) {
      recordsBody.innerHTML = '<tr><td colspan="20" class="fa-empty">Nenhum registro encontrado.</td></tr>';
      return;
    }
    recordsBody.innerHTML = state.records.map((record) => `
      <tr data-record-id="${record.id}">
        <td><input type="checkbox" class="fa-record-select" value="${record.id}"></td>
        <td>${badge(record.status)}</td>
        <td><strong>${documentLabel(record)}</strong><br><span class="fa-muted">${escapeHtml(record.document_group_key || '-')}</span></td>
        <td>${originLabel(record)}</td>
        <td>${escapeHtml(partiesLabel(record))}</td>
        <td>${keyLabel(record)}</td>
        <td>${selectHtml([{id:'payable',name:'Pagar'},{id:'receivable',name:'Receber'}], record.entry_direction, 'Tipo', (item) => item.id, optionLabel, 'entry_direction')}</td>
        <td>${selectHtml([{id:'settled',name:'Já pago/recebido'},{id:'open',name:'Em aberto'}], record.settlement_state, 'Situação', (item) => item.id, optionLabel, 'settlement_state')}</td>
        <td><input type="text" value="${escapeHtml(record.description || '')}" data-field="description"></td>
        <td>${selectHtml(state.options?.counterparties, record.counterparty_id, 'Favorecido', (item) => item.id, optionLabel, 'counterparty_id')}</td>
        <td><input type="number" step="0.01" value="${record.amount || 0}" data-field="amount"></td>
        <td><input type="date" value="${record.competence_date || ''}" data-field="competence_date"></td>
        <td><input type="date" value="${record.due_date || ''}" data-field="due_date"></td>
        <td>${selectHtml(state.options?.bank_accounts, record.bank_account_id, 'Conta', (item) => item.id, optionLabel, 'bank_account_id')}</td>
        <td>${selectHtml(state.options?.chart_accounts, record.chart_account_id, 'Conta contábil', (item) => item.id, optionLabel, 'chart_account_id')}</td>
        <td>${selectHtml(state.options?.cost_centers, record.cost_center_id, 'Centro', (item) => item.id, optionLabel, 'cost_center_id')}</td>
        <td>${selectHtml(state.options?.domain_options, domainLabel(record), 'Projeto/Processo', (item) => `${item.domain_type}:${item.source_id}`, (item) => item.label, 'domain_link')}</td>
        <td>${record.confidence_score ?? '-'}</td>
        <td>${pendingLabel(record)}</td>
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
    originFilter.innerHTML = '<option value="">Todas</option>' + ['accountability', 'csv', 'xlsx', 'ofx', 'api', 'mcp', 'manual_upload', 'integration']
      .map((item) => `<option value="${item}">${originLabels[item] || item}</option>`).join('');
    const documentTypeFilter = byId('filter-document-type');
    const documentOptions = state.options?.document_type_options || Object.keys(documentTypeLabels);
    documentTypeFilter.innerHTML = '<option value="">Todos</option>' + documentOptions
      .map((item) => `<option value="${item}">${documentTypeLabels[item] || item}</option>`).join('');
  }

  async function loadRecords() {
    const query = new URLSearchParams({ company_id: companyId });
    [
      ['status', 'filter-status'],
      ['origin_type', 'filter-origin'],
      ['document_type', 'filter-document-type'],
      ['competence_date_from', 'filter-competence-from'],
      ['competence_date_to', 'filter-competence-to'],
      ['due_date_from', 'filter-due-from'],
      ['due_date_to', 'filter-due-to'],
    ].forEach(([key, id]) => { const value = byId(id).value; if (value) query.set(key, value); });
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

  function renderDocumentLinks(payload) {
    const related = payload.related_documents || [];
    if (!related.length) return '<p class="fa-muted">Nenhum documento vinculado.</p>';
    return `
      <ul>
        ${related.map((doc) => `
          <li>
            <strong>${escapeHtml(documentTypeLabels[doc.document_type] || doc.document_type || doc.file_name || 'Documento')}</strong>
            — ${escapeHtml(doc.file_name || '-')}
            ${doc.original_relative_path ? ` · <a href="/uploads/${doc.original_relative_path}" target="_blank" rel="noopener">Original</a>` : ''}
            ${doc.preview_relative_path ? ` · <a href="/uploads/${doc.preview_relative_path}" target="_blank" rel="noopener">Preview</a>` : ''}
            ${doc.optimized_relative_path ? ` · <a href="/uploads/${doc.optimized_relative_path}" target="_blank" rel="noopener">Otimizado</a>` : ''}
          </li>
        `).join('')}
      </ul>
    `;
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
    const previewLink = payload.preview_public_url ? `<p><a href="${payload.preview_public_url}" target="_blank" rel="noopener">Abrir preview</a></p>` : '';
    const optimizedLink = payload.optimized_public_url ? `<p><a href="${payload.optimized_public_url}" target="_blank" rel="noopener">Abrir otimizado</a></p>` : '';
    const publicUrl = payload.original_public_url || payload.public_url;
    const originalLink = publicUrl ? `<p><a href="${publicUrl}" target="_blank" rel="noopener">Abrir original</a></p>` : '';
    documentBody.innerHTML = `
      <div class="fa-doc-preview">
        <div>
          <h4>Resumo documental</h4>
          <pre>${escapeHtml(JSON.stringify({
            document_type: payload.document_type,
            document_family: payload.document_family,
            parser_status: payload.parser_status,
            parser_version: payload.parser_version,
            document_group_key: payload.document_group_key,
            confidence_score: payload.confidence_score,
            structured_payload_json: payload.structured_payload_json,
          }, null, 2))}</pre>
          <h4>Arquivos vinculados</h4>
          ${renderDocumentLinks(payload)}
        </div>
        <div>
          <h4>Texto extraído</h4>
          <pre>${escapeHtml(payload.extracted_text || '(sem texto extraído)')}</pre>
          ${originalLink}
          ${optimizedLink}
          ${previewLink}
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
      const files = Array.from(byId('fa-import-files')?.files || []);
      if (files.length) {
        const formData = new FormData();
        formData.append('origin_type', byId('fa-import-origin').value);
        formData.append('source_label', byId('fa-import-source-label').value || '');
        files.forEach((file) => formData.append('files', file));
        const response = await fetch(`/api/financial/automation/uploads?company_id=${companyId}`, {
          method: 'POST',
          body: formData,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || 'Falha no upload da Central.');
        if (payload.batch?.id) {
          const parsePayload = await api(`/api/financial/automation/batches/${payload.batch.id}/parse?company_id=${companyId}`, {
            method: 'POST',
          });
          payload.records = parsePayload.records || [];
        }
        importDialog.close();
        byId('fa-import-files').value = '';
        byId('fa-import-documents').value = '';
        byId('fa-import-records').value = '';
        await loadRecords();
        alert(`Upload concluído: ${payload.documents?.length || 0} documento(s) e ${payload.records?.length || 0} registro(s) estruturado(s) na Central.`);
        return;
      }
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
      if (byId('fa-import-files')) byId('fa-import-files').value = '';
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
      recordsBody.innerHTML = `<tr><td colspan="20" class="fa-empty">${error.message}</td></tr>`;
    }
  })();
})();
