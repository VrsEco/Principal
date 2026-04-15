
(() => {
    const SOURCE_LABELS = {
        human_review: 'Revisões humanas',
        sapiens_workflow: 'Sapiens / workflows',
        agent_action: 'Ações de agentes / MCP',
    };

    const escapeHtml = (value) => String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');

    const formatDate = (value) => {
        if (!value) return 'Sem data';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleString('pt-BR');
    };

    const eventTemplate = (event) => `
        <article class="ai-monitoring-event">
            <div class="ai-monitoring-event__top">
                <div>
                    <strong>${escapeHtml(event.title || 'Evento operacional')}</strong>
                    <span>${escapeHtml(formatDate(event.created_at))} · ${escapeHtml(event.actor || 'APP32')} · ${escapeHtml(event.channel || 'canal não informado')}</span>
                </div>
                <mark>${escapeHtml(SOURCE_LABELS[event.source] || event.source || 'auditoria')}</mark>
            </div>
            <p>${escapeHtml(event.description || 'Sem descrição operacional.')}</p>
        </article>
    `;

    const requestTemplate = (item) => `
        <article class="ai-monitoring-request-item">
            <strong>${escapeHtml(item.title || 'Solicitação')}</strong>
            <span>${escapeHtml(item.request_kind_label || item.request_kind || 'Solicitação')} · ${escapeHtml(item.status_label || '-')}</span>
            <small>${escapeHtml(item.backlog_task_code || ('#' + (item.backlog_task_id || '-')))}</small>
        </article>
    `;

    const boot = () => {
        const root = document.querySelector('[data-monitoring-page="true"]');
        if (!root) return;

        const companyId = root.dataset.companyId;
        const panelEndpoint = root.dataset.panelEndpoint;
        const requestsEndpoint = root.dataset.requestsEndpoint;
        const requestEndpoint = root.dataset.requestEndpoint;
        const pdfExportUrl = root.dataset.pdfExportUrl;
        const summaryTargets = Array.from(document.querySelectorAll('[data-summary-key]'));
        const sourceInput = document.getElementById('aiMonitoringSource');
        const limitInput = document.getElementById('aiMonitoringLimit');
        const refreshButton = document.getElementById('aiMonitoringRefresh');
        const exportButton = document.getElementById('aiMonitoringExportPdf');
        const openRequestButton = document.getElementById('aiMonitoringOpenRequest');
        const cancelRequestButton = document.getElementById('aiMonitoringCancelRequest');
        const requestPanel = document.getElementById('aiMonitoringRequestPanel');
        const requestForm = document.getElementById('aiMonitoringRequestForm');
        const requestFeedback = document.getElementById('aiMonitoringRequestFeedback');
        const eventsTarget = document.getElementById('aiMonitoringEvents');
        const requestsTarget = document.getElementById('aiMonitoringRequestList');
        const statusTarget = document.getElementById('aiMonitoringPanelStatus');

        const setStatus = (value) => {
            if (statusTarget) statusTarget.textContent = value;
        };

        const setFeedback = (message, isError = false) => {
            if (!requestFeedback) return;
            requestFeedback.hidden = !message;
            requestFeedback.textContent = message || '';
            requestFeedback.classList.toggle('is-error', Boolean(isError));
        };

        const summarizeEvidence = (panel) => {
            const summary = panel?.summary || {};
            const bySource = summary.by_source || {};
            return [
                `Total de eventos: ${summary.total || 0}`,
                `Revisões humanas: ${bySource.human_review || 0}`,
                `Sapiens/workflows: ${bySource.sapiens_workflow || 0}`,
                `Ações de agentes: ${bySource.agent_action || 0}`,
                `Filtro atual: ${SOURCE_LABELS[sourceInput?.value] || 'Todas as fontes'}`,
            ].join(' | ');
        };

        const updateSummary = (panel) => {
            const summary = panel?.summary || {};
            const bySource = summary.by_source || {};
            const values = [
                summary.total || 0,
                bySource.human_review || 0,
                bySource.sapiens_workflow || 0,
                bySource.agent_action || 0,
            ];
            summaryTargets.forEach((target, index) => {
                target.textContent = values[index] ?? 0;
            });
        };

        const loadPanel = async () => {
            if (!companyId) {
                eventsTarget.innerHTML = '<div class="ai-monitoring-empty">Selecione uma empresa ativa para carregar o monitoramento.</div>';
                setStatus('Sem empresa ativa');
                return null;
            }

            setStatus('Carregando...');
            const params = new URLSearchParams({ company_id: companyId, limit: limitInput?.value || root.dataset.defaultLimit || '12' });
            if (sourceInput?.value) params.set('source', sourceInput.value);

            try {
                const response = await fetch(`${panelEndpoint}?${params.toString()}`, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Falha ao consultar monitoramento.');
                }
                const panel = payload.panel || {};
                updateSummary(panel);
                const events = panel.events || [];
                eventsTarget.innerHTML = events.length
                    ? events.map(eventTemplate).join('')
                    : '<div class="ai-monitoring-empty">Nenhum evento encontrado para os filtros selecionados.</div>';
                if (requestForm) {
                    requestForm.elements.source_filter.value = sourceInput?.value || '';
                    requestForm.elements.evidence_summary.value = summarizeEvidence(panel);
                }
                setStatus(`${events.length} evento(s)`);
                return panel;
            } catch (error) {
                updateSummary({ summary: { total: 0, by_source: {} } });
                eventsTarget.innerHTML = `<div class="ai-monitoring-empty">${escapeHtml(error.message)}</div>`;
                setStatus('Erro na consulta');
                return null;
            }
        };

        const loadRequests = async () => {
            try {
                const response = await fetch(`${requestsEndpoint}?limit=10`, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Falha ao carregar solicitações.');
                }
                const items = payload.requests || [];
                requestsTarget.innerHTML = items.length
                    ? items.map(requestTemplate).join('')
                    : '<div class="ai-monitoring-empty">Nenhuma solicitação aberta por esta tela até agora.</div>';
            } catch (error) {
                requestsTarget.innerHTML = `<div class="ai-monitoring-empty">${escapeHtml(error.message)}</div>`;
            }
        };

        refreshButton?.addEventListener('click', () => { void loadPanel(); });
        sourceInput?.addEventListener('change', () => { void loadPanel(); });

        exportButton?.addEventListener('click', () => {
            const params = new URLSearchParams({ company_id: companyId, limit: limitInput?.value || root.dataset.defaultLimit || '12' });
            if (sourceInput?.value) params.set('source', sourceInput.value);
            window.location.href = `${pdfExportUrl}?${params.toString()}`;
        });

        openRequestButton?.addEventListener('click', () => {
            if (requestPanel) requestPanel.hidden = false;
            setFeedback('');
            requestForm?.elements.title?.focus();
        });

        cancelRequestButton?.addEventListener('click', () => {
            if (requestPanel) requestPanel.hidden = true;
            requestForm?.reset();
            if (requestForm) {
                requestForm.elements.source_filter.value = sourceInput?.value || '';
                requestForm.elements.evidence_summary.value = '';
            }
            setFeedback('');
        });

        requestForm?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = Object.fromEntries(new FormData(requestForm).entries());
            setFeedback('Criando card no backlog...');
            try {
                const response = await fetch(requestEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Falha ao criar solicitação.');
                }
                const item = payload.request || {};
                setFeedback(`Card criado em AA.J.31: ${item.backlog_task_code || ('#' + item.backlog_task_id)}.`);
                requestForm.reset();
                requestForm.elements.source_filter.value = sourceInput?.value || '';
                await loadRequests();
            } catch (error) {
                setFeedback(error.message, true);
            }
        });

        void loadPanel();
        void loadRequests();
    };

    document.addEventListener('DOMContentLoaded', boot);
})();
