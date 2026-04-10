(() => {
    const SOURCE_LABELS = {
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

    const renderRaw = (raw) => {
        try {
            return escapeHtml(JSON.stringify(raw || {}, null, 2));
        } catch (error) {
            return escapeHtml(String(raw || ''));
        }
    };

    const eventTemplate = (event) => `
        <article class="ops-audit-event">
            <div class="ops-audit-event__top">
                <div>
                    <h3 class="ops-audit-event__title">${escapeHtml(event.title || 'Evento operacional')}</h3>
                    <div class="ops-audit-meta">
                        ${escapeHtml(formatDate(event.created_at))} · ${escapeHtml(event.actor || 'APP32')} · ${escapeHtml(event.channel || 'canal não informado')}
                    </div>
                </div>
                <span class="ops-audit-pill">${escapeHtml(SOURCE_LABELS[event.source] || event.source || 'auditoria')}</span>
            </div>
            <p>${escapeHtml(event.description || 'Sem descrição operacional.')}</p>
            <div class="ops-audit-meta">
                Entidade: ${escapeHtml(event.entity_type || '-')} #${escapeHtml(event.entity_id || '-')} · Status: ${escapeHtml(event.status || '-')}
            </div>
            <details>
                <summary>Ver payload auditado</summary>
                <pre>${renderRaw(event.raw)}</pre>
            </details>
        </article>
    `;

    const updateSummary = (summary = {}) => {
        const total = document.querySelector('[data-summary-total]');
        if (total) total.textContent = summary.total || 0;
        const bySource = summary.by_source || {};
        document.querySelectorAll('[data-summary-source]').forEach((item) => {
            item.textContent = bySource[item.dataset.summarySource] || 0;
        });
    };

    const boot = () => {
        const root = document.querySelector('.ops-audit-page');
        if (!root) return;

        const eventsTarget = document.getElementById('opsAuditEvents');
        const statusTarget = document.getElementById('opsAuditStatus');
        const sourceInput = document.getElementById('opsAuditSource');
        const limitInput = document.getElementById('opsAuditLimit');
        const refreshButton = document.getElementById('opsAuditRefresh');
        const companyId = root.dataset.companyId;

        const setStatus = (message) => {
            if (statusTarget) statusTarget.textContent = message;
        };

        const load = async () => {
            if (!companyId) {
                eventsTarget.innerHTML = '<div class="ops-audit-error">Selecione uma empresa ativa para carregar a auditoria operacional.</div>';
                setStatus('Sem empresa ativa');
                return;
            }

            setStatus('Carregando...');
            eventsTarget.innerHTML = '<div class="ops-audit-empty">Consultando trilhas operacionais...</div>';

            const params = new URLSearchParams({ company_id: companyId, limit: limitInput.value || '50' });
            if (sourceInput.value) params.set('source', sourceInput.value);

            try {
                const response = await fetch(`/api/operations/audit?${params.toString()}`, {
                    headers: { Accept: 'application/json' },
                    credentials: 'same-origin',
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || 'Falha ao carregar auditoria operacional.');
                }

                updateSummary(payload.summary || {});
                const events = payload.events || [];
                eventsTarget.innerHTML = events.length
                    ? events.map(eventTemplate).join('')
                    : '<div class="ops-audit-empty">Nenhuma trilha encontrada para os filtros selecionados.</div>';
                setStatus(`${events.length} evento(s)`);
            } catch (error) {
                updateSummary({ total: 0, by_source: {} });
                eventsTarget.innerHTML = `<div class="ops-audit-error">${escapeHtml(error.message)}</div>`;
                setStatus('Erro na consulta');
            }
        };

        refreshButton?.addEventListener('click', load);
        sourceInput?.addEventListener('change', load);
        load();
    };

    document.addEventListener('DOMContentLoaded', boot);
})();
