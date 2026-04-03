(() => {
  const bootstrap = window.workJourneyBootstrap || {};
  const companyId = bootstrap.companyId;
  const employeeSelect = document.getElementById('journeyEmployeeSelect');
  const dateInput = document.getElementById('journeyDateInput');
  const scopeSelect = document.getElementById('journeyScopeSelect');

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
    rules: [],
    absences: [],
    transfers: [],
  };

  function selectedEmployeeId() {
    return parseInt(employeeSelect.value, 10) || null;
  }

  function selectedDate() {
    return dateInput.value || bootstrap.today;
  }

  function renderSummary() {
    const summary = state.board?.summary;
    const container = document.getElementById('journeySummaryCards');
    if (!summary) {
      container.innerHTML = '';
      return;
    }
    container.innerHTML = [
      ['Capacidade do dia', formatMinutes(summary.daily_capacity_minutes)],
      ['Carga planejada', formatMinutes(summary.planned_minutes)],
      ['Carga realizada', formatMinutes(summary.worked_minutes)],
      ['Sobrecarga', formatMinutes(summary.overload_minutes)],
      ['Pendentes', summary.pending_count],
      ['Concluídas', summary.completed_count],
    ].map(([label, value]) => `
      <div class="journey-summary-card">
        <span class="text-secondary">${label}</span>
        <strong class="${label === 'Sobrecarga' && Number(summary.overload_minutes || 0) > 0 ? 'journey-overload' : ''}">${value}</strong>
      </div>
    `).join('');
  }

  function itemBadges(item) {
    const badges = [
      `<span class="badge-pill">${item.item_type_label || item.item_type}</span>`,
      `<span class="badge-pill ${item.status === 'completed' ? 'badge-pill--success' : item.is_overdue ? 'badge-pill--danger' : 'badge-pill--warning'}">${item.status_label || item.status}</span>`,
      item.recurrence_type ? `<span class="badge-pill">${item.recurrence_type}</span>` : '',
      item.estimated_minutes ? `<span class="badge-pill">${formatMinutes(item.estimated_minutes)}</span>` : '',
    ];
    return badges.join('');
  }

  function itemActions(item) {
    const worked = item.worked_minutes || 0;
    return `
      <div class="journey-item-card__actions">
        <button class="btn btn-secondary btn-sm" data-action="start-item" data-id="${item.id}">Iniciar</button>
        <button class="btn btn-secondary btn-sm" data-action="complete-item" data-id="${item.id}" data-worked="${worked}">Concluir</button>
        <button class="btn btn-secondary btn-sm" data-action="move-item" data-id="${item.id}">Mover bloco</button>
        <button class="btn btn-secondary btn-sm" data-action="transfer-item" data-id="${item.id}">Transferir</button>
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
            <div class="journey-block__meta">${block.start_time} → ${block.end_time} · Planejado ${formatMinutes(block.planned_minutes)} / Capacidade ${formatMinutes(block.capacity_minutes)}</div>
          </div>
          <div class="journey-badges">${block.planned_minutes > block.capacity_minutes ? '<span class="badge-pill badge-pill--danger">Acima da capacidade</span>' : '<span class="badge-pill badge-pill--success">Dentro da capacidade</span>'}</div>
        </div>
        <div class="journey-block__items">${(block.items || []).length ? block.items.map(itemCard).join('') : '<div class="journey-item-empty">Nenhuma atividade sugerida para este bloco.</div>'}</div>
      </section>
    `).join('') : '<div class="journey-item-empty">Nenhum bloco ativo para o dia selecionado.</div>';

    unassignedContainer.innerHTML = unassigned.length ? unassigned.map(itemCard).join('') : '<div class="journey-item-empty">Sem pendências fora dos blocos.</div>';

    const periodItems = state.board?.period_items || [];
    periodContainer.innerHTML = periodItems.length ? periodItems.slice(0, 12).map((item) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <strong>${item.title}</strong>
          <span class="badge-pill">${item.due_date || item.occurrence_date || '-'}</span>
        </div>
        <div class="journey-badges">${itemBadges(item)}</div>
      </div>
    `).join('') : '<div class="journey-item-empty">Sem atividades no período.</div>';

    bindItemActions();
  }

  function renderBlocksList() {
    const container = document.getElementById('journeyBlocksList');
    const options = ['<option value="">Sem preferência</option>', ...state.blocks.map((block) => `<option value="${block.id}">${block.name}</option>`)].join('');
    document.getElementById('ruleBlockInput').innerHTML = options;

    container.innerHTML = state.blocks.length ? state.blocks.map((block) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${block.name}</strong>
            <div class="text-secondary small">${block.start_time} → ${block.end_time}</div>
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

  function renderRulesList() {
    const container = document.getElementById('journeyRulesList');
    container.innerHTML = state.rules.length ? state.rules.map((rule) => `
      <div class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${rule.title}</strong>
            <div class="text-secondary small">${rule.recurrence_type} · ${formatMinutes(rule.estimated_minutes)}</div>
          </div>
          <div class="journey-item-card__actions">
            <button class="btn btn-secondary btn-sm" data-action="edit-rule" data-id="${rule.id}">Editar</button>
            <button class="btn btn-secondary btn-sm" data-action="delete-rule" data-id="${rule.id}">Excluir</button>
          </div>
        </div>
      </div>
    `).join('') : '<div class="journey-item-empty">Nenhuma obrigação cadastrada.</div>';

    container.querySelectorAll('[data-action="edit-rule"]').forEach((btn) => btn.addEventListener('click', () => populateRuleForm(Number(btn.dataset.id))));
    container.querySelectorAll('[data-action="delete-rule"]').forEach((btn) => btn.addEventListener('click', () => deleteRule(Number(btn.dataset.id))));
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
            <strong>${transfer.item?.title || 'Atividade'}</strong>
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
    renderCheckboxGrid('blockWeekdaysGroup', weekdays, block.weekdays || []);
    renderCheckboxGrid('blockTypesGroup', itemTypes, block.accepted_item_types || []);
  }

  function resetBlockForm() {
    document.getElementById('journeyBlockForm').reset();
    document.getElementById('blockIdInput').value = '';
    renderCheckboxGrid('blockWeekdaysGroup', weekdays, [0, 1, 2, 3, 4]);
    renderCheckboxGrid('blockTypesGroup', itemTypes, itemTypes.map((item) => item.value));
  }

  function recurrenceConfigToForm(rule) {
    const type = document.getElementById('ruleRecurrenceInput').value;
    const config = rule?.recurrence_config || {};
    const container = document.getElementById('ruleConfigContainer');
    if (type === 'weekly') {
      container.innerHTML = `<div class="journey-checkbox-grid" id="ruleWeeklyGroup"></div>`;
      renderCheckboxGrid('ruleWeeklyGroup', weekdays, config.weekdays || [0]);
      return;
    }
    if (type === 'monthly') {
      container.innerHTML = `<input id="ruleMonthlyDaysInput" class="form-control" placeholder="Ex.: 2,10,20" value="${(config.days || []).join(',')}">`;
      return;
    }
    if (type === 'annual') {
      container.innerHTML = `
        <div class="journey-inline-grid">
          <div class="form-group"><label class="form-label">Início MM-DD</label><input id="ruleAnnualStartInput" class="form-control" value="${config.start_mmdd || ''}" placeholder="11-01"></div>
          <div class="form-group"><label class="form-label">Fim MM-DD</label><input id="ruleAnnualEndInput" class="form-control" value="${config.end_mmdd || ''}" placeholder="11-15"></div>
        </div>`;
      return;
    }
    if (type === 'sporadic') {
      container.innerHTML = `
        <div class="journey-inline-grid">
          <div class="form-group"><label class="form-label">Data única</label><input id="ruleSpecificDateInput" type="date" class="form-control" value="${config.date || ''}"></div>
          <div class="form-group"><label class="form-label">Intervalo opcional</label><input id="ruleSpecificStartInput" type="date" class="form-control" value="${config.start_date || ''}"></div>
        </div>
        <div class="form-group"><label class="form-label">Fim do intervalo</label><input id="ruleSpecificEndInput" type="date" class="form-control" value="${config.end_date || ''}"></div>`;
      return;
    }
    container.innerHTML = '<div class="journey-item-empty">Diária não exige configuração adicional.</div>';
  }

  function ruleConfigFromForm() {
    const type = document.getElementById('ruleRecurrenceInput').value;
    if (type === 'weekly') return { weekdays: collectCheckedValues('ruleWeeklyGroup', true) };
    if (type === 'monthly') return { days: (document.getElementById('ruleMonthlyDaysInput').value || '').split(',').map((item) => Number(item.trim())).filter(Boolean) };
    if (type === 'annual') return { start_mmdd: document.getElementById('ruleAnnualStartInput').value, end_mmdd: document.getElementById('ruleAnnualEndInput').value };
    if (type === 'sporadic') return { date: document.getElementById('ruleSpecificDateInput').value, start_date: document.getElementById('ruleSpecificStartInput').value, end_date: document.getElementById('ruleSpecificEndInput').value };
    return {};
  }

  function populateRuleForm(id) {
    const rule = state.rules.find((item) => item.id === id);
    if (!rule) return;
    document.getElementById('ruleIdInput').value = rule.id;
    document.getElementById('ruleTitleInput').value = rule.title;
    document.getElementById('ruleDescriptionInput').value = rule.description || '';
    document.getElementById('ruleItemTypeInput').value = rule.item_type;
    document.getElementById('ruleRecurrenceInput').value = rule.recurrence_type;
    document.getElementById('ruleMinutesInput').value = rule.estimated_minutes;
    document.getElementById('rulePriorityInput').value = rule.priority;
    document.getElementById('ruleStartDateInput').value = rule.start_date || '';
    document.getElementById('ruleEndDateInput').value = rule.end_date || '';
    document.getElementById('ruleBlockInput').value = rule.preferred_block_id || '';
    recurrenceConfigToForm(rule);
  }

  function resetRuleForm() {
    document.getElementById('journeyRuleForm').reset();
    document.getElementById('ruleIdInput').value = '';
    recurrenceConfigToForm();
  }

  function bindItemActions() {
    document.querySelectorAll('[data-action="start-item"]').forEach((btn) => btn.addEventListener('click', () => patchItem(Number(btn.dataset.id), { status: 'in_progress' })));
    document.querySelectorAll('[data-action="complete-item"]').forEach((btn) => btn.addEventListener('click', () => {
      const worked = Number(window.prompt('Minutos realizados:', btn.dataset.worked || '60'));
      patchItem(Number(btn.dataset.id), { status: 'completed', worked_minutes: Number.isFinite(worked) ? worked : 0 });
    }));
    document.querySelectorAll('[data-action="move-item"]').forEach((btn) => btn.addEventListener('click', () => {
      const options = state.blocks.map((block) => `${block.id}:${block.name}`).join('\n');
      const choice = window.prompt(`Informe o ID do bloco desejado:\n${options}`);
      if (!choice) return;
      patchItem(Number(btn.dataset.id), { block_id: Number(choice) });
    }));
    document.querySelectorAll('[data-action="transfer-item"]').forEach((btn) => btn.addEventListener('click', () => createTransfer(Number(btn.dataset.id))));
  }

  async function patchItem(itemId, payload) {
    try {
      await api(`/api/companies/${companyId}/work-journey/items/${itemId}`, { method: 'PATCH', body: JSON.stringify(payload) });
      await loadBoard();
      await loadTransfers();
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
    } catch (error) {
      toast(error.message);
    }
  }

  async function deleteRule(id) {
    if (!window.confirm('Excluir esta obrigação?')) return;
    try {
      await api(`/api/companies/${companyId}/work-journey/rules/${id}`, { method: 'DELETE' });
      resetRuleForm();
      await Promise.all([loadRules(), loadBoard()]);
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

  async function loadRules() {
    const json = await api(`/api/companies/${companyId}/work-journey/rules?employee_id=${selectedEmployeeId()}`);
    state.rules = json.rules;
    renderRulesList();
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
      await Promise.all([loadBlocks(), loadRules(), loadAbsences(), loadTransfers()]);
      await loadBoard();
    } catch (error) {
      toast(error.message);
    }
  }

  document.getElementById('journeyRefreshBtn').addEventListener('click', refreshAll);
  employeeSelect.addEventListener('change', refreshAll);
  scopeSelect.addEventListener('change', loadBoard);
  document.getElementById('blockCancelBtn').addEventListener('click', resetBlockForm);
  document.getElementById('ruleCancelBtn').addEventListener('click', resetRuleForm);
  document.getElementById('ruleRecurrenceInput').addEventListener('change', () => recurrenceConfigToForm());

  document.getElementById('journeyBlockForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      employee_id: selectedEmployeeId(),
      name: document.getElementById('blockNameInput').value,
      description: document.getElementById('blockDescriptionInput').value,
      start_time: document.getElementById('blockStartInput').value,
      end_time: document.getElementById('blockEndInput').value,
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
    } catch (error) {
      toast(error.message);
    }
  });

  document.getElementById('journeyRuleForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      employee_id: selectedEmployeeId(),
      preferred_block_id: document.getElementById('ruleBlockInput').value ? Number(document.getElementById('ruleBlockInput').value) : null,
      title: document.getElementById('ruleTitleInput').value,
      description: document.getElementById('ruleDescriptionInput').value,
      item_type: document.getElementById('ruleItemTypeInput').value,
      recurrence_type: document.getElementById('ruleRecurrenceInput').value,
      recurrence_config: ruleConfigFromForm(),
      estimated_minutes: Number(document.getElementById('ruleMinutesInput').value || 60),
      priority: document.getElementById('rulePriorityInput').value,
      start_date: document.getElementById('ruleStartDateInput').value || null,
      end_date: document.getElementById('ruleEndDateInput').value || null,
      is_active: true,
    };
    const ruleId = document.getElementById('ruleIdInput').value;
    try {
      await api(`/api/companies/${companyId}/work-journey/rules${ruleId ? `/${ruleId}` : ''}`, { method: ruleId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      resetRuleForm();
      await Promise.all([loadRules(), loadBoard()]);
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
  resetRuleForm();
  refreshAll();
})();
