(function () {
  const root = document.querySelector('.fa-page');
  if (!root) return;
  const companyId = Number(root.dataset.companyId || 0);
  const companyCode = String(root.dataset.companyCode || 'VS').trim().toUpperCase();
  const recordsBody = document.getElementById('fa-records-body');
  const importDialog = document.getElementById('fa-import-dialog');
  const documentDialog = document.getElementById('fa-document-dialog');
  const reviewDialog = document.getElementById('fa-review-dialog');
  const documentBody = document.getElementById('fa-document-body');
  const state = { options: null, records: [], activeReviewId: null, documentCache: {}, reviewQueueIds: [] };
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
  const pendingFlagLabels = {
    missing_document_number: 'Sem número do documento',
    missing_issuer: 'Sem emissor identificado',
    missing_total_amount: 'Sem valor total extraído',
    missing_issue_date: 'Sem data de emissão',
    manual_review_required: 'Revisão manual obrigatória',
    duplicate_detected: 'Duplicidade exata detectada',
    possible_duplicate_detected: 'Possível duplicidade',
  };
  const filterDefinitions = [
    { key: 'status', id: 'filter-status', label: 'Status', format: (value) => statusLabels[value] || value },
    { key: 'origin_type', id: 'filter-origin', label: 'Origem', format: (value) => originLabels[value] || value },
    { key: 'batch_id', id: 'filter-batch', label: 'Lote', format: (value) => batchOptionLabel(value) },
    { key: 'document_type', id: 'filter-document-type', label: 'Tipo documental', format: (value) => documentTypeLabels[value] || value },
    { key: 'competence_date_from', id: 'filter-competence-from', label: 'Competência de' },
    { key: 'competence_date_to', id: 'filter-competence-to', label: 'Competência até' },
    { key: 'due_date_from', id: 'filter-due-from', label: 'Vencimento de' },
    { key: 'due_date_to', id: 'filter-due-to', label: 'Vencimento até' },
  ];

  const byId = (id) => document.getElementById(id);
  const filtersForm = byId('fa-filters');
  const filterCountNode = byId('fa-filters-count');
  const activeFiltersNode = byId('fa-active-filters');
  const selectedIds = () => Array.from(document.querySelectorAll('.fa-record-select:checked')).map((el) => Number(el.value));
  const badge = (status) => `<span class="fa-badge fa-badge--${status}">${statusLabels[status] || status || '-'}</span>`;
  const reviewCarouselStatuses = new Set(['imported']);

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

  function readFilters() {
    return filterDefinitions.reduce((acc, { key, id }) => {
      const value = byId(id)?.value;
      if (value) acc[key] = value;
      return acc;
    }, {});
  }

  function updateFiltersUi() {
    const filters = readFilters();
    const entries = filterDefinitions
      .map((definition) => {
        const value = filters[definition.key];
        if (!value) return null;
        const text = definition.format ? definition.format(value) : value;
        return { label: definition.label, text };
      })
      .filter(Boolean);

    if (filterCountNode) filterCountNode.textContent = String(entries.length);
    if (!activeFiltersNode) return;

    if (!entries.length) {
      activeFiltersNode.innerHTML = '<span class="fa-filter-chip fa-filter-chip--muted">Sem filtros ativos</span>';
      return;
    }

    activeFiltersNode.innerHTML = entries
      .map((entry) => `<span class="fa-filter-chip"><strong>${escapeHtml(entry.label)}:</strong> ${escapeHtml(entry.text)}</span>`)
      .join('');
  }

  function domainLabel(record) {
    if (!record.domain_type || !record.domain_source_id) return '';
    return `${record.domain_type}:${record.domain_source_id}`;
  }

  function defaultDomainValue(record) {
    const current = domainLabel(record);
    if (current) return current;
    const defaultOption = (state.options?.domain_options || []).find((item) => item.is_default_suggestion);
    if (!defaultOption) return '';
    return `${defaultOption.domain_type}:${defaultOption.source_id}`;
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

  function normalizeSearchTerm(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function filterSelectOptions(selectId, searchValue) {
    const select = byId(selectId);
    if (!select) return;
    const search = normalizeSearchTerm(searchValue);
    Array.from(select.options || []).forEach((option, index) => {
      if (index === 0) {
        option.hidden = false;
        return;
      }
      const haystack = normalizeSearchTerm(option.textContent || option.label || '');
      option.hidden = Boolean(search) && !haystack.includes(search);
    });
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
    const flags = [...(record.review_flags_json || [])];
    const dedupe = record.metadata_json?.dedupe || {};
    if (dedupe.status === 'duplicate' && !flags.includes('duplicate_detected')) flags.unshift('duplicate_detected');
    if (dedupe.status === 'possible_duplicate' && !flags.includes('possible_duplicate_detected')) flags.unshift('possible_duplicate_detected');
    if (!flags.length) return '<span class="fa-muted">Sem pendências</span>';
    return flags.map((flag) => `<span class="fa-badge fa-badge--excluded">${escapeHtml(pendingFlagLabels[flag] || flag)}</span>`).join(' ');
  }

  function pendingHelpText(record) {
    const flags = new Set(record.review_flags_json || []);
    const dedupe = record.metadata_json?.dedupe || {};
    if (dedupe.status === 'duplicate') flags.add('duplicate_detected');
    if (dedupe.status === 'possible_duplicate') flags.add('possible_duplicate_detected');
    if (!flags.size) return 'Sem ação obrigatória pendente.';

    const messages = [];
    const missingCoreFields = ['missing_document_number', 'missing_issuer', 'missing_total_amount', 'missing_issue_date']
      .filter((flag) => flags.has(flag));
    if (missingCoreFields.length) {
      messages.push('Os dados documentais não foram extraídos por completo. Revise só o que for necessário para gerar com segurança.');
    }
    if (flags.has('manual_review_required')) {
      messages.push('Recibos e imagens exigem revisão humana antes da validação.');
    }
    if (flags.has('duplicate_detected')) {
      messages.push('Duplicidade exata detectada: o recomendado é excluir este registro para evitar geração duplicada.');
    } else if (flags.has('possible_duplicate_detected')) {
      messages.push('Possível duplicidade: confira o documento antes de validar ou gerar.');
    }
    return messages.join(' ');
  }

  function suggestionNote(record, field) {
    const suggestion = record.metadata_json?.auto_suggestions?.[field];
    if (!suggestion?.suggested_id) return '';
    const source = suggestion.source ? ` · ${suggestion.source}` : '';
    const score = suggestion.memory_score ? ` · score ${Number(suggestion.memory_score).toFixed(2)}` : '';
    return `<div class="fa-muted">Sugestão automática${source}${score}</div>`;
  }

  function dedupeLabel(record) {
    const dedupe = record.metadata_json?.dedupe || {};
    if (!dedupe.status || dedupe.status === 'unique') return '';
    const reason = dedupe.reason ? ` · ${dedupe.reason}` : '';
    const match = dedupe.matched_record_id ? ` · ref ${dedupe.matched_record_id}` : '';
    return `<div class="fa-muted">Dedupe: ${escapeHtml(dedupe.status)}${escapeHtml(reason)}${escapeHtml(match)}</div>`;
  }

  function originLabel(record) {
    const batchMeta = record.batch?.metadata_json || {};
    const documentMeta = record.document?.metadata_json || {};
    const sourceChannel = String(batchMeta.source_channel || documentMeta.source_channel || '').toLowerCase();
    if (sourceChannel === 'whatsapp') return 'WhatsApp';
    if (sourceChannel === 'email') return 'E-mail';
    if (sourceChannel === 'planilha' || sourceChannel === 'spreadsheet') return 'Planilha';
    return originLabels[record.batch?.origin_type] || 'Origem externa';
  }

  function digitsOnly(value) {
    return String(value || '').replace(/\D/g, '');
  }

  function padNumber(value, size = 4) {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric) || numeric <= 0) return ''.padStart(size, '0');
    return String(Math.trunc(numeric)).padStart(size, '0');
  }

  function compactDate(value) {
    if (!value) return '';
    const dateText = String(value).slice(0, 10);
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateText);
    if (!match) return '';
    return `${match[3]}${match[2]}${match[1].slice(-2)}`;
  }

  function sourceToken(record) {
    const batchMeta = record.batch?.metadata_json || {};
    const documentMeta = record.document?.metadata_json || {};
    const candidates = [
      batchMeta.source_contact,
      batchMeta.contact,
      batchMeta.sender,
      documentMeta.source_contact,
      documentMeta.contact,
      documentMeta.sender,
      batchMeta.source_external_reference,
      documentMeta.source_external_reference,
      record.batch?.source_label,
    ].filter(Boolean);
    for (const candidate of candidates) {
      const digits = digitsOnly(candidate);
      if (digits.length >= 8) return digits;
    }
    const sourceChannel = String(batchMeta.source_channel || documentMeta.source_channel || '').toLowerCase();
    if (sourceChannel === 'whatsapp') return 'WPP';
    if (sourceChannel === 'email') return 'EMAIL';
    if (sourceChannel === 'planilha' || sourceChannel === 'spreadsheet') return 'PLAN';
    const originType = String(record.batch?.origin_type || '').toLowerCase();
    if (originType === 'integration') return 'WPP';
    if (originType === 'accountability') return 'ACC';
    if (originType === 'manual_upload') return 'MAN';
    if (originType === 'csv' || originType === 'xlsx') return 'PLAN';
    if (originType === 'ofx') return 'OFX';
    return 'SRC';
  }

  function documentDisplayCode(record) {
    const documentId = record.document?.id || record.source_document_id || record.id;
    const receivedDate = compactDate(record.document?.created_at || record.created_at || record.batch?.created_at);
    return [companyCode, 'D', receivedDate || '000000', padNumber(documentId)].join('.');
  }

  function batchDisplayCode(batch) {
    if (!batch?.id) return '-';
    const receivedDate = compactDate(batch.created_at);
    return [companyCode, 'L', receivedDate || '000000', padNumber(batch.id)].join('.');
  }

  function batchOptionLabel(batchId) {
    const batch = (state.options?.batch_options || []).find((item) => String(item.id) === String(batchId));
    if (!batch) return `Lote #${batchId}`;
    return batchDisplayCode(batch);
  }

  function batchLabel(record) {
    const batch = record.batch || {};
    if (!batch.id) return '<span class="fa-muted">Sem lote</span>';
    return `<strong>${escapeHtml(batchDisplayCode(batch))}</strong>`;
  }

  function sourceDisplayCode(record) {
    const sequence = padNumber(record.batch?.id || record.document?.batch_id || record.id);
    return [companyCode, 'R', sourceToken(record), sequence].join('.');
  }

  function isCarouselRecord(record) {
    return reviewCarouselStatuses.has(String(record?.status || '').toLowerCase());
  }

  function refreshReviewQueue() {
    state.reviewQueueIds = state.records.filter(isCarouselRecord).map((record) => record.id);
  }

  function reviewQueueIndex(recordId) {
    return state.reviewQueueIds.findIndex((id) => id === Number(recordId));
  }

  function activeReviewRecord() {
    return state.records.find((item) => item.id === Number(state.activeReviewId));
  }

  function documentUrlCandidates(payload = {}) {
    return [
      payload.preview_public_url,
      payload.optimized_public_url,
      payload.original_public_url,
      payload.public_url,
    ].filter(Boolean);
  }

  function previewKind(payload = {}) {
    const documentType = String(payload.document_type || '').toLowerCase();
    const mimeType = String(payload.mime_type || '').toLowerCase();
    const sourceUrl = documentUrlCandidates(payload)[0] || '';
    const lowerUrl = String(sourceUrl).toLowerCase();
    if (mimeType.startsWith('image/') || documentType === 'receipt_image' || /\.(png|jpg|jpeg|webp|gif|bmp|svg)(\?|$)/.test(lowerUrl)) return 'image';
    if (mimeType.includes('pdf') || /(\.pdf)(\?|$)/.test(lowerUrl) || ['receipt_pdf', 'danfe_pdf', 'dacte_pdf'].includes(documentType)) return 'pdf';
    return 'external';
  }

  function formatCurrency(value) {
    return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function confidenceBadge(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '<span class="fa-muted">-</span>';
    const pct = Math.round(numeric * 100);
    const tone = pct >= 85 ? 'high' : pct >= 60 ? 'medium' : 'low';
    return `<span class="fa-confidence fa-confidence--${tone}">${pct}%</span>`;
  }

  function counterpartyDisplay(record) {
    const matched = (state.options?.counterparties || []).find((item) => String(item.id) === String(record.counterparty_id));
    if (matched) return optionLabel(matched);
    return record.recipient_name || record.issuer_name || 'Não definido';
  }

  function deleteBlockersTitle(record) {
    const blockers = Array.isArray(record?.delete_blockers) ? record.delete_blockers : [];
    if (!blockers.length) return '';
    return `Exclusão bloqueada: ${blockers.map((item) => item.label || item.type || 'vínculo ativo').join(', ')}`;
  }

  function render() {
    refreshReviewQueue();
    if (!state.records.length) {
      recordsBody.innerHTML = '<tr><td colspan="12" class="fa-empty">Nenhum registro encontrado.</td></tr>';
      return;
    }
    recordsBody.innerHTML = state.records.map((record) => `
      <tr data-record-id="${record.id}">
        <td><input type="checkbox" class="fa-record-select" value="${record.id}"></td>
        <td>${badge(record.status)}</td>
        <td class="fa-cell-batch">${batchLabel(record)}</td>
        <td class="fa-cell-origin">
          <strong>${escapeHtml(sourceDisplayCode(record))}</strong>
          <span class="fa-cell-document__meta">${escapeHtml(originLabel(record))}</span>
          ${dedupeLabel(record)}
        </td>
        <td><span class="fa-type-pill fa-type-pill--${record.entry_direction === 'receivable' ? 'receivable' : 'payable'}">${record.entry_direction === 'receivable' ? 'Receber' : 'Pagar'}</span></td>
        <td><span class="fa-state-pill fa-state-pill--${record.settlement_state === 'settled' ? 'settled' : 'open'}">${record.settlement_state === 'settled' ? 'Já pago/recebido' : 'Em aberto'}</span></td>
        <td class="fa-cell-counterparty">${escapeHtml(counterpartyDisplay(record))}</td>
        <td class="fa-cell-amount">${formatCurrency(record.amount)}</td>
        <td class="fa-cell-due">${record.due_date ? new Date(`${record.due_date}T00:00:00`).toLocaleDateString('pt-BR') : '<span class="fa-muted">Sem vencimento</span>'}</td>
        <td>${confidenceBadge(record.confidence_score)}</td>
        <td class="fa-cell-pendencies">${pendingLabel(record)}</td>
        <td>
          <div class="fa-inline fa-inline--table">
            <button type="button" class="fa-btn fa-btn--primary" data-action="review">Revisar</button>
            <button type="button" class="fa-btn fa-btn--secondary" data-action="origin">Documento</button>
            <button type="button" class="fa-btn fa-btn--danger" data-action="exclude" ${record.can_delete ? '' : 'disabled'} title="${escapeHtml(deleteBlockersTitle(record))}">Excluir</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  function renderReviewSelect(targetId, items, selectedValue, placeholder, valueGetter = (item) => item.id, labelGetter = optionLabel) {
    const target = byId(targetId);
    if (!target) return;
    target.innerHTML = [`<option value="">${placeholder}</option>`]
      .concat((items || []).map((item) => {
        const value = valueGetter(item);
        const selected = String(value) === String(selectedValue ?? '') ? 'selected' : '';
        return `<option value="${value}" ${selected}>${labelGetter(item)}</option>`;
      }))
      .join('');
    const searchInput = document.querySelector(`[data-select-filter-target="${targetId}"]`);
    if (searchInput) {
      searchInput.value = '';
      filterSelectOptions(targetId, '');
    }
  }

  function setText(targetId, html) {
    const node = byId(targetId);
    if (node) node.innerHTML = html;
  }

  async function fetchDocumentPayload(record) {
    const documentId = record?.document?.id;
    if (!documentId) return null;
    if (!state.documentCache[documentId]) {
      state.documentCache[documentId] = await api(`/api/financial/automation/documents/${documentId}?company_id=${companyId}`);
    }
    return state.documentCache[documentId];
  }

  function renderReviewQueueState(record) {
    const queueIndex = reviewQueueIndex(record?.id);
    const queueStatus = byId('fa-review-queue-status');
    const prevButton = byId('fa-review-prev');
    const nextButton = byId('fa-review-next');
    const completeButton = byId('fa-review-complete');
    if (!queueStatus || !prevButton || !nextButton || !completeButton) return;

    const total = state.reviewQueueIds.length;
    const inQueue = queueIndex >= 0;
    queueStatus.textContent = inQueue
      ? `${queueIndex + 1} de ${total} pendente(s) na esteira de revisão.`
      : 'Registro fora do carrossel. Para revisar novamente, abra-o diretamente na grade.';
    prevButton.disabled = !inQueue || queueIndex === 0;
    nextButton.disabled = !inQueue || queueIndex === total - 1;
    completeButton.disabled = !record || ['validated', 'generated', 'excluded'].includes(record.status);
    completeButton.textContent = record?.status === 'validated' ? 'Revisão concluída' : 'Revisão completa';
  }

  function syncSettlementDateField(settlementState, settlementDate = '') {
    const input = byId('fa-review-settlement-date');
    const help = byId('fa-review-settlement-date-help');
    if (!input) return;
    const isSettled = settlementState === 'settled';
    input.disabled = !isSettled;
    if (!isSettled) {
      input.value = '';
      if (help) help.textContent = 'Disponível apenas quando o documento já estiver pago/recebido.';
      return;
    }
    input.value = settlementDate || input.value || '';
    if (help) help.textContent = 'Será usada como data da baixa na geração financeira.';
  }

  function reviewPreviewFallback(message, links = '') {
    return `
      <div class="fa-review-preview__fallback">
        <p class="fa-muted">${escapeHtml(message)}</p>
        ${links}
      </div>
    `;
  }

  function renderInlinePreview(payload) {
    if (!payload) {
      return reviewPreviewFallback('Este registro não possui documento estruturado para visualização inline.');
    }
    const urls = {
      preview: payload.preview_public_url,
      optimized: payload.optimized_public_url,
      original: payload.original_public_url || payload.public_url,
    };
    const links = `
      <div class="fa-review-preview__meta">
        ${urls.preview ? `<a href="${urls.preview}" target="_blank" rel="noopener">Preview</a>` : ''}
        ${urls.optimized ? `<a href="${urls.optimized}" target="_blank" rel="noopener">Otimizado</a>` : ''}
        ${urls.original ? `<a href="${urls.original}" target="_blank" rel="noopener">Original</a>` : ''}
      </div>
    `;
    const primaryUrl = urls.preview || urls.optimized || urls.original;
    if (!primaryUrl) {
      return reviewPreviewFallback('O documento foi recebido, mas ainda não há arquivo público disponível para visualização.', links);
    }
    const kind = previewKind(payload);
    if (kind === 'image') {
      return `
        <div class="fa-review-preview__viewport">
          <img src="${primaryUrl}" alt="Documento da revisão">
        </div>
        ${links}
      `;
    }
    if (kind === 'pdf') {
      return `
        <div class="fa-review-preview__viewport">
          <iframe src="${primaryUrl}" title="Preview do documento"></iframe>
        </div>
        ${links}
      `;
    }
    return reviewPreviewFallback('Este formato não possui preview inline ideal. Abra o documento em pop-up quando precisar conferir o original.', links);
  }

  async function updateReviewPreview(record) {
    const previewBody = byId('fa-review-preview-body');
    const previewOpenButton = byId('fa-review-preview-open');
    if (!previewBody || !previewOpenButton) return;
    previewBody.innerHTML = '<p class="fa-muted">Carregando documento...</p>';
    previewOpenButton.disabled = true;

    const payload = await fetchDocumentPayload(record).catch(() => null);
    previewBody.innerHTML = renderInlinePreview(payload);
    previewOpenButton.disabled = !documentUrlCandidates(payload || {}).length;
  }

  async function populateReviewForm(record) {
    state.activeReviewId = record.id;
    byId('fa-review-record-id').value = String(record.id);
    byId('fa-review-title').textContent = `Revisar registro #${record.id}`;
    byId('fa-review-subtitle').textContent = record.description || 'Ajuste os dados antes de validar ou gerar no Financeiro.';
    setText('fa-review-status', badge(record.status));
    setText('fa-review-document', `<strong>${escapeHtml(documentDisplayCode(record))}</strong><div class="fa-muted">${escapeHtml(documentLabel(record))}</div>`);
    setText('fa-review-origin', `<strong>${escapeHtml(sourceDisplayCode(record))}</strong><div class="fa-muted">${escapeHtml(originLabel(record))}</div>`);
    setText('fa-review-parties', escapeHtml(partiesLabel(record)));
    setText('fa-review-key', keyLabel(record));
    setText('fa-review-pendencies', pendingLabel(record));
    setText('fa-review-pendencies-help', escapeHtml(record.validation_notes || pendingHelpText(record)));

    renderReviewSelect('fa-review-entry-direction', [{ id: 'payable', name: 'Pagar' }, { id: 'receivable', name: 'Receber' }], record.entry_direction, 'Tipo', (item) => item.id, optionLabel);
    renderReviewSelect('fa-review-settlement-state', [{ id: 'settled', name: 'Já pago/recebido' }, { id: 'open', name: 'Em aberto' }], record.settlement_state, 'Situação', (item) => item.id, optionLabel);
    renderReviewSelect('fa-review-counterparty', state.options?.counterparties, record.counterparty_id, 'Favorecido', (item) => item.id, optionLabel);
    renderReviewSelect('fa-review-bank-account', state.options?.bank_accounts, record.bank_account_id, 'Conta bancária', (item) => item.id, optionLabel);
    renderReviewSelect('fa-review-chart-account', state.options?.chart_accounts, record.chart_account_id, 'Conta contábil', (item) => item.id, optionLabel);
    renderReviewSelect('fa-review-cost-center', state.options?.cost_centers, record.cost_center_id, 'Centro', (item) => item.id, optionLabel);
    const domainOptions = state.options?.domain_options || [];
    const domainPlaceholder = domainOptions.length ? 'Projeto/Processo habilitado no Financeiro' : 'Nenhum Projeto/Processo habilitado no Financeiro';
    renderReviewSelect('fa-review-domain-link', domainOptions, defaultDomainValue(record), domainPlaceholder, (item) => `${item.domain_type}:${item.source_id}`, (item) => item.label);

    byId('fa-review-description').value = record.description || '';
    byId('fa-review-amount').value = record.amount || 0;
    byId('fa-review-competence-date').value = record.competence_date || '';
    byId('fa-review-due-date').value = record.due_date || '';
    syncSettlementDateField(record.settlement_state, record.settlement_date || '');

    byId('fa-review-counterparty-note').innerHTML = suggestionNote(record, 'counterparty').replace(/^<div class="fa-muted">|<\/div>$/g, '');
    byId('fa-review-chart-account-note').innerHTML = suggestionNote(record, 'chart_account').replace(/^<div class="fa-muted">|<\/div>$/g, '');
    byId('fa-review-cost-center-note').innerHTML = suggestionNote(record, 'cost_center').replace(/^<div class="fa-muted">|<\/div>$/g, '');
    byId('fa-review-save').textContent = record.status === 'validated' ? 'Salvar ajustes' : 'Salvar revisão';
    renderReviewQueueState(record);
    await updateReviewPreview(record);
  }

  function reviewPayload() {
    const payload = {
      entry_direction: byId('fa-review-entry-direction').value || null,
      settlement_state: byId('fa-review-settlement-state').value || null,
      description: byId('fa-review-description').value || null,
      counterparty_id: byId('fa-review-counterparty').value ? Number(byId('fa-review-counterparty').value) : null,
      bank_account_id: byId('fa-review-bank-account').value ? Number(byId('fa-review-bank-account').value) : null,
      chart_account_id: byId('fa-review-chart-account').value ? Number(byId('fa-review-chart-account').value) : null,
      cost_center_id: byId('fa-review-cost-center').value ? Number(byId('fa-review-cost-center').value) : null,
      amount: byId('fa-review-amount').value ? Number(byId('fa-review-amount').value) : 0,
      competence_date: byId('fa-review-competence-date').value || null,
      due_date: byId('fa-review-due-date').value || null,
      settlement_date: byId('fa-review-settlement-date').disabled ? null : (byId('fa-review-settlement-date').value || null),
    };
    const domainValue = byId('fa-review-domain-link').value;
    if (domainValue) {
      const [domain_type, source_id] = domainValue.split(':');
      payload.domain_type = domain_type;
      payload.domain_source_id = Number(source_id);
    } else {
      payload.domain_type = null;
      payload.domain_source_id = null;
    }
    return payload;
  }

  async function openReview(recordId) {
    const record = state.records.find((item) => item.id === Number(recordId));
    if (!record) return;
    await populateReviewForm(record);
    reviewDialog?.showModal();
  }

  async function openAdjacentReview(offset) {
    const currentRecord = activeReviewRecord();
    if (!currentRecord) return;
    const currentIndex = reviewQueueIndex(currentRecord.id);
    if (currentIndex < 0) return;
    const nextId = state.reviewQueueIds[currentIndex + offset];
    if (!nextId) return;
    await openReview(nextId);
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
    const batchFilter = byId('filter-batch');
    const batchOptions = state.options?.batch_options || [];
    batchFilter.innerHTML = '<option value="">Todos</option>' + batchOptions
      .map((item) => `<option value="${item.id}">${escapeHtml(batchOptionLabel(item.id))}</option>`).join('');
  }

  async function loadRecords() {
    const query = new URLSearchParams({ company_id: companyId });
    Object.entries(readFilters()).forEach(([key, value]) => query.set(key, value));
    state.records = await api(`/api/financial/automation/records?${query.toString()}`);
    render();
  }

  async function applyFilters() {
    updateFiltersUi();
    await loadRecords();
    window.closeAllSidebars?.();
  }

  async function clearFilters() {
    filterDefinitions.forEach(({ id }) => {
      const element = byId(id);
      if (element) element.value = '';
    });
    updateFiltersUi();
    await loadRecords();
  }

  async function saveRow(row) {
    const { id, payload } = rowPayload(row);
    await api(`/api/financial/automation/records/${id}?company_id=${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    await loadRecords();
  }

  async function saveReview(closeAfterSave = true) {
    const recordId = Number(byId('fa-review-record-id').value || 0);
    if (!recordId) return;
    await api(`/api/financial/automation/records/${recordId}?company_id=${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(reviewPayload()),
    });
    await loadRecords();
    if (closeAfterSave) {
      reviewDialog?.close();
      return;
    }
    const refreshed = state.records.find((item) => item.id === recordId);
    if (refreshed) {
      await populateReviewForm(refreshed);
    }
  }

  async function completeReview() {
    const record = activeReviewRecord();
    if (!record) return;
    const currentIndex = reviewQueueIndex(record.id);
    const nextId = currentIndex >= 0 ? state.reviewQueueIds[currentIndex + 1] : null;

    await saveReview(false);
    await api(`/api/financial/automation/records/bulk-status?company_id=${companyId}`, {
      method: 'POST',
      body: JSON.stringify({ record_ids: [record.id], status: 'validated' }),
    });
    await loadRecords();

    if (nextId) {
      const nextRecord = state.records.find((item) => item.id === nextId);
      if (nextRecord) {
        await populateReviewForm(nextRecord);
        return;
      }
    }

    const fallback = state.records.find((item) => state.reviewQueueIds.includes(item.id));
    if (fallback) {
      await populateReviewForm(fallback);
      return;
    }
    reviewDialog?.close();
    alert('Revisão concluída. Não há mais registros pendentes no carrossel atual.');
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
    const payload = await fetchDocumentPayload(record);
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

  async function openReviewDocumentExternal() {
    const record = activeReviewRecord();
    if (!record) return;
    const payload = await fetchDocumentPayload(record).catch(() => null);
    const url = documentUrlCandidates(payload || {})[0];
    if (url) {
      window.open(url, '_blank', 'noopener');
      return;
    }
    await showOrigin({ dataset: { recordId: String(record.id) } });
  }

  async function bulkStatus(status) {
    const ids = selectedIds();
    if (!ids.length) return alert('Selecione ao menos um registro.');
    try {
      const payload = await api(`/api/financial/automation/records/bulk-status?company_id=${companyId}`, {
        method: 'POST',
        body: JSON.stringify({ record_ids: ids, status }),
      });
      await loadRecords();
      const label = statusLabels[status] || status;
      alert(`${payload.count || 0} registro(s) atualizado(s) para ${label}.`);
    } catch (error) {
      await loadRecords();
      alert(error.message);
    }
  }

  async function excludeRecord(recordId) {
    const id = Number(recordId || 0);
    if (!id) return;
    const record = state.records.find((item) => item.id === id);
    if (record && record.can_delete === false) {
      alert(deleteBlockersTitle(record));
      return;
    }
    const details = record
      ? `\n\nLote: ${batchOptionLabel(record.batch_id)}\nDocumento: ${documentDisplayCode(record)} · ${documentLabel(record)}`
      : '';
    const confirmed = window.confirm(`Deseja excluir este registro da Central de Automação?${details}`);
    if (!confirmed) return;
    await api(`/api/financial/automation/records/${id}?company_id=${companyId}`, {
      method: 'DELETE',
    });
    await loadRecords();
  }

  async function generateSelected() {
    const ids = selectedIds();
    try {
      const payload = await api(`/api/financial/automation/generate?company_id=${companyId}`, {
        method: 'POST',
        body: JSON.stringify({ record_ids: ids.length ? ids : null }),
      });
      await loadRecords();
      const count = Number(payload?.count || 0);
      if (count <= 0) {
        alert(ids.length
          ? 'Nenhum dos registros selecionados estava apto para gerar como validado.'
          : 'Nenhum registro validado encontrado para geração.');
        return;
      }
      alert(`${count} registro(s) gerado(s) com sucesso.`);
    } catch (error) {
      alert(error.message);
    }
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
  byId('fa-apply-filters')?.addEventListener('click', applyFilters);
  byId('fa-clear-filters')?.addEventListener('click', clearFilters);
  byId('fa-review-save')?.addEventListener('click', () => saveReview(true));
  byId('fa-review-prev')?.addEventListener('click', () => openAdjacentReview(-1));
  byId('fa-review-next')?.addEventListener('click', () => openAdjacentReview(1));
  byId('fa-review-complete')?.addEventListener('click', completeReview);
  byId('fa-review-origin-action')?.addEventListener('click', openReviewDocumentExternal);
  byId('fa-review-preview-open')?.addEventListener('click', openReviewDocumentExternal);
  byId('fa-review-settlement-state')?.addEventListener('change', (event) => syncSettlementDateField(event.target.value));
  document.querySelectorAll('[data-select-filter-target]').forEach((input) => {
    input.addEventListener('input', (event) => {
      filterSelectOptions(event.target.dataset.selectFilterTarget, event.target.value || '');
    });
  });
  byId('fa-select-all').addEventListener('change', (event) => {
    document.querySelectorAll('.fa-record-select').forEach((el) => { el.checked = event.target.checked; });
  });
  filtersForm?.addEventListener('change', updateFiltersUi);
  recordsBody.addEventListener('click', async (event) => {
    const action = event.target.dataset.action;
    const row = event.target.closest('tr');
    if (!action || !row) return;
    if (action === 'review') await openReview(row.dataset.recordId);
    if (action === 'save') await saveRow(row);
    if (action === 'origin') await showOrigin(row);
    if (action === 'exclude') await excludeRecord(row.dataset.recordId);
  });

  (async function init() {
    try {
      await loadOptions();
      updateFiltersUi();
      await loadRecords();
    } catch (error) {
      recordsBody.innerHTML = `<tr><td colspan="12" class="fa-empty">${error.message}</td></tr>`;
    }
  })();
})();
