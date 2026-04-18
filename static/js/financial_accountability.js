(function () {
  const page = document.querySelector('.acc-page');
  if (!page) return;

  const companyId = Number(page.dataset.companyId || 0);
  const canCreate = Number(page.dataset.canCreate || 0) === 1;

  const els = {
    reference: document.getElementById('acc-reference'),
    counterparty: document.getElementById('acc-counterparty'),
    amount: document.getElementById('acc-amount'),
    competenceDate: document.getElementById('acc-competence-date'),
    dueDate: document.getElementById('acc-due-date'),
    documentNumber: document.getElementById('acc-document-number'),
    file: document.getElementById('acc-file'),
    entryType: document.getElementById('acc-entry-type'),
    description: document.getElementById('acc-description'),
    extractedText: document.getElementById('acc-extracted-text'),
    upload: document.getElementById('acc-upload'),
    uploadStatus: document.getElementById('acc-upload-status'),
    bankAccount: document.getElementById('acc-bank-account'),
    chartAccount: document.getElementById('acc-chart-account'),
    costCenter: document.getElementById('acc-cost-center'),
    domain: document.getElementById('acc-domain'),
    movementNature: document.getElementById('acc-movement-nature'),
    confidenceLevel: document.getElementById('acc-confidence-level'),
    reviewNotes: document.getElementById('acc-review-notes'),
    preview: document.getElementById('acc-preview-box'),
    refreshPreview: document.getElementById('acc-refresh-preview'),
    submit: document.getElementById('acc-submit'),
    result: document.getElementById('acc-result'),
  };

  const uploadState = {
    uploadedFile: null,
  };

  function setTodayIfEmpty() {
    const today = new Date().toISOString().slice(0, 10);
    if (!els.competenceDate.value) els.competenceDate.value = today;
    if (!els.dueDate.value) els.dueDate.value = today;
  }

  function parseDomain() {
    const raw = String(els.domain.value || '');
    if (!raw.includes(':')) return { domainType: null, sourceId: null };
    const [domainType, sourceId] = raw.split(':');
    return { domainType, sourceId: Number(sourceId || 0) || null };
  }

  function selectedFileMeta() {
    if (uploadState.uploadedFile) {
      return {
        file_name: uploadState.uploadedFile.file_name,
        mime_type: uploadState.uploadedFile.mime_type || null,
        file_size: uploadState.uploadedFile.file_size || null,
        stored_relative_path: uploadState.uploadedFile.stored_relative_path || null,
        public_url: uploadState.uploadedFile.public_url || null,
        sha256: uploadState.uploadedFile.sha256 || null,
        extraction_method: uploadState.uploadedFile.extraction_method || null,
      };
    }
    const file = els.file.files && els.file.files[0];
    if (!file) return {};
    return {
      file_name: file.name,
      mime_type: file.type || null,
      file_size: file.size || null,
      last_modified: file.lastModified || null,
    };
  }

  function inferMovementNature() {
    const option = els.chartAccount.options[els.chartAccount.selectedIndex];
    const byChart = option?.dataset?.movementNature || '';
    const fallback = String(els.entryType.value || '') === 'receivable' ? 'credit' : 'debit';
    const value = byChart || fallback;
    els.movementNature.value = value;
    return value;
  }

  function applyCounterpartyDefaults() {
    const option = els.counterparty.options[els.counterparty.selectedIndex];
    if (!option) return;
    if (!els.chartAccount.value && option.dataset.defaultChartAccountId) {
      els.chartAccount.value = option.dataset.defaultChartAccountId;
    }
    if (!els.costCenter.value && option.dataset.defaultCostCenterId) {
      els.costCenter.value = option.dataset.defaultCostCenterId;
    }
    inferMovementNature();
    renderPreview();
  }

  function buildPayload() {
    const fileMeta = selectedFileMeta();
    const { domainType, sourceId } = parseDomain();
    const amount = Number(els.amount.value || 0);
    const movementNature = inferMovementNature();
    const reference = String(els.reference.value || '').trim();
    const description = String(els.description.value || '').trim();
    const documentNumber = String(els.documentNumber.value || '').trim();
    const extractedText = String(els.extractedText.value || '').trim();
    const reviewNotes = String(els.reviewNotes.value || '').trim();

    return {
      company_id: companyId,
      origin_type: 'sapiens_document',
      origin_reference: reference || documentNumber || `Prestação de contas ${new Date().toISOString().slice(0, 10)}`,
      external_system: 'operations_hub',
      source_file_name: fileMeta.file_name || null,
      source_mime_type: fileMeta.mime_type || null,
      source_channel: 'operations_hub',
      completion_status: 'review_required',
      review_status: 'pending_review',
      confidence_level: els.confidenceLevel.value || 'medium',
      raw_payload_json: {
        reference,
        description,
        amount,
        document_number: documentNumber || null,
        extracted_text: extractedText || null,
        domain_type: domainType,
        source_id: sourceId,
        bank_account_id: Number(els.bankAccount.value || 0) || null,
        counterparty_id: Number(els.counterparty.value || 0) || null,
        chart_account_id: Number(els.chartAccount.value || 0) || null,
        cost_center_id: Number(els.costCenter.value || 0) || null,
        entry_type: els.entryType.value,
        movement_nature: movementNature,
        competence_date: els.competenceDate.value || null,
        due_date: els.dueDate.value || null,
        ...fileMeta,
      },
      normalized_payload_json: {
        description: description || reference || 'Prestação de contas',
        amount,
        document_number: documentNumber || null,
        entry_type: els.entryType.value || 'payable',
        movement_nature: movementNature,
        competence_date: els.competenceDate.value || null,
        occurred_on: els.competenceDate.value || null,
        due_date: els.dueDate.value || null,
        counterparty_id: Number(els.counterparty.value || 0) || null,
        bank_account_id: Number(els.bankAccount.value || 0) || null,
        chart_account_id: Number(els.chartAccount.value || 0) || null,
        cost_center_id: Number(els.costCenter.value || 0) || null,
        notes: reviewNotes || null,
        metadata_json: {
          workflow_key: 'financial_accountability',
          origin_channel: 'operations_hub',
          linked_domain_type: domainType,
          linked_domain_source_id: sourceId,
        },
      },
      extracted_text: extractedText || null,
      review_notes: reviewNotes || null,
      metadata_json: {
        workflow_key: 'financial_accountability',
        file_size: fileMeta.file_size || null,
        stored_relative_path: fileMeta.stored_relative_path || null,
        public_url: fileMeta.public_url || null,
        sha256: fileMeta.sha256 || null,
        extraction_method: fileMeta.extraction_method || null,
        linked_domain_type: domainType,
        linked_domain_source_id: sourceId,
      },
    };
  }

  function renderPreview() {
    els.preview.textContent = JSON.stringify(buildPayload(), null, 2);
  }

  function showResult(message, isError = false) {
    els.result.classList.remove('hidden');
    els.result.classList.toggle('is-error', Boolean(isError));
    els.result.innerHTML = message;
  }

  function setUploadStatus(message, kind = 'neutral') {
    if (!els.uploadStatus) return;
    els.uploadStatus.textContent = message;
    els.uploadStatus.classList.remove('is-success', 'is-error');
    if (kind === 'success') els.uploadStatus.classList.add('is-success');
    if (kind === 'error') els.uploadStatus.classList.add('is-error');
  }

  async function uploadDocument() {
    if (!canCreate) {
      setUploadStatus('Você não possui permissão para enviar documentos.', 'error');
      return;
    }

    const file = els.file.files && els.file.files[0];
    if (!file) {
      setUploadStatus('Selecione um arquivo antes de executar o upload.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    els.upload.disabled = true;
    setUploadStatus('Enviando e processando arquivo...', 'neutral');

    try {
      const response = await fetch(`/api/financial/accountability/uploads?company_id=${companyId}`, {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || 'Falha ao processar arquivo da prestação de contas.');
      }
      uploadState.uploadedFile = result;
      if (!els.reference.value) {
        els.reference.value = result.file_name.replace(/\.[^.]+$/, '');
      }
      if (!els.extractedText.value && result.extracted_text) {
        els.extractedText.value = result.extracted_text;
      }
      setUploadStatus(`Arquivo processado: ${result.file_name} (${result.extraction_method}).`, 'success');
      renderPreview();
    } catch (error) {
      setUploadStatus(error.message, 'error');
    } finally {
      els.upload.disabled = false;
    }
  }

  async function createRecord() {
    if (!canCreate) {
      showResult('Você não possui permissão para criar registros de prestação de contas.', true);
      return;
    }

    const payload = buildPayload();
    if (!payload.origin_reference || !payload.normalized_payload_json.description || !(payload.normalized_payload_json.amount > 0)) {
      showResult('Preencha ao menos referência, descrição e valor da prestação de contas.', true);
      return;
    }

    els.submit.disabled = true;
    try {
      const response = await fetch(`/api/financial/ingestions?company_id=${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || 'Falha ao criar registro de ingestão financeira.');
      }
      showResult(`
        <strong>Registro criado com sucesso.</strong><br>
        ID da ingestão: <strong>#${result.id}</strong><br><br>
        <a href="/financial/automation" class="acc-btn acc-btn--primary">Abrir central de automação</a>
      `);
    } catch (error) {
      showResult(error.message, true);
    } finally {
      els.submit.disabled = false;
    }
  }

  setTodayIfEmpty();
  inferMovementNature();
  renderPreview();

  [
    els.reference,
    els.counterparty,
    els.amount,
    els.competenceDate,
    els.dueDate,
    els.documentNumber,
    els.file,
    els.entryType,
    els.description,
    els.extractedText,
    els.bankAccount,
    els.chartAccount,
    els.costCenter,
    els.domain,
    els.movementNature,
    els.confidenceLevel,
    els.reviewNotes,
  ].forEach((element) => {
    if (!element) return;
    const eventName = element.tagName === 'SELECT' || element.type === 'file' ? 'change' : 'input';
    element.addEventListener(eventName, renderPreview);
  });

  els.counterparty?.addEventListener('change', applyCounterpartyDefaults);
  els.file?.addEventListener('change', () => {
    uploadState.uploadedFile = null;
    setUploadStatus('Arquivo selecionado. Execute o upload para extrair e vincular o documento.', 'neutral');
    renderPreview();
  });
  els.entryType?.addEventListener('change', () => {
    inferMovementNature();
    renderPreview();
  });
  els.chartAccount?.addEventListener('change', () => {
    inferMovementNature();
    renderPreview();
  });
  els.refreshPreview?.addEventListener('click', renderPreview);
  els.upload?.addEventListener('click', uploadDocument);
  els.submit?.addEventListener('click', createRecord);
})();
