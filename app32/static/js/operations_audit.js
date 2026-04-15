(() => {
    const SOURCE_LABELS = {
        ai_mcp_runtime: 'IA / MCP runtime',
        human_review: 'Revisão humana',
        sapiens_workflow: 'Sapiens / workflow',
        agent_action: 'Ação de agente',
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

    const listMarkup = (values, emptyText = 'Sem dados.') => {
        const items = Array.isArray(values) ? values.filter(Boolean) : [];
        if (!items.length) return `<li>${escapeHtml(emptyText)}</li>`;
        return items.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
    };

    const rawMarkup = (raw) => {
        try {
            return escapeHtml(JSON.stringify(raw || {}, null, 2));
        } catch (error) {
            return escapeHtml(String(raw || ''));
        }
    };

    const summaryCardTemplate = (item) => `
        <article class="ops-audit-summary-card">
            <span>${escapeHtml(item.label || '-')}</span>
            <strong>${escapeHtml(item.value ?? 0)}</strong>
            <small>${escapeHtml(item.hint || '')}</small>
        </article>
    `;

    const eventButtonTemplate = (event, selectedId) => {
        const title = event.title || 'Evento operacional';
        const subtitle = [
            SOURCE_LABELS[event.source] || event.source || 'auditoria',
            event.tool_name || event.domain || event.channel || '',
            event.status || '',
        ].filter(Boolean).join(' · ');
        const isSelected = String(selectedId || '') === String(event.entity_id || '');
        return `
            <button type="button" class="int-tree-tool ops-audit-event-btn ${isSelected ? 'active' : ''}" data-event-id="${escapeHtml(event.entity_id || '')}">
                <strong>${escapeHtml(title)}</strong>
                <span>${escapeHtml(subtitle || 'Sem subtítulo')}</span>
            </button>
        `;
    };

    const approvalTemplate = (item) => {
        const approval = item.approval || {};
        const actionKey = approval.action_key || 'workflow';
        const objectCode = approval.object_code || item.title || `#${item.id || '-'}`;
        const status = approval.approval_status || item.status || 'unknown';
        const isToolGate = String(actionKey).startsWith('tool.');
        return `
            <article class="ops-audit-approval-card">
                <div class="ops-audit-approval-head">
                    <strong>${escapeHtml(actionKey)}</strong>
                    <span class="ops-audit-pill">${escapeHtml(status)}</span>
                </div>
                <div class="ops-audit-approval-title">${escapeHtml(objectCode)}</div>
                <div class="ops-audit-meta">${escapeHtml(item.title || '')}</div>
                <div class="ops-audit-meta">${escapeHtml(item.description || '')}</div>
                ${isToolGate ? '<div class="ops-audit-resume-hint">Após aprovar, peça ao Sapiens para repetir a mesma solicitação para retomar a tool com segurança.</div>' : ''}
            </article>
        `;
    };

    const analyticsTemplate = (analytics = {}) => {
        const cards = analytics.cards || [];
        const topTools = analytics.top_tools || [];
        const topDomains = analytics.top_domains || [];
        return `
            <div class="ops-audit-summary-grid">
                ${cards.map(summaryCardTemplate).join('')}
            </div>
            <div class="ops-audit-analytics-block">
                <span class="int-detail-label">Top tools</span>
                <ul>${listMarkup(topTools.map((item) => `${item.name} · ${item.count}`), 'Sem tools registradas.')}</ul>
            </div>
            <div class="ops-audit-analytics-block">
                <span class="int-detail-label">Top domínios</span>
                <ul>${listMarkup(topDomains.map((item) => `${item.name} · ${item.count}`), 'Sem domínios registrados.')}</ul>
            </div>
        `;
    };

    const renderDetail = (event) => {
        document.getElementById('opsAuditDetailTitle').textContent = event?.title || 'Selecione um evento';
        document.getElementById('opsAuditDetailSummary').textContent = event?.description || 'No centro exibimos o contexto técnico completo do evento auditado.';
        document.getElementById('opsAuditDetailSource').textContent = SOURCE_LABELS[event?.source] || event?.source || '-';
        document.getElementById('opsAuditDetailRuntime').textContent = [event?.runtime, event?.channel].filter(Boolean).join(' · ') || '-';
        document.getElementById('opsAuditDetailStatus').textContent = event?.status || '-';
        document.getElementById('opsAuditDetailTool').textContent = [event?.tool_name, event?.operation].filter(Boolean).join(' · ') || '-';
        document.getElementById('opsAuditDetailDomain').textContent = event?.domain || '-';
        document.getElementById('opsAuditDetailActor').textContent = event?.actor || '-';
        document.getElementById('opsAuditDetailTrace').innerHTML = listMarkup([
            event?.thread_id ? `thread: ${event.thread_id}` : '',
            event?.trace_id ? `trace: ${event.trace_id}` : '',
            event?.request_id ? `request: ${event.request_id}` : '',
            event?.created_at ? `ocorrido em: ${formatDate(event.created_at)}` : '',
        ], 'Sem correlação detalhada.');
        document.getElementById('opsAuditDetailGovernance').innerHTML = listMarkup([
            event?.scope ? `scope: ${event.scope}` : '',
            event?.domain ? `domínio: ${event.domain}` : '',
            event?.status ? `status: ${event.status}` : '',
            event?.metadata_preview?.reason ? `motivo: ${event.metadata_preview.reason}` : '',
            event?.metadata_preview?.risk ? `risk: ${event.metadata_preview.risk}` : '',
        ], 'Sem metadados extras de governança.');
        document.getElementById('opsAuditDetailRaw').textContent = rawMarkup(event?.raw || {});
    };

    const boot = () => {
        const root = document.querySelector('.ops-audit-page');
        if (!root) return;

        const state = {
            payload: null,
            filteredEvents: [],
            selectedEventId: null,
        };

        const companyId = root.dataset.companyId;
        const sourceInput = document.getElementById('opsAuditSource');
        const limitInput = document.getElementById('opsAuditLimit');
        const refreshButton = document.getElementById('opsAuditRefresh');
        const searchInput = document.getElementById('opsAuditSearchInput');
        const listTarget = document.getElementById('opsAuditEventsList');
        const summaryTarget = document.getElementById('opsAuditSummaryCards');
        const analyticsTarget = document.getElementById('opsAuditAnalytics');
        const approvalsTarget = document.getElementById('opsAuditApprovalsList');
        const statusTarget = document.getElementById('opsAuditStatus');
        const listHintTarget = document.getElementById('opsAuditListHint');

        const setStatus = (message) => {
            if (statusTarget) statusTarget.textContent = message;
        };

        const filterEvents = () => {
            const query = (searchInput.value || '').trim().toLowerCase();
            const events = state.payload?.events || [];
            state.filteredEvents = events.filter((event) => {
                const haystack = [
                    event.title,
                    event.description,
                    event.source,
                    event.runtime,
                    event.tool_name,
                    event.domain,
                    event.status,
                    event.channel,
                ].join(' ').toLowerCase();
                return !query || haystack.includes(query);
            });

            if (!state.filteredEvents.length) {
                listTarget.innerHTML = '<div class="int-empty">Nenhum evento corresponde aos filtros atuais.</div>';
                listHintTarget.textContent = 'Nenhum evento visível';
                renderDetail(null);
                return;
            }

            if (!state.filteredEvents.some((event) => String(event.entity_id || '') === String(state.selectedEventId || ''))) {
                state.selectedEventId = state.filteredEvents[0].entity_id;
            }

            listTarget.innerHTML = state.filteredEvents.map((event) => eventButtonTemplate(event, state.selectedEventId)).join('');
            listHintTarget.textContent = `${state.filteredEvents.length} evento(s) visíveis`;
            listTarget.querySelectorAll('[data-event-id]').forEach((button) => {
                button.addEventListener('click', () => {
                    state.selectedEventId = button.dataset.eventId;
                    filterEvents();
                });
            });

            renderDetail(state.filteredEvents.find((event) => String(event.entity_id || '') === String(state.selectedEventId || '')) || state.filteredEvents[0]);
        };

        const render = () => {
            const payload = state.payload || {};
            summaryTarget.innerHTML = (payload.analytics?.cards || []).map(summaryCardTemplate).join('');
            analyticsTarget.innerHTML = analyticsTemplate(payload.analytics || {});
            approvalsTarget.innerHTML = (payload.approvals || []).length
                ? payload.approvals.map(approvalTemplate).join('')
                : '<div class="int-empty">Nenhum approval operacional encontrado.</div>';
            filterEvents();
        };

        const load = async () => {
            if (!companyId) {
                listTarget.innerHTML = '<div class="int-empty">Selecione uma empresa ativa para carregar a auditoria operacional.</div>';
                approvalsTarget.innerHTML = '<div class="int-empty">Sem empresa ativa.</div>';
                setStatus('Sem empresa ativa');
                return;
            }

            setStatus('Atualizando...');
            listTarget.innerHTML = '<div class="int-empty">Consultando trilhas operacionais...</div>';
            approvalsTarget.innerHTML = '<div class="int-empty">Consultando approvals...</div>';

            const params = new URLSearchParams({ company_id: companyId, limit: limitInput.value || '50' });
            if (sourceInput.value) params.set('source', sourceInput.value);

            try {
                const response = await fetch(`/api/operations/audit?${params.toString()}`, {
                    headers: { Accept: 'application/json' },
                    credentials: 'same-origin',
                });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Falha ao carregar a auditoria operacional.');
                }
                state.payload = payload;
                state.selectedEventId = payload.events?.[0]?.entity_id || null;
                render();
                setStatus(`${(payload.events || []).length} evento(s) auditados`);
            } catch (error) {
                state.payload = { events: [], approvals: [], analytics: { cards: [] } };
                render();
                listTarget.innerHTML = `<div class="ops-audit-error">${escapeHtml(error.message)}</div>`;
                approvalsTarget.innerHTML = '<div class="ops-audit-error">Não foi possível carregar a fila de approvals.</div>';
                setStatus('Erro na consulta');
            }
        };

        refreshButton?.addEventListener('click', load);
        sourceInput?.addEventListener('change', load);
        searchInput?.addEventListener('input', filterEvents);
        load();
    };

    document.addEventListener('DOMContentLoaded', boot);
})();
