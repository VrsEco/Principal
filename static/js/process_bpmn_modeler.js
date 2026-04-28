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
  let modeler = null;
  let currentDiagram = null;
  let currentZoom = 1;
  let popCandidatesByElementId = new Map();

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
    const usedNumbers = new Set();
    const assignments = [];

    for (const element of activities) {
      const currentCode = getSemanticActivityCode(element);
      if (currentCode) {
        usedNumbers.add(currentCode.number);
        continue;
      }
      const nextNumber = nextActivityNumber(usedNumbers);
      usedNumbers.add(nextNumber);
      assignments.push({
        element,
        oldId: element.id,
        newCode: `${processCode}.${String(nextNumber).padStart(2, '0')}`
      });
    }

    if (!assignments.length) {
      if (!opts.silent) setStatus('Atividades já codificadas', `Todas as atividades já seguem o padrão ${processCode}.NN.`);
      return { changed: 0 };
    }

    const modeling = modeler.get('modeling');
    for (const assignment of assignments) {
      const currentName = assignment.element.businessObject.name || '';
      const nextName = buildActivityLabel(assignment.newCode, currentName, assignment.oldId);
      modeling.updateProperties(assignment.element, {
        id: assignment.newCode,
        name: nextName
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

  function nextActivityNumber(usedNumbers) {
    let number = 1;
    while (usedNumbers.has(number)) number += 1;
    return number;
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
    if (!cleanName || cleanName === oldId || isGeneratedBpmnId(cleanName)) return defaultActivityNameFromCode(code);
    return stripActivityCodePrefix(cleanName, code) || defaultActivityNameFromCode(code);
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
