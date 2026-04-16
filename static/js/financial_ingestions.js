(function () {
  const page = document.querySelector('.ing-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const listEl = document.getElementById('ing-list');
  const searchEl = document.getElementById('ing-search');
  const originFilterEl = document.getElementById('ing-origin-filter');
  const completionFilterEl = document.getElementById('ing-completion-filter');
  const reviewFilterEl = document.getElementById('ing-review-filter');
  const detailEl = document.getElementById('ing-detail');
  const emptyDetailEl = document.getElementById('ing-empty-detail');

  let items = [];
  let selected = null;

  const title = document.getElementById('ing-title');
  const subtitle = document.getElementById('ing-subtitle');
  const origin = document.getElementById('ing-origin');
  const completion = document.getElementById('ing-completion');
  const review = document.getElementById('ing-review');
  const confidence = document.getElementById('ing-confidence');
  const reference = document.getElementById('ing-reference');
  const system = document.getElementById('ing-system');
  const file = document.getElementById('ing-file');
  const channel = document.getElementById('ing-channel');
  const scheduleLink = document.getElementById('ing-schedule-link');
  const entryLink = document.getElementById('ing-entry-link');
  const normalizedBox = document.getElementById('ing-normalized');
  const rawBox = document.getElementById('ing-raw');
  const extractedBox = document.getElementById('ing-extracted');
  const auditTrailBox = document.getElementById('ing-audit-trail');
  const reviewNotes = document.getElementById('ing-review-notes');
  const focusId = Number(new URLSearchParams(window.location.search).get('focus_id') || 0);
  const guided = {
    targetType: document.getElementById('guided-target-type'),
    description: document.getElementById('guided-description'),
    entryType: document.getElementById('guided-entry-type'),
    movementNature: document.getElementById('guided-movement-nature'),
    amount: document.getElementById('guided-amount'),
    competenceDate: document.getElementById('guided-competence-date'),
    occurredOn: document.getElementById('guided-occurred-on'),
    dueDate: document.getElementById('guided-due-date'),
    counterparty: document.getElementById('guided-counterparty'),
    bankAccount: document.getElementById('guided-bank-account'),
    chartAccount: document.getElementById('guided-chart-account'),
    costCenter: document.getElementById('guided-cost-center'),
    domain: document.getElementById('guided-domain'),
    notes: document.getElementById('guided-notes'),
    saveDraft: document.getElementById('ing-save-draft'),
    saveConvert: document.getElementById('ing-save-convert'),
    feedback: document.getElementById('guided-feedback'),
  };

  const conversionOptions = {
    loaded: false,
    counterparties: [],
    bankAccounts: [],
    chartAccounts: [],
    costCenters: [],
    enabledDomains: [],
  };

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Falha na operação financeira.');
    return result;
  }

  function pretty(value) {
    try {
      return JSON.stringify(value || {}, null, 2);
    } catch {
      return '{}';
    }
  }

  function filteredItems() {
    const term = String(searchEl.value || '').trim().toLowerCase();
    return items.filter((item) => {
      const haystack = `${item.origin_type || ''} ${item.origin_reference || ''} ${item.external_system || ''} ${item.source_file_name || ''}`.toLowerCase();
      const byTerm = !term || haystack.includes(term);
      const byOrigin = !originFilterEl.value || item.origin_type === originFilterEl.value;
      const byCompletion = !completionFilterEl.value || item.completion_status === completionFilterEl.value;
      const byReview = !reviewFilterEl.value || item.review_status === reviewFilterEl.value;
      return byTerm && byOrigin && byCompletion && byReview;
    });
  }

  function renderList() {
    const visible = filteredItems();
    listEl.innerHTML = visible.length ? visible.map((item) => `
      <article class="ing-item ${selected && selected.id === item.id ? 'active' : ''}" data-id="${item.id}">
        <strong>${item.origin_reference || item.source_file_name || ('Registro #' + item.id)}</strong>
        <small>${item.origin_type || '-'} · ${item.external_system || 'sem sistema externo'}</small>
        <div class="meta-row">
          <span class="badge-lite">${item.completion_status || '-'}</span>
          <span class="badge-lite">${item.review_status || '-'}</span>
        </div>
      </article>
    `).join('') : '<div class="empty-state">Nenhuma entrada encontrada.</div>';
  }

  function setLink(container, href, text) {
    if (!href || !text) {
      container.textContent = '-';
      return;
    }
    container.innerHTML = `<a href="${href}">${text}</a>`;
  }

  function setGuidedFeedback(message, isError = false) {
    if (!guided.feedback) return;
    if (!message) {
      guided.feedback.classList.add('hidden');
      guided.feedback.classList.remove('is-error');
      guided.feedback.textContent = '';
      return;
    }
    guided.feedback.classList.remove('hidden');
    guided.feedback.classList.toggle('is-error', Boolean(isError));
    guided.feedback.textContent = message;
  }

  function buildOptionLabel(item) {
    if (!item) return '-';
    return item.display_label || item.label || [item.code, item.name || item.title].filter(Boolean).join(' · ') || String(item.id || '-');
  }

  function renderSelectOptions(select, items, selectedValue) {
    if (!select) return;
    const currentValue = selectedValue != null ? String(selectedValue) : '';
    select.innerHTML = `<option value="">Selecionar</option>${(items || []).map((item) => {
      const value = item.value != null ? item.value : item.id;
      return `<option value="${value}">${buildOptionLabel(item)}</option>`;
    }).join('')}`;
    select.value = currentValue;
  }

  async function ensureConversionOptions() {
    if (conversionOptions.loaded) return;
    const options = await fetchJson(`/api/financial/schedules/options?company_id=${companyId}`);
    conversionOptions.counterparties = options.counterparties || [];
    conversionOptions.bankAccounts = options.bank_accounts || [];
    conversionOptions.chartAccounts = options.chart_accounts || [];
    conversionOptions.costCenters = options.cost_centers || [];
    conversionOptions.enabledDomains = (options.enabled_domains || []).map((item) => ({
      ...item,
      value: `${item.domain_type}:${item.source_id}`,
      label: item.display_label || item.domain_label || item.name || `${item.domain_type}:${item.source_id}`,
    }));
    conversionOptions.loaded = true;
  }

  function parseDomainValue(rawValue) {
    const raw = String(rawValue || '');
    if (!raw.includes(':')) return { domainType: null, domainSourceId: null };
    const [domainType, sourceId] = raw.split(':');
    return { domainType, domainSourceId: Number(sourceId || 0) || null };
  }

  function fillGuidedForm(item) {
    const normalized = item.normalized_payload_json || {};
    const metadata = normalized.metadata_json || {};
    const domainType = metadata.linked_domain_type || item.metadata_json?.linked_domain_type || '';
    const domainSourceId = metadata.linked_domain_source_id || item.metadata_json?.linked_domain_source_id || '';
    const domainValue = domainType && domainSourceId ? `${domainType}:${domainSourceId}` : '';

    guided.description.value = normalized.description || '';
    guided.entryType.value = normalized.entry_type || 'payable';
    guided.movementNature.value = normalized.movement_nature || (guided.entryType.value === 'receivable' ? 'credit' : 'debit');
    guided.amount.value = normalized.amount != null ? normalized.amount : '';
    guided.competenceDate.value = normalized.competence_date || '';
    guided.occurredOn.value = normalized.occurred_on || normalized.competence_date || '';
    guided.dueDate.value = normalized.due_date || '';
    guided.counterparty.value = normalized.counterparty_id != null ? String(normalized.counterparty_id) : '';
    guided.bankAccount.value = normalized.bank_account_id != null ? String(normalized.bank_account_id) : '';
    guided.chartAccount.value = normalized.chart_account_id != null ? String(normalized.chart_account_id) : '';
    guided.costCenter.value = normalized.cost_center_id != null ? String(normalized.cost_center_id) : '';
    guided.domain.value = domainValue;
    guided.notes.value = normalized.notes || item.review_notes || '';
  }

  async function prepareGuidedForm(item) {
    await ensureConversionOptions();
    renderSelectOptions(guided.counterparty, conversionOptions.counterparties, item.normalized_payload_json?.counterparty_id);
    renderSelectOptions(guided.bankAccount, conversionOptions.bankAccounts, item.normalized_payload_json?.bank_account_id);
    renderSelectOptions(guided.chartAccount, conversionOptions.chartAccounts, item.normalized_payload_json?.chart_account_id);
    renderSelectOptions(guided.costCenter, conversionOptions.costCenters, item.normalized_payload_json?.cost_center_id);
    renderSelectOptions(guided.domain, conversionOptions.enabledDomains, null);
    fillGuidedForm(item);
    setGuidedFeedback('');
  }

  function buildNormalizedPayloadFromForm() {
    const current = selected?.normalized_payload_json || {};
    const { domainType, domainSourceId } = parseDomainValue(guided.domain.value);
    return {
      ...current,
      description: String(guided.description.value || '').trim(),
      entry_type: guided.entryType.value || 'payable',
      movement_nature: guided.movementNature.value || 'debit',
      amount: Number(guided.amount.value || 0),
      competence_date: guided.competenceDate.value || null,
      occurred_on: guided.occurredOn.value || guided.competenceDate.value || null,
      due_date: guided.dueDate.value || null,
      counterparty_id: Number(guided.counterparty.value || 0) || null,
      bank_account_id: Number(guided.bankAccount.value || 0) || null,
      chart_account_id: Number(guided.chartAccount.value || 0) || null,
      cost_center_id: Number(guided.costCenter.value || 0) || null,
      notes: String(guided.notes.value || '').trim() || null,
      metadata_json: {
        ...(current.metadata_json || {}),
        linked_domain_type: domainType,
        linked_domain_source_id: domainSourceId,
      },
    };
  }

  async function persistGuidedChanges() {
    if (!selected) throw new Error('Selecione uma entrada para revisar.');
    const normalizedPayload = buildNormalizedPayloadFromForm();
    if (!normalizedPayload.description || !(normalizedPayload.amount > 0)) {
      throw new Error('Informe ao menos descrição e valor válidos para concluir a revisão.');
    }
    const updated = await fetchJson(`/api/financial/ingestions/${selected.id}?company_id=${companyId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        normalized_payload_json: normalizedPayload,
        review_notes: guided.notes.value || reviewNotes.value || null,
        completion_status: 'review_required',
      }),
    });
    reviewNotes.value = updated.review_notes || guided.notes.value || '';
    renderDetail(updated);
    return updated;
  }

  async function renderDetail(item) {
    selected = item;
    emptyDetailEl.classList.add('hidden');
    detailEl.classList.remove('hidden');
    title.textContent = item.origin_reference || item.source_file_name || `Registro #${item.id}`;
    subtitle.textContent = `Registro ${item.id} · atualizado em ${item.updated_at || item.created_at || '-'}`;
    origin.textContent = item.origin_type || '-';
    completion.textContent = item.completion_status || '-';
    review.textContent = item.review_status || '-';
    confidence.textContent = item.confidence_score != null ? `${Number(item.confidence_score).toFixed(2)} (${item.confidence_level || 'sem nível'})` : (item.confidence_level || 'não informado');
    reference.textContent = item.origin_reference || '-';
    system.textContent = item.external_system || '-';
    file.textContent = item.source_file_name || '-';
    channel.textContent = item.source_channel || '-';
    setLink(scheduleLink, item.related_schedule_id ? `/financial/schedules/${item.related_schedule_id}` : '', item.related_schedule_id ? `Agendamento #${item.related_schedule_id}` : '');
    setLink(entryLink, item.related_entry_id ? `/financial/entries/${item.related_entry_id}` : '', item.related_entry_id ? `Lançamento #${item.related_entry_id}` : '');
    normalizedBox.textContent = pretty(item.normalized_payload_json);
    rawBox.textContent = pretty(item.raw_payload_json);
    extractedBox.textContent = item.extracted_text || pretty(item.llm_response_json);
    auditTrailBox.textContent = pretty(item.metadata_json?.guided_audit_trail || []);
    reviewNotes.value = item.review_notes || '';
    await prepareGuidedForm(item);
    renderList();
  }

  async function loadItems() {
    const params = new URLSearchParams({ company_id: String(companyId) });
    if (originFilterEl.value) params.set('origin_type', originFilterEl.value);
    if (completionFilterEl.value) params.set('completion_status', completionFilterEl.value);
    if (reviewFilterEl.value) params.set('review_status', reviewFilterEl.value);
    items = await fetchJson(`/api/financial/ingestions?${params.toString()}`);
    renderList();
    if (focusId) {
      const focused = items.find((item) => item.id === focusId);
      if (focused) {
        await renderDetail(focused);
        return;
      }
    }
    if (selected) {
      const current = items.find((item) => item.id === selected.id);
      if (current) await renderDetail(current);
    }
  }

  window.reviewIngestion = async (status) => {
    if (!selected) return;
    try {
      const result = await fetchJson(`/api/financial/ingestions/${selected.id}/review?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_status: status, review_notes: reviewNotes.value || null, completion_status: status === 'rejected' ? 'rejected' : undefined }),
      });
      await renderDetail(result);
      await loadItems();
      alert('Revisão registrada com sucesso.');
    } catch (error) {
      alert(error.message);
    }
  };

  window.convertIngestion = async (targetType, options = {}) => {
    if (!selected) return;
    try {
      if (!options.skipPersist) {
        await persistGuidedChanges();
      }
      const result = await fetchJson(`/api/financial/ingestions/${selected.id}/convert?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_type: targetType }),
      });
      if (result.schedule?.id) {
        window.location.href = `/financial/schedules/${result.schedule.id}`;
        return;
      }
      if (result.entry?.id) {
        window.location.href = `/financial/entries/${result.entry.id}`;
        return;
      }
      await loadItems();
    } catch (error) {
      alert(error.message);
    }
  };

  listEl.addEventListener('click', async (event) => {
    const card = event.target.closest('.ing-item[data-id]');
    if (!card) return;
    const id = Number(card.dataset.id || 0);
    if (!id) return;
    try {
      const item = await fetchJson(`/api/financial/ingestions/${id}?company_id=${companyId}`);
      await renderDetail(item);
    } catch (error) {
      alert(error.message);
    }
  });

  guided.saveDraft?.addEventListener('click', async () => {
    try {
      await persistGuidedChanges();
      setGuidedFeedback('Revisão salva com sucesso.');
      await loadItems();
    } catch (error) {
      setGuidedFeedback(error.message, true);
    }
  });

  guided.saveConvert?.addEventListener('click', async () => {
    try {
      setGuidedFeedback('');
      await persistGuidedChanges();
      await window.convertIngestion(guided.targetType.value || 'schedule', { skipPersist: true });
    } catch (error) {
      setGuidedFeedback(error.message, true);
    }
  });

  [searchEl, originFilterEl, completionFilterEl, reviewFilterEl].forEach((el) => {
    el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', async () => {
      await loadItems();
    });
  });

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadItems();
    } catch (error) {
      alert(error.message);
    }
  });
})();
