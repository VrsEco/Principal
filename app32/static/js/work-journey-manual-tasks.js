(() => {
  const bootstrap = window.workJourneyBootstrap || {};
  const companyId = bootstrap.companyId;
  const employeeSelect = document.getElementById('journeyEmployeeSelect');
  const listContainer = document.getElementById('journeyManualTasksList');
  const summaryContainer = document.getElementById('manualTasksSummary');
  const launchButton = document.getElementById('manualTaskTabStartBtn');
  const { api, formatMinutes, toast } = window.WorkJourneyUtils;

  function selectedEmployeeId() {
    return parseInt(employeeSelect?.value || '', 10) || null;
  }

  function renderSummary(summary = {}) {
    summaryContainer.innerHTML = [
      `<span class="badge-pill">Total ${summary.total_count || 0}</span>`,
      `<span class="badge-pill badge-pill--success">Concluídas ${summary.completed_count || 0}</span>`,
      `<span class="badge-pill badge-pill--warning">Pendentes ${summary.pending_count || 0}</span>`,
      `<span class="badge-pill">Previsto ${formatMinutes(summary.planned_minutes || 0)}</span>`,
      `<span class="badge-pill">Realizado ${formatMinutes(summary.worked_minutes || 0)}</span>`,
    ].join('');
  }

  function renderTasks(items = []) {
    if (!items.length) {
      listContainer.innerHTML = '<div class="journey-item-empty">Nenhuma tarefa avulsa cadastrada para este colaborador.</div>';
      return;
    }

    listContainer.innerHTML = items.map((item) => `
      <article class="journey-list-item">
        <div class="journey-list-item__top">
          <div>
            <strong>${item.title}</strong>
            <div class="journey-manual-task-meta">Prazo ${item.due_date || '-'} · ${item.block_name || 'Sem bloco'} · Previsto ${formatMinutes(item.estimated_minutes || 0)} · Realizado ${formatMinutes(item.worked_minutes || 0)}</div>
          </div>
          <div class="journey-item-card__actions">
            <button class="btn btn-secondary btn-sm" data-action="edit-manual-task" data-id="${item.id}">Editar</button>
            <button class="btn btn-secondary btn-sm" data-action="delete-manual-task" data-id="${item.id}">Excluir</button>
          </div>
        </div>
        <div class="journey-item-card__desc">${item.description || 'Sem descrição adicional.'}</div>
        <div class="journey-badges">
          <span class="badge-pill">${item.item_type_label || 'Tarefa Avulsa'}</span>
          <span class="badge-pill ${item.status === 'completed' ? 'badge-pill--success' : item.is_overdue ? 'badge-pill--danger' : 'badge-pill--warning'}">${item.status_label || item.status}</span>
          ${item.priority ? `<span class="badge-pill">${item.priority}</span>` : ''}
        </div>
      </article>
    `).join('');

    listContainer.querySelectorAll('[data-action="edit-manual-task"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const task = items.find((entry) => Number(entry.id) === Number(btn.dataset.id));
        window.WorkJourneyPage?.openManualTaskForm?.(task);
      });
    });

    listContainer.querySelectorAll('[data-action="delete-manual-task"]').forEach((btn) => {
      btn.addEventListener('click', () => window.WorkJourneyPage?.deleteManualTask?.(Number(btn.dataset.id)));
    });
  }

  async function loadManualTasks() {
    const employeeId = selectedEmployeeId();
    if (!employeeId || !listContainer || !summaryContainer) return;
    try {
      const response = await api(`/api/companies/${companyId}/work-journey/manual-tasks?employee_id=${employeeId}`);
      renderSummary(response.data?.summary || {});
      renderTasks(response.data?.items || []);
    } catch (error) {
      toast(error.message || 'Não foi possível carregar as tarefas avulsas.');
    }
  }

  launchButton?.addEventListener('click', () => window.WorkJourneyPage?.openManualTaskForm?.());
  employeeSelect?.addEventListener('change', loadManualTasks);
  document.addEventListener('workJourney:refreshed', loadManualTasks);
  loadManualTasks();
})();
