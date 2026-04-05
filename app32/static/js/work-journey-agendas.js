(() => {
  const bootstrap = window.workJourneyBootstrap || {};
  const companyId = bootstrap.companyId;
  const renderer = window.WorkJourneyAgendasRenderer;
  const utils = window.WorkJourneyUtils || {};
  const { api, toast } = utils;

  const employeeSelect = document.getElementById('journeyEmployeeSelect');
  const dateInput = document.getElementById('journeyDateInput');
  const refreshBtn = document.getElementById('agendaRefreshBtn');
  const generateBtn = document.getElementById('agendaGenerateBtn');
  const lockBtn = document.getElementById('agendaLockBtn');
  const unlockBtn = document.getElementById('agendaUnlockBtn');
  const pdfBtn = document.getElementById('agendaPdfBtn');
  const boardContainer = document.getElementById('agendaBoardContainer');
  const summaryContainer = document.getElementById('agendaSummaryCards');
  const statusLabel = document.getElementById('agendaStatusLabel');
  const statusBadge = document.getElementById('agendaLockBadge');
  const metaLine = document.getElementById('agendaMetaLine');
  const searchStatus = document.getElementById('agendaSearchStatus');

  const state = {
    agenda: null,
    loading: false,
    collapsedBlocks: new Set(),
    collapsedDays: new Set(),
    collapsedPanels: new Set(),
    legacyFallback: false,
    storageKey: null,
    draggingItemId: null,
  };

  if (!renderer || !api) return;

  function selectedEmployeeId() {
    return parseInt(employeeSelect?.value, 10) || null;
  }

  function selectedDate() {
    return dateInput?.value || bootstrap.today;
  }

  function currentScope() {
    return 'week';
  }

  function currentSearchTerm() {
    return window.WorkJourneyPage?.getSearchTerm?.() || '';
  }

  function getStorageKeyBase() {
    return [
      'workJourney',
      'agenda',
      companyId || 'unknown',
      selectedEmployeeId() || 'all',
      currentScope(),
      selectedDate(),
    ].join(':');
  }

  function readPersistedSet(name) {
    try {
      const raw = localStorage.getItem(`${getStorageKeyBase()}:${name}`);
      if (!raw) return new Set();
      const values = JSON.parse(raw);
      return new Set(Array.isArray(values) ? values : []);
    } catch (_error) {
      return new Set();
    }
  }

  function writePersistedSet(name, setValue) {
    try {
      localStorage.setItem(`${getStorageKeyBase()}:${name}`, JSON.stringify(Array.from(setValue)));
    } catch (_error) {
      // silently ignore storage failures
    }
  }

  function setLoading(nextValue) {
    state.loading = nextValue;
    [refreshBtn, generateBtn, lockBtn, unlockBtn].forEach((btn) => {
      if (btn) btn.disabled = nextValue;
    });
  }

  function agendaTitle(item) {
    return item.display_title || item.title || `Tarefa ${item.id}`;
  }

  function findItem(itemId) {
    for (const day of state.agenda?.days || []) {
      for (const block of day.blocks || []) {
        const found = (block.items || []).find((item) => Number(item.id) === Number(itemId));
        if (found) return { item: found, day, block };
      }
      const unassigned = (day.unassigned_items || []).find((item) => Number(item.id) === Number(itemId));
      if (unassigned) return { item: unassigned, day, block: null };
    }
    return null;
  }

  function updateControls() {
    const agenda = state.agenda;
    const locked = Boolean(agenda?.locked);
    const hasAgenda = Boolean(agenda?.id);

    if (statusLabel) {
      const status = locked ? 'Travada' : (agenda?.status === 'suggested' ? 'Sugerida' : 'Rascunho');
      statusLabel.textContent = status;
      statusLabel.className = `agenda-status-pill ${locked ? 'agenda-status-pill--locked' : agenda?.status === 'suggested' ? 'agenda-status-pill--suggested' : 'agenda-status-pill--draft'}`;
    }

    if (statusBadge) {
      statusBadge.textContent = locked ? 'Agenda travada' : 'Agenda aberta';
      statusBadge.className = `agenda-status-pill ${locked ? 'agenda-status-pill--locked' : 'agenda-status-pill--draft'}`;
    }

    if (lockBtn) lockBtn.style.display = !hasAgenda || locked ? 'none' : '';
    if (unlockBtn) unlockBtn.style.display = hasAgenda && locked ? '' : 'none';

    if (pdfBtn) {
      pdfBtn.href = hasAgenda ? `/api/companies/${companyId}/work-journey/agendas/${agenda.id}/pdf` : '#';
      pdfBtn.style.pointerEvents = hasAgenda ? 'auto' : 'none';
      pdfBtn.style.opacity = hasAgenda ? '1' : '0.5';
    }

    if (metaLine) {
      const parts = [];
      if (agenda?.generated_at) parts.push(`Gerada em ${agenda.generated_at}`);
      if (agenda?.locked_at) parts.push(`Travada em ${agenda.locked_at}`);
      if (agenda?.locked_by_name) parts.push(`por ${agenda.locked_by_name}`);
      if (agenda?.engine_version) parts.push(`Motor ${agenda.engine_version}`);
      metaLine.textContent = parts.length ? parts.join(' · ') : (state.legacyFallback ? 'Fallback do board legado em uso.' : 'Sem agenda materializada ainda.');
    }
  }

  function applyPanelCollapseState() {
    document.querySelectorAll('[data-collapse-panel]').forEach((panel) => {
      const key = panel.dataset.collapsePanel;
      const collapsed = state.collapsedPanels.has(key);
      const body = panel.querySelector('[data-collapse-body]');
      const toggle = panel.querySelector(`[data-collapse-toggle="${key}"]`);
      panel.classList.toggle('is-collapsed', collapsed);
      body?.classList.toggle('is-hidden', collapsed);
      if (body) body.setAttribute('aria-hidden', collapsed ? 'true' : 'false');
      if (toggle) {
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        toggle.setAttribute('aria-label', collapsed ? `Expandir ${panel.dataset.collapseLabel || key}` : `Colapsar ${panel.dataset.collapseLabel || key}`);
      }
    });
  }

  function clearDropHighlights() {
    document.querySelectorAll('.agenda-dropzone--over').forEach((zone) => zone.classList.remove('agenda-dropzone--over'));
  }

  function renderAgenda() {
    updateControls();

    const searchTerm = currentSearchTerm();
    const agenda = filterAgendaBySearch(state.agenda, searchTerm);
    const summary = agenda?.summary || renderer.buildSummaryFromDays(agenda?.days || []);

    if (summaryContainer) {
      summaryContainer.innerHTML = renderer.renderSummaryCards(summary);
    }

    if (searchStatus) {
      searchStatus.hidden = !searchTerm;
      searchStatus.textContent = searchTerm ? `Busca ativa: "${searchTerm}"` : '';
    }

    if (!boardContainer) return;

    if (!agenda) {
      boardContainer.innerHTML = '<div class="agenda-empty-state">Nenhuma agenda disponível para o contexto selecionado.</div>';
      applyPanelCollapseState();
      return;
    }

    if (!agenda.days?.length && !(agenda.overdue_items || []).length && !(agenda.unassigned_items || []).length) {
      boardContainer.innerHTML = '<div class="agenda-empty-state">Nenhum bloco ou tarefa corresponde à busca aplicada.</div>';
      applyPanelCollapseState();
      return;
    }

    const html = renderer.renderAgendaHTML(agenda, state, agenda.locked);
    boardContainer.innerHTML = html.boardHTML || '<div class="agenda-empty-state">Sem dias na agenda.</div>';
    applyPanelCollapseState();
  }

  function filterAgendaBySearch(agenda, searchTerm) {
    if (!agenda || !searchTerm) return agenda;

    const filteredDays = (agenda.days || []).map((day) => {
      const blocks = (day.blocks || []).map((block) => {
        const blockMatches = utils.searchIncludes({
          ...block,
          day_label: day.label,
          day_subtitle: day.subtitle,
          day_date: day.date,
        }, searchTerm);
        const items = blockMatches
          ? [...(block.items || [])]
          : (block.items || []).filter((item) => utils.searchIncludes({
            ...item,
            block_name: block.name,
            block_description: block.description,
            block_mode: block.block_mode,
            block_mode_label: block.block_mode_label,
            day_label: day.label,
            day_subtitle: day.subtitle,
            day_date: day.date,
          }, searchTerm));

        if (!blockMatches && !items.length) return null;
        return { ...block, items };
      }).filter(Boolean);

      const unassignedItems = (day.unassigned_items || []).filter((item) => utils.searchIncludes({
        ...item,
        day_label: day.label,
        day_subtitle: day.subtitle,
        day_date: day.date,
      }, searchTerm));

      if (!blocks.length && !unassignedItems.length) {
        return null;
      }

      return {
        ...day,
        blocks,
        unassigned_items: unassignedItems,
      };
    }).filter(Boolean);

    const overdueItems = renderer.sortAgendaItems((agenda.overdue_items || []).filter((item) => utils.searchIncludes(item, searchTerm)));
    const unassignedItems = renderer.sortAgendaItems((agenda.unassigned_items || []).filter((item) => utils.searchIncludes(item, searchTerm)));
    const summary = renderer.buildSummaryFromDays(filteredDays);
    summary.unassigned_count = unassignedItems.length;
    summary.overdue_count = overdueItems.length;

    return {
      ...agenda,
      days: filteredDays,
      overdue_items: overdueItems,
      unassigned_items: unassignedItems,
      summary,
    };
  }

  function toggleBlock(toggleButton) {
    const key = toggleButton?.dataset?.agendaToggle;
    if (!key) return;
    const block = toggleButton.closest('.agenda-block');
    const content = block?.querySelector('.agenda-block__content');
    const collapsed = state.collapsedBlocks.has(key);

    if (collapsed) {
      state.collapsedBlocks.delete(key);
      block?.classList.remove('is-collapsed');
      content?.classList.remove('is-hidden');
      content?.setAttribute('aria-hidden', 'false');
      toggleButton.setAttribute('aria-expanded', 'true');
    } else {
      state.collapsedBlocks.add(key);
      block?.classList.add('is-collapsed');
      content?.classList.add('is-hidden');
      content?.setAttribute('aria-hidden', 'true');
      toggleButton.setAttribute('aria-expanded', 'false');
    }

    writePersistedSet('collapsedBlocks', state.collapsedBlocks);
  }

  function toggleDay(toggleButton) {
    const key = toggleButton?.dataset?.agendaDayToggle;
    if (!key) return;
    const column = toggleButton.closest('.agenda-day-column');
    const body = column?.querySelector('.agenda-day-column__body');
    const collapsed = state.collapsedDays.has(key);

    if (collapsed) {
      state.collapsedDays.delete(key);
      column?.classList.remove('is-collapsed');
      body?.classList.remove('is-hidden');
      body?.setAttribute('aria-hidden', 'false');
      toggleButton.setAttribute('aria-expanded', 'true');
      toggleButton.setAttribute('aria-label', 'Colapsar dia');
    } else {
      state.collapsedDays.add(key);
      column?.classList.add('is-collapsed');
      body?.classList.add('is-hidden');
      body?.setAttribute('aria-hidden', 'true');
      toggleButton.setAttribute('aria-expanded', 'false');
      toggleButton.setAttribute('aria-label', 'Expandir dia');
    }

    writePersistedSet('collapsedDays', state.collapsedDays);
  }

  function togglePanel(toggleButton) {
    const key = toggleButton?.dataset?.collapseToggle;
    if (!key) return;
    const panel = toggleButton.closest('[data-collapse-panel]');
    const body = panel?.querySelector('[data-collapse-body]');
    const label = panel?.dataset?.collapseLabel || key;
    const collapsed = state.collapsedPanels.has(key);

    if (collapsed) {
      state.collapsedPanels.delete(key);
      panel?.classList.remove('is-collapsed');
      body?.classList.remove('is-hidden');
      body?.setAttribute('aria-hidden', 'false');
      toggleButton.setAttribute('aria-expanded', 'true');
      toggleButton.setAttribute('aria-label', `Colapsar ${label}`);
    } else {
      state.collapsedPanels.add(key);
      panel?.classList.add('is-collapsed');
      body?.classList.add('is-hidden');
      body?.setAttribute('aria-hidden', 'true');
      toggleButton.setAttribute('aria-expanded', 'false');
      toggleButton.setAttribute('aria-label', `Expandir ${label}`);
    }

    writePersistedSet('collapsedPanels', state.collapsedPanels);
  }

  function onDragStart(event) {
    const card = event.target.closest?.('.agenda-card');
    if (!card || state.agenda?.locked) return;
    if (card.dataset.itemType === 'meeting') {
      toast('Reuniões não podem ser arrastadas. Ajuste no módulo de reuniões.');
      event.preventDefault();
      return;
    }

    state.draggingItemId = card.dataset.agendaItem;
    card.classList.add('is-dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', state.draggingItemId);
  }

  function onDragEnd(event) {
    const card = event.target.closest?.('.agenda-card');
    card?.classList.remove('is-dragging');
    state.draggingItemId = null;
    clearDropHighlights();
  }

  function onDragOver(event) {
    if (state.agenda?.locked) return;
    const zone = event.target.closest?.('[data-dropzone]');
    if (!zone) return;
    const dragged = state.draggingItemId ? findItem(state.draggingItemId) : null;
    if (!dragged || dragged.item.item_type === 'meeting') return;

    event.preventDefault();
    clearDropHighlights();
    zone.classList.add('agenda-dropzone--over');
    event.dataTransfer.dropEffect = 'move';
  }

  async function onDrop(event) {
    if (state.agenda?.locked) return;
    const zone = event.target.closest?.('[data-dropzone]');
    if (!zone) return;
    event.preventDefault();

    const itemId = state.draggingItemId || event.dataTransfer.getData('text/plain');
    const source = findItem(itemId);
    clearDropHighlights();

    if (!source) return;
    if (source.item.item_type === 'meeting') {
      toast('Reuniões não podem ser arrastadas. Ajuste no módulo de reuniões.');
      return;
    }

    const targetBlockId = zone.dataset.blockId ? Number(zone.dataset.blockId) : null;
    const targetDay = zone.dataset.agendaDay || source.day?.date || source.item.agenda_date || source.item.due_date || selectedDate();
    const sourceDay = source.day?.date || source.item.agenda_date || source.item.due_date || selectedDate();
    const dayChanged = Boolean(targetDay && sourceDay && targetDay !== sourceDay);

    if (dayChanged) {
      const answer = confirm(`Mover ${agendaTitle(source.item)} de ${sourceDay} para ${targetDay} e atualizar a data?`);
      if (!answer) return;
    }

    try {
      if (state.legacyFallback || !state.agenda?.id) {
        await api(`/api/companies/${companyId}/work-journey/items/${source.item.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            block_id: targetBlockId || null,
            due_date: targetDay,
          }),
        });
      } else {
        await api(`/api/companies/${companyId}/work-journey/agendas/items/${source.item.agenda_item_id || source.item.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            target_block_id: targetBlockId || null,
            target_date: targetDay,
            confirm_date_change: dayChanged,
          }),
        });
      }
      await loadAgenda(true);
      toast('Tarefa reposicionada com sucesso.');
    } catch (error) {
      toast(error.message);
    }
  }

  function wireInteractions() {
    boardContainer?.addEventListener('click', (event) => {
      const dayToggle = event.target.closest('[data-agenda-day-toggle]');
      if (dayToggle) toggleDay(dayToggle);

      const blockToggle = event.target.closest('[data-agenda-toggle]');
      if (blockToggle) toggleBlock(blockToggle);
    });

    document.addEventListener('click', (event) => {
      const panelToggle = event.target.closest('[data-collapse-toggle]');
      if (panelToggle) togglePanel(panelToggle);

      const meetingHint = event.target.closest('[data-action="meeting-hint"]');
      if (meetingHint) {
        toast('Esta reunião deve ser ajustada no módulo de reuniões.');
      }
    });

    [boardContainer].forEach((container) => {
      if (!container) return;
      container.addEventListener('dragstart', onDragStart);
      container.addEventListener('dragend', onDragEnd);
      container.addEventListener('dragover', onDragOver);
      container.addEventListener('drop', onDrop);
    });
  }

  async function loadAgenda(forceFallback = false) {
    if (!companyId || !renderer) return;
    const employeeId = selectedEmployeeId();
    setLoading(true);

    state.storageKey = getStorageKeyBase();
    state.collapsedBlocks = readPersistedSet('collapsedBlocks');
    state.collapsedDays = readPersistedSet('collapsedDays');
    state.collapsedPanels = readPersistedSet('collapsedPanels');

    try {
      const response = await api(`/api/companies/${companyId}/work-journey/agendas?employee_id=${employeeId}&date=${selectedDate()}&scope=${currentScope()}`);
      state.agenda = renderer.normalizeAgenda(response, {
        selectedDate: selectedDate(),
        scope: currentScope(),
        employeeId,
        companyId,
      });
      state.legacyFallback = false;
    } catch (error) {
      if (!forceFallback) {
        try {
          const fallback = await api(`/api/companies/${companyId}/work-journey/board?employee_id=${employeeId}&date=${selectedDate()}&scope=${currentScope()}`);
          state.agenda = renderer.normalizeAgenda({
            agenda: {
              id: null,
              company_id: companyId,
              employee_id: employeeId,
              scope: currentScope(),
              status: 'draft',
              locked: false,
              generated_at: null,
              engine_version: 'board-fallback',
              days: [{
                date: selectedDate(),
                label: renderer.formatDayLabel(selectedDate(), 0),
                subtitle: 'Legado',
                blocks: fallback.data.blocks || [],
                unassigned_items: fallback.data.unassigned_items || [],
              }],
              unassigned_items: fallback.data.unassigned_items || [],
              summary: {
                ...(fallback.data.summary || {}),
                unassigned_count: (fallback.data.unassigned_items || []).length,
              },
            },
          }, {
            selectedDate: selectedDate(),
            scope: currentScope(),
            employeeId,
            companyId,
          });
          state.legacyFallback = true;
        } catch (fallbackError) {
          state.agenda = null;
          state.legacyFallback = false;
          toast(fallbackError.message || error.message);
        }
      }
    } finally {
      setLoading(false);
      renderAgenda();
    }
  }

  async function generateAgenda() {
    try {
      await api(`/api/companies/${companyId}/work-journey/agendas/generate`, {
        method: 'POST',
        body: JSON.stringify({
          employee_id: selectedEmployeeId(),
          date: selectedDate(),
          scope: currentScope(),
        }),
      });
      await loadAgenda();
      document.dispatchEvent(new CustomEvent('workJourney:refreshed'));
      toast('Agenda sugerida gerada com sucesso.');
    } catch (error) {
      toast(error.message);
    }
  }

  async function lockAgenda() {
    if (!state.agenda?.id) {
      toast('Gere uma agenda antes de travar.');
      return;
    }

    try {
      await api(`/api/companies/${companyId}/work-journey/agendas/${state.agenda.id}/lock`, {
        method: 'POST',
        body: JSON.stringify({ employee_id: selectedEmployeeId() }),
      });
      await loadAgenda();
      toast('Agenda travada.');
    } catch (error) {
      toast(error.message);
    }
  }

  async function unlockAgenda() {
    if (!state.agenda?.id) return;

    try {
      await api(`/api/companies/${companyId}/work-journey/agendas/${state.agenda.id}/unlock`, {
        method: 'POST',
        body: JSON.stringify({ employee_id: selectedEmployeeId() }),
      });
      await loadAgenda();
      toast('Travamento cancelado.');
    } catch (error) {
      toast(error.message);
    }
  }

  function wireControls() {
    refreshBtn?.addEventListener('click', () => loadAgenda());
    generateBtn?.addEventListener('click', generateAgenda);
    lockBtn?.addEventListener('click', lockAgenda);
    unlockBtn?.addEventListener('click', unlockAgenda);
    employeeSelect?.addEventListener('change', () => loadAgenda());
    dateInput?.addEventListener('change', () => loadAgenda());
    document.addEventListener('workJourney:refreshed', () => loadAgenda(true));
    document.addEventListener('workJourney:filters-changed', renderAgenda);
  }

  function init() {
    if (!boardContainer) return;
    wireControls();
    wireInteractions();
    loadAgenda();
  }

  window.WorkJourneyAgendas = {
    refresh: loadAgenda,
    generate: generateAgenda,
    lock: lockAgenda,
    unlock: unlockAgenda,
  };

  init();
})();
