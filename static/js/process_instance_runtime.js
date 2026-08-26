(function () {
  const root = document.getElementById('processRuntimeShell');
  if (!root) return;

  const instanceId = root.dataset.instanceId;
  const processId = root.dataset.processId;
  const companyId = root.dataset.companyId;
  const focusedExecutionId = new URLSearchParams(window.location.search).get('execution_id');

  const runtimeStatusLabel = document.getElementById('runtimeStatusLabel');
  const runtimeStartedAt = document.getElementById('runtimeStartedAt');
  const runtimeCompletedAt = document.getElementById('runtimeCompletedAt');
  const runtimeCurrentElement = document.getElementById('runtimeCurrentElement');
  const runtimeTimeline = document.getElementById('runtimeTimeline');
  const runtimeCurrentActivity = document.getElementById('runtimeCurrentActivity');
  const runtimeFlowMeta = document.getElementById('runtimeFlowMeta');
  const runtimeFlowEmpty = document.getElementById('runtimeFlowEmpty');
  const runtimeProcessIndicators = document.getElementById('runtimeProcessIndicators');
  const runtimeDocumentHistory = document.getElementById('runtimeDocumentHistory');

  const btnPause = document.getElementById('btnPauseRuntime');
  const btnResume = document.getElementById('btnResumeRuntime');
  const btnRefresh = document.getElementById('btnRefreshRuntime');
  const btnRefreshSecondary = document.getElementById('btnRefreshRuntimeSecondary');

  let viewer = null;
  let appliedMarkers = [];
  let latestRuntime = null;
  let autoOpenedArtifactKey = null;

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
    const focusQuery = focusedExecutionId ? `?execution_id=${encodeURIComponent(focusedExecutionId)}` : '';
    const response = await fetch(`/api/process-instances/${instanceId}/runtime${focusQuery}`, {
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
        container: '#runtimeBpmnCanvas'
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
      if (root) root.dataset.runtimeDiagram = 'false';
      runtimeFlowMeta.textContent = 'Processo sem BPMN publicado. A shell continua disponível em modo manual.';
      if (runtimeFlowEmpty) runtimeFlowEmpty.hidden = false;
      return;
    }
    if (root) root.dataset.runtimeDiagram = 'true';
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

  function renderDocumentHistory(runtime) {
    if (!runtimeDocumentHistory) return;
    const documents = Array.isArray(runtime?.document_history) ? runtime.document_history : [];
    if (!documents.length) {
      runtimeDocumentHistory.innerHTML = '<div class="bpms-support-empty">Nenhum formulário ou checklist concluído nesta instância.</div>';
      return;
    }
    runtimeDocumentHistory.innerHTML = documents.map(document => `
      <button type="button" class="bpms-document-history__item bpms-artifact-card--${escapeHtml(document.artifact_type)}" data-history-document-id="${escapeHtml(document.id)}">
        <span class="bpms-artifact-card__type">${escapeHtml(document.artifact_type === 'form' ? 'FORMULÁRIO' : 'CHECKLIST')}</span>
        <span><strong>${escapeHtml(document.name || 'Documento')}</strong><small>${escapeHtml(document.activity_name || 'Atividade')} · v${escapeHtml(document.artifact_version || 1)}</small></span>
        <span><strong>${escapeHtml(document.performed_by_name || 'Executor da atividade')}</strong><small>${escapeHtml(formatDateTime(document.completed_at))}</small></span>
        <span class="bpms-artifact-card__action">Ver resultado ›</span>
      </button>
    `).join('');
    runtimeDocumentHistory.querySelectorAll('[data-history-document-id]').forEach(button => {
      button.addEventListener('click', () => {
        const document = documents.find(item => String(item.id) === String(button.dataset.historyDocumentId));
        if (document?.artifact_type === 'form') openFormArtifactModal(document);
        if (document?.artifact_type === 'check') openCheckArtifactModal(document);
      });
    });
  }

  function renderCurrentActivity(runtime) {
    if (!runtimeCurrentActivity) return;
    const payload = runtime?.current_activity || {};
    const execution = payload.execution || null;
    const action = payload.action || {};
    const materials = payload.support_materials || {};
    const artifactsPayload = payload.artifacts || {};
    const artifacts = Array.isArray(artifactsPayload.items) ? artifactsPayload.items : [];
    const operationalDocuments = artifacts.filter((artifact) => artifact.artifact_type === 'form' || artifact.artifact_type === 'check');
    const artifactCompletion = artifactsPayload.completion || {};
    const quickSteps = Array.isArray(materials.quick_steps) ? materials.quick_steps : [];
    const nextCandidates = Array.isArray(payload.next_candidates) ? payload.next_candidates : [];

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

        <div class="bpms-artifact-runtime bpms-document-worklist">
          <div class="bpms-artifact-runtime__head">
            <div><span class="bpms-document-worklist__eyebrow">Documentos operacionais</span><h4>Pendências para concluir</h4></div>
            <span>${escapeHtml(`${artifactCompletion.required_completed || 0}/${artifactCompletion.required_total || 0} obrigatórios concluídos`)}</span>
          </div>
          ${operationalDocuments.length ? `<div class="bpms-artifact-runtime__list">
            ${operationalDocuments.map(renderOperationalDocumentCard).join('')}
          </div>` : '<div class="bpms-support-empty">Esta atividade não possui formulário ou checklist vinculado.</div>'}
          ${execution && artifactCompletion.activity_may_complete === false ? '<div class="bpms-document-gate"><strong>Conclusão bloqueada</strong><span>Finalize os documentos obrigatórios indicados acima.</span></div>' : ''}
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
          ${execution && nextCandidates.length > 1 ? `
            <label class="bpms-runtime-next-path">
              <span>Próximo caminho</span>
              <select data-runtime-next-element required>
                <option value="">Selecione o resultado desta decisão</option>
                ${nextCandidates.map(candidate => `<option value="${escapeHtml(candidate.element_id)}">${escapeHtml(candidate.path_label ? `${candidate.path_label} · ${candidate.element_name}` : candidate.element_name)}</option>`).join('')}
              </select>
            </label>
          ` : ''}
          ${hasOpenAction
            ? `<a class="btn btn-secondary" href="${escapeHtml(openActionHref)}" ${openActionTarget}>${escapeHtml(action.action_label || 'Abrir tela operacional')}</a>`
            : ''}
          <button type="button" class="btn btn-primary" data-runtime-action="complete" ${(action.can_complete || action.can_start) && (!execution || artifactCompletion.activity_may_complete !== false) ? '' : 'disabled'}>${execution ? 'Concluir atividade' : 'Iniciar atividade'}</button>
        </div>
      </div>
    `;

    runtimeCurrentActivity.querySelectorAll('[data-support-type]').forEach((button) => {
      button.addEventListener('click', () => {
        openSupportMaterialModal(button.dataset.supportType, payload);
      });
    });

    runtimeCurrentActivity.querySelectorAll('[data-artifact-type]').forEach((button) => {
      button.addEventListener('click', async () => {
        const artifact = artifacts.find((item) => String(item.id || '') === String(button.dataset.artifactId || '') && item.artifact_type === button.dataset.artifactType)
          || artifacts.find((item) => item.artifact_type === button.dataset.artifactType && !item.id);
        try {
          await openArtifactExecution(artifact, payload, execution, action);
        } catch (error) {
          window.alert(error.message || 'Erro ao abrir artefato.');
        }
      });
    });

    const autoArtifact = operationalDocuments
      .filter(artifact => artifact.status !== 'completed' && artifact.status !== 'skipped')
      .sort((left, right) => Number(Boolean(right.is_required)) - Number(Boolean(left.is_required)))[0];
    const autoArtifactKey = autoArtifact
      ? `${payload.element_id || 'activity'}:${autoArtifact.artifact_definition_id || autoArtifact.id || autoArtifact.artifact_key}`
      : null;
    if (autoArtifact && !focusedExecutionId && autoOpenedArtifactKey !== autoArtifactKey) {
      autoOpenedArtifactKey = autoArtifactKey;
      window.setTimeout(() => {
        openArtifactExecution(autoArtifact, payload, execution, action)
          .catch(error => window.alert(error.message || 'Erro ao abrir o documento obrigatório.'));
      }, 0);
    }

    const concludeButton = runtimeCurrentActivity.querySelector('[data-runtime-action="complete"]');
    if (concludeButton) {
      concludeButton.addEventListener('click', async () => {
        concludeButton.disabled = true;
        try {
          if (!execution) {
            await createExecution({
              bpmn_element_id: payload.element_id,
              bpmn_element_name: payload.element_name,
              bpmn_element_type: payload.element_type,
              execution_mode: action.execution_mode || 'human_task',
              interaction_mode: action.interaction_mode || null,
              capability_key: action.capability_key || null,
              handler_key: action.handler_key || null,
              status: 'in_progress'
            });
          } else {
            const nextElement = runtimeCurrentActivity.querySelector('[data-runtime-next-element]')?.value || null;
            if (nextCandidates.length > 1 && !nextElement) {
              window.alert('Selecione o próximo caminho antes de concluir a atividade.');
              return;
            }
            await handleCompleteCurrentActivity(payload, execution, action, nextElement);
          }
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

  function artifactTypeLabel(type) {
    return ({ pop: 'POP', form: 'FORM', check: 'CHECK', ai: 'IA', data_in: 'IN', data_out: 'OUT' })[type] || 'ARTEFATO';
  }

  function artifactStatusLabel(status) {
    return ({ pending: 'Pendente', in_progress: 'Em andamento', waiting_external: 'Aguardando', waiting_human: 'Revisão humana', completed: 'Concluído', failed: 'Falhou', skipped: 'Dispensado' })[status] || status || 'Pendente';
  }

  function artifactProgress(artifact) {
    const config = artifact?.configuration_json || {};
    const answers = artifact?.output_json?.answers || {};
    if (artifact?.artifact_type === 'form') {
      const fields = (config.sections || []).flatMap(section => section.fields || []);
      const answered = fields.filter(field => {
        const value = answers[field.id];
        return value !== undefined && value !== null && value !== '' && (!Array.isArray(value) || value.length > 0);
      }).length;
      return { answered, total: fields.length, unit: fields.length === 1 ? 'campo' : 'campos' };
    }
    const items = config.items || [];
    const answered = items.filter(item => Boolean(answers[item.id]?.status)).length;
    return { answered, total: items.length, unit: items.length === 1 ? 'item' : 'itens' };
  }

  function renderOperationalDocumentCard(artifact) {
    const progress = artifactProgress(artifact);
    const percentage = progress.total ? Math.round((progress.answered / progress.total) * 100) : 0;
    const actionLabel = artifact.status === 'completed' ? 'Ver resultado' : artifact.status === 'in_progress' ? 'Continuar' : 'Preencher';
    return `
      <button type="button" class="bpms-artifact-card bpms-artifact-card--${escapeHtml(artifact.artifact_type || 'generic')} bpms-artifact-card--status-${escapeHtml(artifact.status || 'pending')}" data-artifact-id="${artifact.id || ''}" data-artifact-type="${escapeHtml(artifact.artifact_type || '')}">
        <span class="bpms-artifact-card__type">${escapeHtml(artifact.artifact_type === 'form' ? 'FORMULÁRIO' : 'CHECKLIST')}</span>
        <span class="bpms-artifact-card__body">
          <strong>${escapeHtml(artifact.name || 'Documento')}</strong>
          <small>${artifact.is_required ? 'Obrigatório' : 'Opcional'} · ${escapeHtml(artifactStatusLabel(artifact.status))}</small>
          <span class="bpms-document-progress"><i style="width:${percentage}%"></i></span>
          <small>${progress.answered}/${progress.total} ${escapeHtml(progress.unit)} preenchidos</small>
        </span>
        <span class="bpms-artifact-card__action">${escapeHtml(actionLabel)} ${artifact.status === 'completed' ? '✓' : '›'}</span>
      </button>`;
  }

  async function openArtifactExecution(artifact, currentActivity, execution, action) {
    if (!artifact) return;
    if (artifact.artifact_type === 'pop') {
      openSupportMaterialModal('pop', currentActivity);
      return;
    }
    if (!execution?.id || !artifact.id) {
      if (!execution?.id) {
        await createExecution({
          bpmn_element_id: currentActivity.element_id,
          bpmn_element_name: currentActivity.element_name,
          bpmn_element_type: currentActivity.element_type,
          execution_mode: action.execution_mode || 'human_task',
          status: 'in_progress'
        });
      }
      const runtime = await refreshRuntime();
      const refreshedActivity = runtime?.current_activity || {};
      const refreshedArtifact = (refreshedActivity.artifacts?.items || []).find(item =>
        Number(item.artifact_definition_id) === Number(artifact.artifact_definition_id)
      );
      if (!refreshedArtifact?.id) throw new Error('Documento não foi materializado para esta atividade.');
      await openArtifactExecution(refreshedArtifact, refreshedActivity, refreshedActivity.execution, refreshedActivity.action || action);
      return;
    }
    if (artifact.artifact_type === 'form') openFormArtifactModal(artifact);
    else if (artifact.artifact_type === 'check') openCheckArtifactModal(artifact);
    else window.alert(`${artifactTypeLabel(artifact.artifact_type)} será executado automaticamente pelo runtime configurado.`);
  }

  function fieldInputHtml(field, value, { readOnly = false } = {}) {
    const id = escapeHtml(field.id || 'field');
    const label = escapeHtml(field.label || field.id || 'Campo');
    const required = field.required && !readOnly ? 'required' : '';
    const disabled = readOnly ? 'disabled' : '';
    const current = value ?? '';
    if (field.type === 'file') {
      const currentFile = current && typeof current === 'object' ? current : null;
      const currentLink = currentFile?.download_url
        ? `<a class="bpms-document-file-link" href="${escapeHtml(currentFile.download_url)}">Baixar ${escapeHtml(currentFile.name || 'arquivo')}</a>`
        : current ? `<span class="bpms-document-file-link">${escapeHtml(current)}</span>` : '<span class="bpms-document-file-empty">Nenhum arquivo enviado</span>';
      if (readOnly) return `<div class="bpms-runtime-form-field"><span>${label}${field.required ? ' *' : ''}</span>${currentLink}</div>`;
      return `<label class="bpms-runtime-form-field"><span>${label}${field.required ? ' *' : ''}</span><input type="file" data-form-field="${id}" data-document-file accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv,.doc,.docx,.xls,.xlsx" ${field.required && !currentFile ? 'required' : ''}><small data-file-name>${currentFile ? `Arquivo atual: ${escapeHtml(currentFile.name || 'arquivo')}` : 'Limite de 10 MB'}</small></label>`;
    }
    if (field.type === 'textarea') return `<label class="bpms-runtime-form-field"><span>${label}${field.required ? ' *' : ''}</span><textarea data-form-field="${id}" ${required} ${disabled}>${escapeHtml(current)}</textarea></label>`;
    if (field.type === 'checkbox') return `<label class="bpms-runtime-form-field bpms-runtime-form-field--check"><input type="checkbox" data-form-field="${id}" ${current ? 'checked' : ''} ${disabled}> <span>${label}</span></label>`;
    if (field.type === 'select' || field.type === 'multiselect') {
      const selected = Array.isArray(current) ? current.map(String) : [String(current)];
      const options = (field.options || []).map(option => typeof option === 'object' ? option : { value: option, label: option });
      return `<label class="bpms-runtime-form-field"><span>${label}${field.required ? ' *' : ''}</span><select data-form-field="${id}" ${field.type === 'multiselect' ? 'multiple' : ''} ${required} ${disabled}>${options.map(option => `<option value="${escapeHtml(option.value)}" ${selected.includes(String(option.value)) ? 'selected' : ''}>${escapeHtml(option.label)}</option>`).join('')}</select></label>`;
    }
    const htmlType = ({number:'number',date:'date',datetime:'datetime-local',email:'email',phone:'tel'})[field.type] || 'text';
    return `<label class="bpms-runtime-form-field"><span>${label}${field.required ? ' *' : ''}</span><input type="${htmlType}" data-form-field="${id}" value="${escapeHtml(current)}" ${required} ${disabled}></label>`;
  }

  function openFormArtifactModal(artifact) {
    const config = artifact.configuration_json || {};
    const answers = artifact.output_json?.answers || {};
    const readOnly = artifact.status === 'completed';
    const html = `<div class="bpms-document-context"><span>${artifact.is_required ? 'Obrigatório' : 'Opcional'}</span><span>${escapeHtml(artifactStatusLabel(artifact.status))}</span><span>Versão ${escapeHtml(artifact.artifact_version || 1)}</span></div><form id="runtimeArtifactForm" class="bpms-runtime-form">${(config.sections || []).map(section => `<fieldset><legend>${escapeHtml(section.title || 'Seção')}</legend>${section.description ? `<p class="bpms-document-section-help">${escapeHtml(section.description)}</p>` : ''}${(section.fields || []).map(field => fieldInputHtml(field, answers[field.id], { readOnly })).join('')}</fieldset>`).join('')}<div class="bpms-document-feedback" data-document-feedback role="status"></div><div class="bpms-runtime-form__actions">${readOnly ? `<a class="btn btn-primary" href="/api/process-artifact-executions/${artifact.id}/pdf?company_id=${encodeURIComponent(companyId)}" target="_blank" rel="noopener">Emitir PDF</a><button type="button" class="btn btn-secondary" data-document-close>Fechar resultado</button>` : '<button type="button" class="btn btn-secondary" data-artifact-save="progress">Salvar rascunho</button><button type="submit" class="btn btn-primary">Concluir formulário</button>'}</div></form>`;
    window.openRuntimeSupportModal(`${readOnly ? 'Resultado do formulário' : 'Preencher formulário'} · ${artifact.name || 'Formulário'}`, readOnly ? `Concluído em ${formatDateTime(artifact.completed_at)}.` : 'Preencha os campos e salve um rascunho quando necessário.', html);
    const form = document.getElementById('runtimeArtifactForm');
    if (readOnly) { form.querySelector('[data-document-close]')?.addEventListener('click', closeDocumentModal); return; }
    bindDocumentFileInputs(form, artifact, answers);
    const collect = () => {
      const values = {};
      form.querySelectorAll('[data-form-field]').forEach(input => {
        if (input.type === 'file') values[input.dataset.formField] = parseFilePayload(input) || answers[input.dataset.formField] || null;
        else if (input.type === 'checkbox') values[input.dataset.formField] = input.checked;
        else if (input.multiple) values[input.dataset.formField] = Array.from(input.selectedOptions).map(option => option.value);
        else values[input.dataset.formField] = input.value;
      });
      return values;
    };
    form.querySelector('[data-artifact-save]').addEventListener('click', () => submitDocument(form, () => saveArtifactExecution(artifact.id, 'in_progress', { answers: collect() }, {}), 'Rascunho salvo. Você pode continuar depois.'));
    form.addEventListener('submit', event => { event.preventDefault(); submitDocument(form, () => saveArtifactExecution(artifact.id, 'completed', { answers: collect() }, {}), 'Formulário concluído.'); });
  }

  function openCheckArtifactModal(artifact) {
    const config = artifact.configuration_json || {};
    const answers = artifact.output_json?.answers || {};
    const evidence = artifact.evidence_json || {};
    const readOnly = artifact.status === 'completed';
    const disabled = readOnly ? 'disabled' : '';
    const html = `<div class="bpms-document-context"><span>${artifact.is_required ? 'Obrigatório' : 'Opcional'}</span><span>${escapeHtml(artifactStatusLabel(artifact.status))}</span><span>Versão ${escapeHtml(artifact.artifact_version || 1)}</span></div><form id="runtimeArtifactCheck" class="bpms-runtime-check"><div class="bpms-runtime-check__columns"><span>Critério</span><span>Resultado</span><span>Comentário</span><span>Evidência</span></div>${(config.items || []).map(item => { const answer=answers[item.id]||{}; const evidenceValue=evidence[item.id]; const evidenceFile=evidenceValue&&typeof evidenceValue==='object'?evidenceValue:null; const evidenceControl=readOnly?(evidenceFile?.download_url?`<a class="bpms-document-file-link" href="${escapeHtml(evidenceFile.download_url)}">Baixar ${escapeHtml(evidenceFile.name||'evidência')}</a>`:`<span>${escapeHtml(evidenceValue||'Sem evidência')}</span>`):`<input type="file" data-check-evidence="${escapeHtml(item.id)}" data-document-file accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv,.doc,.docx,.xls,.xlsx"><small data-file-name>${evidenceFile?`Arquivo atual: ${escapeHtml(evidenceFile.name||'evidência')}`:(item.evidence_required?'Evidência obrigatória':'Evidência opcional')}</small>`; return `<article class="bpms-runtime-check__item"><strong>${escapeHtml(item.label || 'Item')}${item.required ? ' *' : ''}</strong><label><span class="bpms-mobile-label">Resultado</span><select data-check-status="${escapeHtml(item.id)}" ${disabled}><option value="">Selecione</option><option value="accepted" ${answer.status==='accepted'?'selected':''}>Conforme</option><option value="rejected" ${answer.status==='rejected'?'selected':''}>Não conforme</option>${item.allow_na?`<option value="na" ${answer.status==='na'?'selected':''}>N/A</option>`:''}</select></label><label><span class="bpms-mobile-label">Comentário</span><input type="text" data-check-comment="${escapeHtml(item.id)}" value="${escapeHtml(answer.comment || '')}" placeholder="Comentário" ${disabled}></label><label><span class="bpms-mobile-label">Evidência</span>${evidenceControl}</label></article>`; }).join('')}<div class="bpms-document-feedback" data-document-feedback role="status"></div><div class="bpms-runtime-form__actions">${readOnly ? `<a class="btn btn-primary" href="/api/process-artifact-executions/${artifact.id}/pdf?company_id=${encodeURIComponent(companyId)}" target="_blank" rel="noopener">Emitir PDF</a><button type="button" class="btn btn-secondary" data-document-close>Fechar resultado</button>` : '<button type="button" class="btn btn-secondary" data-artifact-save="progress">Salvar rascunho</button><button type="submit" class="btn btn-primary">Concluir checklist</button>'}</div></form>`;
    window.openRuntimeSupportModal(`${readOnly ? 'Resultado do checklist' : 'Executar checklist'} · ${artifact.name || 'Checklist'}`, readOnly ? `Concluído em ${formatDateTime(artifact.completed_at)}.` : 'Verifique cada critério antes de concluir.', html);
    const form=document.getElementById('runtimeArtifactCheck');
    if (readOnly) { form.querySelector('[data-document-close]')?.addEventListener('click', closeDocumentModal); return; }
    bindDocumentFileInputs(form, artifact, evidence);
    const collect=()=>{const output={};const evidencePayload={};form.querySelectorAll('[data-check-status]').forEach(select=>{const id=select.dataset.checkStatus;output[id]={status:select.value,comment:form.querySelector(`[data-check-comment="${CSS.escape(id)}"]`)?.value||''};const evidenceInput=form.querySelector(`[data-check-evidence="${CSS.escape(id)}"]`);evidencePayload[id]=parseFilePayload(evidenceInput)||evidence[id]||'';});return {output,evidencePayload};};
    form.querySelector('[data-artifact-save]').addEventListener('click',()=>{const data=collect();submitDocument(form,()=>saveArtifactExecution(artifact.id,'in_progress',{answers:data.output},data.evidencePayload),'Rascunho salvo. Você pode continuar depois.');});
    form.addEventListener('submit',event=>{event.preventDefault();const data=collect();submitDocument(form,()=>saveArtifactExecution(artifact.id,'completed',{answers:data.output},data.evidencePayload),'Checklist concluído.');});
  }

  function closeDocumentModal() {
    const modal = document.getElementById('resourceContentModal');
    if (modal) modal.style.display = 'none';
  }

  function parseFilePayload(input) {
    if (!input?.dataset?.filePayload) return null;
    try { return JSON.parse(input.dataset.filePayload); } catch (_) { return null; }
  }

  function bindDocumentFileInputs(form, artifact, currentValues = {}) {
    form.querySelectorAll('[data-document-file]').forEach(input => {
      const key = input.dataset.formField || input.dataset.checkEvidence;
      if (currentValues[key] && typeof currentValues[key] === 'object') {
        input.dataset.filePayload = JSON.stringify(currentValues[key]);
      }
      input.addEventListener('change', async () => {
        const file = input.files?.[0];
        if (!file) return;
        const name = input.parentElement?.querySelector('[data-file-name]');
        input.disabled = true;
        input.dataset.uploading = 'true';
        if (name) name.textContent = 'Enviando arquivo...';
        try {
          const body = new FormData();
          body.append('file', file);
          const response = await fetch(`/api/process-artifact-executions/${artifact.id}/files?company_id=${encodeURIComponent(companyId)}`, { method:'POST', body });
          const data = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(data.error || 'Falha ao enviar arquivo.');
          input.dataset.filePayload = JSON.stringify(data);
          if (name) name.textContent = `${data.name} enviado. Salve o documento para vinculá-lo.`;
          setDocumentFeedback(form, 'Arquivo enviado. Salve o rascunho ou conclua o documento.', false);
        } catch (error) {
          input.value = '';
          if (name) name.textContent = error.message || 'Falha ao enviar arquivo.';
          setDocumentFeedback(form, error.message || 'Falha ao enviar arquivo.', true);
        } finally {
          input.disabled = false;
          input.dataset.uploading = 'false';
        }
      });
    });
  }

  function setDocumentFeedback(form, message, isError = false) {
    const feedback = form?.querySelector('[data-document-feedback]');
    if (!feedback) return;
    feedback.textContent = message || '';
    feedback.className = `bpms-document-feedback${isError ? ' is-error' : ' is-success'}`;
  }

  async function submitDocument(form, action, successMessage) {
    if (form.querySelector('[data-uploading="true"]')) {
      setDocumentFeedback(form, 'Aguarde o término do envio do arquivo.', true);
      return;
    }
    const buttons = form.querySelectorAll('button');
    buttons.forEach(button => { button.disabled = true; });
    setDocumentFeedback(form, 'Salvando...', false);
    try {
      await action();
      setDocumentFeedback(form, successMessage, false);
    } catch (error) {
      setDocumentFeedback(form, error.message || 'Não foi possível salvar.', true);
    } finally {
      buttons.forEach(button => { button.disabled = false; });
    }
  }

  async function saveArtifactExecution(artifactExecutionId, status, outputJson, evidenceJson) {
    const response = await fetch(`/api/process-artifact-executions/${artifactExecutionId}`, { method:'PUT', headers:{'Content-Type':'application/json',Accept:'application/json'}, body:JSON.stringify({company_id:Number(companyId),status,output_json:outputJson,evidence_json:evidenceJson}) });
    const data = await response.json().catch(()=>({}));
    if(!response.ok) throw new Error(data.error || `Falha ao salvar artefato (${response.status})`);
    await refreshRuntime();
    if(status === 'completed') closeDocumentModal();
    return data;
  }

  function openSupportMaterialModal(type, currentActivity) {
    const materials = currentActivity?.support_materials || {};
    const linkedArtifacts = (currentActivity?.artifacts?.items || [])
      .filter((item) => item.artifact_type === 'form' || item.artifact_type === 'check');
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
      if (linkedArtifacts.length) {
        html += `
          <section class="bpms-artifact-runtime" style="margin-top:1rem;">
            <div class="bpms-artifact-runtime__head">
              <h4>Formulários e checklists vinculados</h4>
              <span>${linkedArtifacts.length} artefato(s)</span>
            </div>
            <div class="bpms-artifact-runtime__list">
              ${linkedArtifacts.map((artifact) => `
                <button type="button" class="bpms-artifact-card bpms-artifact-card--${escapeHtml(artifact.artifact_type)}" data-pop-artifact-id="${escapeHtml(artifact.id || '')}">
                  <span class="bpms-artifact-card__type">${escapeHtml(artifactTypeLabel(artifact.artifact_type))}</span>
                  <span class="bpms-artifact-card__body"><strong>${escapeHtml(artifact.name || 'Artefato')}</strong><small>${artifact.is_required ? 'Obrigatório' : 'Opcional'} · ${escapeHtml(artifactStatusLabel(artifact.status))}</small></span>
                  <span class="bpms-artifact-card__state">${artifact.status === 'completed' ? '✓' : '›'}</span>
                </button>
              `).join('')}
            </div>
          </section>
        `;
      }
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
      if (type === 'pop') {
        document.querySelectorAll('[data-pop-artifact-id]').forEach((button) => {
          button.addEventListener('click', () => {
            const artifact = linkedArtifacts.find(item => String(item.id || '') === String(button.dataset.popArtifactId || ''));
            openArtifactExecution(
              artifact,
              currentActivity,
              currentActivity?.execution,
              currentActivity?.action || {},
            ).catch(error => window.alert(error.message || 'Erro ao abrir artefato.'));
          });
        });
      }
    }
  }

  async function handleCompleteCurrentActivity(currentPayload, execution, actionMeta, nextElementId = null) {
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
      completed_at: now,
      next_bpmn_element_id: nextElementId
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
    renderDocumentHistory(runtime);

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
