(function () {
    const bootstrap = window.workJourneyBootstrap || {};
    const companyId = bootstrap.companyId;

    function selectedEmployeeId() {
        const el = document.getElementById('journeyEmployeeSelect');
        return el && el.value ? Number(el.value) : Number(bootstrap.selectedEmployeeId || 0);
    }

    function anchorDate() {
        const el = document.getElementById('journeyDateInput');
        return (el && el.value) || bootstrap.today;
    }

    function weekRange(dateText) {
        const current = new Date(`${dateText}T00:00:00`);
        const start = new Date(current);
        start.setDate(current.getDate() - current.getDay());
        const end = new Date(start);
        end.setDate(start.getDate() + 6);
        return {
            start: start.toISOString().slice(0, 10),
            end: end.toISOString().slice(0, 10),
        };
    }

    function showMessage(message, type = 'success') {
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }
        alert(message);
    }

    async function fetchEvents() {
        const listEl = document.getElementById('calendarEventsList');
        if (!listEl || !companyId || !selectedEmployeeId()) return;
        const range = weekRange(anchorDate());
        listEl.innerHTML = '<div class="text-tertiary p-3">Carregando eventos...</div>';
        const params = new URLSearchParams({
            employee_id: String(selectedEmployeeId()),
            start_date: range.start,
            end_date: range.end,
        });
        const sourceType = bootstrap.sourceType;
        const sourceId = bootstrap.sourceId;
        if (sourceType && sourceType !== 'manual' && sourceId) {
            params.set('source_type', sourceType);
            params.set('source_id', String(sourceId));
        }
        const response = await fetch(`/api/companies/${companyId}/work-journey/calendar/events?${params.toString()}`);
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            listEl.innerHTML = `<div class="text-danger p-3">${payload.message || 'Erro ao carregar eventos.'}</div>`;
            return;
        }
        renderEvents(payload.data || []);
    }

    function renderEvents(events) {
        const listEl = document.getElementById('calendarEventsList');
        const summaryEl = document.getElementById('calendarEventsSummary');
        if (!listEl) return;
        if (summaryEl) {
            summaryEl.innerHTML = `
                <span class="badge-pill">${events.length} evento(s)</span>
                <span class="badge-pill">${events.filter(event => event.status === 'done').length} concluído(s)</span>
            `;
        }
        if (!events.length) {
            listEl.innerHTML = '<div class="text-tertiary p-3">Nenhum evento neste período.</div>';
            return;
        }
        listEl.innerHTML = events.map((event) => `
            <article class="journey-item-card" style="margin-bottom:0.75rem;">
                <div class="journey-item-card__header">
                    <div>
                        <strong>${escapeHtml(event.title || '')}</strong>
                        <div class="text-secondary" style="font-size:0.85rem;">
                            ${formatDate(event.event_date)}${event.start_time ? ` • ${event.start_time}` : ''}${event.end_time ? ` → ${event.end_time}` : ''}
                        </div>
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:center;">
                        <span class="badge-pill">${escapeHtml(event.status_label || event.status || '')}</span>
                        <span class="badge-pill">${escapeHtml(event.priority_label || event.priority || '')}</span>
                    </div>
                </div>
                <div class="text-secondary" style="margin-top:0.5rem;">
                    ${event.description ? escapeHtml(event.description) : 'Sem descrição.'}
                </div>
                <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; flex-wrap:wrap; margin-top:0.75rem;">
                    <div class="text-secondary" style="font-size:0.82rem;">
                        Origem: ${escapeHtml(event.source_label || 'Evento livre')}
                        ${event.source_code ? ` • ${escapeHtml(event.source_code)}` : ''}
                        ${event.source_title ? ` • ${escapeHtml(event.source_title)}` : ''}
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                        ${event.source_url ? `<a class="btn btn-secondary btn-sm" href="${event.source_url}">Abrir origem</a>` : ''}
                        <button type="button" class="btn btn-secondary btn-sm" data-calendar-edit="${event.id}">Editar</button>
                        <button type="button" class="btn btn-outline btn-sm" data-calendar-delete="${event.id}">Excluir</button>
                    </div>
                </div>
            </article>
        `).join('');

        listEl.querySelectorAll('[data-calendar-edit]').forEach((button) => {
            button.addEventListener('click', () => startEdit(events.find(event => event.id === Number(button.dataset.calendarEdit))));
        });
        listEl.querySelectorAll('[data-calendar-delete]').forEach((button) => {
            button.addEventListener('click', () => removeEvent(Number(button.dataset.calendarDelete)));
        });
    }

    function startEdit(event) {
        if (!event) return;
        toggleForm(true);
        document.getElementById('calendarEventIdInput').value = event.id || '';
        document.getElementById('calendarEventTitleInput').value = event.title || '';
        document.getElementById('calendarEventDateInput').value = event.event_date || anchorDate();
        document.getElementById('calendarEventStartTimeInput').value = event.start_time || '';
        document.getElementById('calendarEventEndTimeInput').value = event.end_time || '';
        document.getElementById('calendarEventStatusInput').value = event.status || 'planned';
        document.getElementById('calendarEventPriorityInput').value = event.priority || 'normal';
        document.getElementById('calendarEventDescriptionInput').value = event.description || '';
        document.getElementById('calendarEventExecutionNotesInput').value = event.execution_notes || '';
    }

    function resetForm() {
        document.getElementById('calendarEventIdInput').value = '';
        document.getElementById('calendarEventTitleInput').value = '';
        document.getElementById('calendarEventDateInput').value = anchorDate();
        document.getElementById('calendarEventStartTimeInput').value = '';
        document.getElementById('calendarEventEndTimeInput').value = '';
        document.getElementById('calendarEventStatusInput').value = 'planned';
        document.getElementById('calendarEventPriorityInput').value = 'normal';
        document.getElementById('calendarEventDescriptionInput').value = '';
        document.getElementById('calendarEventExecutionNotesInput').value = '';
    }

    function toggleForm(show) {
        const form = document.getElementById('calendarEventForm');
        if (!form) return;
        form.style.display = show ? 'block' : 'none';
        if (!show) resetForm();
    }

    async function saveEvent(event) {
        event.preventDefault();
        const eventId = document.getElementById('calendarEventIdInput').value;
        const payload = {
            employee_id: selectedEmployeeId(),
            title: document.getElementById('calendarEventTitleInput').value.trim(),
            event_date: document.getElementById('calendarEventDateInput').value,
            start_time: document.getElementById('calendarEventStartTimeInput').value || null,
            end_time: document.getElementById('calendarEventEndTimeInput').value || null,
            status: document.getElementById('calendarEventStatusInput').value,
            priority: document.getElementById('calendarEventPriorityInput').value,
            description: document.getElementById('calendarEventDescriptionInput').value.trim() || null,
            execution_notes: document.getElementById('calendarEventExecutionNotesInput').value.trim() || null,
            source_type: (bootstrap.sourceType && bootstrap.sourceId) ? bootstrap.sourceType : 'manual',
            source_id: (bootstrap.sourceType && bootstrap.sourceId) ? bootstrap.sourceId : null,
        };
        if (!payload.title || !payload.event_date) {
            showMessage('Informe título e data do evento.', 'error');
            return;
        }
        const url = eventId
            ? `/api/companies/${companyId}/work-journey/calendar/events/${eventId}`
            : `/api/companies/${companyId}/work-journey/calendar/events`;
        const method = eventId ? 'PATCH' : 'POST';
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            showMessage(result.message || 'Erro ao salvar evento.', 'error');
            return;
        }
        toggleForm(false);
        showMessage('Evento salvo com sucesso.');
        await fetchEvents();
    }

    async function removeEvent(eventId) {
        if (!confirm('Deseja excluir este evento do calendário?')) return;
        const response = await fetch(`/api/companies/${companyId}/work-journey/calendar/events/${eventId}`, {
            method: 'DELETE',
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            showMessage(result.message || 'Erro ao excluir evento.', 'error');
            return;
        }
        showMessage('Evento removido.');
        await fetchEvents();
    }

    function formatDate(value) {
        if (!value) return 'Sem data';
        const [year, month, day] = value.split('-');
        return `${day}/${month}/${year}`;
    }

    function escapeHtml(value) {
        return String(value || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    document.addEventListener('DOMContentLoaded', () => {
        const form = document.getElementById('calendarEventForm');
        if (!form) return;
        const sourceHint = document.getElementById('calendarEventSourceHint');
        if (sourceHint && bootstrap.sourceType && bootstrap.sourceType !== 'manual' && bootstrap.sourceId) {
            sourceHint.textContent = `Novo evento vinculado a ${bootstrap.sourceType === 'project_task' ? 'atividade de projeto' : 'instância de processo'} #${bootstrap.sourceId}.`;
        }
        document.getElementById('calendarEventStartBtn')?.addEventListener('click', () => {
            resetForm();
            toggleForm(true);
        });
        document.getElementById('calendarEventCancelBtn')?.addEventListener('click', () => toggleForm(false));
        form.addEventListener('submit', saveEvent);
        document.getElementById('journeyApplyFiltersBtn')?.addEventListener('click', () => setTimeout(fetchEvents, 0));
        document.getElementById('journeyRefreshBtn')?.addEventListener('click', () => setTimeout(fetchEvents, 0));
        document.getElementById('journeyDateInput')?.addEventListener('change', fetchEvents);
        document.getElementById('journeyEmployeeSelect')?.addEventListener('change', fetchEvents);
        fetchEvents();
    });
})();
