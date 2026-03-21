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
  const reviewNotes = document.getElementById('ing-review-notes');

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

  function renderDetail(item) {
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
    reviewNotes.value = item.review_notes || '';
    renderList();
  }

  async function loadItems() {
    const params = new URLSearchParams({ company_id: String(companyId) });
    if (originFilterEl.value) params.set('origin_type', originFilterEl.value);
    if (completionFilterEl.value) params.set('completion_status', completionFilterEl.value);
    if (reviewFilterEl.value) params.set('review_status', reviewFilterEl.value);
    items = await fetchJson(`/api/financial/ingestions?${params.toString()}`);
    renderList();
    if (selected) {
      const current = items.find((item) => item.id === selected.id);
      if (current) renderDetail(current);
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
      renderDetail(result);
      await loadItems();
      alert('Revisão registrada com sucesso.');
    } catch (error) {
      alert(error.message);
    }
  };

  window.convertIngestion = async (targetType) => {
    if (!selected) return;
    try {
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
      renderDetail(item);
    } catch (error) {
      alert(error.message);
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
