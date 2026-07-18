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
  const runtimeFlowEmpty = document.getElementById('runtimeFlowEmpty');
  const runtimeProcessIndicators = document.getElementById('runtimeProcessIndicators');

  const btnPause = document.getElementById('btnPauseRuntime');
  const btnResume = document.getElementById('btnResumeRuntime');
  const btnRefresh = document.getElementById('btnRefreshRuntime');
  const btnRefreshSecondary = document.getElementById('btnRefreshRuntimeSecondary');

  let viewer = null;
  let appliedMarkers = [];
  let latestRuntime = null;

  const currentMarkerMap = {
    in_progress: 'is-active',
    paused: 'is-paused',
    waiting_external: 'is-waiting-external',
    failed: 'is-failed'
  };

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDateTime(value, fallback = '—') {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || fallback);
    return date.toLocaleString('pt-BR');
  }

  function formatIndicatorValue(value, unit) {
    if (value === null || value === undefined || value === '') return '—';
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return String(value);
    const formatted = Number.isInteger(numeric) ? numeric.toString() : numeric.toFixed(1).replace('.', ',');
    return unit ? `${formatted}${unit === '%' ? '%' : ` ${unit}`}` : formatted;
  }

  function farolLabel(farol) {
    switch (farol) {
      case 'green':
        return 'Dentro da meta';
      case 'yellow':
        return 'Atenção';
      case 'red':
        return 'Abaixo da meta';
      default:
        return 'Sem leitura';
    }
  }

  function getBpmnCtor() {
    return window.BpmnJS || window.BpmnModeler;
  }

  async function fetchRuntime() {
    const response = await fetch(`/api/process-instances/${instanceId}/runtime`, {
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`Falha ao carregar runtime (${response.status})`);
    }
    return response.json();
  }

  async function ensureViewer(xml) {
    if (!xml) return null;
    const BpmnCtor = getBpmnCtor();
    if (!BpmnCtor) throw new Error('Biblioteca BPMN não carregada.');
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
      } catch (error) {
        // noop
      }
    });
    appliedMarkers = [];
  }

  function addMarker(elementId, marker) {
    if (!viewer || !elementId || !marker) return;
    viewer.get('canvas').addMarker(elementId, marker);
    appliedMarkers.push({ elementId, marker });
  }

  function applyOverlay(overlay) {
    if (!viewer) return;
    clearMarkers();

    const currentElementId = overlay?.current_bpmn_element_id;
    if (!currentElementId) return;

    const currentExecution = (overlay?.elements || []).find((item) => item.bpmn_element_id === currentElementId)
      || (overlay?.elements || []).find((item) => item.status === 'in_progress');
    const marker = currentMarkerMap[currentExecution?.status] || currentMarkerMap[overlay?.status] || 'is-active';
    addMarker(currentElementId, marker);

    const elementRegistry = viewer.get('elementRegistry');
    const canvas = viewer.get('canvas');
    const element = elementRegistry.get(currentElementId);
    if (element && typeof canvas.scrollToElement === 'function') {
      canvas.scrollToElement(element);
    }
  }

  function renderFlowMeta(runtime) {
    const diagram = runtime?.diagram || {};
    if (!diagram.id || !diagram.bpmn_xml) {
      runtimeFlowMeta.textContent = 'Processo sem BPMN publicado. A shell continua disponível em modo manual.';
      if (runtimeFlowEmpty) runtimeFlowEmpty.hidden = false;
      return;
    }
    runtimeFlowMeta.textContent = `Fluxo BPMN publicado v${diagram.version || '—'} carregado para acompanhamento operacional.`;
    if (runtimeFlowEmpty) runtimeFlowEmpty.hidden = true;
  }

  function renderHeader(runtime) {
    const overlay = runtime?.overlay || {};
    if (runtimeStatusLabel) {
      runtimeStatusLabel.textContent = overlay.status || 'pending';
      runtimeStatusLabel.className = `badge status-${overlay.status || 'pending'}`;
    }
    if (runtimeStartedAt) runtimeStartedAt.textContent = formatDateTime(overlay.started_at);
    if (runtimeCompletedAt) runtimeCompletedAt.textContent = formatDateTime(overlay.completed_at);
    if (runtimeCurrentElement) runtimeCurrentElement.textContent = overlay.current_bpmn_element_id || '—';

    if (btnPause) btnPause.hidden = overlay.status === 'paused' || overlay.status === 'completed';
    if (btnResume) btnResume.hidden = overlay.status !== 'paused';
  }

  function renderTimeline(runtime) {
    if (!runtimeTimeline) return;
    const timeline = Array.isArray(runtime?.timeline) ? runtime.timeline.slice(-4).reverse() : [];
    if (!timeline.length) {
      runtimeTimeline.innerHTML = '<div class="runtime-empty-card"><strong>Sem eventos ainda.</strong><span>Os eventos da execução aparecerão aqui.</span></div>';
      return;
    }
    runtimeTimeline.innerHTML = timeline.map((item) => `
      <div class="runtime-timeline-item">
        <div class="runtime-timeline-dot"></div>
        <div>
          <strong>${escapeHtml(item.label || item.kind || 'Evento')}</strong>
          <div class="runtime-timeline-time">${escapeHtml(formatDateTime(item.timestamp))}</div>
        </div>
      </div>
    `).join('');
  }

  function renderIndicators(runtime) {
    if (!runtimeProcessIndicators) return;
    const indicators = Array.isArray(runtime?.process_indicators) ? runtime.process_indicators : [];
    if (!indicators.length) {
      runtimeProcessIndicators.innerHTML = '<div class="runtime-empty-card"><strong>Sem KPIs vinculados.</strong><span>Associe indicadores a este processo para acompanhar o desempenho aqui.</span></div>';
      return;
    }

    runtimeProcessIndicators.innerHTML = indicators.map((indicator) => `
      <div class="bpms-indicator-row">
        <div class="bpms-indicator-row__meta">
          <strong>${escapeHtml(indicator.name || indicator.code || 'Indicador')}</strong>
          <small>${escapeHtml(indicator.code || 'Sem código')}</small>
        </div>
        <div class="bpms-indicator-row__value">${escapeHtml(formatIndicatorValue(indicator.current_value, indicator.unit))}</div>
        <div class="bpms-indicator-row__goal">
          <strong>${escapeHtml(formatIndicatorValue(indicator.goal_value, indicator.unit))}</strong>
          <small>Meta</small>
        </div>
        <div class="bpms-indicator-farol" data-farol="${escapeHtml(indicator.farol || 'neutral')}">${escapeHtml(farolLabel(indicator.farol))}</div>
      </div>
    `).join('');
  }

  function renderCurrentActivity(runtime) {
    if (!runtimeCurrentActivity) return;
    const payload = runtime?.current_activity || {};
    const execution = payload.execution || null;
    const action = payload.action || {};
    const materials = payload.support_materials || {};
    const quickSteps = Array.isArray(materials.quick_steps) ? materials.quick_steps : [];

    if (!payload.element_id && !execution && !payload.routine) {
      runtimeCurrentActivity.innerHTML = `
        <div class="runtime-empty-card">
          <strong>Nenhuma atividade corrente definida.</strong>
          <span>Esta instância ainda não recebeu um ponteiro de execução BPMN.</span>
        </div>
      `;
      return;
    }

    const hasOpenAction = Boolean(action.internal_url || action.external_url);
    const openActionHref = action.internal_url || action.external_url || '#';
    const openActionTarget = action.external_url ? 'target="_blank" rel="noopener noreferrer"' : '';
    const supportButtons = [
      { key: 'pop', label: 'Abrir POP', available: Boolean(materials.pop?.available) },
      { key: 'video', label: 'Abrir vídeo', available: Boolean(materials.video?.available) },
      { key: 'spec_ai', label: 'Abrir SPEC IA', available: Boolean(materials.spec_ai?.available) }
    ];

    runtimeCurrentActivity.innerHTML = `
      <div class="bpms-activity-card">
        <div class="bpms-activity-title">
          <h3>${escapeHtml(payload.element_name || payload.element_id || 'Atividade atual')}</h3>
          <p>${escapeHtml(payload.lane_name || 'Responsável não definido por lane')}</p>
        </div>

        <div class="bpms-activity-meta">
          <div class="bpms-activity-meta__row"><span>Tipo de execução</span><strong>${escapeHtml(action.execution_mode_label || 'Tarefa humana')}</strong></div>
          <div class="bpms-activity-meta__row"><span>Status</span><strong class="bpms-activity-status">${escapeHtml(payload.status || 'pending')}</strong></div>
          <div class="bpms-activity-meta__row"><span>Início</span><strong>${escapeHtml(formatDateTime(execution?.started_at))}</strong></div>
          <div class="bpms-activity-meta__row"><span>Término</span><strong>${escapeHtml(formatDateTime(execution?.completed_at))}</strong></div>
          <div class="bpms-activity-meta__row"><span>SLA</span><strong>${escapeHtml(action.sla_minutes ? `${action.sla_minutes} min` : 'Não definido')}</strong></div>
        </div>

        <div class="bpms-activity-support">
          ${supportButtons.map((button) => `
            <button type="button" class="btn btn-outline btn-sm" data-support-type="${button.key}" ${button.available ? '' : 'disabled'}>
              ${escapeHtml(button.label)}
            </button>
          `).join('')}
        </div>

        <div class="bpms-activity-steps">
          <h4>Etapas da atividade</h4>
          ${quickSteps.length ? `
            <ol>
              ${quickSteps.map((step) => `
                <li>
                  <strong>${escapeHtml(step.title || 'Etapa')}</strong>
                  ${step.description ? escapeHtml(step.description) : ''}
                </li>
              `).join('')}
            </ol>
          ` : '<div class="bpms-support-empty">Nenhuma etapa POP cadastrada para esta atividade.</div>'}
        </div>

        <div class="bpms-activity-actions">
          ${hasOpenAction
            ? `<a class="btn btn-secondary" href="${escapeHtml(openActionHref)}" ${openActionTarget}>${escapeHtml(action.action_label || 'Abrir tela operacional')}</a>`
            : ''}
          <button type="button" class="btn btn-primary" data-runtime-action="complete" ${(action.can_complete || action.can_start) ? '' : 'disabled'}>Concluir atividade</button>
        </div>
      </div>
    `;

    runtimeCurrentActivity.querySelectorAll('[data-support-type]').forEach((button) => {
      button.addEventListener('click', () => {
        openSupportMaterialModal(button.dataset.supportType, payload);
      });
    });

    const concludeButton = runtimeCurrentActivity.querySelector('[data-runtime-action="complete"]');
    if (concludeButton) {
      concludeButton.addEventListener('click', async () => {
        concludeButton.disabled = true;
        try {
          await handleCompleteCurrentActivity(payload, execution, action);
          await refreshRuntime();
        } catch (error) {
          console.error('[process-instance-runtime] conclude error', error);
          window.alert(error.message || 'Erro ao concluir a atividade.');
        } finally {
          concludeButton.disabled = false;
        }
      });
    }
  }

  function openSupportMaterialModal(type, currentActivity) {
    const materials = currentActivity?.support_materials || {};
    let title = 'Conteúdo da atividade';
    let subtitle = currentActivity?.element_name || 'Material de apoio';
    let html = '<div class="bpms-support-empty">Sem conteúdo disponível.</div>';

    if (type === 'pop') {
      title = 'POP da atividade';
      const entries = materials.pop?.entries || [];
      html = entries.length
        ? `<div class="bpms-support-entries">${entries.map((entry) => `
            <article class="bpms-support-entry">
              <h4>${escapeHtml(entry.name || 'Passo')}</h4>
              ${entry.description ? `<p>${escapeHtml(entry.description)}</p>` : ''}
              ${entry.expected_result ? `<p><strong>Resultado esperado:</strong> ${escapeHtml(entry.expected_result)}</p>` : ''}
              ${entry.image_url ? `<img src="${escapeHtml(entry.image_url)}" alt="${escapeHtml(entry.name || 'Passo POP')}">` : ''}
            </article>
          `).join('')}</div>`
        : '<div class="bpms-support-empty">Nenhum POP vinculado a esta atividade.</div>';
    } else if (type === 'video') {
      title = 'Vídeos da atividade';
      const entries = materials.video?.entries || [];
      html = entries.length
        ? `<div class="bpms-support-videos">${entries.map((entry) => `
            <article class="bpms-support-video">
              <h4>${escapeHtml(entry.name || 'Vídeo')}</h4>
              ${entry.video_narration ? `<p>${escapeHtml(entry.video_narration)}</p>` : ''}
              <video controls preload="metadata" src="${escapeHtml(entry.video_url)}"></video>
            </article>
          `).join('')}</div>`
        : '<div class="bpms-support-empty">Nenhum vídeo cadastrado para esta atividade.</div>';
    } else if (type === 'spec_ai') {
      title = 'SPEC IA da atividade';
      const sections = materials.spec_ai?.sections || [];
      html = sections.length
        ? `<div class="bpms-support-sections">${sections.map((section) => `
            <article class="bpms-support-section">
              <h4>${escapeHtml(section.label || 'Bloco')}</h4>
              <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(section.content || '')}</pre>
            </article>
          `).join('')}</div>`
        : '<div class="bpms-support-empty">Nenhuma SPEC IA configurada para esta atividade.</div>';
    }

    if (typeof window.openRuntimeSupportModal === 'function') {
      window.openRuntimeSupportModal(title, subtitle, html);
    }
  }

  async function handleCompleteCurrentActivity(currentPayload, execution, actionMeta) {
    const payload = currentPayload || {};
    const now = new Date().toISOString();
    const executionPayload = {
      bpmn_element_id: payload.element_id,
      bpmn_element_name: payload.element_name,
      bpmn_element_type: payload.element_type,
      execution_mode: actionMeta.execution_mode || 'human_task',
      interaction_mode: actionMeta.interaction_mode || null,
      capability_key: actionMeta.capability_key || null,
      handler_key: actionMeta.handler_key || null,
      started_at: now,
      completed_at: now
    };

    if (!execution || !execution.id) {
      await createExecution({
        ...executionPayload,
        status: 'completed'
      });
      return;
    }

    await updateExecution(execution.id, {
      status: 'completed',
      started_at: execution.started_at || now,
      completed_at: now
    });
  }

  async function createExecution(payload) {
    const response = await fetch(`/api/process-instances/${instanceId}/executions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao criar execução (${response.status})`);
    }
    return response.json();
  }

  async function updateExecution(executionId, payload) {
    const response = await fetch(`/api/process-instances/${instanceId}/executions/${executionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao atualizar execução (${response.status})`);
    }
    return response.json();
  }

  async function postAction(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload || {})
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Falha ao executar ação (${response.status})`);
    }
    return response.json();
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

  async function refreshRuntime() {
    const runtime = await fetchRuntime();
    latestRuntime = runtime;

    renderHeader(runtime);
    renderFlowMeta(runtime);
    renderCurrentActivity(runtime);
    renderTimeline(runtime);
    renderIndicators(runtime);

    if (runtime.diagram?.bpmn_xml) {
      await ensureViewer(runtime.diagram.bpmn_xml);
      applyOverlay(runtime.overlay || {});
    } else if (runtimeFlowEmpty) {
      runtimeFlowEmpty.hidden = false;
    }

    return runtime;
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
