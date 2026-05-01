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
  const OPERATIONAL_ACTIVITY_LABEL_FONT_SCALE = 1.5;
  const OPERATIONAL_TASK_ID_PATTERN = /\.\d{2}$/;
  let modeler = null;
  let currentDiagram = null;
  let currentZoom = 1;
  let popCandidatesByElementId = new Map();
  let manualResizeHandleEl = null;
  let manualResizeState = null;
  let operationalLabelRefreshFrame = null;

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

  async function fetchDiagram() {
    const res = await fetch(`/api/processes/${processId}/bpmn-diagram`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) throw new Error(`Falha ao carregar BPMN (${res.status})`);
    return res.json();
  }

  async function importXml(xml) {
    const result = await modeler.importXML(xml);
    const canvas = modeler.get('canvas');
    canvas.zoom('fit-viewport', 'auto');
    currentZoom = 1;
    scheduleOperationalActivityLabelRefresh();
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
        keyboard: {
          bindTo: document
        }
      });
      installOperationalActivityAutoSizing();
      installOperationalActivityManualResize();

      currentDiagram = await fetchDiagram();
      await importXml(currentDiagram.bpmn_xml);
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
      refreshOperationalActivityLabelPresentation();
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
        svg_snapshot: enhanceOperationalActivitySvgSnapshot(svg),
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
      scheduleOperationalActivityLabelRefresh();
    };

    eventBus.on('commandStack.shape.create.postExecute', resizeContextShape);
    eventBus.on('commandStack.shape.replace.postExecute', resizeContextShape);
    eventBus.on('commandStack.element.updateLabel.postExecute', () => {
      scheduleOperationalActivityLabelRefresh();
    });
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
      scheduleOperationalActivityLabelRefresh();
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
    refreshOperationalActivityLabelPresentation();
    const { svg } = await modeler.saveSVG();
    downloadText(`${safeFileName(processName)}.svg`, enhanceOperationalActivitySvgSnapshot(svg), 'image/svg+xml');
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
    const scaledLabelLength = label.length * OPERATIONAL_ACTIVITY_LABEL_FONT_SCALE;
    const baseMeasuredWidth = Math.max(164, Math.min(220, 132 + Math.ceil(scaledLabelLength * 1.55)));
    const width = Math.max(
      OPERATIONAL_ACTIVITY_BASE_WIDTH,
      Math.min(OPERATIONAL_ACTIVITY_MAX_WIDTH, baseMeasuredWidth * 2)
    );
    const estimatedLines = Math.max(2, Math.ceil(scaledLabelLength / 38));
    const dynamicHeight = 54 + (estimatedLines * 18);
    const height = Math.max(
      OPERATIONAL_ACTIVITY_BASE_HEIGHT,
      Math.min(OPERATIONAL_ACTIVITY_EXPANDED_HEIGHT + 18, dynamicHeight)
    );
    return { width, height };
  }

  function scheduleOperationalActivityLabelRefresh() {
    if (operationalLabelRefreshFrame) {
      window.cancelAnimationFrame(operationalLabelRefreshFrame);
    }
    operationalLabelRefreshFrame = window.requestAnimationFrame(() => {
      operationalLabelRefreshFrame = null;
      refreshOperationalActivityLabelPresentation();
    });
  }

  function refreshOperationalActivityLabelPresentation() {
    if (!canvasEl) return;
    const svg = canvasEl.querySelector('svg');
    if (!svg) return;
    retuneOperationalTaskLabels(svg);
  }

  function retuneOperationalTaskLabels(svgRoot) {
    getOperationalTaskGroupsFromSvg(svgRoot).forEach((group) => {
      group.querySelectorAll('text.djs-label, text.djs-label tspan').forEach((labelNode) => {
        scaleSvgFontNode(labelNode, OPERATIONAL_ACTIVITY_LABEL_FONT_SCALE);
      });
    });
  }

  function getOperationalTaskGroupsFromSvg(svgRoot) {
    if (!svgRoot || typeof svgRoot.querySelectorAll !== 'function') return [];
    return Array.from(svgRoot.querySelectorAll('.djs-element.djs-shape[data-element-id]')).filter((node) => {
      const elementId = String(node.getAttribute('data-element-id') || '').trim();
      return OPERATIONAL_TASK_ID_PATTERN.test(elementId);
    });
  }

  function scaleSvgFontNode(node, scale) {
    if (!node || !Number.isFinite(scale) || scale <= 0) return;

    const style = node.getAttribute('style') || '';
    const styleMatch = style.match(/font-size:\s*([0-9.]+)px/i);
    if (styleMatch) {
      const baseSize = parseFloat(node.dataset.gvBaseFontSize || styleMatch[1]);
      if (!Number.isFinite(baseSize) || baseSize <= 0) return;
      node.dataset.gvBaseFontSize = String(baseSize);
      node.dataset.gvFontScale = String(scale);
      const nextSize = Math.round(baseSize * scale * 100) / 100;
      node.setAttribute('style', style.replace(/font-size:\s*[0-9.]+px/i, `font-size: ${nextSize}px`));
      return;
    }

    const attrSize = parseFloat(node.dataset.gvBaseFontSize || node.getAttribute('font-size') || '');
    if (Number.isFinite(attrSize) && attrSize > 0) {
      node.dataset.gvBaseFontSize = String(attrSize);
      node.dataset.gvFontScale = String(scale);
      node.setAttribute('font-size', String(Math.round(attrSize * scale * 100) / 100));
    }
  }

  function enhanceOperationalActivitySvgSnapshot(svgMarkup) {
    if (!svgMarkup || typeof DOMParser === 'undefined' || typeof XMLSerializer === 'undefined') {
      return svgMarkup;
    }

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(svgMarkup, 'image/svg+xml');
      const taskGroups = getOperationalTaskGroupsFromSvg(doc);

      taskGroups.forEach((group) => {
        group.querySelectorAll('text.djs-label, text.djs-label tspan').forEach((label) => {
          scaleSvgFontNode(label, OPERATIONAL_ACTIVITY_LABEL_FONT_SCALE);
        });
      });

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

  init();
})();
