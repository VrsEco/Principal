(function () {
    function escapeHtml(value) {
        return String(value || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function showToastSafe(message, type = 'success') {
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }
        alert(message);
    }

    async function initCalendarPanel(root) {
        const companyId = Number(root.dataset.companyId || 0);
        const employeeId = Number(root.dataset.employeeId || 0);
        const sourceType = root.dataset.sourceType;
        const sourceId = Number(root.dataset.sourceId || 0);
        if (!companyId || !employeeId || !sourceType || !sourceId) return;

        const listEl = root.querySelector('[data-calendar-source-list]');
        const form = root.querySelector('[data-calendar-source-form]');
        const dateInput = root.querySelector('[data-calendar-source-date]');
        const titleInput = root.querySelector('[data-calendar-source-title]');
        const startInput = root.querySelector('[data-calendar-source-start]');
        const endInput = root.querySelector('[data-calendar-source-end]');
        const descInput = root.querySelector('[data-calendar-source-description]');
        const statusInput = root.querySelector('[data-calendar-source-status]');
        const priorityInput = root.querySelector('[data-calendar-source-priority]');

        async function loadEvents() {
            listEl.innerHTML = '<div class="text-tertiary">Carregando eventos...</div>';
            const params = new URLSearchParams({
                employee_id: String(employeeId),
                source_type: sourceType,
                source_id: String(sourceId),
            });
            const response = await fetch(`/api/companies/${companyId}/work-journey/calendar/events?${params.toString()}`);
            const payload = await response.json();
            if (!response.ok || !payload.success) {
                listEl.innerHTML = `<div class="text-danger">${payload.message || 'Erro ao carregar eventos.'}</div>`;
                return;
            }
            const items = payload.data || [];
            if (!items.length) {
                listEl.innerHTML = '<div class="text-tertiary">Nenhum evento vinculado.</div>';
                return;
            }
            listEl.innerHTML = items.map((event) => `
                <div class="dependency-item" style="align-items:flex-start;">
                    <div>
                        <strong>${escapeHtml(event.title)}</strong>
                        <div class="text-secondary" style="font-size:0.82rem;">${escapeHtml(event.event_date || '')}${event.start_time ? ` • ${escapeHtml(event.start_time)}` : ''}</div>
                        <div class="text-secondary" style="font-size:0.82rem;">${escapeHtml(event.status_label || event.status || '')} • ${escapeHtml(event.priority_label || event.priority || '')}</div>
                        ${event.description ? `<div style="margin-top:0.35rem;">${escapeHtml(event.description)}</div>` : ''}
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                        <a class="btn btn-secondary btn-sm" href="/calendar?employee_id=${employeeId}&source_type=${sourceType}&source_id=${sourceId}&date=${encodeURIComponent(event.event_date || '')}">Calendário</a>
                    </div>
                </div>
            `).join('');
        }

        form?.addEventListener('submit', async (submitEvent) => {
            submitEvent.preventDefault();
            const payload = {
                employee_id: employeeId,
                source_type: sourceType,
                source_id: sourceId,
                title: titleInput.value.trim(),
                event_date: dateInput.value,
                start_time: startInput.value || null,
                end_time: endInput.value || null,
                description: descInput.value.trim() || null,
                status: statusInput.value,
                priority: priorityInput.value,
            };
            if (!payload.title || !payload.event_date) {
                showToastSafe('Informe título e data do evento.', 'error');
                return;
            }
            const response = await fetch(`/api/companies/${companyId}/work-journey/calendar/events`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                showToastSafe(result.message || 'Erro ao salvar evento.', 'error');
                return;
            }
            form.reset();
            dateInput.value = new Date().toISOString().slice(0, 10);
            statusInput.value = 'planned';
            priorityInput.value = 'normal';
            showToastSafe('Evento criado com sucesso.');
            await loadEvents();
        });

        if (dateInput && !dateInput.value) {
            dateInput.value = new Date().toISOString().slice(0, 10);
        }
        await loadEvents();
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-calendar-source-panel]').forEach((panel) => {
            initCalendarPanel(panel);
        });
    });
})();
