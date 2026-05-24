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

    function blockInput() {
        return document.getElementById('calendarEventBlockInput');
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
        listEl.innerHTML = '<div class="journey-item-empty">Carregando tarefas...</div>';
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
            listEl.innerHTML = `<div class="journey-item-empty">${payload.message || 'Erro ao carregar tarefas.'}</div>`;
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
                <span class="badge-pill">${events.length} tarefa(s)</span>
                <span class="badge-pill">${events.filter(event => event.status === 'done').length} concluído(s)</span>
            `;
        }
        if (!events.length) {
            listEl.innerHTML = '<div class="journey-item-empty">Nenhuma tarefa neste período.</div>';
            return;
        }
        listEl.innerHTML = events.map((event) => `
            <article class="journey-list-item agenda-feed-card">
                <div class="journey-list-item__top">
                    <div class="agenda-feed-card__main">
                        <strong class="agenda-feed-card__title">${escapeHtml(event.title || '')}</strong>
                        <div class="agenda-feed-card__meta">
                            ${formatDate(event.event_date)}${event.start_time ? ` • ${event.start_time}` : ''}${event.end_time ? ` → ${event.end_time}` : ''}
                        </div>
                    </div>
                    <div class="agenda-feed-card__badges">
                        <span class="badge-pill">${escapeHtml(event.status_label || event.status || '')}</span>
                        <span class="badge-pill">${escapeHtml(event.priority_label || event.priority || '')}</span>
                    </div>
                </div>
                <div class="agenda-feed-card__description">
                    ${event.description ? escapeHtml(event.description) : 'Sem descrição.'}
                </div>
                <div class="agenda-feed-card__footer">
                    <div class="agenda-feed-card__origin">
                        Origem: ${escapeHtml(event.source_label || 'Evento Avulso')}
                        ${event.source_code ? ` • ${escapeHtml(event.source_code)}` : ''}
                        ${event.source_title ? ` • ${escapeHtml(event.source_title)}` : ''}
                        ${event.block_name ? ` • Bloco: ${escapeHtml(event.block_name)}` : ''}
                    </div>
                    <div class="agenda-feed-card__actions">
                        ${event.source_url ? `<a class="btn btn-secondary btn-sm" href="${event.source_url}">${event.source_type === 'project_task' ? '+Horas/Info' : 'Abrir origem'}</a>` : ''}
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
        if (blockInput()) blockInput().value = event.block_id || '';
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
        if (blockInput()) blockInput().value = '';
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
            block_id: blockInput()?.value ? Number(blockInput().value) : null,
            description: document.getElementById('calendarEventDescriptionInput').value.trim() || null,
            execution_notes: document.getElementById('calendarEventExecutionNotesInput').value.trim() || null,
            source_type: (bootstrap.sourceType && bootstrap.sourceId) ? bootstrap.sourceType : 'manual',
            source_id: (bootstrap.sourceType && bootstrap.sourceId) ? bootstrap.sourceId : null,
        };
        if (!payload.title || !payload.event_date) {
            showMessage('Informe título e data da tarefa.', 'error');
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
            showMessage(result.message || 'Erro ao salvar tarefa.', 'error');
            return;
        }
        toggleForm(false);
        showMessage('Tarefa salva com sucesso.');
        await fetchEvents();
        window.WorkJourneyAgendas?.refresh?.();
    }

    async function removeEvent(eventId) {
        if (!confirm('Deseja excluir esta tarefa do calendário?')) return;
        const response = await fetch(`/api/companies/${companyId}/work-journey/calendar/events/${eventId}`, {
            method: 'DELETE',
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            showMessage(result.message || 'Erro ao excluir tarefa.', 'error');
            return;
        }
        showMessage('Tarefa removida.');
        await fetchEvents();
        window.WorkJourneyAgendas?.refresh?.();
    }

    function pythonWeekdayOfDate(dateText) {
        if (!dateText) return null;
        const current = new Date(`${dateText}T00:00:00`);
        if (Number.isNaN(current.getTime())) return null;
        return (current.getDay() + 6) % 7;
    }

    async function loadBlockOptions() {
        const select = blockInput();
        if (!select || !companyId || !selectedEmployeeId()) return;
        const response = await fetch(`/api/companies/${companyId}/work-journey/blocks?employee_id=${selectedEmployeeId()}`);
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            return;
        }
        const weekday = pythonWeekdayOfDate(document.getElementById('calendarEventDateInput')?.value || anchorDate());
        const currentValue = select.value;
        const options = (payload.blocks || []).filter((block) => {
            const weekdays = Array.isArray(block.weekdays) ? block.weekdays : [];
            return weekday === null || !weekdays.length || weekdays.includes(weekday);
        });
        select.innerHTML = '<option value="">Sem bloco</option>' + options.map((block) => (
            `<option value="${block.id}">${escapeHtml(block.name)} · ${escapeHtml(block.start_time || '--:--')} às ${escapeHtml(block.end_time || '--:--')}</option>`
        )).join('');
        if (currentValue && options.some((block) => String(block.id) === String(currentValue))) {
            select.value = currentValue;
        }
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
            sourceHint.textContent = `Nova tarefa vinculada à ${bootstrap.sourceType === 'project_task' ? 'atividade de projeto' : 'instância de processo'} #${bootstrap.sourceId}.`;
        }
        document.getElementById('calendarEventStartBtn')?.addEventListener('click', () => {
            resetForm();
            toggleForm(true);
            loadBlockOptions();
        });
        document.getElementById('calendarEventCancelBtn')?.addEventListener('click', () => toggleForm(false));
        form.addEventListener('submit', saveEvent);
        document.getElementById('journeyApplyFiltersBtn')?.addEventListener('click', () => setTimeout(fetchEvents, 0));
        document.getElementById('journeyRefreshBtn')?.addEventListener('click', () => setTimeout(fetchEvents, 0));
        document.getElementById('journeyDateInput')?.addEventListener('change', () => {
            fetchEvents();
            loadBlockOptions();
        });
        document.getElementById('journeyEmployeeSelect')?.addEventListener('change', () => {
            fetchEvents();
            loadBlockOptions();
        });
        document.getElementById('calendarEventDateInput')?.addEventListener('change', loadBlockOptions);
        document.addEventListener('workJourney:refreshed', loadBlockOptions);
        loadBlockOptions();
        fetchEvents();
    });
})();
