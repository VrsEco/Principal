(() => {
  const bootstrap = window.workJourneyBootstrap || {};
  const companyId = bootstrap.companyId;
  const employeeSelect = document.getElementById('journeyEmployeeSelect');
  const dateInput = document.getElementById('journeyDateInput');
  const scopeSelect = document.getElementById('journeyScopeSelect');
  const manualTaskForm = document.getElementById('journeyManualTaskForm');

  const {
    api,
    toast,
    formatMinutes,
    renderTabs,
    renderCheckboxGrid,
    collectCheckedValues,
    itemTypes,
    weekdays,
  } = window.WorkJourneyUtils;

  const state = {
    board: null,
    blocks: [],
    absences: [],
    transfers: [],
  };

  function selectedEmployeeId() {
    return parseInt(employeeSelect.value, 10) || null;
  }

  function selectedDate() {
    return dateInput.value || bootstrap.today;
  }

  function availableManualBlocks() {
    return state.blocks.filter((block) => block.block_mode !== 'reserved_full' && (block.accepted_item_types || []).includes('manual'));
  }

  function renderSummary() {
    const summary = state.board?.summary;
    const container = document.getElementById('journeySummaryCards');
    if (!summary) {
      container.innerHTML = '';
      return;
    }

    const cards = [
      ['Capacidade útil', formatMinutes(summary.daily_capacity_minutes)],
      ['Período reservado', formatMinutes(summary.reserved_minutes)],
      ['Janela buffer', formatMinutes(summary.buffer_minutes)],
      ['Carga planejada', formatMinutes(summary.planned_minutes)],
      ['Carga realizada', formatMinutes(summary.worked_minutes)],
      ['Sobrecarga', formatMinutes(summary.overload_minutes)],
      ['Pendentes', summary.pending_count],
      ['Concluídas', summary.completed_count],
    ];

    container.innerHTML = cards.map(([label, value]) => `
      <div class="journey-summary-card">
        <span class="text-secondary">${label}</span>
        <strong class="${label === 'Sobrecarga' && Number(summary.overload_minutes || 0) > 0 ? 'journey-overload' : ''}">${value}</strong>
      </div>
    `).join('');
  }

  function itemBadges(item) {
    return [
      `<span class="badge-pill">${item.item_type_label || item.item_type}</span>`,
      `<span class="badge-pill ${item.status === 'completed' ? 'badge-pill--success' : item.is_overdue ? 'badge-pill--danger' : 'badge-pill--warning'}">${item.status_label || item.status}</span>`,
      item.estimated_minutes ? `<span class="badge-pill">${formatMinutes(item.estimated_minutes)}</span>` : '',
      item.source_label ? `<span class="badge-pill">${item.source_label}</span>` : '',
    ].join('');
  }

  function itemActions(item) {
    const worked = item.worked_minutes || 0;
    return `
      <div class="journey-item-card__actions">
        <button class="btn btn-secondary btn-sm" data-action="start-item" data-id="${item.id}">Iniciar</button>
        <button class="btn btn-secondary btn-sm" data-action="complete-item" data-id="${item.id}" data-worked="${worked}">Concluir</button>
        <button class="btn btn-secondary btn-sm" data-action="move-item" data-id="${item.id}">Mover bloco</button>
        <button class="btn btn-secondary btn-sm" data-action="transfer-item" data-id="${item.id}">Transferir</button>
        ${item.item_type === 'manual' ? `<button class="btn btn-secondary btn-sm" data-action="edit-manual-item" data-id="${item.id}">Editar</button><button class="btn btn-secondary btn-sm" data-action="delete-manual-item" data-id="${item.id}">Excluir</button>` : ''}
        ${item.source_url ? `<a class="btn btn-secondary btn-sm" href="${item.source_url}">Abrir origem</a>` : ''}
      </div>
    `;
  }

  function itemCard(item) {
    return `
      <article class="journey-item-card">
        <div class="journey-item-card__top">
          <div>
            <div class="journey-item-card__title">${item.title}</div>
            <div class="journey-item-card__desc">${item.description || 'Sem descrição adicional.'}</div>
          </div>
          <div class="journey-item-card__badges">${itemBadges(item)}</div>
        </div>
        ${itemActions(item)}
      </article>
    `;
  }

  function blockStatusBadge(block) {
    if (block.block_mode === 'reserved_full') return '<span class="badge-pill badge-pill--warning">Capacidade ocupada</span>';
    if (block.block_mode === 'buffer') return '<span class="badge-pill">Buffer para urgências</span>';
    return block.planned_task_minutes > block.operational_capacity_minutes
      ? '<span class="badge-pill badge-pill--danger">Acima da capacidade</span>'
      : '<span class="badge-pill badge-pill--success">Dentro da capacidade</span>';
  }

  function emptyBlockMessage(block) {
    if (block.block_mode === 'reserved_full') return 'Bloco reservado integralmente. O período fica protegido e não recebe tarefas.';
    if (block.block_mode === 'buffer') return 'Janela livre para urgências, encaixes manuais e reorganização do dia.';
    return 'Nenhuma tarefa sugerida para este bloco.';
  }

  function renderBoard() {
    const blocksContainer = document.getElementById('journeyBlocksContainer');
    const unassignedContainer = document.getElementById('journeyUnassignedContainer');
    const periodContainer = document.getElementById('journeyPeriodContainer');
    const unassigned = state.board?.unassigned_items || [];
    document.getElementById('journeyUnassignedCount').textContent = unassigned.length;

    const blocks = state.board?.blocks || [];
    blocksContainer.innerHTML = blocks.length ? blocks.map((block) => `
      <section class="journey-block">
        <div class="journey-block__header">
          <div>
            <h3 class="journey-block__title">${block.name}</h3>
            <div class="journey-block__meta">${block.start_time} → ${block.end_time} · ${block.block_mode_label} · Planejado ${formatMinutes(block.planned_minutes)} / Capacidade ${formatMinutes(block.capacity_minutes)}</div>
          </div>
          <div class="journey-badges">${blockStatusBadge(block)}</div>
        </div>
        <div class="journey-block__items">${(block.items || []).length ? block.items.map(itemCard).join('') : `<div class="journey-item-empty">${emptyBlockMessage(block)}</div>`}</div>
      </section>
    `).join('') : '<div class="journey-item-empty">Nenhum bloco ativo para o dia selecionado.</div>';

    unassignedContainer.innerHTML = unassigned.length ? unassigned.map(itemCard).join('') : '<div class="journey-item-empty">Sem tarefas fora dos blocos.</div>';

    const periodItems = state.board?.period_items || [];
    periodContainer.innerHTML = periodItems.length ? periodItems.slice(0, 12).map((item) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <strong>${item.title}</strong>
          <span class="badge-pill">${item.due_date || item.occurrence_date || '-'}</span>
        </div>
        <div class="journey-badges">${itemBadges(item)}</div>
      </div>
    `).join('') : '<div class="journey-item-empty">Sem tarefas no período.</div>';

    bindItemActions();
  }

  function renderBlocksList() {
    const container = document.getElementById('journeyBlocksList');
    const manualBlockSelect = document.getElementById('manualTaskBlockInput');
    const manualOptions = ['<option value="">Sem bloco</option>', ...availableManualBlocks().map((block) => `<option value="${block.id}">${block.name} · ${block.start_time} → ${block.end_time}</option>`)].join('');
    manualBlockSelect.innerHTML = manualOptions;

    container.innerHTML = state.blocks.length ? state.blocks.map((block) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${block.name}</strong>
            <div class="text-secondary small">${block.start_time} → ${block.end_time} · ${block.block_mode === 'reserved_full' ? 'Capacidade ocupada' : block.block_mode === 'buffer' ? 'Buffer' : 'Operacional'}</div>
          </div>
          <div class="journey-item-card__actions">
            <button class="btn btn-secondary btn-sm" data-action="edit-block" data-id="${block.id}">Editar</button>
            <button class="btn btn-secondary btn-sm" data-action="delete-block" data-id="${block.id}">Excluir</button>
          </div>
        </div>
      </div>
    `).join('') : '<div class="journey-item-empty">Nenhum bloco cadastrado.</div>';

    container.querySelectorAll('[data-action="edit-block"]').forEach((btn) => btn.addEventListener('click', () => populateBlockForm(Number(btn.dataset.id))));
    container.querySelectorAll('[data-action="delete-block"]').forEach((btn) => btn.addEventListener('click', () => deleteBlock(Number(btn.dataset.id))));
  }

  function renderAbsences() {
    const container = document.getElementById('journeyAbsenceList');
    container.innerHTML = state.absences.length ? state.absences.map((absence) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${absence.absence_type}</strong>
            <div class="text-secondary small">${absence.start_date} → ${absence.end_date}</div>
          </div>
          <div class="journey-item-card__actions">
            ${bootstrap.canManageAll && absence.status === 'pending' ? `<button class="btn btn-primary btn-sm" data-action="approve-absence" data-id="${absence.id}">Aprovar</button>` : ''}
          </div>
        </div>
        <div class="journey-badges"><span class="badge-pill">${absence.status}</span><span class="badge-pill">Itens impactados: ${(absence.impacted_items || []).length}</span></div>
      </div>
    `).join('') : '<div class="journey-item-empty">Nenhuma solicitação registrada.</div>';
    container.querySelectorAll('[data-action="approve-absence"]').forEach((btn) => btn.addEventListener('click', () => approveAbsence(Number(btn.dataset.id))));
  }

  function renderTransfers() {
    const container = document.getElementById('journeyTransferList');
    container.innerHTML = state.transfers.length ? state.transfers.map((transfer) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${transfer.item?.title || 'Tarefa'}</strong>
            <div class="text-secondary small">${transfer.from_employee_name || '-'} → ${transfer.to_employee_name || '-'}</div>
          </div>
          <div class="journey-item-card__actions">
            ${bootstrap.canManageAll && transfer.status === 'pending' ? `<button class="btn btn-primary btn-sm" data-action="approve-transfer" data-id="${transfer.id}">Aprovar</button>` : ''}
          </div>
        </div>
        <div class="journey-badges"><span class="badge-pill">${transfer.status}</span></div>
      </div>
    `).join('') : '<div class="journey-item-empty">Nenhuma transferência registrada.</div>';
    container.querySelectorAll('[data-action="approve-transfer"]').forEach((btn) => btn.addEventListener('click', () => approveTransfer(Number(btn.dataset.id))));
  }

  function populateBlockForm(id) {
    const block = state.blocks.find((item) => item.id === id);
    if (!block) return;
    document.getElementById('blockIdInput').value = block.id;
    document.getElementById('blockNameInput').value = block.name;
    document.getElementById('blockDescriptionInput').value = block.description || '';
    document.getElementById('blockStartInput').value = block.start_time;
    document.getElementById('blockEndInput').value = block.end_time;
    document.getElementById('blockModeInput').value = block.block_mode || 'operational';
    renderCheckboxGrid('blockWeekdaysGroup', weekdays, block.weekdays || []);
    renderCheckboxGrid('blockTypesGroup', itemTypes, block.accepted_item_types || []);
  }

  function resetBlockForm() {
    document.getElementById('journeyBlockForm').reset();
    document.getElementById('blockIdInput').value = '';
    document.getElementById('blockModeInput').value = 'operational';
    renderCheckboxGrid('blockWeekdaysGroup', weekdays, [0, 1, 2, 3, 4]);
    renderCheckboxGrid('blockTypesGroup', itemTypes, itemTypes.map((item) => item.value));
  }

  function openManualTaskForm(item = null) {
    manualTaskForm.style.display = 'block';
    document.getElementById('manualTaskIdInput').value = item?.id || '';
    document.getElementById('manualTaskTitleInput').value = item?.title || '';
    document.getElementById('manualTaskDescriptionInput').value = item?.description || '';
    document.getElementById('manualTaskDateInput').value = item?.due_date || selectedDate();
    document.getElementById('manualTaskMinutesInput').value = item?.estimated_minutes || 60;
    document.getElementById('manualTaskPriorityInput').value = item?.priority || 'normal';
    document.getElementById('manualTaskStatusInput').value = item?.status || 'pending';
    document.getElementById('manualTaskBlockInput').value = item?.block_id || '';
    manualTaskForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function resetManualTaskForm() {
    document.getElementById('manualTaskIdInput').value = '';
    document.getElementById('manualTaskTitleInput').value = '';
    document.getElementById('manualTaskDescriptionInput').value = '';
    document.getElementById('manualTaskDateInput').value = selectedDate();
    document.getElementById('manualTaskMinutesInput').value = 60;
    document.getElementById('manualTaskPriorityInput').value = 'normal';
    document.getElementById('manualTaskStatusInput').value = 'pending';
    document.getElementById('manualTaskBlockInput').value = '';
    manualTaskForm.style.display = 'none';
  }

  function bindItemActions() {
    document.querySelectorAll('[data-action="start-item"]').forEach((btn) => btn.addEventListener('click', () => patchItem(Number(btn.dataset.id), { status: 'in_progress' })));
    document.querySelectorAll('[data-action="complete-item"]').forEach((btn) => btn.addEventListener('click', () => {
      const worked = Number(window.prompt('Minutos realizados:', btn.dataset.worked || '60'));
      patchItem(Number(btn.dataset.id), { status: 'completed', worked_minutes: Number.isFinite(worked) ? worked : 0 });
    }));
    document.querySelectorAll('[data-action="move-item"]').forEach((btn) => btn.addEventListener('click', () => {
      const current = (state.board?.period_items || []).find((item) => item.id === Number(btn.dataset.id));
      const options = state.blocks
        .filter((block) => block.block_mode !== 'reserved_full' && (!current || (block.accepted_item_types || []).includes(current.item_type)))
        .map((block) => `${block.id}:${block.name}`)
        .join('\n');
      const choice = window.prompt(`Informe o ID do bloco desejado:\n${options}`);
      if (!choice) return;
      patchItem(Number(btn.dataset.id), { block_id: Number(choice) });
    }));
    document.querySelectorAll('[data-action="transfer-item"]').forEach((btn) => btn.addEventListener('click', () => createTransfer(Number(btn.dataset.id))));
    document.querySelectorAll('[data-action="edit-manual-item"]').forEach((btn) => btn.addEventListener('click', () => {
      const item = (state.board?.period_items || []).find((entry) => entry.id === Number(btn.dataset.id) && entry.item_type === 'manual');
      if (item) openManualTaskForm(item);
    }));
    document.querySelectorAll('[data-action="delete-manual-item"]').forEach((btn) => btn.addEventListener('click', () => deleteManualTask(Number(btn.dataset.id))));
  }

  async function patchItem(itemId, payload) {
    try {
      await api(`/api/companies/${companyId}/work-journey/items/${itemId}`, { method: 'PATCH', body: JSON.stringify(payload) });
      await Promise.all([loadBoard(), loadTransfers()]);
    } catch (error) {
      toast(error.message);
    }
  }

  async function saveManualTask(event) {
    event.preventDefault();
    const itemId = document.getElementById('manualTaskIdInput').value;
    const sharedPayload = {
      block_id: document.getElementById('manualTaskBlockInput').value ? Number(document.getElementById('manualTaskBlockInput').value) : null,
      title: document.getElementById('manualTaskTitleInput').value,
      description: document.getElementById('manualTaskDescriptionInput').value,
      due_date: document.getElementById('manualTaskDateInput').value,
      estimated_minutes: Number(document.getElementById('manualTaskMinutesInput').value || 60),
      priority: document.getElementById('manualTaskPriorityInput').value,
      status: document.getElementById('manualTaskStatusInput').value,
    };

    try {
      if (itemId) {
        await api(`/api/companies/${companyId}/work-journey/items/${itemId}`, { method: 'PATCH', body: JSON.stringify(sharedPayload) });
      } else {
        await api(`/api/companies/${companyId}/work-journey/items/manual`, {
          method: 'POST',
          body: JSON.stringify({ employee_id: selectedEmployeeId(), ...sharedPayload }),
        });
      }
      resetManualTaskForm();
      await Promise.all([loadBoard(), loadTransfers()]);
      toast('Tarefa avulsa salva com sucesso.');
    } catch (error) {
      toast(error.message);
    }
  }

  async function deleteManualTask(itemId) {
    if (!window.confirm('Excluir esta tarefa avulsa?')) return;
    try {
      await api(`/api/companies/${companyId}/work-journey/items/${itemId}`, { method: 'DELETE' });
      await Promise.all([loadBoard(), loadTransfers()]);
      toast('Tarefa avulsa excluída.');
    } catch (error) {
      toast(error.message);
    }
  }

  async function createTransfer(itemId) {
    const options = bootstrap.employees.filter((employee) => employee.id !== selectedEmployeeId()).map((employee) => `${employee.id}: ${employee.name}`).join('\n');
    const toEmployeeId = Number(window.prompt(`Transferir para qual colaborador?\n${options}`));
    if (!toEmployeeId) return;
    const reason = window.prompt('Motivo da transferência:', '') || '';
    try {
      await api(`/api/companies/${companyId}/work-journey/items/${itemId}/transfer`, { method: 'POST', body: JSON.stringify({ to_employee_id: toEmployeeId, reason }) });
      await loadTransfers();
      toast('Solicitação de transferência registrada.');
    } catch (error) {
      toast(error.message);
    }
  }

  async function approveTransfer(id) {
    const resolution_notes = window.prompt('Notas da aprovação:', '') || '';
    try {
      await api(`/api/companies/${companyId}/work-journey/transfers/${id}/approve`, { method: 'POST', body: JSON.stringify({ resolution_notes }) });
      await Promise.all([loadTransfers(), loadBoard(), loadAbsences()]);
    } catch (error) {
      toast(error.message);
    }
  }

  async function approveAbsence(id) {
    const cleanup_notes = window.prompt('Notas da aprovação/limpeza do período:', '') || '';
    try {
      await api(`/api/companies/${companyId}/work-journey/absences/${id}/approve`, { method: 'POST', body: JSON.stringify({ cleanup_notes }) });
      await loadAbsences();
    } catch (error) {
      toast(error.message);
    }
  }

  async function deleteBlock(id) {
    if (!window.confirm('Excluir este bloco?')) return;
    try {
      await api(`/api/companies/${companyId}/work-journey/blocks/${id}`, { method: 'DELETE' });
      resetBlockForm();
      await Promise.all([loadBlocks(), loadBoard()]);
      document.dispatchEvent(new CustomEvent('workJourney:refreshed'));
    } catch (error) {
      toast(error.message);
    }
  }

  async function loadBoard() {
    const json = await api(`/api/companies/${companyId}/work-journey/board?employee_id=${selectedEmployeeId()}&date=${selectedDate()}&scope=${scopeSelect.value}`);
    state.board = json.data;
    renderSummary();
    renderBoard();
  }

  async function loadBlocks() {
    const json = await api(`/api/companies/${companyId}/work-journey/blocks?employee_id=${selectedEmployeeId()}`);
    state.blocks = json.blocks;
    renderBlocksList();
  }

  async function loadAbsences() {
    const json = await api(`/api/companies/${companyId}/work-journey/absences?employee_id=${selectedEmployeeId()}`);
    state.absences = json.absences;
    renderAbsences();
  }

  async function loadTransfers() {
    const json = await api(`/api/companies/${companyId}/work-journey/transfers?employee_id=${selectedEmployeeId()}`);
    state.transfers = json.transfers;
    renderTransfers();
  }

  async function refreshAll() {
    try {
      await Promise.all([loadBlocks(), loadAbsences(), loadTransfers()]);
      await loadBoard();
      document.dispatchEvent(new CustomEvent('workJourney:refreshed'));
    } catch (error) {
      toast(error.message);
    }
  }

  document.getElementById('journeyRefreshBtn').addEventListener('click', refreshAll);
  document.getElementById('manualTaskStartBtn').addEventListener('click', () => openManualTaskForm());
  document.getElementById('manualTaskCancelBtn').addEventListener('click', resetManualTaskForm);
  manualTaskForm.addEventListener('submit', saveManualTask);
  employeeSelect.addEventListener('change', () => {
    resetManualTaskForm();
    refreshAll();
  });
  dateInput.addEventListener('change', () => {
    if (!document.getElementById('manualTaskIdInput').value) {
      document.getElementById('manualTaskDateInput').value = selectedDate();
    }
    loadBoard();
  });
  scopeSelect.addEventListener('change', loadBoard);
  document.getElementById('blockCancelBtn').addEventListener('click', resetBlockForm);

  document.getElementById('journeyBlockForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      employee_id: selectedEmployeeId(),
      name: document.getElementById('blockNameInput').value,
      description: document.getElementById('blockDescriptionInput').value,
      start_time: document.getElementById('blockStartInput').value,
      end_time: document.getElementById('blockEndInput').value,
      block_mode: document.getElementById('blockModeInput').value,
      weekdays: collectCheckedValues('blockWeekdaysGroup', true),
      accepted_item_types: collectCheckedValues('blockTypesGroup'),
      order_index: state.blocks.length,
      is_active: true,
    };
    const blockId = document.getElementById('blockIdInput').value;
    try {
      await api(`/api/companies/${companyId}/work-journey/blocks${blockId ? `/${blockId}` : ''}`, { method: blockId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      resetBlockForm();
      await Promise.all([loadBlocks(), loadBoard()]);
      document.dispatchEvent(new CustomEvent('workJourney:refreshed'));
    } catch (error) {
      toast(error.message);
    }
  });

  document.getElementById('journeyAbsenceForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      employee_id: selectedEmployeeId(),
      absence_type: document.getElementById('absenceTypeInput').value,
      start_date: document.getElementById('absenceStartInput').value,
      end_date: document.getElementById('absenceEndInput').value,
      reason: document.getElementById('absenceReasonInput').value,
    };
    try {
      await api(`/api/companies/${companyId}/work-journey/absences`, { method: 'POST', body: JSON.stringify(payload) });
      document.getElementById('journeyAbsenceForm').reset();
      await loadAbsences();
    } catch (error) {
      toast(error.message);
    }
  });

  renderTabs();
  resetBlockForm();
  resetManualTaskForm();
  refreshAll();
})();
