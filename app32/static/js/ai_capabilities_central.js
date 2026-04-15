(function () {
  const page = document.getElementById('aiCapabilitiesPage');
  if (!page) return;

  const initialStateNode = document.getElementById('aiCapabilitiesInitialState');
  const searchInput = document.getElementById('aiCapabilitiesSearch');
  const listNode = document.getElementById('aiCapabilitiesList');
  const filtersNode = document.getElementById('aiCapabilitiesDomainFilters');
  const contentNode = document.getElementById('aiCapabilitiesContent');
  const countNode = document.getElementById('aiCapabilitiesCatalogCount');
  const requestListNode = document.getElementById('aiCapabilitiesRequestList');
  const requestForm = document.getElementById('capabilityRequestForm');
  const requestModal = document.getElementById('capabilityRequestModal');
  const requestKeyInput = document.getElementById('capabilityRequestKey');
  const requestNameInput = document.getElementById('capabilityRequestName');
  const endpoint = page.dataset.stateEndpoint;
  const requestsEndpoint = '/api/configs/ai/capabilities/requests';

  let state = {};
  let selectedKey = page.dataset.selectedCapability || '';
  let searchQuery = '';
  let activeDomain = 'all';
  let loading = false;

  try {
    state = JSON.parse(initialStateNode?.textContent || '{}');
  } catch (error) {
    console.error('Falha ao carregar estado inicial da Central de Capacidades.', error);
    state = {};
  }

  function normalize(value) {
    return (value || '')
      .toString()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  }

  function escapeHtml(value) {
    return (value || '')
      .toString()
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function badge(label, tone) {
    return `<span class="ai-cap-badge ${tone ? `is-${tone}` : ''}">${escapeHtml(label)}</span>`;
  }

  function renderFilters() {
    const domains = ['all'].concat(state.catalog?.filters?.domains || []);
    filtersNode.innerHTML = domains.map((domain) => {
      const label = domain === 'all' ? 'Todos' : domain;
      const isActive = activeDomain === domain;
      return `<button type="button" class="ai-cap-filter ${isActive ? 'is-active' : ''}" data-domain="${escapeHtml(domain)}">${escapeHtml(label)}</button>`;
    }).join('');
  }

  function getFilteredItems() {
    const items = state.catalog?.items || [];
    return items.filter((item) => {
      const matchesDomain = activeDomain === 'all' || item.domain === activeDomain;
      const haystack = [item.key, item.name, item.domain, item.type, item.risk, item.description, ...(item.badges || [])].join(' ');
      const matchesSearch = !searchQuery || normalize(haystack).includes(normalize(searchQuery));
      return matchesDomain && matchesSearch;
    });
  }

  function renderList() {
    const items = getFilteredItems();
    const groups = new Map();
    items.forEach((item) => {
      if (!groups.has(item.domain)) groups.set(item.domain, []);
      groups.get(item.domain).push(item);
    });

    countNode.textContent = `${items.length} capacidades visíveis`;

    if (!items.length) {
      listNode.innerHTML = '<div class="int-empty">Nenhuma capability encontrada com os filtros atuais.</div>';
      return;
    }

    listNode.innerHTML = Array.from(groups.entries()).map(([domain, domainItems]) => `
      <section class="ai-cap-group">
        <header class="ai-cap-group__title">${escapeHtml(domain)}</header>
        <div class="ai-cap-group__items">
          ${domainItems.map((item) => `
            <button type="button" class="ai-cap-list-item ${item.key === selectedKey ? 'is-active' : ''}" data-capability-key="${escapeHtml(item.key)}">
              <div>
                <strong>${escapeHtml(item.name)}</strong>
                <span>${escapeHtml(item.key)}</span>
              </div>
              <div class="ai-cap-list-item__meta">
                ${badge(item.status, item.status)}
                ${badge(item.risk, item.risk === 'low' ? 'success' : item.risk === 'medium' ? 'warning-soft' : 'danger')}
              </div>
            </button>
          `).join('')}
        </div>
      </section>
    `).join('');
  }

  function renderOperatorActions(selectedCatalog) {
    const steps = state.assistant?.steps?.[0]?.options || [];
    return `
      <section class="ai-cap-section-card">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Comandos do operador</span>
            <h3>O que você quer fazer agora?</h3>
            <p class="muted">Ações guiadas para tratar acesso, configuração, rollout e auditoria.</p>
          </div>
        </div>
        <div class="ai-cap-operator-grid">
          ${steps.map((option) => `
            <button type="button" class="ai-cap-operator-card" data-jump-target="${escapeHtml(option.target_tab || 'overview')}">
              <strong>${escapeHtml(option.label)}</strong>
              <span>${escapeHtml(option.description)}</span>
            </button>
          `).join('')}
          <button type="button" class="ai-cap-operator-card is-primary" data-open-capability-request="1">
            <strong>Registrar solicitação</strong>
            <span>Abrir atividade no backlog para ${escapeHtml(selectedCatalog.name || 'esta capability')}.</span>
          </button>
        </div>
      </section>
    `;
  }

  function renderContent() {
    const selected = state.availability?.selected_context || {};
    const requirements = state.requirements || {};
    const rollout = state.rollout || {};
    const audit = state.audit?.events || [];
    const availabilityViews = state.availability?.views || [];
    const catalogItems = state.catalog?.items || [];
    const selectedCatalog = catalogItems.find((item) => item.key === state.selected_capability_key) || catalogItems[0] || {};
    const settings = requirements.company_settings || [];
    const checklist = requirements.checklist || [];
    const hero = state.hero || {};
    const sidebar = state.sidebar || {};

    contentNode.innerHTML = `
      <section class="ai-cap-hero-panel" id="section-overview">
        <div>
          <span class="int-eyebrow">Capability em foco</span>
          <h2>${escapeHtml(selected.title || 'Nenhuma capability selecionada')}</h2>
          <p class="muted">${escapeHtml(selected.subtitle || 'Sem descrição operacional disponível.')}</p>
        </div>
        <div class="ai-cap-hero-status">
          ${badge(selected.status || selectedCatalog.status || 'draft', selected.status || selectedCatalog.status || 'draft')}
          ${badge(selectedCatalog.type || '-', 'neutral')}
          ${badge(selectedCatalog.domain || '-', 'neutral')}
        </div>
      </section>

      <section class="ai-cap-detail-grid">
        <article class="ai-cap-detail-block">
          <span class="ai-cap-detail-label">Código</span>
          <strong>${escapeHtml(selectedCatalog.key || '-')}</strong>
        </article>
        <article class="ai-cap-detail-block">
          <span class="ai-cap-detail-label">Domínio</span>
          <strong>${escapeHtml(selectedCatalog.domain || '-')}</strong>
        </article>
        <article class="ai-cap-detail-block">
          <span class="ai-cap-detail-label">Tipo</span>
          <strong>${escapeHtml(selectedCatalog.type || '-')}</strong>
        </article>
        <article class="ai-cap-detail-block">
          <span class="ai-cap-detail-label">Risco</span>
          <strong>${escapeHtml(selectedCatalog.risk || '-')}</strong>
        </article>
        <article class="ai-cap-detail-block ai-cap-detail-block--wide">
          <span class="ai-cap-detail-label">Regra efetiva</span>
          <strong>${escapeHtml(selected.effective_rule || 'fallback negado')}</strong>
          <p>${escapeHtml(selected.company || 'Sem empresa ativa')}</p>
        </article>
        <article class="ai-cap-detail-block ai-cap-detail-block--wide">
          <span class="ai-cap-detail-label">Canais / surfaces</span>
          <div class="ai-cap-badge-row">
            ${(selectedCatalog.badges || []).map((item) => badge(item, 'neutral')).join('') || '<span class="muted">Sem metadados.</span>'}
          </div>
        </article>
      </section>

      ${renderOperatorActions(selectedCatalog)}

      <section class="ai-cap-section-card">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Resumo da central</span>
            <h3>Contexto operacional consolidado</h3>
            <p class="muted">Leitura rápida para tomada de decisão sem depender da coluna lateral.</p>
          </div>
        </div>
        <div class="ai-cap-summary-grid">
          ${(hero.metrics || []).map((metric) => `
            <article class="ai-cap-summary-card is-primary">
              <span>${escapeHtml(metric.label)}</span>
              <strong>${escapeHtml(metric.value)}</strong>
            </article>
          `).join('')}
        </div>
        <div class="ai-cap-inline-context">
          ${(sidebar.context?.items || []).map((item) => `
            <div class="ai-cap-inline-context-item">
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </div>
          `).join('')}
        </div>
      </section>

      <section class="ai-cap-section-card" id="section-availability">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Disponibilização</span>
            <h3>Quem pode usar e como a regra é resolvida</h3>
            <p class="muted">Leitura consolidada por capacidade, empresa e usuário.</p>
          </div>
        </div>
        <div class="ai-cap-surface-grid">
          ${availabilityViews.map((view) => `
            <article class="ai-cap-surface-card">
              <header>
                <h4>${escapeHtml(view.title)}</h4>
                <p>${escapeHtml(view.summary)}</p>
              </header>
              <div class="ai-cap-mini-list">
                ${(view.cards || []).slice(0, 4).map((card) => `
                  <div class="ai-cap-mini-card">
                    <div class="ai-cap-mini-card__top">
                      <strong>${escapeHtml(card.title)}</strong>
                      ${badge(card.status || 'draft', card.status || 'draft')}
                    </div>
                    <span>${escapeHtml(card.meta || '')}</span>
                    <p>${escapeHtml(card.description || '')}</p>
                    <div class="ai-cap-badge-row">${(card.chips || []).map((chip) => badge(chip, 'neutral')).join('')}</div>
                  </div>
                `).join('')}
              </div>
            </article>
          `).join('')}
        </div>
        <div class="ai-cap-precedence">
          <strong>Precedência de decisão</strong>
          <ol>${(state.availability?.precedence || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ol>
        </div>
      </section>

      <section class="ai-cap-section-card" id="section-requirements">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Pré-requisitos</span>
            <h3>Checklist operacional e parâmetros por empresa</h3>
          </div>
        </div>
        <div class="ai-cap-dual-grid">
          <article class="ai-cap-stack-card">
            <h4>Checklist</h4>
            <div class="ai-cap-checklist">
              ${checklist.map((item) => `
                <div class="ai-cap-check-item is-${escapeHtml(item.status || 'warning')}">
                  <div>
                    <strong>${escapeHtml(item.title)}</strong>
                    <p>${escapeHtml(item.detail || '')}</p>
                  </div>
                  <div class="ai-cap-check-item__meta">
                    ${badge(item.status || '-', item.status || 'neutral')}
                    ${item.href ? `<a href="${escapeHtml(item.href)}" class="ai-cap-link">${escapeHtml(item.action || 'Abrir')}</a>` : ''}
                  </div>
                </div>
              `).join('') || '<div class="int-empty">Nenhum checklist calculado.</div>'}
            </div>
          </article>
          <article class="ai-cap-stack-card">
            <h4>Configuração por empresa</h4>
            <div class="ai-cap-setting-grid">
              ${settings.map((item) => `
                <div class="ai-cap-setting-card">
                  <span>${escapeHtml(item.label)}</span>
                  <strong>${escapeHtml(item.value)}</strong>
                </div>
              `).join('') || '<div class="int-empty">Nenhum parâmetro encontrado.</div>'}
            </div>
          </article>
        </div>
      </section>

      <section class="ai-cap-section-card" id="section-rollout">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Rollout</span>
            <h3>Expansão controlada da capability</h3>
            <p class="muted">Status oficial, owner e sinais de operação.</p>
          </div>
          <div class="ai-cap-rollout-meta">
            <strong>${escapeHtml(rollout.status_label || '-')}</strong>
            <span>Responsável: ${escapeHtml(rollout.owner || '-')}</span>
            <span>Atualizado em: ${escapeHtml(rollout.updated_at || '-')}</span>
          </div>
        </div>
        <div class="ai-cap-track">
          ${(rollout.steps || []).map((item) => `
            <div class="ai-cap-track-step is-${escapeHtml(item.state || 'upcoming')}">
              <span></span>
              <strong>${escapeHtml(item.label)}</strong>
            </div>
          `).join('')}
        </div>
        <div class="ai-cap-summary-grid">
          ${(rollout.summary_cards || []).map((item) => `
            <article class="ai-cap-summary-card is-${escapeHtml(item.tone || 'primary')}">
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </article>
          `).join('')}
        </div>
      </section>

      <section class="ai-cap-section-card" id="section-audit">
        <div class="ai-cap-section-head">
          <div>
            <span class="int-eyebrow">Auditoria</span>
            <h3>Linha do tempo de decisões e eventos</h3>
          </div>
        </div>
        <div class="ai-cap-audit-list">
          ${audit.map((item) => `
            <article class="ai-cap-audit-item is-${escapeHtml(item.result || 'neutral')}">
              <div class="ai-cap-audit-item__top">
                <div>
                  <span>${escapeHtml(item.when || '-')}</span>
                  <strong>${escapeHtml(item.event || '-')}</strong>
                </div>
                ${badge(item.result || '-', item.result || 'neutral')}
              </div>
              <p>${escapeHtml(item.detail || 'Sem detalhe.')}</p>
              <div class="ai-cap-audit-meta">
                <span><strong>Ator:</strong> ${escapeHtml(item.actor || 'Sistema')}</span>
                <span><strong>Empresa:</strong> ${escapeHtml(item.company || 'Global')}</span>
              </div>
            </article>
          `).join('') || '<div class="int-empty">Sem eventos recentes.</div>'}
        </div>
      </section>
    `;
  }

  async function renderRequestsBoard() {
    try {
      const url = new URL(requestsEndpoint, window.location.origin);
      if (state.selected_capability_key) {
        url.searchParams.set('capability_key', state.selected_capability_key);
      }
      const response = await fetch(url.toString(), { credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Falha ao carregar backlog.');
      const requests = data.requests || [];
      const statusLabels = {
        inbox: 'Caixa de Entrada', waiting: 'Aguardando', executing: 'Executando', pending: 'Pendências', suspended: 'Suspensos', completed: 'Concluídos'
      };
      if (!requests.length) {
        requestListNode.innerHTML = '<div class="int-empty">Nenhum item aberto na central.</div>';
        return;
      }
      const grouped = {};
      requests.forEach((req) => {
        const status = req.status || 'pending';
        grouped[status] = grouped[status] || [];
        grouped[status].push(req);
      });
      requestListNode.innerHTML = Object.entries(grouped).map(([status, items]) => `
        <div class="int-request-group">
          <div class="int-request-title">${statusLabels[status] || status}</div>
          ${items.map((req) => `
            <div class="int-request-item">
              <strong>${escapeHtml(req.title || '-')}</strong>
              <span class="muted">${escapeHtml(req.capability_name || req.business_domain || 'Capability IA')} · ${escapeHtml(req.backlog_task_code || ('AA.J.31.' + (req.backlog_task_id || '-')))}</span>
              ${req.backlog_task_href ? `<a class="ai-cap-request-link" href="${escapeHtml(req.backlog_task_href)}">Abrir atividade</a>` : ''}
            </div>
          `).join('')}
        </div>
      `).join('');
    } catch (error) {
      requestListNode.innerHTML = '<div class="int-empty">Falha ao carregar backlog da central.</div>';
    }
  }

  function openCapabilityRequestModal() {
    const catalogItems = state.catalog?.items || [];
    const selectedCatalog = catalogItems.find((item) => item.key === state.selected_capability_key) || catalogItems[0] || {};
    if (requestKeyInput) requestKeyInput.value = selectedCatalog.key || '';
    if (requestNameInput) requestNameInput.value = selectedCatalog.name || '';
    const domainInput = requestForm?.querySelector('[name="business_domain"]');
    if (domainInput && !domainInput.value) domainInput.value = selectedCatalog.domain || 'IA Corporativa';
    if (requestModal) {
      requestModal.classList.add('show');
      requestModal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
  }

  function closeCapabilityRequestModal() {
    if (!requestModal) return;
    requestModal.classList.remove('show');
    requestModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  window.closeCapabilityRequestModal = closeCapabilityRequestModal;

  function renderAll() {
    renderFilters();
    renderList();
    renderContent();
  }

  async function loadCapability(capabilityKey) {
    if (!capabilityKey || loading || capabilityKey === state.selected_capability_key) return;
    loading = true;
    page.classList.add('is-loading');
    try {
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set('capability_key', capabilityKey);
      const response = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error || 'Falha ao carregar capability.');
      state = payload.state || {};
      selectedKey = state.selected_capability_key || capabilityKey;
      page.dataset.selectedCapability = selectedKey;
      window.history.replaceState({}, '', `${window.location.pathname}?capability_key=${encodeURIComponent(selectedKey)}`);
      renderAll();
      renderRequestsBoard();
    } catch (error) {
      console.error(error);
    } finally {
      loading = false;
      page.classList.remove('is-loading');
    }
  }

  page.addEventListener('click', (event) => {
    const capabilityButton = event.target.closest('[data-capability-key]');
    if (capabilityButton) return void loadCapability(capabilityButton.dataset.capabilityKey);
    const domainButton = event.target.closest('[data-domain]');
    if (domainButton) {
      activeDomain = domainButton.dataset.domain || 'all';
      return void renderAll();
    }
    const jumpButton = event.target.closest('[data-jump-target]');
    if (jumpButton) {
      const section = document.getElementById(`section-${jumpButton.dataset.jumpTarget}`);
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (event.target.closest('[data-open-capability-request]')) {
      openCapabilityRequestModal();
    }
  });

  document.getElementById('openCapabilityRequestAssistant')?.addEventListener('click', openCapabilityRequestModal);

  requestModal?.addEventListener('click', (event) => {
    if (event.target === requestModal) {
      closeCapabilityRequestModal();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && requestModal?.classList.contains('show')) {
      closeCapabilityRequestModal();
    }
  });

  if (searchInput) {
    searchInput.addEventListener('input', (event) => {
      searchQuery = event.target.value || '';
      renderList();
    });
  }

  requestForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(requestsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Falha ao registrar solicitação.');
      form.reset();
      closeCapabilityRequestModal();
      await renderRequestsBoard();
      window.alert('Solicitação registrada com sucesso no backlog AA.J.31.');
    } catch (error) {
      window.alert(error.message || 'Falha ao registrar solicitação.');
    }
  });

  selectedKey = state.selected_capability_key || selectedKey;
  renderAll();
  renderRequestsBoard();
})();
