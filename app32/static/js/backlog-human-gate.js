(function () {
    const state = {
        getTaskById: null,
        afterOperation: null,
        notify: null,
        isReadOnly: false,
        activeTaskId: null,
        activeOperation: null,
        boardFilterMode: 'all',
        onBoardFilterChange: null,
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getHumanGate(task) {
        return task && task.backlog_human_gate && task.backlog_human_gate.enabled
            ? task.backlog_human_gate
            : null;
    }

    function shouldLockTask(task) {
        return Boolean(getHumanGate(task));
    }

    function getStatusMeta(statusRaw) {
        const status = String(statusRaw || '').trim().toLowerCase();
        if (status === 'pending') return { label: 'Pendente', tone: 'warning' };
        if (status === 'expired') return { label: 'Expirado', tone: 'danger' };
        if (status === 'approved') return { label: 'Aprovado', tone: 'info' };
        if (status === 'executed') return { label: 'Executado', tone: 'success' };
        if (status === 'rejected') return { label: 'Rejeitado', tone: 'muted' };
        if (status === 'awaiting_approval') return { label: 'Aguardando aprovação', tone: 'warning' };
        if (status === 'failed') return { label: 'Falhou', tone: 'danger' };
        if (status === 'rolled_back') return { label: 'Rollback', tone: 'muted' };
        return { label: statusRaw || 'Operacional', tone: 'muted' };
    }

    function getOperationMeta(operationId, fallbackLabel) {
        const operation = String(operationId || '').trim().toLowerCase();
        const defaultMeta = {
            label: fallbackLabel || operation || 'Executar',
            needsFeedback: false,
            confirmTitle: fallbackLabel || 'Executar operação',
            confirmDescription: 'Confirme a operação deste card operacional.',
        };

        if (operation === 'approve') {
            return {
                label: fallbackLabel || 'Aprovar',
                needsFeedback: false,
                confirmTitle: fallbackLabel || 'Confirmar aprovação',
                confirmDescription: 'Esta ação executará o fluxo operacional vinculado ao card.',
            };
        }
        if (operation === 'reject') {
            return {
                label: fallbackLabel || 'Rejeitar',
                needsFeedback: true,
                confirmTitle: fallbackLabel || 'Confirmar rejeição',
                confirmDescription: 'Você pode registrar um feedback opcional para auditoria.',
            };
        }
        if (operation === 'revalidate') {
            return {
                label: fallbackLabel || 'Revalidar',
                needsFeedback: false,
                confirmTitle: fallbackLabel || 'Revalidar prazo',
                confirmDescription: 'Esta ação renovará o prazo operacional do approval.',
            };
        }
        if (operation === 'rollback') {
            return {
                label: fallbackLabel || 'Rollback',
                needsFeedback: false,
                confirmTitle: fallbackLabel || 'Confirmar rollback',
                confirmDescription: 'Esta ação reverterá o hotfix previamente aplicado.',
            };
        }
        return defaultMeta;
    }

    function getActionLabel(action) {
        if (!action || !action.id) return '';
        const type = String(action.type || '').trim().toLowerCase();
        if (type === 'workflow_approval_request') return 'Workflow HITL';
        if (type === 'approval_request') return 'Aprovação legada';
        if (type === 'technical_fix') return 'Hotfix técnico';
        return action.type || 'Operacional';
    }

    function isPendingLikeStatus(statusRaw) {
        const status = String(statusRaw || '').trim().toLowerCase();
        return ['pending', 'awaiting_approval', 'expired'].includes(status);
    }

    function getOperationalHealth(humanGate) {
        const fallback = {
            age_label: 'N/D',
            age_hours: null,
            queue_bucket: 'unknown',
            badges: [],
            requires_attention: false,
            requires_reprocess: false,
            has_pending_error: false,
            sla: { label: 'Sem SLA', tone: 'muted', bucket: 'unknown' },
        };
        if (!humanGate || !humanGate.operational_health) return fallback;
        return {
            ...fallback,
            ...humanGate.operational_health,
            sla: {
                ...fallback.sla,
                ...(humanGate.operational_health.sla || {}),
            },
            badges: Array.isArray(humanGate.operational_health.badges) ? humanGate.operational_health.badges : [],
        };
    }

    function hasOperationalBadge(humanGate, badgeId) {
        return getOperationalHealth(humanGate).badges.some((badge) => badge && badge.id === badgeId);
    }

    function taskMatchesBoardFilter(task, mode = null) {
        const filterMode = String(mode || state.boardFilterMode || 'all').trim().toLowerCase();
        const humanGate = getHumanGate(task);
        const health = getOperationalHealth(humanGate);
        const effectiveStatus = String(humanGate?.effective_status || humanGate?.agent_action_status || '').trim().toLowerCase();

        if (filterMode === 'all') return true;
        if (!humanGate) return false;
        if (filterMode === 'hitl') return true;
        if (filterMode === 'pending') return isPendingLikeStatus(effectiveStatus);
        if (filterMode === 'attention') return Boolean(health.requires_attention);
        if (filterMode === 'reprocess') return Boolean(health.requires_reprocess || health.has_pending_error);
        return true;
    }

    function filterTasks(tasks, mode = null) {
        if (!Array.isArray(tasks)) return [];
        return tasks.filter((task) => taskMatchesBoardFilter(task, mode));
    }

    function buildBoardMetrics(tasks) {
        const all = Array.isArray(tasks) ? tasks : [];
        const hitlTasks = all.filter((task) => Boolean(getHumanGate(task)));
        const pending = hitlTasks.filter((task) => {
            const humanGate = getHumanGate(task);
            return isPendingLikeStatus(humanGate?.effective_status || humanGate?.agent_action_status);
        }).length;
        const attention = hitlTasks.filter((task) => getOperationalHealth(getHumanGate(task)).requires_attention).length;
        const reprocess = hitlTasks.filter((task) => {
            const health = getOperationalHealth(getHumanGate(task));
            return Boolean(health.requires_reprocess || health.has_pending_error);
        }).length;

        const oldestHours = hitlTasks.reduce((maxValue, task) => {
            const ageHours = getOperationalHealth(getHumanGate(task)).age_hours;
            return typeof ageHours === 'number' && ageHours > maxValue ? ageHours : maxValue;
        }, 0);

        return {
            totalHitl: hitlTasks.length,
            pending,
            attention,
            reprocess,
            oldestHours,
            oldestAgeLabel: oldestHours > 0 ? `${oldestHours}h` : '0h',
            visibleHitl: filterTasks(hitlTasks).length,
        };
    }

    function getBoardFilterOptions(tasks) {
        const metrics = buildBoardMetrics(tasks);
        return [
            { id: 'all', label: 'Tudo', count: Array.isArray(tasks) ? tasks.length : 0 },
            { id: 'hitl', label: 'Só HITL', count: metrics.totalHitl },
            { id: 'pending', label: 'Pendentes', count: metrics.pending },
            { id: 'attention', label: 'Atenção SLA', count: metrics.attention },
            { id: 'reprocess', label: 'Erro/Reprocesso', count: metrics.reprocess },
        ];
    }

    function setBoardFilter(mode) {
        state.boardFilterMode = String(mode || 'all').trim().toLowerCase() || 'all';
        if (typeof state.onBoardFilterChange === 'function') {
            state.onBoardFilterChange({ mode: state.boardFilterMode });
        }
    }

    function formatTimestamp(value) {
        if (!value) return '';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return String(value);
        }
        return parsed.toLocaleString('pt-BR');
    }

    function formatStatusTransition(entry) {
        if (!entry) return '';
        const before = entry.status_before ? getStatusMeta(entry.status_before).label : '';
        const after = entry.status_after ? getStatusMeta(entry.status_after).label : '';
        if (before && after) return `${before} → ${after}`;
        return after || before || '';
    }

    function buildTimelineMeta(entry) {
        const items = [];
        if (entry && entry.author) items.push(`por ${entry.author}`);
        const statusTransition = formatStatusTransition(entry);
        if (statusTransition) items.push(`status: ${statusTransition}`);
        return items;
    }

    function renderLastEvent(humanGate) {
        const entry = humanGate && humanGate.last_event ? humanGate.last_event : null;
        if (!entry) return '';

        const tone = entry.tone || (entry.success === false ? 'danger' : 'info');
        const timestamp = formatTimestamp(entry.timestamp);
        const metaItems = buildTimelineMeta(entry);

        return `
            <div class="backlog-human-gate-last-event tone-${escapeHtml(tone)}">
                <div class="backlog-human-gate-last-event-head">
                    <strong>${escapeHtml(entry.label || 'Último evento')}</strong>
                    ${timestamp ? `<span class="backlog-human-gate-last-event-time">${escapeHtml(timestamp)}</span>` : ''}
                </div>
                <div class="backlog-human-gate-last-event-summary">
                    ${escapeHtml(entry.summary || entry.message || 'Atualização operacional registrada.')}
                </div>
                ${metaItems.length ? `<div class="backlog-human-gate-last-event-meta">${escapeHtml(metaItems.join(' · '))}</div>` : ''}
            </div>
        `;
    }

    function renderTimelineItem(entry) {
        if (!entry) return '';
        const tone = entry.tone || (entry.success === false ? 'danger' : 'info');
        const timestamp = formatTimestamp(entry.timestamp);
        const metaItems = buildTimelineMeta(entry);

        return `
            <div class="backlog-human-gate-timeline-item">
                <span class="backlog-human-gate-timeline-dot tone-${escapeHtml(tone)}" aria-hidden="true"></span>
                <div class="backlog-human-gate-timeline-content">
                    <div class="backlog-human-gate-timeline-head">
                        <strong>${escapeHtml(entry.label || 'Evento operacional')}</strong>
                        ${timestamp ? `<span class="backlog-human-gate-timeline-time">${escapeHtml(timestamp)}</span>` : ''}
                    </div>
                    <div class="backlog-human-gate-timeline-summary">
                        ${escapeHtml(entry.summary || entry.message || 'Atualização operacional registrada.')}
                    </div>
                    ${metaItems.length ? `<div class="backlog-human-gate-timeline-meta">${escapeHtml(metaItems.join(' · '))}</div>` : ''}
                    ${entry.feedback ? `<div class="backlog-human-gate-timeline-feedback">Feedback: ${escapeHtml(entry.feedback)}</div>` : ''}
                </div>
            </div>
        `;
    }

    function renderTimeline(humanGate) {
        const entries = Array.isArray(humanGate && humanGate.timeline) ? humanGate.timeline : [];
        if (!entries.length) {
            return '<div class="backlog-human-gate-timeline-empty">Nenhum histórico operacional registrado ainda.</div>';
        }

        return `
            <div class="backlog-human-gate-timeline">
                ${entries.map((entry) => renderTimelineItem(entry)).join('')}
            </div>
        `;
    }

    function renderOperationalBadges(humanGate) {
        const health = getOperationalHealth(humanGate);
        const parts = [
            `<span class="backlog-human-gate-chip tone-${escapeHtml(health.sla?.tone || 'muted')}">SLA · ${escapeHtml(health.sla?.label || 'Sem SLA')}</span>`,
            `<span class="backlog-human-gate-chip tone-muted">Idade · ${escapeHtml(health.age_label || 'N/D')}</span>`,
        ];

        (health.badges || []).forEach((badge) => {
            parts.push(
                `<span class="backlog-human-gate-chip tone-${escapeHtml(badge.tone || 'info')}">${escapeHtml(badge.label || badge.id || 'Operacional')}</span>`
            );
        });

        return `<div class="backlog-human-gate-operational-row">${parts.join('')}</div>`;
    }

    function renderBoardSection(tasks) {
        const metrics = buildBoardMetrics(tasks);
        const filterOptions = getBoardFilterOptions(tasks);
        const activeMode = String(state.boardFilterMode || 'all').trim().toLowerCase();

        return `
            <div class="backlog-human-gate-board-panel">
                <div class="backlog-human-gate-board-head">
                    <div>
                        <div class="backlog-human-gate-eyebrow">Cockpit HITL do backlog</div>
                        <div class="backlog-human-gate-board-title">Fila operacional unificada do board</div>
                    </div>
                    <div class="backlog-human-gate-board-caption">
                        ${metrics.totalHitl} card(s) HITL mapeado(s) · ${metrics.visibleHitl} no recorte atual
                    </div>
                </div>
                <div class="backlog-human-gate-board-stats">
                    <div class="backlog-human-gate-board-stat">
                        <span>Total HITL</span>
                        <strong>${metrics.totalHitl}</strong>
                    </div>
                    <div class="backlog-human-gate-board-stat">
                        <span>Pendentes</span>
                        <strong>${metrics.pending}</strong>
                    </div>
                    <div class="backlog-human-gate-board-stat">
                        <span>Atenção SLA</span>
                        <strong>${metrics.attention}</strong>
                    </div>
                    <div class="backlog-human-gate-board-stat">
                        <span>Erro/Reprocesso</span>
                        <strong>${metrics.reprocess}</strong>
                    </div>
                    <div class="backlog-human-gate-board-stat">
                        <span>Maior idade</span>
                        <strong>${escapeHtml(metrics.oldestAgeLabel)}</strong>
                    </div>
                </div>
                <div class="backlog-human-gate-board-filters">
                    ${filterOptions.map((option) => `
                        <button
                            type="button"
                            class="backlog-human-gate-filter-chip ${option.id === activeMode ? 'active' : ''}"
                            onclick="window.BacklogHumanGate.setBoardFilter('${escapeHtml(option.id)}')">
                            <span>${escapeHtml(option.label)}</span>
                            <strong>${escapeHtml(option.count)}</strong>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function mountBoardSection(tasks, container) {
        if (!container) return;
        container.innerHTML = renderBoardSection(tasks);
        container.style.display = 'block';
    }

    function getOperationButtonsHtml(task, options = {}) {
        const humanGate = getHumanGate(task);
        if (!humanGate) return '';
        const operations = Array.isArray(humanGate.available_operations) ? humanGate.available_operations : [];
        if (!operations.length || state.isReadOnly) return '';

        const compact = Boolean(options.compact);
        return `
            <div class="backlog-human-gate-actions ${compact ? 'compact' : ''}">
                ${operations.map((operation) => `
                    <button
                        type="button"
                        class="backlog-human-gate-action tone-${escapeHtml(operation.style || 'secondary')}"
                        onclick="window.BacklogHumanGate.handleAction(${Number(task.id)}, '${escapeHtml(operation.id)}', event)">
                        ${escapeHtml(operation.label || operation.id)}
                    </button>
                `).join('')}
            </div>
        `;
    }

    function renderCardSection(task) {
        const humanGate = getHumanGate(task);
        if (!humanGate) return '';

        const statusMeta = getStatusMeta(humanGate.effective_status || humanGate.agent_action_status);
        const actionSummary = humanGate.action || {};
        const objectCode = actionSummary?.approval?.object_code || actionSummary?.approval?.action_key || actionSummary?.title_plain || actionSummary?.title;

        return `
            <div class="backlog-human-gate-card-strip">
                <div class="backlog-human-gate-card-top">
                    <span class="backlog-human-gate-badge tone-${escapeHtml(statusMeta.tone)}">
                        HITL · ${escapeHtml(statusMeta.label)}
                    </span>
                    <span class="backlog-human-gate-kind">${escapeHtml(getActionLabel(actionSummary))}</span>
                </div>
                ${objectCode ? `<div class="backlog-human-gate-caption">${escapeHtml(objectCode)}</div>` : ''}
                ${renderOperationalBadges(humanGate)}
                ${renderLastEvent(humanGate)}
                ${getOperationButtonsHtml(task, { compact: true })}
            </div>
        `;
    }

    function mountTaskSection(task, container) {
        if (!container) return;

        const humanGate = getHumanGate(task);
        if (!humanGate) {
            container.innerHTML = '';
            container.style.display = 'none';
            return;
        }

        const actionSummary = humanGate.action || {};
        const statusMeta = getStatusMeta(humanGate.effective_status || humanGate.agent_action_status);
        const approval = actionSummary.approval || {};
        const objectCode = approval.object_code || actionSummary.title_plain || actionSummary.title || `#${humanGate.agent_action_id}`;
        const description = actionSummary.subtitle || actionSummary.description || '';

        container.style.display = 'block';
        container.innerHTML = `
            <div class="backlog-human-gate-panel">
                <div class="backlog-human-gate-panel-head">
                    <div>
                        <div class="backlog-human-gate-eyebrow">Cockpit HITL</div>
                        <div class="backlog-human-gate-title">${escapeHtml(objectCode)}</div>
                    </div>
                    <span class="backlog-human-gate-badge tone-${escapeHtml(statusMeta.tone)}">
                        ${escapeHtml(statusMeta.label)}
                    </span>
                </div>
                ${description ? `<div class="backlog-human-gate-description">${escapeHtml(description)}</div>` : ''}
                <div class="backlog-human-gate-meta-grid">
                    <div><span>Tipo</span><strong>${escapeHtml(getActionLabel(actionSummary))}</strong></div>
                    <div><span>Action ID</span><strong>#${escapeHtml(humanGate.agent_action_id)}</strong></div>
                    <div><span>Empresa origem</span><strong>${escapeHtml(humanGate.source_company_id || '-')}</strong></div>
                    <div><span>Status</span><strong>${escapeHtml(statusMeta.label)}</strong></div>
                    <div><span>Idade</span><strong>${escapeHtml(getOperationalHealth(humanGate).age_label || 'N/D')}</strong></div>
                    <div><span>SLA</span><strong>${escapeHtml(getOperationalHealth(humanGate).sla?.label || 'Sem SLA')}</strong></div>
                </div>
                ${getOperationButtonsHtml(task)}
                ${renderOperationalBadges(humanGate)}
                ${renderLastEvent(humanGate)}
                <div class="backlog-human-gate-timeline-block">
                    <div class="backlog-human-gate-section-title">Histórico operacional</div>
                    ${renderTimeline(humanGate)}
                </div>
                <div class="backlog-human-gate-help">
                    Este card é espelhado da fila operacional. O fluxo normal do card fica em modo leitura.
                </div>
            </div>
        `;
    }

    function ensureModal() {
        if (document.getElementById('backlogHumanGateActionModal')) return;

        const wrapper = document.createElement('div');
        wrapper.id = 'backlogHumanGateActionModal';
        wrapper.className = 'backlog-human-gate-modal-backdrop';
        wrapper.innerHTML = `
            <div class="backlog-human-gate-modal-card">
                <div class="backlog-human-gate-modal-header">
                    <div>
                        <div class="backlog-human-gate-eyebrow">Operação do backlog</div>
                        <h3 id="backlogHumanGateActionTitle">Confirmar operação</h3>
                    </div>
                    <button type="button" class="backlog-human-gate-modal-close" onclick="window.BacklogHumanGate.closeActionModal()">×</button>
                </div>
                <div class="backlog-human-gate-modal-body">
                    <p id="backlogHumanGateActionDescription" class="backlog-human-gate-modal-description"></p>
                    <div id="backlogHumanGateActionTaskMeta" class="backlog-human-gate-modal-meta"></div>
                    <div id="backlogHumanGateFeedbackWrap" class="backlog-human-gate-feedback-wrap" style="display:none;">
                        <label for="backlogHumanGateFeedbackInput">Feedback</label>
                        <textarea id="backlogHumanGateFeedbackInput" rows="3" placeholder="Opcional: informe o motivo ou contexto."></textarea>
                    </div>
                </div>
                <div class="backlog-human-gate-modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="window.BacklogHumanGate.closeActionModal()">Cancelar</button>
                    <button type="button" class="btn btn-primary" id="backlogHumanGateConfirmButton" onclick="window.BacklogHumanGate.confirmAction()">Confirmar</button>
                </div>
            </div>
        `;
        wrapper.addEventListener('click', (event) => {
            if (event.target === wrapper) {
                closeActionModal();
            }
        });
        document.body.appendChild(wrapper);
    }

    function openActionModal(task, operationId) {
        ensureModal();
        const modal = document.getElementById('backlogHumanGateActionModal');
        const taskMeta = document.getElementById('backlogHumanGateActionTaskMeta');
        const titleEl = document.getElementById('backlogHumanGateActionTitle');
        const descriptionEl = document.getElementById('backlogHumanGateActionDescription');
        const feedbackWrap = document.getElementById('backlogHumanGateFeedbackWrap');
        const feedbackInput = document.getElementById('backlogHumanGateFeedbackInput');
        const confirmButton = document.getElementById('backlogHumanGateConfirmButton');

        const humanGate = getHumanGate(task);
        if (!humanGate) {
            (state.notify || window.alert)('Este card não possui operação HITL disponível.');
            return;
        }

        const available = (humanGate.available_operations || []).find((item) => item.id === operationId);
        const operationMeta = getOperationMeta(operationId, available?.label);
        const statusMeta = getStatusMeta(humanGate.effective_status || humanGate.agent_action_status);

        state.activeTaskId = Number(task.id);
        state.activeOperation = operationId;
        titleEl.textContent = operationMeta.confirmTitle;
        descriptionEl.textContent = operationMeta.confirmDescription;
        taskMeta.innerHTML = `
            <span>${escapeHtml(task.code || `#${task.id}`)}</span>
            <span>·</span>
            <span>${escapeHtml(getActionLabel(humanGate.action || {}))}</span>
            <span>·</span>
            <span>${escapeHtml(statusMeta.label)}</span>
        `;

        feedbackWrap.style.display = operationMeta.needsFeedback ? 'block' : 'none';
        feedbackInput.value = '';
        confirmButton.textContent = operationMeta.label;
        modal.classList.add('open');
    }

    function closeActionModal() {
        const modal = document.getElementById('backlogHumanGateActionModal');
        if (modal) modal.classList.remove('open');
        state.activeTaskId = null;
        state.activeOperation = null;
    }

    async function confirmAction() {
        const notify = state.notify || window.alert;
        const task = typeof state.getTaskById === 'function' ? state.getTaskById(state.activeTaskId) : null;
        if (!task || !state.activeOperation) {
            notify('Não encontrei o card operacional para concluir a ação.');
            closeActionModal();
            return;
        }

        const confirmButton = document.getElementById('backlogHumanGateConfirmButton');
        const feedbackInput = document.getElementById('backlogHumanGateFeedbackInput');
        const originalText = confirmButton ? confirmButton.textContent : '';

        try {
            if (confirmButton) {
                confirmButton.disabled = true;
                confirmButton.textContent = 'Processando...';
            }

            const response = await fetch(
                `/api/projects/${task.project_id}/tasks/${task.id}/backlog-actions/${state.activeOperation}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        feedback: feedbackInput ? feedbackInput.value.trim() : '',
                    }),
                }
            );
            const payload = await response.json();

            if (!response.ok || !payload.success) {
                throw new Error(payload.error || payload.message || 'Falha ao operar o card do backlog.');
            }

            closeActionModal();
            notify(payload.message || 'Operação realizada com sucesso.', 'success');

            if (typeof state.afterOperation === 'function') {
                await state.afterOperation({
                    taskId: Number(task.id),
                    task,
                    payload,
                    operation: state.activeOperation,
                });
            }
        } catch (error) {
            console.error(error);
            notify(error.message || 'Erro ao operar o card do backlog.', 'error');
        } finally {
            if (confirmButton) {
                confirmButton.disabled = false;
                confirmButton.textContent = originalText;
            }
        }
    }

    function handleAction(taskId, operationId, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        const task = typeof state.getTaskById === 'function' ? state.getTaskById(Number(taskId)) : null;
        if (!task) {
            (state.notify || window.alert)('Card operacional não encontrado na memória da tela.');
            return;
        }
        openActionModal(task, operationId);
    }

    function configure(options = {}) {
        state.getTaskById = typeof options.getTaskById === 'function' ? options.getTaskById : state.getTaskById;
        state.afterOperation = typeof options.afterOperation === 'function' ? options.afterOperation : state.afterOperation;
        state.notify = typeof options.notify === 'function' ? options.notify : (state.notify || ((message) => window.alert(message)));
        state.isReadOnly = Boolean(options.isReadOnly);
        state.onBoardFilterChange = typeof options.onBoardFilterChange === 'function' ? options.onBoardFilterChange : state.onBoardFilterChange;
        ensureModal();
    }

    window.BacklogHumanGate = {
        configure,
        escapeHtml,
        shouldLockTask,
        filterTasks,
        setBoardFilter,
        mountBoardSection,
        buildBoardMetrics,
        renderCardSection,
        mountTaskSection,
        handleAction,
        openActionModal,
        closeActionModal,
        confirmAction,
    };
})();
