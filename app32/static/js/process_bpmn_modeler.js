(function () {
  const root = document.getElementById('app32BpmnModeler');
  if (!root) return;

  const processId = root.dataset.processId;
  const processName = root.dataset.processName || 'Processo';
  const processCode = root.dataset.processCode || '';
  const statusEl = document.getElementById('bpmnSaveStatus');
  const metaEl = document.getElementById('bpmnDiagramMeta');
  const loadingEl = document.getElementById('bpmnLoading');
  const importInput = document.getElementById('bpmnImportInput');
  const canvasEl = document.getElementById('bpmnCanvas');
  const canvasCardEl = canvasEl ? canvasEl.closest('.bpmn-canvas-card') : root.querySelector('.bpmn-canvas-card');
  const OPERATIONAL_ACTIVITY_BASE_WIDTH = 280;
  const OPERATIONAL_ACTIVITY_MAX_WIDTH = 392;
  const OPERATIONAL_ACTIVITY_BASE_HEIGHT = 90;
  const OPERATIONAL_ACTIVITY_EXPANDED_HEIGHT = 130;
  const OPERATIONAL_ACTIVITY_MIN_WIDTH = 240;
  const OPERATIONAL_ACTIVITY_MIN_HEIGHT = 72;
  let modeler = null;
  let currentDiagram = null;
  let currentZoom = 1;
  let popCandidatesByElementId = new Map();
  let executionContractsByElementId = new Map();
  let aiInspectorDraftByElementId = new Map();
  let aiAssistantCatalog = {
    task_operation_options: ['extract', 'classify', 'summarize', 'validate', 'enrich', 'act'],
    gateway_operation_options: ['route', 'triage', 'qualify'],
    fallback_actions: ['human_review', 'fail', 'continue_with_warning'],
    tool_sources: ['none', 'mcp', 'api'],
    model_roles: ['expert', 'router'],
    templates: []
  };
  let toolCatalog = [];
  let currentSelection = null;
  let inspectorBusy = false;
  let manualResizeHandleEl = null;
  let manualResizeState = null;

  function setStatus(text, detail, isError) {
    if (statusEl) {
      statusEl.textContent = text;
      statusEl.style.color = isError ? '#b91c1c' : '';
    }
    if (metaEl && detail !== undefined) metaEl.textContent = detail || '';
  }

  function setLoading(visible) {
    if (!loadingEl) return;
    loadingEl.classList.toggle('is-hidden', !visible);
  }

  function getModelerCtor() {
    return window.BpmnJS || window.BpmnModeler;
  }

  function buildAiReplaceModule() {
    function App32AiReplaceMenuProvider(popupMenu) {
      popupMenu.registerProvider('bpmn-replace', this);
    }

    App32AiReplaceMenuProvider.$inject = ['popupMenu'];

    App32AiReplaceMenuProvider.prototype.getPopupMenuEntries = function (element) {
      return function (entries) {
        const type = element && element.businessObject && element.businessObject.$type;
        if (isOperationalActivityType(type)) {
          entries['app32-ai-task'] = {
            label: 'AI Task',
            className: 'bpmn-icon-service-task',
            action: function () {
              applySemanticPreset(element, 'ai_task');
            }
          };
        }
        if (isGatewayType(type)) {
          entries['app32-ai-gateway'] = {
            label: 'AI Gateway',
            className: 'bpmn-icon-gateway-xor',
            action: function () {
              applySemanticPreset(element, 'ai_gateway');
            }
          };
        }
        return entries;
      };
    };

    return {
      __init__: ['app32AiReplaceMenuProvider'],
      app32AiReplaceMenuProvider: ['type', App32AiReplaceMenuProvider]
    };
  }

  async function fetchDiagram() {
    const res = await fetch(`/api/processes/${processId}/bpmn-diagram`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) throw new Error(`Falha ao carregar BPMN (${res.status})`);
    return res.json();
  }

  async function fetchExecutionContracts() {
    const res = await fetch(`/api/processes/${processId}/activity-execution-contracts`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) throw new Error(`Falha ao carregar contratos BPMS (${res.status})`);
    return res.json();
  }

  async function fetchAiAssistantCatalog() {
    const res = await fetch(`/api/processes/${processId}/bpmn-ai-assistant`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) throw new Error(`Falha ao carregar catálogo IA (${res.status})`);
    return res.json();
  }

  async function importXml(xml) {
    const result = await modeler.importXML(xml);
    const canvas = modeler.get('canvas');
    canvas.zoom('fit-viewport', 'auto');
    currentZoom = 1;
    return result;
  }

  async function init() {
    setLoading(true);
    try {
      const Modeler = getModelerCtor();
      if (!Modeler) {
        throw new Error('Biblioteca bpmn-js local não foi carregada. Verifique /static/vendor/bpmn-js/18.6.3/dist/bpmn-modeler.production.min.js.');
      }

      modeler = new Modeler({
        container: '#bpmnCanvas',
        additionalModules: [buildAiReplaceModule()],
        keyboard: {
          bindTo: document
        },
        textRenderer: {
          defaultStyle: {
            fontFamily: 'Arial, sans-serif',
            fontSize: 16.5,
            lineHeight: 1.2
          },
          externalStyle: {
            fontFamily: 'Arial, sans-serif',
            fontSize: 16.5,
            lineHeight: 1.2
          }
        }
      });
      installOperationalActivityAutoSizing();
      installOperationalActivityManualResize();

      currentDiagram = await fetchDiagram();
      const [contracts, catalogPayload] = await Promise.all([
        fetchExecutionContracts(),
        fetchAiAssistantCatalog()
      ]);
      executionContractsByElementId = new Map((contracts || [])
        .filter((item) => item && item.is_active !== false && item.bpmn_element_id)
        .map((item) => [item.bpmn_element_id, item]));
      aiAssistantCatalog = {
        ...aiAssistantCatalog,
        ...(((catalogPayload || {}).catalog || {}))
      };
      toolCatalog = (aiAssistantCatalog.tool_items || []);
      await importXml(currentDiagram.bpmn_xml);
      installAiInspector();
      updateMeta();
      setStatus('Pronto para modelar', 'Use a paleta BPMN no canvas.');
    } catch (err) {
      console.error('[APP32 BPMN] init error', err);
      setStatus('Erro ao carregar modeler', err.message, true);
    } finally {
      setLoading(false);
    }
  }

  function updateMeta() {
    if (!currentDiagram) return;
    const version = currentDiagram.version || 0;
    const status = currentDiagram.status || 'unsaved';
    const updated = currentDiagram.updated_at ? new Date(currentDiagram.updated_at).toLocaleString('pt-BR') : 'não salvo';
    if (metaEl) metaEl.textContent = `Versão ${version} · ${status} · ${updated}`;
  }

  async function saveDiagram(status) {
    if (!modeler) return;
    setStatus(status === 'published' ? 'Publicando...' : 'Salvando...');
    try {
      const codeResult = normalizeActivityCodes({ silent: true });
      const [{ xml }, { svg }] = await Promise.all([
        modeler.saveXML({ format: true }),
        modeler.saveSVG()
      ]);
      const payload = {
        id: currentDiagram && currentDiagram.id,
        name: processName,
        status: status || 'draft',
        bpmn_xml: xml,
        svg_snapshot: svg,
        metadata_json: {
          source: 'app32_bpmn_modeler',
          saved_at_client: new Date().toISOString(),
          activity_code_rule: 'process_code_dot_two_digit_sequence',
          activity_code_prefix: processCode || null,
          activity_code_normalized_count: codeResult.changed,
          pop_binding_rule: 'activity_with_data_object_reference',
          pop_candidates: extractPopBindingCandidates()
        }
      };

      const res = await fetch(`/api/processes/${processId}/bpmn-diagram`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Falha ao salvar (${res.status})`);
      currentDiagram = data;
      updateMeta();
      setStatus(
        status === 'published' ? 'Versão publicada' : 'Rascunho salvo',
        status === 'published'
          ? `BPMN publicado e disponível na aba Fluxo do processo.${codeResult.changed ? ` ${codeResult.changed} atividade(s) codificada(s).` : ''}`
          : `BPMN salvo no APP32.${codeResult.changed ? ` ${codeResult.changed} atividade(s) codificada(s).` : ''}`
      );
    } catch (err) {
      console.error('[APP32 BPMN] save error', err);
      setStatus('Erro ao salvar', err.message, true);
    }
  }

  function installOperationalActivityAutoSizing() {
    if (!modeler) return;
    const eventBus = modeler.get('eventBus');
    if (!eventBus || installOperationalActivityAutoSizing._installed) return;

    const resizeContextShape = (event) => {
      const shape = event && event.context && (event.context.newShape || event.context.shape);
      ensureOperationalActivityShapeSize(shape);
    };
    const preserveContextShapeOnReplace = (event) => {
      const context = event && event.context;
      const newShape = context && (context.newShape || context.shape);
      const oldShape = getReplacedOperationalActivityShape(context);

      if (preserveOperationalActivityShapeSize(oldShape, newShape)) {
        return;
      }

      ensureOperationalActivityShapeSize(newShape);
    };

    eventBus.on('commandStack.shape.create.postExecute', resizeContextShape);
    eventBus.on('commandStack.shape.replace.postExecute', preserveContextShapeOnReplace);
    installOperationalActivityAutoSizing._installed = true;
  }

  function installOperationalActivityManualResize() {
    if (!modeler || installOperationalActivityManualResize._installed) return;
    ensureManualResizeHandle();

    const eventBus = modeler.get('eventBus');
    eventBus.on('selection.changed', (event) => {
      const shape = getSingleOperationalActivity(event && event.newSelection);
      attachManualResizeHandle(shape);
    });
    eventBus.on('elements.changed', () => {
      syncManualResizeHandlePosition();
    });
    eventBus.on('canvas.viewbox.changed', () => {
      syncManualResizeHandlePosition();
    });
    eventBus.on('shape.remove', () => {
      syncManualResizeHandlePosition();
    });

    installOperationalActivityManualResize._installed = true;
  }

  function ensureManualResizeHandle() {
    if (manualResizeHandleEl || !canvasCardEl) return;

    manualResizeHandleEl = document.createElement('button');
    manualResizeHandleEl.type = 'button';
    manualResizeHandleEl.className = 'bpmn-manual-resize-handle';
    manualResizeHandleEl.title = 'Arraste para redimensionar a atividade';
    manualResizeHandleEl.setAttribute('aria-label', 'Arraste para redimensionar a atividade BPMN');
    manualResizeHandleEl.hidden = true;
    manualResizeHandleEl.addEventListener('mousedown', startManualResizeDrag);
    canvasCardEl.appendChild(manualResizeHandleEl);
  }

  function getSingleOperationalActivity(selection) {
    if (!Array.isArray(selection) || selection.length !== 1) return null;
    const [shape] = selection;
    return isOperationalActivityType(shape && shape.businessObject && shape.businessObject.$type) ? shape : null;
  }

  function attachManualResizeHandle(shape) {
    ensureManualResizeHandle();
    manualResizeState = shape ? { shape } : null;
    syncManualResizeHandlePosition();
  }

  function syncManualResizeHandlePosition() {
    if (!manualResizeHandleEl || !canvasCardEl || !manualResizeState || !manualResizeState.shape) {
      hideManualResizeHandle();
      return;
    }

    const shape = manualResizeState.shape;
    const elementRegistry = modeler && modeler.get('elementRegistry');
    const gfx = elementRegistry && elementRegistry.getGraphics(shape);
    if (!gfx || typeof gfx.getBoundingClientRect !== 'function') {
      hideManualResizeHandle();
      return;
    }

    const shapeRect = gfx.getBoundingClientRect();
    const canvasRect = canvasCardEl.getBoundingClientRect();
    if (!shapeRect.width || !shapeRect.height || !canvasRect.width || !canvasRect.height) {
      hideManualResizeHandle();
      return;
    }

    manualResizeHandleEl.hidden = false;
    manualResizeHandleEl.style.left = `${shapeRect.right - canvasRect.left - 8}px`;
    manualResizeHandleEl.style.top = `${shapeRect.bottom - canvasRect.top - 8}px`;
  }

  function hideManualResizeHandle() {
    if (!manualResizeHandleEl) return;
    manualResizeHandleEl.hidden = true;
  }

  function startManualResizeDrag(event) {
    if (!manualResizeState || !manualResizeState.shape || !modeler) return;
    event.preventDefault();
    event.stopPropagation();

    const shape = manualResizeState.shape;
    const canvas = modeler.get('canvas');
    const viewbox = canvas && canvas.viewbox ? canvas.viewbox() : null;
    const scale = viewbox && Number.isFinite(viewbox.scale) ? viewbox.scale : 1;

    manualResizeHandleEl.classList.add('is-dragging');

    const dragState = {
      shape,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startWidth: Number.isFinite(shape.width) ? shape.width : OPERATIONAL_ACTIVITY_MIN_WIDTH,
      startHeight: Number.isFinite(shape.height) ? shape.height : OPERATIONAL_ACTIVITY_MIN_HEIGHT,
      scale
    };

    const onMouseMove = (moveEvent) => {
      moveEvent.preventDefault();
      const bounds = calculateManualResizeBounds(dragState, moveEvent);
      resizeOperationalActivityShape(shape, bounds);
      if (manualResizeState) manualResizeState.shape = shape;
      syncManualResizeHandlePosition();
    };

    const finishDrag = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', finishDrag);
      manualResizeHandleEl.classList.remove('is-dragging');
      syncManualResizeHandlePosition();
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', finishDrag);
  }

  function calculateManualResizeBounds(dragState, moveEvent) {
    const deltaX = (moveEvent.clientX - dragState.startClientX) / dragState.scale;
    const deltaY = (moveEvent.clientY - dragState.startClientY) / dragState.scale;
    const width = Math.max(OPERATIONAL_ACTIVITY_MIN_WIDTH, Math.round(dragState.startWidth + deltaX));
    const height = Math.max(OPERATIONAL_ACTIVITY_MIN_HEIGHT, Math.round(dragState.startHeight + deltaY));
    return {
      x: dragState.shape.x,
      y: dragState.shape.y,
      width,
      height
    };
  }

  async function exportBpmn() {
    if (!modeler) return;
    const { xml } = await modeler.saveXML({ format: true });
    downloadText(`${safeFileName(processName)}.bpmn`, xml, 'application/xml');
  }

  async function exportSvg() {
    if (!modeler) return;
    const { svg } = await modeler.saveSVG();
    downloadText(`${safeFileName(processName)}.svg`, svg, 'image/svg+xml');
  }

  function downloadText(filename, content, type) {
    const blob = new Blob([content], { type: type || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function safeFileName(value) {
    return String(value || 'processo-bpmn')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9._-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .toLowerCase() || 'processo-bpmn';
  }

  async function importFile(file) {
    if (!file) return;
    setStatus('Importando BPMN...');
    try {
      const xml = await file.text();
      await importXml(xml);
      currentDiagram = {
        ...(currentDiagram || {}),
        id: null,
        status: 'draft',
        version: currentDiagram ? currentDiagram.version : 0,
        bpmn_xml: xml
      };
      setStatus('BPMN importado', 'Revise o fluxo e salve o rascunho no APP32.');
    } catch (err) {
      console.error('[APP32 BPMN] import error', err);
      setStatus('Erro ao importar', err.message, true);
    } finally {
      importInput.value = '';
    }
  }

  function zoom(delta) {
    if (!modeler) return;
    currentZoom = Math.max(0.2, Math.min(4, currentZoom + delta));
    modeler.get('canvas').zoom(currentZoom);
  }

  function fitViewport() {
    if (!modeler) return;
    modeler.get('canvas').zoom('fit-viewport', 'auto');
    currentZoom = 1;
  }

  function installAiInspector() {
    if (!modeler) return;
    const eventBus = modeler.get('eventBus');
    if (!eventBus || installAiInspector._installed) return;

    eventBus.on('selection.changed', (event) => {
      currentSelection = (event && event.newSelection && event.newSelection[0]) || null;
      renderAiInspector(currentSelection);
    });
    eventBus.on('elements.changed', () => {
      if (currentSelection) {
        const registry = modeler.get('elementRegistry');
        currentSelection = registry.get(currentSelection.id) || currentSelection;
      }
      renderAiInspector(currentSelection);
    });
    renderAiInspector(null);
    installAiInspector._installed = true;
  }

  function renderAiInspector(element) {
    const inspector = document.getElementById('bpmnAiInspector');
    if (!inspector) return;

    if (!element) {
      inspector.innerHTML = `
        <div class="bpmn-ai-empty">
          <strong>Nenhum elemento selecionado</strong>
          <p>Selecione uma task ou gateway para configurar AI Task ou AI Gateway com apoio do Sapiens.</p>
        </div>
      `;
      return;
    }

    const type = element.businessObject && element.businessObject.$type;
    if (!isOperationalActivityType(type) && !isGatewayType(type)) {
      inspector.innerHTML = `
        <div class="bpmn-ai-empty">
          <strong>Elemento sem configuração de IA</strong>
          <p>O assistente do APP32 atua apenas sobre tasks e gateways.</p>
        </div>
      `;
      return;
    }

    const contract = executionContractsByElementId.get(element.id) || null;
    const draft = aiInspectorDraftByElementId.get(element.id) || null;
    const semanticType = getSemanticType(element, contract, draft);
    const executionMode = getCurrentExecutionMode(element, contract, draft, semanticType);
    const nextCandidates = getNextCandidates(element);
    const decisionRows = semanticType === 'ai_gateway'
      ? renderDecisionRows(contract, draft, nextCandidates)
      : '';
    const toolsMarkup = renderToolOptions(contract, draft);
    inspector.innerHTML = `
      <div class="bpmn-ai-card">
        <div class="bpmn-ai-badges">
          <span class="bpmn-ai-badge">${escapeHtml(getSemanticLabel(semanticType))}</span>
          <span class="bpmn-ai-badge bpmn-ai-badge--neutral">${escapeHtml(formatElementType(type))}</span>
        </div>
        <div class="bpmn-ai-grid-2">
          <div>
            <span class="bpmn-ai-label">Elemento</span>
            <span class="bpmn-ai-readonly">${escapeHtml(element.businessObject.name || '(sem nome)')}</span>
          </div>
          <div>
            <span class="bpmn-ai-label">ID BPMN</span>
            <span class="bpmn-ai-readonly">${escapeHtml(element.id)}</span>
          </div>
        </div>
        <div class="bpmn-ai-actions">
          ${isOperationalActivityType(type) ? '<button type="button" class="bpmn-ai-btn bpmn-ai-btn--ghost" data-ai-preset="ai_task">Converter em AI Task</button>' : ''}
          ${isGatewayType(type) ? '<button type="button" class="bpmn-ai-btn bpmn-ai-btn--ghost" data-ai-preset="ai_gateway">Converter em AI Gateway</button>' : ''}
          ${contract ? '<button type="button" class="bpmn-ai-btn bpmn-ai-btn--danger" data-ai-remove="1">Remover contrato IA</button>' : ''}
        </div>
      </div>
      <div class="bpmn-ai-card">
        <div class="bpmn-ai-grid-2">
          <div>
            <label class="bpmn-ai-label" for="executionModeSelect">Executor da atividade</label>
            <select id="executionModeSelect" class="bpmn-ai-select">${buildExecutionModeOptions(element, executionMode)}</select>
          </div>
          <div class="bpmn-ai-sapiens-note">
            <strong>Modo operacional</strong>
            <p class="bpmn-ai-help">Escolha se a task abre formulário, tela do APP32, API, MCP ou IA. Gateways usam AI Gateway para roteamento assistido.</p>
          </div>
        </div>
        <div class="bpmn-ai-grid-2">
          <div>
            <label class="bpmn-ai-label" for="executionTemplateSelect">Template pronto</label>
            <select id="executionTemplateSelect" class="bpmn-ai-select">${buildTemplateOptions(element)}</select>
          </div>
          <div class="bpmn-ai-actions bpmn-ai-actions--end">
            <button type="button" class="bpmn-ai-btn bpmn-ai-btn--ghost" data-apply-template="1">Aplicar template</button>
          </div>
        </div>
        <div class="bpmn-ai-grid-2">
          <div>
            <label class="bpmn-ai-label" for="aiObjective">Objetivo da IA</label>
            <textarea id="aiObjective" class="bpmn-ai-textarea" placeholder="Ex.: Leia o documento e extraia valor, data, fornecedor e histórico.">${escapeHtml(getCurrentObjective(contract, draft, semanticType, element))}</textarea>
          </div>
          <div class="bpmn-ai-sapiens-note">
            <strong>Sapiens como copiloto</strong>
            <p class="bpmn-ai-help">Use o botão abaixo para gerar instrução, schema, tools e decisões sugeridas de forma assistida.</p>
            <div class="bpmn-ai-actions" style="margin-top:0.75rem;">
              <button type="button" class="bpmn-ai-btn bpmn-ai-btn--primary" data-ai-suggest="1">Preencher com Sapiens</button>
            </div>
          </div>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="ai">
          <div>
            <label class="bpmn-ai-label" for="aiOperationType">Tipo de operação</label>
            <select id="aiOperationType" class="bpmn-ai-select">${buildOperationOptions(semanticType, contract, draft)}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="aiModelRole">Modelo</label>
            <select id="aiModelRole" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.model_roles || ['expert', 'router'], getAiFieldValue(contract, draft, 'model_role') || 'expert')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="aiToolSource">Origem das tools</label>
            <select id="aiToolSource" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.tool_sources || ['none', 'mcp', 'api'], getAiFieldValue(contract, draft, 'tool_source') || 'none')}</select>
          </div>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="ai">
          <div>
            <label class="bpmn-ai-label" for="aiMinConfidence">Confiança mínima</label>
            <input id="aiMinConfidence" class="bpmn-ai-input" type="number" min="0" max="1" step="0.01" value="${escapeHtml(String(getAiFieldValue(contract, draft, 'min_confidence') ?? (semanticType === 'ai_gateway' ? 0.8 : 0.85)))}">
          </div>
          <div>
            <label class="bpmn-ai-label" for="aiFallbackAction">Fallback</label>
            <select id="aiFallbackAction" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.fallback_actions || ['human_review', 'fail', 'continue_with_warning'], getAiFieldValue(contract, draft, 'fallback_action') || 'human_review')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="aiRequiresHumanGate">Gate humano</label>
            <select id="aiRequiresHumanGate" class="bpmn-ai-select">${buildSelectOptions(['yes', 'no'], getRequiresHumanGateValue(contract, draft))}</select>
          </div>
        </div>
        <div data-execution-section="ai">
          <label class="bpmn-ai-label" for="aiAllowedTools">Tools permitidas</label>
          <div id="aiAllowedTools" class="bpmn-ai-tools">${toolsMarkup}</div>
        </div>
        <div data-execution-section="ai">${decisionRows}</div>
        <div data-execution-section="ai">
          <label class="bpmn-ai-label" for="aiOutputSchema">Schema / saída esperada</label>
          <textarea id="aiOutputSchema" class="bpmn-ai-textarea" placeholder='{"type":"object","properties":{"data":{"type":"object"}}}'>${escapeHtml(formatJson(getAiFieldValue(contract, draft, 'output_schema') || {}))}</textarea>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="open_form">
          <div>
            <label class="bpmn-ai-label" for="formCode">Formulário</label>
            <input id="formCode" class="bpmn-ai-input" value="${escapeHtml(getUiConfigValue(contract, draft, 'form_code'))}" placeholder="ex.: financial_document_review">
          </div>
          <div>
            <label class="bpmn-ai-label" for="formTarget">Abrir em</label>
            <select id="formTarget" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.form_targets || ['drawer', 'modal', 'page'], getUiConfigValue(contract, draft, 'open_in') || 'drawer')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="formSubmitAction">Ao enviar</label>
            <select id="formSubmitAction" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.submit_actions || ['complete_task', 'stay_open', 'trigger_next_step'], getUiConfigValue(contract, draft, 'submit_action') || 'complete_task')}</select>
          </div>
        </div>
        <div data-execution-section="open_form">
          <label class="bpmn-ai-label" for="formPrefillMapping">Pré-preenchimento (JSON)</label>
          <textarea id="formPrefillMapping" class="bpmn-ai-textarea" placeholder='{"document_id":"{{process.document_id}}"}'>${escapeHtml(formatJson(getUiConfigValue(contract, draft, 'prefill_mapping') || {}))}</textarea>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="open_app32_page">
          <div>
            <label class="bpmn-ai-label" for="pageCode">Page code</label>
            <input id="pageCode" class="bpmn-ai-input" value="${escapeHtml(getUiConfigValue(contract, draft, 'page_code'))}" placeholder="ex.: finance_prelaunch_editor">
          </div>
          <div>
            <label class="bpmn-ai-label" for="pageTarget">Abrir em</label>
            <select id="pageTarget" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.page_targets || ['page', 'drawer', 'modal'], getUiConfigValue(contract, draft, 'open_in') || 'page')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="pageInternalUrl">URL interna opcional</label>
            <input id="pageInternalUrl" class="bpmn-ai-input" value="${escapeHtml(getUiConfigValue(contract, draft, 'internal_url'))}" placeholder="/financial/prelaunch">
          </div>
        </div>
        <div data-execution-section="open_app32_page">
          <label class="bpmn-ai-label" for="pageParamsMapping">Parâmetros da página (JSON)</label>
          <textarea id="pageParamsMapping" class="bpmn-ai-textarea" placeholder='{"document_id":"{{process.document_id}}"}'>${escapeHtml(formatJson(getUiConfigValue(contract, draft, 'params_mapping') || {}))}</textarea>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="api_task">
          <div>
            <label class="bpmn-ai-label" for="apiConnectionKey">Conexão API</label>
            <input id="apiConnectionKey" class="bpmn-ai-input" value="${escapeHtml(getRestConfigValue(contract, draft, 'connection_key'))}" placeholder="ex.: erp_financeiro">
          </div>
          <div>
            <label class="bpmn-ai-label" for="apiMethod">Método</label>
            <select id="apiMethod" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.api_methods || ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], getRestConfigValue(contract, draft, 'method') || 'POST')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="apiTimeout">Timeout (s)</label>
            <input id="apiTimeout" class="bpmn-ai-input" type="number" min="1" step="1" value="${escapeHtml(String(getRestConfigValue(contract, draft, 'timeout_seconds') || 20))}">
          </div>
        </div>
        <div class="bpmn-ai-grid-2" data-execution-section="api_task">
          <div>
            <label class="bpmn-ai-label" for="apiPath">Path / URL</label>
            <input id="apiPath" class="bpmn-ai-input" value="${escapeHtml(getRestConfigValue(contract, draft, 'path') || getRestConfigValue(contract, draft, 'url'))}" placeholder="/documents/prelaunch">
          </div>
          <div>
            <label class="bpmn-ai-label" for="apiRetryPolicy">Retry</label>
            <select id="apiRetryPolicy" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.retry_policies || ['none', 'default', 'aggressive'], getRestConfigValue(contract, draft, 'retry_policy') || 'default')}</select>
          </div>
        </div>
        <div data-execution-section="api_task">
          <label class="bpmn-ai-label" for="apiRequestMapping">Request mapping (JSON)</label>
          <textarea id="apiRequestMapping" class="bpmn-ai-textarea" placeholder='{"amount":"{{process.document_data.amount}}"}'>${escapeHtml(formatJson(getRestConfigValue(contract, draft, 'request_mapping') || {}))}</textarea>
        </div>
        <div data-execution-section="api_task">
          <label class="bpmn-ai-label" for="apiResponseSchema">Schema de resposta (JSON)</label>
          <textarea id="apiResponseSchema" class="bpmn-ai-textarea" placeholder='{"type":"object"}'>${escapeHtml(formatJson(getRestConfigValue(contract, draft, 'response_schema') || {}))}</textarea>
        </div>
        <div class="bpmn-ai-grid-3" data-execution-section="mcp_task">
          <div>
            <label class="bpmn-ai-label" for="mcpToolName">Tool MCP</label>
            <input id="mcpToolName" class="bpmn-ai-input" value="${escapeHtml(getMcpConfigValue(contract, draft, 'tool_name'))}" placeholder="ex.: finance.insert_prelaunch">
          </div>
          <div>
            <label class="bpmn-ai-label" for="mcpSurface">Surface</label>
            <select id="mcpSurface" class="bpmn-ai-select">${buildSelectOptions(aiAssistantCatalog.execution_modes?.mcp_surfaces || ['user', 'admin', 'analytics'], getMcpConfigValue(contract, draft, 'surface') || 'admin')}</select>
          </div>
          <div>
            <label class="bpmn-ai-label" for="mcpConfirmationMode">Confirmação</label>
            <select id="mcpConfirmationMode" class="bpmn-ai-select">${buildSelectOptions(['auto', 'confirm_before_run'], getMcpConfigValue(contract, draft, 'confirmation_mode') || 'auto')}</select>
          </div>
        </div>
        <div data-execution-section="mcp_task">
          <label class="bpmn-ai-label" for="mcpInputMapping">Input mapping (JSON)</label>
          <textarea id="mcpInputMapping" class="bpmn-ai-textarea" placeholder='{"company_id":"{{process.company_id}}"}'>${escapeHtml(formatJson(getMcpConfigValue(contract, draft, 'input_mapping') || {}))}</textarea>
        </div>
        <div class="bpmn-ai-actions">
          <button type="button" class="bpmn-ai-btn bpmn-ai-btn--primary" data-ai-save="1">Salvar contrato IA</button>
        </div>
        <div id="bpmnAiStatus" class="bpmn-ai-status" hidden></div>
      </div>
    `;
    toggleExecutionSections();
  }

  function renderDecisionRows(contract, draft, nextCandidates) {
    const decisions = getAiFieldValue(contract, draft, 'allowed_decisions')
      || nextCandidates.map((candidate) => slugifyDecision(candidate.element_name || candidate.element_id));
    const routeMap = getAiMetadataValue(contract, draft, 'decision_routes') || {};
    const rows = (decisions || []).map((decision) => `
      <div class="bpmn-ai-choice">
        <label class="bpmn-ai-label">Decisão</label>
        <input class="bpmn-ai-input" data-decision-name value="${escapeHtml(decision)}">
        <label class="bpmn-ai-label" style="margin-top:0.65rem;">Rota BPMN</label>
        <select class="bpmn-ai-select" data-decision-route>
          <option value="">Selecione a saída</option>
            ${nextCandidates.map((candidate) => `
              <option value="${escapeHtml(candidate.element_id)}" ${routeMap[decision] === candidate.element_id ? 'selected' : ''}>
                ${escapeHtml(candidate.element_name || candidate.element_id)}
              </option>
            `).join('')}
          </select>
          <button type="button" class="bpmn-ai-link-btn" data-ai-remove-decision="${escapeHtml(decision)}">Remover decisão</button>
        </div>
      `).join('');
    return `
      <div>
        <div class="bpmn-ai-actions bpmn-ai-actions--spread">
          <span class="bpmn-ai-label">Decisões fechadas do gateway</span>
          <button type="button" class="bpmn-ai-link-btn" data-ai-add-decision="1">Adicionar decisão</button>
        </div>
        <div class="bpmn-ai-choice-row" id="aiDecisionRows">${rows || '<div class="bpmn-ai-muted">Conecte saídas ao gateway para habilitar rotas sugeridas.</div>'}</div>
      </div>
    `;
  }

  function renderToolOptions(contract, draft) {
    const selected = new Set(getAiFieldValue(contract, draft, 'allowed_tools') || []);
    return toolCatalog.map((tool) => `
      <label class="bpmn-ai-tool-option">
        <input type="checkbox" value="${escapeHtml(tool.name)}" ${selected.has(tool.name) ? 'checked' : ''}>
        <span>
          <strong>${escapeHtml(tool.name)}</strong>
          <small>${escapeHtml(tool.description || 'Tool operacional do APP32.')}</small>
        </span>
      </label>
    `).join('') || '<div class="bpmn-ai-muted">Nenhuma tool catalogada para seleção.</div>';
  }

  function buildOperationOptions(semanticType, contract, draft) {
    const current = getUiSchemaValue(contract, 'operation_type')
      || (draft && draft.operation_type)
      || (semanticType === 'ai_gateway' ? 'route' : 'extract');
    const options = semanticType === 'ai_gateway'
      ? (aiAssistantCatalog.gateway_operation_options || ['route', 'triage', 'qualify'])
      : (aiAssistantCatalog.task_operation_options || ['extract', 'classify', 'summarize', 'validate', 'enrich', 'act']);
    return buildSelectOptions(options, current);
  }

  function buildSelectOptions(options, currentValue) {
    return (options || []).map((value) => `
      <option value="${escapeHtml(value)}" ${String(currentValue) === String(value) ? 'selected' : ''}>${escapeHtml(value)}</option>
    `).join('');
  }

  function getSemanticType(element, contract, draft) {
    const type = element && element.businessObject && element.businessObject.$type;
    if (draft && draft.semantic_type === 'ai_task') return 'ai_task';
    if (draft && draft.semantic_type === 'ai_gateway') return 'ai_gateway';
    if (contract && contract.execution_mode === 'ai_task') return 'ai_task';
    if (contract && contract.execution_mode === 'ai_decision') return 'ai_gateway';
    if (isGatewayType(type)) return 'gateway';
    return 'task';
  }

  function getCurrentExecutionMode(element, contract, draft, semanticType) {
    if (draft && draft.execution_mode) return draft.execution_mode;
    if (contract && contract.execution_mode) return contract.execution_mode;
    return semanticType === 'ai_gateway' ? 'ai_decision' : 'human_task';
  }

  function buildExecutionModeOptions(element, currentValue) {
    const type = element && element.businessObject && element.businessObject.$type;
    const catalog = isGatewayType(type)
      ? (aiAssistantCatalog.execution_modes?.gateway_modes || [])
      : (aiAssistantCatalog.execution_modes?.task_modes || []);
    return (catalog || []).map((item) => `
      <option value="${escapeHtml(item.key)}" ${String(currentValue) === String(item.key) ? 'selected' : ''}>${escapeHtml(item.label || item.key)}</option>
    `).join('');
  }

  function buildTemplateOptions(element) {
    const type = element && element.businessObject && element.businessObject.$type;
    const scope = isGatewayType(type) ? 'gateway' : 'task';
    const templates = (aiAssistantCatalog.templates || []).filter((item) => item.scope === scope);
    const options = ['<option value="">Selecione um template</option>'];
    templates.forEach((item) => {
      options.push(`<option value="${escapeHtml(item.key)}">${escapeHtml(item.label)}</option>`);
    });
    return options.join('');
  }

  function getTemplateByKey(templateKey) {
    return (aiAssistantCatalog.templates || []).find((item) => item.key === templateKey) || null;
  }

  function getSemanticLabel(semanticType) {
    return {
      ai_task: 'AI Task',
      ai_gateway: 'AI Gateway',
      gateway: 'Gateway BPMN',
      task: 'Task BPMN'
    }[semanticType] || 'Elemento BPMN';
  }

  function formatElementType(type) {
    return String(type || '').replace('bpmn:', '');
  }

  function getCurrentObjective(contract, draft, semanticType, element) {
    return getAiFieldValue(contract, draft, 'instruction')
      || (semanticType === 'ai_gateway'
        ? `Classifique a rota do gateway ${element.id} entre as saídas conectadas.`
        : `Descreva o que a IA deve fazer na task ${element.id}.`);
  }

  function getContractAiValue(contract, key) {
    return contract && contract.ai_config_json ? contract.ai_config_json[key] : null;
  }

  function getAiFieldValue(contract, draft, key) {
    if (draft && draft[key] !== undefined && draft[key] !== null) return draft[key];
    return getContractAiValue(contract, key);
  }

  function getAiMetadataValue(contract, draft, key) {
    if (draft && draft.metadata && draft.metadata[key] !== undefined) return draft.metadata[key];
    const metadata = getContractAiValue(contract, 'metadata') || {};
    return metadata[key];
  }

  function getRequiresHumanGateValue(contract, draft) {
    if (draft && typeof draft.requires_human_gate === 'boolean') {
      return draft.requires_human_gate ? 'yes' : 'no';
    }
    return contract && contract.requires_human_gate ? 'yes' : 'no';
  }

  function addGatewayDecisionRow() {
    const container = document.getElementById('aiDecisionRows');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'bpmn-ai-choice';
    row.innerHTML = `
      <label class="bpmn-ai-label">Decisão</label>
      <input class="bpmn-ai-input" data-decision-name placeholder="ex.: human_review">
      <label class="bpmn-ai-label" style="margin-top:0.65rem;">Rota BPMN</label>
      <select class="bpmn-ai-select" data-decision-route>
        <option value="">Selecione a saída</option>
        ${getNextCandidates(currentSelection).map((candidate) => `
          <option value="${escapeHtml(candidate.element_id)}">${escapeHtml(candidate.element_name || candidate.element_id)}</option>
        `).join('')}
      </select>
      <button type="button" class="bpmn-ai-link-btn" data-ai-remove-decision="__new__">Remover decisão</button>
    `;
    const muted = container.querySelector('.bpmn-ai-muted');
    if (muted) muted.remove();
    container.appendChild(row);
  }

  function getUiSchemaValue(contract, key) {
    return contract && contract.ui_schema_json ? contract.ui_schema_json[key] : null;
  }

  function getUiConfigValue(contract, draft, key) {
    if (draft && draft.ui_schema_json && draft.ui_schema_json[key] !== undefined) return draft.ui_schema_json[key];
    return getUiSchemaValue(contract, key) || '';
  }

  function getRestConfigValue(contract, draft, key) {
    if (draft && draft.rest_config_json && draft.rest_config_json[key] !== undefined) return draft.rest_config_json[key];
    return contract && contract.rest_config_json ? contract.rest_config_json[key] : '';
  }

  function getMcpConfigValue(contract, draft, key) {
    if (draft && draft.mcp_config_json && draft.mcp_config_json[key] !== undefined) return draft.mcp_config_json[key];
    return contract && contract.mcp_config_json ? contract.mcp_config_json[key] : '';
  }

  function getNextCandidates(element) {
    return (element.outgoing || [])
      .map((flow) => flow && flow.target)
      .filter((target) => target && target.id)
      .map((target) => ({
        element_id: target.id,
        element_name: target.businessObject && target.businessObject.name,
        element_type: target.businessObject && target.businessObject.$type
      }));
  }

  function isGatewayType(type) {
    return Boolean(type && type.includes('Gateway'));
  }

  function slugifyDecision(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'route';
  }

  function formatJson(value) {
    try {
      return JSON.stringify(value || {}, null, 2);
    } catch (error) {
      return '{}';
    }
  }

  function showAiStatus(message, isError) {
    const status = document.getElementById('bpmnAiStatus');
    if (!status) return;
    status.hidden = false;
    status.classList.toggle('is-error', Boolean(isError));
    status.textContent = message;
  }

  function setInspectorBusy(value) {
    inspectorBusy = Boolean(value);
    const inspector = document.getElementById('bpmnAiInspector');
    if (!inspector) return;
    inspector.querySelectorAll('button, input, select, textarea').forEach((field) => {
      field.disabled = inspectorBusy;
    });
  }

  function collectAiFormPayload(element) {
    const contract = executionContractsByElementId.get(element.id);
    const semanticType = getSemanticType(element, contract, aiInspectorDraftByElementId.get(element.id));
    const executionMode = document.getElementById('executionModeSelect')?.value || (semanticType === 'ai_gateway' ? 'ai_decision' : 'human_task');
    const outputSchemaValue = document.getElementById('aiOutputSchema')?.value || '{}';
    let outputSchema = {};
    try {
      outputSchema = outputSchemaValue.trim() ? JSON.parse(outputSchemaValue) : {};
    } catch (error) {
      throw new Error('O schema/saída esperada precisa ser um JSON válido.');
    }

    const selectedTools = Array.from(document.querySelectorAll('#aiAllowedTools input[type="checkbox"]:checked'))
      .map((input) => input.value);
    const decisionRows = Array.from(document.querySelectorAll('#aiDecisionRows .bpmn-ai-choice'));
    const decisionRoutes = {};
    const allowedDecisions = [];
    decisionRows.forEach((row) => {
      const decision = row.querySelector('[data-decision-name]')?.value?.trim();
      const route = row.querySelector('[data-decision-route]')?.value?.trim();
      if (decision) {
        allowedDecisions.push(decision);
        if (route) decisionRoutes[decision] = route;
      }
    });

    const minConfidence = Number(document.getElementById('aiMinConfidence')?.value || 0);
    if (Number.isNaN(minConfidence) || minConfidence < 0 || minConfidence > 1) {
      throw new Error('Confiança mínima deve ficar entre 0 e 1.');
    }

    const formPrefillMapping = parseJsonField('formPrefillMapping');
    const pageParamsMapping = parseJsonField('pageParamsMapping');
    const apiRequestMapping = parseJsonField('apiRequestMapping');
    const apiResponseSchema = parseJsonField('apiResponseSchema');
    const mcpInputMapping = parseJsonField('mcpInputMapping');

    return {
      semantic_type: semanticType,
      execution_mode: executionMode,
      objective: document.getElementById('aiObjective')?.value?.trim() || '',
      operation_type: document.getElementById('aiOperationType')?.value || (semanticType === 'ai_gateway' ? 'route' : 'extract'),
      model_role: document.getElementById('aiModelRole')?.value || 'expert',
      tool_source: document.getElementById('aiToolSource')?.value || 'none',
      min_confidence: minConfidence,
      fallback_action: document.getElementById('aiFallbackAction')?.value || 'human_review',
      requires_human_gate: (document.getElementById('aiRequiresHumanGate')?.value || 'no') === 'yes',
      allowed_tools: selectedTools,
      allowed_decisions: allowedDecisions,
      decision_routes: decisionRoutes,
      output_schema: outputSchema,
      ui_schema_json: {
        form_code: document.getElementById('formCode')?.value?.trim() || null,
        open_in: document.getElementById('formTarget')?.value || document.getElementById('pageTarget')?.value || null,
        submit_action: document.getElementById('formSubmitAction')?.value || null,
        prefill_mapping: formPrefillMapping,
        page_code: document.getElementById('pageCode')?.value?.trim() || null,
        internal_url: document.getElementById('pageInternalUrl')?.value?.trim() || null,
        params_mapping: pageParamsMapping
      },
      rest_config_json: {
        connection_key: document.getElementById('apiConnectionKey')?.value?.trim() || null,
        method: document.getElementById('apiMethod')?.value || 'POST',
        timeout_seconds: Number(document.getElementById('apiTimeout')?.value || 20),
        path: document.getElementById('apiPath')?.value?.trim() || null,
        retry_policy: document.getElementById('apiRetryPolicy')?.value || 'default',
        request_mapping: apiRequestMapping,
        response_schema: apiResponseSchema
      },
      mcp_config_json: {
        tool_name: document.getElementById('mcpToolName')?.value?.trim() || null,
        surface: document.getElementById('mcpSurface')?.value || 'admin',
        confirmation_mode: document.getElementById('mcpConfirmationMode')?.value || 'auto',
        input_mapping: mcpInputMapping
      }
    };
  }

  function parseJsonField(fieldId) {
    const rawValue = document.getElementById(fieldId)?.value || '{}';
    try {
      return rawValue.trim() ? JSON.parse(rawValue) : {};
    } catch (error) {
      throw new Error(`O campo ${fieldId} precisa ser um JSON válido.`);
    }
  }

  function sanitizeConfig(config) {
    return Object.fromEntries(Object.entries(config || {}).filter(([, value]) => {
      if (value === null || value === undefined) return false;
      if (typeof value === 'string' && !value.trim()) return false;
      if (typeof value === 'object' && !Array.isArray(value) && !Object.keys(value).length) return false;
      return true;
    }));
  }

  function applyExecutionTemplate(element, template) {
    if (!element || !template) return;
    const currentDraft = aiInspectorDraftByElementId.get(element.id) || {};
    const executionMode = template.execution_mode || currentDraft.execution_mode || 'human_task';
    aiInspectorDraftByElementId.set(element.id, {
      ...currentDraft,
      execution_mode: executionMode,
      semantic_type: executionMode === 'ai_decision' ? 'ai_gateway' : (currentDraft.semantic_type || 'task'),
      objective: template.objective || currentDraft.objective || '',
      instruction: template.ai_config_json?.instruction || template.objective || currentDraft.instruction || '',
      model_role: template.ai_config_json?.model_role || currentDraft.model_role,
      tool_source: template.ai_config_json?.tool_source || currentDraft.tool_source,
      min_confidence: template.ai_config_json?.min_confidence ?? currentDraft.min_confidence,
      fallback_action: template.ai_config_json?.fallback_action || currentDraft.fallback_action,
      allowed_tools: template.ai_config_json?.allowed_tools || currentDraft.allowed_tools || [],
      allowed_decisions: template.ai_config_json?.allowed_decisions || currentDraft.allowed_decisions || [],
      output_schema: template.ai_config_json?.output_schema || currentDraft.output_schema || {},
      ui_schema_json: template.ui_schema_json || currentDraft.ui_schema_json || {},
      rest_config_json: template.rest_config_json || currentDraft.rest_config_json || {},
      mcp_config_json: template.mcp_config_json || currentDraft.mcp_config_json || {},
      metadata: {
        ...(currentDraft.metadata || {}),
        decision_routes: template.ai_config_json?.metadata?.decision_routes || currentDraft.metadata?.decision_routes || {},
      },
    });
    renderAiInspector(element);
    showAiStatus(`Template aplicado: ${template.label}.`);
  }

  function buildContractPayload(element, formPayload) {
    const interactionMode = formPayload.execution_mode === 'open_form'
      ? (formPayload.ui_schema_json.open_in || 'drawer')
      : formPayload.execution_mode === 'open_app32_page'
        ? (formPayload.ui_schema_json.open_in || 'page')
        : ['api_task', 'mcp_task', 'automatic'].includes(formPayload.execution_mode)
          ? 'headless'
          : formPayload.execution_mode === 'manual_external'
            ? 'shell'
            : 'drawer';
    const autoServiceKey = formPayload.execution_mode === 'ai_decision'
      ? 'process.ai.route'
      : formPayload.execution_mode === 'ai_task'
        ? 'process.ai.execute'
        : `process.${formPayload.execution_mode}`;
    return {
      bpmn_element_id: element.id,
      bpmn_element_type: element.businessObject && element.businessObject.$type,
      execution_mode: formPayload.execution_mode,
      interaction_mode: interactionMode,
      capability_key: formPayload.execution_mode === 'ai_decision' ? 'process.ai_gateway' : `process.${formPayload.execution_mode}`,
      auto_service_key: autoServiceKey,
      requires_human_gate: formPayload.requires_human_gate,
      allows_pause: true,
      allows_retry: true,
      ui_schema_json: {
        semantic_type: formPayload.semantic_type,
        operation_type: formPayload.operation_type,
        ...sanitizeConfig(formPayload.ui_schema_json)
      },
      rest_config_json: sanitizeConfig(formPayload.rest_config_json),
      mcp_config_json: sanitizeConfig(formPayload.mcp_config_json),
      ai_config_json: formPayload.execution_mode.startsWith('ai_') ? {
        instruction: formPayload.objective,
        model_role: formPayload.model_role,
        tool_source: formPayload.tool_source,
        allowed_tools: formPayload.allowed_tools,
        min_confidence: formPayload.min_confidence,
        fallback_action: formPayload.fallback_action,
        allowed_decisions: formPayload.allowed_decisions,
        output_schema: formPayload.output_schema,
        metadata: {
          operation_type: formPayload.operation_type,
          decision_routes: formPayload.decision_routes
        }
      } : {}
    };
  }

  async function saveAiContract(element) {
    const existing = executionContractsByElementId.get(element.id);
    const formPayload = collectAiFormPayload(element);
    if (!formPayload.objective) {
      throw new Error('Descreva o objetivo da IA antes de salvar.');
    }

    const payload = buildContractPayload(element, formPayload);
    const url = existing
      ? `/api/process-activity-execution-contracts/${existing.id}`
      : `/api/processes/${processId}/activity-execution-contracts`;
    const method = existing ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao salvar contrato IA.');
    aiInspectorDraftByElementId.delete(element.id);
    executionContractsByElementId.set(element.id, data);
    renderAiInspector(element);
    showAiStatus('Contrato IA salvo com sucesso.');
  }

  async function removeAiContract(element) {
    const existing = executionContractsByElementId.get(element.id);
    if (!existing) return;
    const res = await fetch(`/api/process-activity-execution-contracts/${existing.id}`, {
      method: 'DELETE',
      headers: { Accept: 'application/json' }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao remover contrato IA.');
    aiInspectorDraftByElementId.delete(element.id);
    executionContractsByElementId.delete(element.id);
    renderAiInspector(element);
    showAiStatus('Contrato IA removido. O elemento voltou ao comportamento BPMN padrão.');
  }

  async function suggestAiConfiguration(element) {
    const existing = executionContractsByElementId.get(element.id);
    const draft = collectAiFormPayload(element);
    const res = await fetch(`/api/processes/${processId}/bpmn-ai-assistant`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify({
        semantic_type: draft.semantic_type,
        element_id: element.id,
        element_name: element.businessObject && element.businessObject.name,
        element_type: element.businessObject && element.businessObject.$type,
        objective: draft.objective,
        next_candidates: getNextCandidates(element),
        current_config: existing && existing.ai_config_json ? existing.ai_config_json : draft
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao consultar o Sapiens.');
    hydrateAiFormFromSuggestion(element, data.suggestion || {});
    showAiStatus('Sugestão do Sapiens aplicada ao formulário.');
  }

  function hydrateAiFormFromSuggestion(element, suggestion) {
    const existingDraft = aiInspectorDraftByElementId.get(element.id) || collectAiFormPayload(element);
    aiInspectorDraftByElementId.set(element.id, {
      ...existingDraft,
      semantic_type: suggestion.execution_mode === 'ai_decision' ? 'ai_gateway' : existingDraft.semantic_type,
      instruction: suggestion.instruction || suggestion.objective || existingDraft.objective,
      objective: suggestion.instruction || suggestion.objective || existingDraft.objective,
      operation_type: suggestion.operation_type || existingDraft.operation_type,
      model_role: suggestion.model_role || existingDraft.model_role,
      tool_source: suggestion.tool_source || existingDraft.tool_source,
      min_confidence: suggestion.min_confidence ?? existingDraft.min_confidence,
      fallback_action: suggestion.fallback_action || existingDraft.fallback_action,
      allowed_tools: suggestion.allowed_tools || existingDraft.allowed_tools || [],
      allowed_decisions: suggestion.allowed_decisions || existingDraft.allowed_decisions || [],
      output_schema: suggestion.output_schema || existingDraft.output_schema || {},
      requires_human_gate: (suggestion.fallback_action || existingDraft.fallback_action) === 'human_review',
      metadata: {
        decision_routes: suggestion.decision_routes || existingDraft.decision_routes || {}
      }
    });
    renderAiInspector(element);
  }

  function applySemanticPreset(element, preset) {
    if (!modeler || !element) return;
    const bpmnReplace = modeler.get('bpmnReplace');
    let target = element;
    const type = element.businessObject && element.businessObject.$type;
    if (preset === 'ai_task' && type !== 'bpmn:ServiceTask') {
      target = bpmnReplace.replaceElement(element, { type: 'bpmn:ServiceTask' });
    }
    if (preset === 'ai_gateway' && type !== 'bpmn:ExclusiveGateway') {
      target = bpmnReplace.replaceElement(element, { type: 'bpmn:ExclusiveGateway' });
    }
    currentSelection = target;
    modeler.get('selection').select(target);
    renderAiInspector(target);
    showAiStatus(preset === 'ai_gateway'
      ? 'Gateway convertido para AI Gateway. Revise decisões, rotas e fallback.'
      : 'Task convertida para AI Task. Revise objetivo, tools e schema.');
  }

  function toggleExecutionSections() {
    const currentMode = document.getElementById('executionModeSelect')?.value || 'human_task';
    const aiVisible = currentMode === 'ai_task' || currentMode === 'ai_decision';
    document.querySelectorAll('[data-execution-section]').forEach((section) => {
      const sectionMode = section.dataset.executionSection;
      const shouldShow = (sectionMode === 'ai' && aiVisible) || sectionMode === currentMode;
      section.hidden = !shouldShow;
    });
    const objectiveLabel = document.querySelector('label[for="aiObjective"]');
    if (objectiveLabel) {
      objectiveLabel.textContent = aiVisible ? 'Objetivo da IA' : 'Objetivo / instrução operacional';
    }
  }

  function inspectElementsForPopBinding() {
    if (!modeler) return;
    normalizeActivityCodes({ silent: true });
    const panel = document.getElementById('bpmnPopBindingPanel');
    const list = document.getElementById('bpmnElementList');
    if (!panel || !list) return;

    const allActivities = getOperationalActivities();
    const elements = extractPopBindingCandidates();
    const ignoredCount = Math.max(0, allActivities.length - elements.length);
    popCandidatesByElementId = new Map(elements.map((item) => [item.id, item]));

    if (!elements.length) {
      list.innerHTML = `
        <div class="bpmn-element-card bpmn-element-card--empty">
          <strong>Nenhuma atividade marcada para POP.</strong>
          <span>Associe um Data Object Reference à atividade BPMN para ela entrar na preparação do POP.</span>
        </div>
      `;
    } else {
      list.innerHTML = elements.map((item) => `
        <div class="bpmn-element-card">
          <code title="${escapeHtml(item.id)}">${escapeHtml(item.id)}</code>
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <span>${escapeHtml(item.type)}</span>
            <small>Data Object: ${escapeHtml(formatDataObjectNames(item.data_objects))}</small>
          </div>
          <button type="button" class="bpmn-chip-btn" data-pop-bind="${escapeHtml(item.id)}">Abrir/Criar POP</button>
        </div>
      `).join('');
    }

    panel.hidden = false;
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setStatus(
      'Atividades POP detectadas',
      `${elements.length} atividade(s) com Data Object Reference. ${ignoredCount} atividade(s) sem marcador POP.`
    );
  }

  function extractPopBindingCandidates() {
    return getOperationalActivities()
      .map((element) => ({
        id: element.id,
        code: element.id,
        type: element.businessObject.$type.replace('bpmn:', ''),
        name: element.businessObject.name || '(sem nome)',
        data_objects: getAssociatedDataObjectRefs(element)
      }))
      .filter((item) => item.data_objects.length > 0)
      .sort((a, b) => a.id.localeCompare(b.id));
  }

  function normalizeActivityCodes(options) {
    const opts = options || {};
    if (!modeler) return { changed: 0, skipped: 'modeler_not_ready' };
    if (!processCode) {
      if (!opts.silent) {
        setStatus('Código do processo ausente', 'Não foi possível gerar códigos automáticos para as atividades.', true);
      }
      return { changed: 0, skipped: 'process_code_missing' };
    }

    const activities = getOperationalActivities().sort(compareElementsByCanvasPosition);
    const usedNumbers = collectUsedActivityNumbers(activities);
    const assignments = [];

    for (const element of activities) {
      const currentCode = getSemanticActivityCode(element);
      let targetCode = currentCode && currentCode.code;
      if (!currentCode) {
        const nextNumber = nextActivityNumber(usedNumbers);
        usedNumbers.add(nextNumber);
        targetCode = `${processCode}.${String(nextNumber).padStart(2, '0')}`;
      }

      const currentName = element.businessObject.name || '';
      const nextName = buildActivityLabel(targetCode, currentName, element.id);
      const shouldUpdateId = element.id !== targetCode;
      const shouldUpdateName = String(currentName || '').trim() !== nextName;

      if (!shouldUpdateId && !shouldUpdateName) continue;

      assignments.push({
        element,
        targetCode,
        nextName
      });
    }

    if (!assignments.length) {
      if (!opts.silent) {
        setStatus(
          'Atividades já codificadas',
          `Todas as atividades já seguem o padrão ${processCode}.NN e já exibem o código no rótulo.`
        );
      }
      return { changed: 0 };
    }

    const modeling = modeler.get('modeling');
    for (const assignment of assignments) {
      modeling.updateProperties(assignment.element, {
        id: assignment.targetCode,
        name: assignment.nextName
      });
    }

    if (!opts.silent) {
      setStatus(
        'Atividades codificadas',
        `${assignments.length} atividade(s) convertida(s) para o padrão ${processCode}.NN.`
      );
    }
    return { changed: assignments.length };
  }

  function getSemanticActivityCode(element) {
    const id = element && element.id;
    if (!id || !processCode) return null;
    const escapedPrefix = escapeRegExp(processCode);
    const match = String(id).match(new RegExp(`^${escapedPrefix}\\.(\\d{2})$`));
    if (!match) return null;
    return { code: id, number: Number(match[1]) };
  }

  function collectUsedActivityNumbers(activities) {
    const usedNumbers = new Set();
    for (const element of activities || []) {
      const currentCode = getSemanticActivityCode(element);
      if (currentCode) usedNumbers.add(currentCode.number);
    }
    return usedNumbers;
  }

  function nextActivityNumber(usedNumbers) {
    let number = 1;
    while (usedNumbers.has(number)) number += 1;
    return number;
  }

  function ensureOperationalActivityShapeSize(element) {
    if (!modeler || !element || !isOperationalActivityType(element.businessObject && element.businessObject.$type)) {
      return false;
    }

    const targetSize = getOperationalActivityTargetSize(element);
    if (!targetSize) return false;

    const currentWidth = Number.isFinite(element.width) ? element.width : 0;
    const currentHeight = Number.isFinite(element.height) ? element.height : 0;
    const targetWidth = Math.max(currentWidth, targetSize.width);
    const targetHeight = Math.max(currentHeight, targetSize.height);

    if (currentWidth >= targetWidth && currentHeight >= targetHeight) return false;

    resizeOperationalActivityShape(element, {
      x: element.x,
      y: element.y,
      width: targetWidth,
      height: targetHeight
    });
    return true;
  }

  function preserveOperationalActivityShapeSize(sourceShape, targetShape) {
    if (!modeler || !sourceShape || !targetShape) return false;

    const sourceType = sourceShape.businessObject && sourceShape.businessObject.$type;
    const targetType = targetShape.businessObject && targetShape.businessObject.$type;
    if (!isOperationalActivityType(sourceType) || !isOperationalActivityType(targetType)) {
      return false;
    }

    const width = Number.isFinite(sourceShape.width) ? Math.round(sourceShape.width) : 0;
    const height = Number.isFinite(sourceShape.height) ? Math.round(sourceShape.height) : 0;
    if (!width || !height) return false;

    const currentWidth = Number.isFinite(targetShape.width) ? Math.round(targetShape.width) : 0;
    const currentHeight = Number.isFinite(targetShape.height) ? Math.round(targetShape.height) : 0;
    if (currentWidth === width && currentHeight === height) {
      return true;
    }

    resizeOperationalActivityShape(targetShape, {
      x: targetShape.x,
      y: targetShape.y,
      width,
      height
    });
    return true;
  }

  function resizeOperationalActivityShape(element, bounds) {
    if (!modeler || !element || !bounds) return false;

    const nextBounds = {
      x: Number.isFinite(bounds.x) ? bounds.x : element.x,
      y: Number.isFinite(bounds.y) ? bounds.y : element.y,
      width: Math.max(OPERATIONAL_ACTIVITY_MIN_WIDTH, Math.round(bounds.width || element.width || OPERATIONAL_ACTIVITY_MIN_WIDTH)),
      height: Math.max(OPERATIONAL_ACTIVITY_MIN_HEIGHT, Math.round(bounds.height || element.height || OPERATIONAL_ACTIVITY_MIN_HEIGHT))
    };

    element.x = nextBounds.x;
    element.y = nextBounds.y;
    element.width = nextBounds.width;
    element.height = nextBounds.height;

    const di = element.di || (element.businessObject && element.businessObject.di);
    if (di && di.bounds) {
      di.bounds.x = nextBounds.x;
      di.bounds.y = nextBounds.y;
      di.bounds.width = nextBounds.width;
      di.bounds.height = nextBounds.height;
    }

    const elementRegistry = modeler.get('elementRegistry');
    const graphicsFactory = modeler.get('graphicsFactory');
    const eventBus = modeler.get('eventBus');
    const gfx = elementRegistry && elementRegistry.getGraphics(element);

    if (gfx && graphicsFactory) {
      graphicsFactory.update('shape', element, gfx);
    }
    if (eventBus) {
      eventBus.fire('elements.changed', { elements: [element] });
    }

    return true;
  }

  function getOperationalActivityTargetSize(element) {
    const label = getOperationalActivityDisplayLabel(element);
    const baseMeasuredWidth = Math.max(156, Math.min(214, 128 + Math.ceil(label.length * 1.65)));
    const width = Math.max(
      OPERATIONAL_ACTIVITY_BASE_WIDTH,
      Math.min(OPERATIONAL_ACTIVITY_MAX_WIDTH, baseMeasuredWidth * 2)
    );
    const estimatedLines = Math.max(2, Math.ceil(label.length / 34));
    const dynamicHeight = 52 + (estimatedLines * 16);
    const height = Math.max(OPERATIONAL_ACTIVITY_BASE_HEIGHT, Math.min(OPERATIONAL_ACTIVITY_EXPANDED_HEIGHT, dynamicHeight));
    return { width, height };
  }

  function enhanceOperationalActivitySvgSnapshot(svgMarkup) {
    if (!svgMarkup || typeof DOMParser === 'undefined' || typeof XMLSerializer === 'undefined') {
      return svgMarkup;
    }

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(svgMarkup, 'image/svg+xml');
      return new XMLSerializer().serializeToString(doc);
    } catch (error) {
      console.warn('[APP32 BPMN] snapshot enhancement failed', error);
      return svgMarkup;
    }
  }

  function getOperationalActivityDisplayLabel(element) {
    const businessObject = element && element.businessObject;
    if (!businessObject) return '';

    const currentName = String(businessObject.name || '').trim();
    const currentCode = getSemanticActivityCode(element);
    if (currentCode) {
      return buildActivityLabel(currentCode.code, currentName, element.id);
    }

    return currentName || processCode || 'Atividade';
  }

  function compareElementsByCanvasPosition(left, right) {
    const leftX = Number.isFinite(left.x) ? left.x : 0;
    const rightX = Number.isFinite(right.x) ? right.x : 0;
    if (leftX !== rightX) return leftX - rightX;

    const leftY = Number.isFinite(left.y) ? left.y : 0;
    const rightY = Number.isFinite(right.y) ? right.y : 0;
    if (leftY !== rightY) return leftY - rightY;

    return String(left.id || '').localeCompare(String(right.id || ''));
  }

  function buildActivityLabel(code, currentName, oldId) {
    const cleanName = String(currentName || '').trim();
    const baseName = (!cleanName || cleanName === oldId || isGeneratedBpmnId(cleanName))
      ? defaultActivityNameFromCode(code)
      : (stripActivityCodePrefix(cleanName, code) || defaultActivityNameFromCode(code));
    return `${code} - ${baseName}`;
  }

  function isGeneratedBpmnId(value) {
    return /^(Activity|Task|SubProcess|CallActivity)_[a-zA-Z0-9]+$/.test(String(value || ''));
  }

  function stripActivityCodePrefix(value, code) {
    const cleanValue = String(value || '').trim();
    if (!cleanValue) return '';
    if (cleanValue === code) return '';

    const exactCodePattern = escapeRegExp(code);
    const exactCodePrefix = new RegExp(`^${exactCodePattern}\\s*[-–—:]\\s*`);
    const withoutExactCode = cleanValue.replace(exactCodePrefix, '').trim();
    if (withoutExactCode !== cleanValue) return withoutExactCode;

    if (!processCode) return cleanValue;
    const genericCodePrefix = new RegExp(`^${escapeRegExp(processCode)}\\.\\d{2}\\s*[-–—:]\\s*`);
    return cleanValue.replace(genericCodePrefix, '').trim();
  }

  function defaultActivityNameFromCode(code) {
    const suffix = String(code || '').split('.').pop();
    return /^\d+$/.test(suffix) ? `Atividade ${suffix}` : 'Atividade';
  }

  function escapeRegExp(value) {
    return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function getOperationalActivities() {
    if (!modeler) return [];
    const registry = modeler.get('elementRegistry');
    return registry.filter((element) => {
      const type = element && element.businessObject && element.businessObject.$type;
      return isOperationalActivityType(type);
    });
  }

  function isOperationalActivityType(type) {
    return Boolean(type && (
      type.includes('Task') ||
      type.includes('SubProcess') ||
      type.includes('CallActivity')
    ));
  }

  function getReplacedOperationalActivityShape(context) {
    if (!context) return null;
    return context.oldShape
      || context.oldElement
      || context.replacedShape
      || context.target
      || null;
  }

  function getAssociatedDataObjectRefs(element) {
    const refs = new Map();
    const businessObject = element && element.businessObject;

    for (const connection of [...(element.incoming || []), ...(element.outgoing || [])]) {
      const connectionBo = connection && connection.businessObject;
      const sourceBo = (connectionBo && connectionBo.sourceRef) || (connection.source && connection.source.businessObject);
      const targetBo = (connectionBo && connectionBo.targetRef) || (connection.target && connection.target.businessObject);
      const otherBo = isSameBpmnElement(sourceBo, businessObject) ? targetBo : sourceBo;
      collectDataObjectRef(refs, otherBo);
    }

    for (const association of businessObject?.dataInputAssociations || []) {
      for (const sourceRef of association.sourceRef || []) {
        collectDataObjectRef(refs, sourceRef);
      }
      collectDataObjectRef(refs, association.targetRef);
    }

    for (const association of businessObject?.dataOutputAssociations || []) {
      collectDataObjectRef(refs, association.targetRef);
      for (const sourceRef of association.sourceRef || []) {
        collectDataObjectRef(refs, sourceRef);
      }
    }

    return Array.from(refs.values()).sort((a, b) => a.id.localeCompare(b.id));
  }

  function isSameBpmnElement(left, right) {
    return left && right && left.id && right.id && left.id === right.id;
  }

  function collectDataObjectRef(refs, businessObject) {
    if (!businessObject || !businessObject.id) return;
    const type = businessObject.$type || '';
    if (!type.includes('DataObjectReference')) return;

    refs.set(businessObject.id, {
      id: businessObject.id,
      name: businessObject.name || businessObject.dataObjectRef?.name || '(sem nome)',
      type: type.replace('bpmn:', '')
    });
  }

  function formatDataObjectNames(dataObjects) {
    return (dataObjects || [])
      .map((item) => item.name && item.name !== '(sem nome)' ? item.name : item.id)
      .join(', ');
  }

  async function openOrCreatePopBinding(bpmnElementId, button) {
    const candidate = popCandidatesByElementId.get(bpmnElementId);
    if (!candidate) {
      setStatus('Atividade BPMN não encontrada', 'Execute novamente “Preparar vínculo com POP”.', true);
      return;
    }

    const previousText = button ? button.textContent : '';
    if (button) {
      button.disabled = true;
      button.textContent = 'Abrindo...';
    }

    try {
      const res = await fetch(`/api/processes/${processId}/bpmn-pop-bindings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify({
          bpmn_element_id: candidate.code || candidate.id,
          bpmn_element_type: candidate.type,
          bpmn_element_name: candidate.name,
          data_objects: candidate.data_objects
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Falha ao abrir/criar POP (${res.status})`);

      const routineId = data.routine && data.routine.id;
      setStatus(
        data.created ? 'Atividade POP criada' : 'Atividade POP aberta',
        routineId ? `POP #${routineId} vinculado ao elemento ${candidate.id}.` : `Elemento ${candidate.id} vinculado.`
      );

      if (routineId) {
        window.location.href = `/processes/${processId}?tab=pops&routine_id=${routineId}#routine-${routineId}`;
      }
    } catch (err) {
      console.error('[APP32 BPMN] POP binding error', err);
      setStatus('Erro ao abrir/criar POP', err.message, true);
      if (button) {
        button.disabled = false;
        button.textContent = previousText || 'Abrir/Criar POP';
      }
    }
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  root.addEventListener('click', async (event) => {
    const aiPresetButton = event.target.closest('[data-ai-preset]');
    if (aiPresetButton && currentSelection) {
      applySemanticPreset(currentSelection, aiPresetButton.dataset.aiPreset);
      return;
    }

    const aiAddDecisionButton = event.target.closest('[data-ai-add-decision]');
    if (aiAddDecisionButton && currentSelection) {
      addGatewayDecisionRow();
      return;
    }

    const aiApplyTemplateButton = event.target.closest('[data-apply-template]');
    if (aiApplyTemplateButton && currentSelection) {
      const templateKey = document.getElementById('executionTemplateSelect')?.value;
      const template = getTemplateByKey(templateKey);
      if (!template) {
        showAiStatus('Selecione um template antes de aplicar.', true);
        return;
      }
      applyExecutionTemplate(currentSelection, template);
      return;
    }

    const aiRemoveDecisionButton = event.target.closest('[data-ai-remove-decision]');
    if (aiRemoveDecisionButton) {
      aiRemoveDecisionButton.closest('.bpmn-ai-choice')?.remove();
      const rows = document.querySelectorAll('#aiDecisionRows .bpmn-ai-choice');
      if (!rows.length) {
        const container = document.getElementById('aiDecisionRows');
        if (container) {
          container.innerHTML = '<div class="bpmn-ai-muted">Adicione pelo menos uma decisão fechada para o gateway.</div>';
        }
      }
      return;
    }

    const aiRemoveButton = event.target.closest('[data-ai-remove]');
    if (aiRemoveButton && currentSelection) {
      try {
        setInspectorBusy(true);
        await removeAiContract(currentSelection);
      } catch (error) {
        showAiStatus(error.message || 'Erro ao remover contrato IA.', true);
      } finally {
        setInspectorBusy(false);
      }
      return;
    }

    const aiSuggestButton = event.target.closest('[data-ai-suggest]');
    if (aiSuggestButton && currentSelection) {
      try {
        setInspectorBusy(true);
        await suggestAiConfiguration(currentSelection);
      } catch (error) {
        showAiStatus(error.message || 'Erro ao consultar o Sapiens.', true);
      } finally {
        setInspectorBusy(false);
      }
      return;
    }

    const aiSaveButton = event.target.closest('[data-ai-save]');
    if (aiSaveButton && currentSelection) {
      try {
        setInspectorBusy(true);
        await saveAiContract(currentSelection);
      } catch (error) {
        showAiStatus(error.message || 'Erro ao salvar contrato IA.', true);
      } finally {
        setInspectorBusy(false);
      }
      return;
    }

    const popBindButton = event.target.closest('[data-pop-bind]');
    if (popBindButton) {
      await openOrCreatePopBinding(popBindButton.dataset.popBind, popBindButton);
      return;
    }

    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'import') importInput.click();
    if (action === 'save') saveDiagram('draft');
    if (action === 'publish') saveDiagram('published');
    if (action === 'normalize-codes') normalizeActivityCodes();
    if (action === 'export') exportBpmn();
    if (action === 'svg') exportSvg();
    if (action === 'zoom-in') zoom(0.2);
    if (action === 'zoom-out') zoom(-0.2);
    if (action === 'fit') fitViewport();
    if (action === 'inspect-elements') inspectElementsForPopBinding();
  });

  importInput.addEventListener('change', (event) => {
    importFile(event.target.files && event.target.files[0]);
  });

  root.addEventListener('change', (event) => {
    if (event.target && event.target.id === 'executionModeSelect') {
      const draft = aiInspectorDraftByElementId.get(currentSelection?.id) || {};
      if (currentSelection) {
        aiInspectorDraftByElementId.set(currentSelection.id, {
          ...draft,
          execution_mode: event.target.value
        });
      }
      toggleExecutionSections();
    }
  });

  init();
})();
