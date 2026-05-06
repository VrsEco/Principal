(() => {
  const bootstrap = window.workJourneyBootstrap || {};
  const { api, toast } = window.WorkJourneyUtils;
  const companyId = bootstrap.companyId;
  const employeeSelect = document.getElementById('journeyEmployeeSelect');
  const container = document.getElementById('journeyRoutineBindingsList');

  if (!companyId || !container) return;

  function selectedEmployeeId() {
    return parseInt(employeeSelect?.value || bootstrap.selectedEmployeeId || '', 10) || null;
  }

  function renderOptions(blocks, selectedId) {
    return ['<option value="">Não vincular agora</option>', ...blocks.map((block) => `
      <option value="${block.id}" ${Number(selectedId) === Number(block.id) ? 'selected' : ''}>
        ${block.name} · ${block.start_time} → ${block.end_time}
      </option>
    `)].join('');
  }

  function render(data) {
    const routines = data?.routines || [];
    const blocks = data?.available_blocks || [];
    if (!routines.length) {
      container.innerHTML = '<div class="journey-item-empty">Nenhuma rotina operacional vinculada ao colaborador selecionado.</div>';
      return;
    }

    container.innerHTML = routines.map((routine) => `
      <div class="journey-list-item">
        <div class="journey-binding-row">
          <div class="journey-binding-row__meta">
            <strong>${routine.process_code ? `${routine.process_code} · ` : ''}${routine.routine_name}</strong>
            <small>${routine.process_name || 'Sem processo associado'} · ${routine.schedule_type || 'sem frequência'} · ${routine.hours_used || 0}h</small>
            <div class="journey-badges">
              <span class="badge-pill">${routine.binding?.block_name || 'Sem bloco vinculado'}</span>
            </div>
          </div>
          <div>
            <select class="form-control" data-routine-binding-select="${routine.routine_id}">
              ${renderOptions(blocks, routine.binding?.block_id)}
            </select>
          </div>
          <div class="journey-item-card__actions" style="margin-top:0;">
            <button class="btn btn-primary btn-sm" data-action="save-routine-binding" data-routine-id="${routine.routine_id}">Salvar vínculo</button>
          </div>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('[data-action="save-routine-binding"]').forEach((button) => {
      button.addEventListener('click', () => saveBinding(Number(button.dataset.routineId)));
    });
  }

  async function load() {
    try {
      const employeeId = selectedEmployeeId();
      if (!employeeId) {
        container.innerHTML = '<div class="journey-item-empty">Selecione um colaborador para visualizar as rotinas encaixáveis.</div>';
        return;
      }
      const response = await api(`/api/companies/${companyId}/work-journey/process-routines?employee_id=${employeeId}`);
      render(response.data);
    } catch (error) {
      container.innerHTML = '<div class="journey-item-empty">Não foi possível carregar as rotinas do colaborador.</div>';
      toast(error.message);
    }
  }

  async function saveBinding(routineId) {
    const employeeId = selectedEmployeeId();
    const select = container.querySelector(`[data-routine-binding-select="${routineId}"]`);
    const blockId = select?.value ? Number(select.value) : null;
    try {
      await api(`/api/companies/${companyId}/work-journey/process-routines/${routineId}/binding`, {
        method: 'POST',
        body: JSON.stringify({ employee_id: employeeId, block_id: blockId, notes: '' }),
      });
      await load();
      document.dispatchEvent(new CustomEvent('workJourney:refreshed'));
    } catch (error) {
      toast(error.message);
    }
  }

  employeeSelect?.addEventListener('change', load);
  document.addEventListener('workJourney:refreshed', load);
  load();
})();
