(function () {
  const root = document.getElementById('processRuntimeShell');
  if (!root) return;

  const instanceId = root.dataset.instanceId;
  const processId = root.dataset.processId;
  const runtimeStatusLabel = document.getElementById('runtimeStatusLabel');
  const runtimeStartedAt = document.getElementById('runtimeStartedAt');
  const runtimeCompletedAt = document.getElementById('runtimeCompletedAt');
  const runtimeCurrentElement = document.getElementById('runtimeCurrentElement');
  const runtimeTimeline = document.getElementById('runtimeTimeline');
  const runtimeCurrentActivity = document.getElementById('runtimeCurrentActivity');
  const runtimeFlowMeta = document.getElementById('runtimeFlowMeta');
  const runtimeEmpty = document.getElementById('runtimeFlowEmpty');
  const btnPause = document.getElementById('btnPauseRuntime');
  const btnResume = document.getElementById('btnResumeRuntime');
  const btnRefresh = document.getElementById('btnRefreshRuntime');
  const btnRefreshSecondary = document.getElementById('btnRefreshRuntimeSecondary');

  let viewer = null;
  let appliedMarkers = [];
  let routinesByElementId = new Map();
  let latestRuntime = null;

  const markerMap = {
    completed: 'is-completed',
    in_progress: 'is-active',
    pending: 'is-pending',
    paused: 'is-paused',
    waiting_external: 'is-waiting-external',
    failed: 'is-failed',
    skipped: 'is-skipped',
    ready: 'is-ready'
  };

  function formatDateTime(value, fallback = '—') {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('pt-BR');
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getBpmnCtor() {
    return window.BpmnJS || window.BpmnModeler;
  }

  async function fetchRuntime() {
    const res = await fetch(`/api/process-instances/${instanceId}/runtime`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) throw new Error(`Falha ao carregar runtime (${res.status})`);
    return res.json();
  }

  async function fetchRoutines() {
    const res = await fetch(`/api/process-routines?process_id=${processId}`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) return [];
    return res.json();
  }

  async function ensureViewer(xml) {
    if (!xml) return null;
    const BpmnCtor = getBpmnCtor();
    if (!BpmnCtor) throw new Error('Biblioteca BPMN local não foi carregada.');
    if (!viewer) {
      viewer = new BpmnCtor({
        container: '#runtimeBpmnCanvas',
        keyboard: { bindTo: document }
      });
    }
    await viewer.importXML(xml);
    viewer.get('canvas').zoom('fit-viewport', 'auto');
    return viewer;
  }

  function clearMarkers() {
    if (!viewer) return;
    const canvas = viewer.get('canvas');
    appliedMarkers.forEach(({ elementId, marker }) => {
      try {
        canvas.removeMarker(elementId, marker);
      } catch (e) {
        // noop
      }
    });
    appliedMarkers = [];
  }

  function addMarker(elementId, marker) {
    if (!viewer || !elementId || !marker) return;
    const canvas = viewer.get('canvas');
    canvas.addMarker(elementId, marker);
    appliedMarkers.push({ elementId, marker });
  }

  function applyOverlay(overlay) {
    if (!viewer || !overlay) return;
    clearMarkers();

    (overlay.elements || []).forEach((item) => {
      const marker = markerMap[item.status] || 'is-pending';
      addMarker(item.bpmn_element_id, marker);
    });

    if (overlay.current_bpmn_element_id) {
      const currentAlreadyMarked = (overlay.elements || []).some(
        (item) => item.bpmn_element_id === overlay.current_bpmn_element_id && item.status === 'in_progress'
      );
      if (!currentAlreadyMarked && overlay.status !== 'completed') {
        addMarker(overlay.current_bpmn_element_id, overlay.status === 'paused' ? 'is-paused' : 'is-active');
      }

      const canvas = viewer.get('canvas');
      const elementRegistry = viewer.get('elementRegistry');
      const element = elementRegistry.get(overlay.current_bpmn_element_id);
      if (element && typeof canvas.scrollToElement === 'function') {
        canvas.scrollToElement(element);
      }
    }
  }

  function renderHeader(overlay) {
    if (runtimeStatusLabel) {
      runtimeStatusLabel.textContent = overlay.status || 'pending';
      runtimeStatusLabel.className = `badge runtime-badge status-${overlay.status || 'pending'}`;
    }
    if (runtimeStartedAt) runtimeStartedAt.textContent = formatDateTime(overlay.started_at);
    if (runtimeCompletedAt) runtimeCompletedAt.textContent = formatDateTime(overlay.completed_at);
    if (runtimeCurrentElement) runtimeCurrentElement.textContent = overlay.current_bpmn_element_id || 'Sem ponteiro BPMN';

    if (btnPause) btnPause.hidden = overlay.status === 'paused' || overlay.status === 'completed';
    if (btnResume) btnResume.hidden = overlay.status !== 'paused';
  }

  function renderCurrentActivity(runtime) {
    if (!runtimeCurrentActivity) return;
    const overlay = runtime.overlay || {};
    const payload = runtime.current_activity || {};
    const currentId = payload.element_id || overlay.current_bpmn_element_id;
    const execution = payload.execution || (overlay.elements || []).find((item) => item.bpmn_element_id === currentId)
      || (overlay.elements || []).find((item) => item.status === 'in_progress')
      || null;
    const routine = payload.routine || (currentId ? routinesByElementId.get(currentId) : null);
    const contract = payload.contract || null;
    const action = payload.action || {};
    const nextCandidates = Array.isArray(payload.next_candidates) ? payload.next_candidates : [];

    if (!currentId && !execution && !routine) {
      runtimeCurrentActivity.innerHTML = `
        <div class="runtime-empty-card">
          <strong>Nenhuma atividade corrente definida.</strong>
          <span>Esta instância ainda não recebeu um ponteiro de execução BPMN.</span>
        </div>
      `;
      return;
    }

    const actionButtons = [];
    if (action.internal_url) {
      actionButtons.push(`<a class="btn btn-primary btn-sm" href="${escapeHtml(action.internal_url)}">${escapeHtml(action.action_label || 'Abrir tela')}</a>`);
    } else if (action.external_url) {
      actionButtons.push(`<a class="btn btn-primary btn-sm" href="${escapeHtml(action.external_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(action.action_label || 'Abrir link externo')}</a>`);
    }
    if (action.can_start) {
      actionButtons.push(`<button type="button" class="btn btn-secondary btn-sm" data-runtime-action="start">Iniciar atividade</button>`);
    }
    if (action.can_mark_waiting) {
      actionButtons.push(`<button type="button" class="btn btn-outline btn-sm" data-runtime-action="waiting">Aguardar externo</button>`);
    }
    if (action.can_complete) {
      actionButtons.push(`<button type="button" class="btn btn-secondary btn-sm" data-runtime-action="complete">Concluir</button>`);
    }
    if (action.can_fail) {
      actionButtons.push(`<button type="button" class="btn btn-outline btn-sm" data-runtime-action="fail">Marcar falha</button>`);
    }

    const nextHtml = nextCandidates.length
      ? nextCandidates.map((candidate) => `
          <div class="runtime-next-item">
            <strong>${escapeHtml(candidate.element_name || candidate.element_id || 'Próxima etapa')}</strong>
            <span>${escapeHtml(candidate.element_type || 'BPMN')}</span>
          </div>
        `).join('')
      : '<div class="runtime-next-item runtime-next-item--empty"><strong>Próxima etapa ainda não inferida</strong><span>O shell continuará controlando a execução pela atividade corrente.</span></div>';

    runtimeCurrentActivity.innerHTML = `
      <div class="runtime-activity-card">
        <div class="runtime-activity-head">
          <div>
            <strong>${escapeHtml(payload.element_name || (execution && execution.bpmn_element_name) || (routine && routine.name) || currentId)}</strong>
            <div class="runtime-activity-sub">${escapeHtml(currentId || 'Sem identificador')}</div>
          </div>
          <span class="badge runtime-badge status-${escapeHtml((execution && execution.status) || overlay.status || 'pending')}">
            ${escapeHtml((execution && execution.status) || overlay.status || 'pending')}
          </span>
        </div>
        <div class="runtime-activity-body">
          <div><span>Modo:</span><strong>${escapeHtml(action.execution_mode_label || (execution && execution.execution_mode) || 'human_task')}</strong></div>
          <div><span>Início:</span><strong>${escapeHtml(formatDateTime(execution && execution.started_at))}</strong></div>
          <div><span>Conclusão:</span><strong>${escapeHtml(formatDateTime(execution && execution.completed_at))}</strong></div>
        </div>
        ${(routine && routine.description) ? `<p class="runtime-activity-description">${escapeHtml(routine.description)}</p>` : ''}
        ${action.instruction ? `<div class="runtime-activity-callout"><strong>Como executar</strong><p>${escapeHtml(action.instruction)}</p></div>` : ''}
        <div class="runtime-contract-grid">
          <div><span>Capability</span><strong>${escapeHtml(action.capability_key || 'Não configurada')}</strong></div>
          <div><span>Contrato BPMS</span><strong>${escapeHtml(contract ? `#${contract.id}` : 'Não configurado')}</strong></div>
          <div><span>SLA</span><strong>${escapeHtml(action.sla_minutes ? `${action.sla_minutes} min` : 'Não definido')}</strong></div>
          <div><span>Gate humano</span><strong>${action.requires_human_gate ? 'Sim' : 'Não'}</strong></div>
        </div>
        ${actionButtons.length ? `<div class="runtime-action-row">${actionButtons.join('')}</div>` : ''}
        <div class="runtime-next-stack">
          <h4>Próximas etapas possíveis</h4>
          ${nextHtml}
        </div>
      </div>
    `;

    runtimeCurrentActivity.querySelectorAll('[data-runtime-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          await handleExecutionAction(button.dataset.runtimeAction, payload, execution, action);
        } catch (error) {
          console.error('[process-instance-runtime] action error', error);
          window.alert(error.message || 'Erro ao executar ação BPMS.');
        }
      });
    });
  }

  function renderTimeline(runtime) {
    if (!runtimeTimeline) return;
    const timeline = runtime.timeline || [];
    if (!timeline.length) {
      runtimeTimeline.innerHTML = `
        <div class="runtime-empty-card">
          <strong>Sem timeline ainda.</strong>
          <span>Os eventos da execução aparecerão aqui conforme a instância avançar.</span>
        </div>
      `;
      return;
    }

    runtimeTimeline.innerHTML = timeline.map((item) => `
      <div class="runtime-timeline-item">
        <div class="runtime-timeline-dot"></div>
        <div>
          <strong>${escapeHtml(item.label || item.kind)}</strong>
          <div class="runtime-timeline-time">${escapeHtml(formatDateTime(item.timestamp))}</div>
          ${(item.details && item.details.reason) ? `<p>${escapeHtml(item.details.reason)}</p>` : ''}
        </div>
      </div>
    `).join('');
  }

  function renderFlowMeta(runtime) {
    if (!runtimeFlowMeta) return;
    const diagram = runtime.diagram || {};
    if (!diagram || !diagram.id) {
      runtimeFlowMeta.textContent = 'Processo sem BPMN publicado. Controle manual continua disponível.';
      if (runtimeEmpty) runtimeEmpty.hidden = false;
      return;
    }
    runtimeFlowMeta.textContent = `Fluxo BPMN v${diagram.version || '—'} carregado para acompanhamento visual.`;
    if (runtimeEmpty) runtimeEmpty.hidden = true;
  }

  async function refreshRuntime() {
    const [runtime, routines] = await Promise.all([fetchRuntime(), fetchRoutines()]);
    latestRuntime = runtime;
    routinesByElementId = new Map(
      (routines || [])
        .filter((item) => item && item.bpmn_element_id)
        .map((item) => [item.bpmn_element_id, item])
    );

    renderHeader(runtime.overlay || {});
    renderFlowMeta(runtime);
    renderCurrentActivity(runtime);
    renderTimeline(runtime);

    if (runtime.diagram && runtime.diagram.bpmn_xml) {
      await ensureViewer(runtime.diagram.bpmn_xml);
      applyOverlay(runtime.overlay || {});
    } else if (runtimeEmpty) {
      runtimeEmpty.hidden = false;
    }

    return runtime;
  }

  async function createExecution(payload) {
    const res = await fetch(`/api/process-instances/${instanceId}/executions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao criar execução (${res.status})`);
    }
    return res.json();
  }

  async function updateExecution(executionId, payload) {
    const res = await fetch(`/api/process-instances/${instanceId}/executions/${executionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao atualizar execução (${res.status})`);
    }
    return res.json();
  }

  async function handleExecutionAction(actionName, currentPayload, execution, actionMeta) {
    const payload = currentPayload || {};
    const executionPayload = {
      bpmn_element_id: payload.element_id,
      bpmn_element_name: payload.element_name,
      bpmn_element_type: payload.element_type,
      execution_mode: actionMeta.execution_mode || 'human_task',
      interaction_mode: actionMeta.interaction_mode || null,
      capability_key: actionMeta.capability_key || null,
      handler_key: actionMeta.handler_key || null
    };

    if (actionName === 'start') {
      await createExecution({
        ...executionPayload,
        status: 'in_progress'
      });
    } else {
      if (!execution || !execution.id) {
        throw new Error('Nenhuma execução ativa encontrada para esta atividade.');
      }
      const statusMap = {
        waiting: 'waiting_external',
        complete: 'completed',
        fail: 'failed'
      };
      await updateExecution(execution.id, {
        status: statusMap[actionName] || execution.status
      });
    }
    await refreshRuntime();
  }

  async function postAction(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload || {})
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao executar ação (${res.status})`);
    }
    return res.json();
  }

  async function handlePause() {
    const reason = window.prompt('Motivo da pausa (opcional):', '');
    await postAction(`/api/process-instances/${instanceId}/pause`, { reason });
    await refreshRuntime();
  }

  async function handleResume() {
    await postAction(`/api/process-instances/${instanceId}/resume`, {});
    await refreshRuntime();
  }

  async function init() {
    try {
      await refreshRuntime();
    } catch (error) {
      console.error('[process-instance-runtime] init error', error);
      if (runtimeFlowMeta) {
        runtimeFlowMeta.textContent = `Erro ao carregar runtime BPMN: ${error.message}`;
      }
    }
  }

  if (btnPause) btnPause.addEventListener('click', handlePause);
  if (btnResume) btnResume.addEventListener('click', handleResume);
  if (btnRefresh) btnRefresh.addEventListener('click', () => refreshRuntime());
  if (btnRefreshSecondary) btnRefreshSecondary.addEventListener('click', () => refreshRuntime());

  init();
})();
