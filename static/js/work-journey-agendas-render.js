(() => {
  const { formatMinutes } = window.WorkJourneyUtils || {};

  const COLOR_MAP = {
    process_instance: 'agenda-card--process',
    project_task: 'agenda-card--project',
    meeting: 'agenda-card--meeting',
    manual: 'agenda-card--manual',
  };

  const PRIORITY_ORDER = {
    urgent: 0,
    high: 1,
    normal: 2,
    low: 3,
  };

  function normalizeItem(item) {
    return {
      id: item.id,
      event_id: item.event_id || null,
      item_kind: item.item_kind || 'journey_item',
      title: item.title,
      display_title: item.display_title || item.title,
      description: item.description || '',
      item_type: item.item_type,
      item_type_label: item.item_type_label || item.item_type,
      status: item.status || 'pending',
      status_label: item.status_label || item.status || 'pending',
      priority: item.priority || 'normal',
      estimated_minutes: Number(item.estimated_minutes || 0),
      worked_minutes: Number(item.worked_minutes || 0),
      source_label: item.source_label || '',
      source_url: item.source_url || '',
      due_date: item.due_date || null,
      occurrence_date: item.occurrence_date || null,
      block_id: item.block_id || null,
      agenda_date: item.agenda_date || item.planned_date || item.due_date || item.occurrence_date || null,
      source_id: item.source_id || null,
      is_overdue: Boolean(item.is_overdue),
      can_drag: item.item_type !== 'meeting',
      display_code: item.display_code || item.code || item.source_code || '',
      source_warning: item.source_warning || '',
      meeting_locked: Boolean(item.meeting_locked),
      planned_start_time: item.planned_start_time || null,
      planned_end_time: item.planned_end_time || null,
      planned_window_label: item.planned_window_label || null,
      execution_notes: item.execution_notes || '',
    };
  }

  function normalizeBlock(block) {
    const items = Array.isArray(block.items) ? block.items.map(normalizeItem) : [];
    const events = Array.isArray(block.events) ? block.events.map(normalizeItem) : [];
    const capacity = Number(block.operational_capacity_minutes || block.capacity_minutes || 0);
    const planned = Number(block.planned_minutes || 0);

    return {
      id: block.id,
      name: block.name,
      description: block.description || '',
      start_time: block.start_time,
      end_time: block.end_time,
      block_mode: block.block_mode || 'operational',
      block_mode_label: block.block_mode_label || block.block_mode || 'operational',
      capacity_minutes: Number(block.capacity_minutes || capacity),
      operational_capacity_minutes: capacity,
      fixed_reserved_minutes: Number(block.fixed_reserved_minutes || 0),
      planned_minutes: planned,
      planned_task_minutes: Number(block.planned_task_minutes || 0),
      planned_event_minutes: Number(block.planned_event_minutes || 0),
      worked_minutes: Number(block.worked_minutes || 0),
      overload_minutes: Number(block.overload_minutes || Math.max(0, planned - capacity)),
      items,
      events,
    };
  }

  function formatDayLabel(rawDate, index) {
    if (!rawDate) return `Dia ${index + 1}`;
    try {
      const date = new Date(`${rawDate}T00:00:00`);
      return new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' }).format(date);
    } catch (_err) {
      return String(rawDate);
    }
  }

  function getDaySortKey(day, index) {
    const weekday = typeof day.weekday_sort_key === 'number'
      ? day.weekday_sort_key
      : (() => {
          try {
            return new Date(`${day.date}T00:00:00`).getDay();
          } catch (_err) {
            return index;
          }
        })();

    return `${weekday}-${day.date || index}`;
  }

  function collectAgendaItems(days) {
    const items = [];
    const seen = new Set();

    days.forEach((day) => {
      (day.blocks || []).forEach((block) => {
        (block.items || []).forEach((item) => {
          if (seen.has(item.id)) return;
          seen.add(item.id);
          items.push(item);
        });
        (block.events || []).forEach((item) => {
          if (seen.has(item.id)) return;
          seen.add(item.id);
          items.push(item);
        });
      });
      (day.unassigned_items || []).forEach((item) => {
        if (seen.has(item.id)) return;
        seen.add(item.id);
        items.push(item);
      });
      (day.unassigned_events || []).forEach((item) => {
        if (seen.has(item.id)) return;
        seen.add(item.id);
        items.push(item);
      });
    });

    return items;
  }

  function sortAgendaItems(items) {
    return [...items].sort((a, b) => {
      const aDate = a.agenda_date || a.due_date || a.occurrence_date || '9999-12-31';
      const bDate = b.agenda_date || b.due_date || b.occurrence_date || '9999-12-31';
      if (aDate !== bDate) return String(aDate).localeCompare(String(bDate));

      const aPriority = PRIORITY_ORDER[a.priority] ?? PRIORITY_ORDER.normal;
      const bPriority = PRIORITY_ORDER[b.priority] ?? PRIORITY_ORDER.normal;
      if (aPriority !== bPriority) return aPriority - bPriority;

      const aTitle = String(a.display_title || a.title || '').toLowerCase();
      const bTitle = String(b.display_title || b.title || '').toLowerCase();
      return aTitle.localeCompare(bTitle);
    });
  }

  function buildSummaryFromDays(days) {
    const blocks = days.flatMap((day) => day.blocks || []);
    const items = collectAgendaItems(days);

    return {
      daily_capacity_minutes: blocks.reduce((sum, block) => sum + Number(block.block_mode === 'operational' ? (block.operational_capacity_minutes || block.capacity_minutes || 0) : 0), 0),
      reserved_minutes: blocks.reduce((sum, block) => sum + Number(block.fixed_reserved_minutes || 0), 0),
      buffer_minutes: blocks.reduce((sum, block) => sum + Number(block.block_mode === 'buffer' ? (block.buffer_minutes || block.capacity_minutes || 0) : 0), 0),
      planned_minutes: items.reduce((sum, item) => sum + Number(item.estimated_minutes || 0), 0),
      worked_minutes: items.reduce((sum, item) => sum + Number(item.worked_minutes || 0), 0),
      overload_minutes: blocks.reduce((sum, block) => sum + Number(block.overload_minutes || 0), 0),
      pending_count: items.filter((item) => item.status !== 'completed').length,
      completed_count: items.filter((item) => item.status === 'completed').length,
      unassigned_count: days.reduce((sum, day) => sum + (day.unassigned_items || []).length + (day.unassigned_events || []).length, 0),
      overdue_count: items.filter((item) => item.is_overdue).length,
      event_count: items.filter((item) => item.item_kind === 'calendar_event').length,
      linked_event_count: items.filter((item) => item.item_kind === 'calendar_event' && item.item_type !== 'manual').length,
      locked: false,
    };
  }

  function buildDaySummary(day) {
    return buildSummaryFromDays([day]);
  }

  function formatCapacityMinutes(minutes) {
    const total = Number(minutes || 0);
    const hours = Math.floor(total / 60);
    const remainder = total % 60;
    if (!hours) return `${remainder} min`;
    if (!remainder) return `${hours} h`;
    return `${hours} h ${remainder} min`;
  }

  function normalizeAgenda(raw, options = {}) {
    const agenda = raw?.agenda || raw?.data || raw || {};
    const selectedDate = options.selectedDate || agenda.date || agenda.agenda_date || new Date().toISOString().slice(0, 10);
    const scope = options.scope || agenda.scope || 'week';
    const employeeId = options.employeeId || agenda.employee_id || null;
    const companyId = options.companyId || agenda.company_id || null;
    const days = Array.isArray(agenda.days) ? agenda.days : Array.isArray(agenda.columns) ? agenda.columns : [];

    const normalizedDays = days.map((day, index) => {
      const dayDate = day.date || day.agenda_date || day.day_date || selectedDate;
      const rawWeekday = typeof day.weekday === 'number' ? day.weekday : null;
      const weekdaySortKey = rawWeekday !== null
        ? ((rawWeekday + 1) % 7)
        : (() => {
            try {
              return new Date(`${dayDate}T00:00:00`).getDay();
            } catch (_error) {
              return index;
            }
          })();

      return {
        key: day.key || dayDate || `day-${index}`,
        date: dayDate,
        label: day.label || day.day_label || formatDayLabel(dayDate, index),
        subtitle: day.subtitle || day.period || '',
        weekday: rawWeekday !== null
          ? rawWeekday
          : (() => {
              try {
                return new Date(`${dayDate}T00:00:00`).getDay();
              } catch (_error) {
                return index;
              }
            })(),
        weekday_sort_key: weekdaySortKey,
        blocks: (Array.isArray(day.blocks) ? day.blocks : []).map(normalizeBlock),
        unassigned_items: Array.isArray(day.unassigned_items) ? day.unassigned_items.map(normalizeItem) : [],
        unassigned_events: Array.isArray(day.unassigned_events) ? day.unassigned_events.map(normalizeItem) : [],
        events: Array.isArray(day.events) ? day.events.map(normalizeItem) : [],
        is_today: Boolean(day.is_today),
      };
    });

    if (scope === 'week') {
      normalizedDays.sort((a, b) => {
        const aKey = typeof a.weekday_sort_key === 'number' ? a.weekday_sort_key : 7;
        const bKey = typeof b.weekday_sort_key === 'number' ? b.weekday_sort_key : 7;
        if (aKey !== bKey) return aKey - bKey;
        return String(a.date || '').localeCompare(String(b.date || ''));
      });
    }

    if (!normalizedDays.length && agenda.blocks) {
      normalizedDays.push({
        key: selectedDate,
        date: selectedDate,
        label: formatDayLabel(selectedDate, 0),
        subtitle: '',
        weekday: new Date(`${selectedDate}T00:00:00`).getDay(),
        weekday_sort_key: new Date(`${selectedDate}T00:00:00`).getDay(),
        blocks: (agenda.blocks || []).map(normalizeBlock),
        unassigned_items: (agenda.unassigned_items || []).map(normalizeItem),
        unassigned_events: (agenda.unassigned_events || []).map(normalizeItem),
        events: (agenda.events || []).map(normalizeItem),
        is_today: true,
      });
    }

    const flattenedItems = collectAgendaItems(normalizedDays);
    const rawOverdue = Array.isArray(agenda.overdue_items) && agenda.overdue_items.length
      ? agenda.overdue_items.map(normalizeItem)
      : flattenedItems.filter((item) => item.is_overdue);
    const rawUnassigned = Array.isArray(agenda.unassigned_items) && agenda.unassigned_items.length
      ? agenda.unassigned_items.map(normalizeItem)
      : normalizedDays.flatMap((day) => day.unassigned_items || []);
    const rawUnassignedEvents = Array.isArray(agenda.unassigned_events) && agenda.unassigned_events.length
      ? agenda.unassigned_events.map(normalizeItem)
      : normalizedDays.flatMap((day) => day.unassigned_events || []);

    const summary = agenda.summary || buildSummaryFromDays(normalizedDays);

    return {
      id: agenda.id || agenda.agenda_id || null,
      company_id: companyId,
      employee_id: employeeId,
      scope,
      status: agenda.status || (agenda.is_locked ? 'locked' : 'draft'),
      locked: Boolean(agenda.locked || agenda.is_locked || agenda.status === 'locked'),
      generated_at: agenda.generated_at || agenda.created_at || null,
      locked_at: agenda.locked_at || null,
      locked_by_name: agenda.locked_by_name || null,
      engine_version: agenda.engine_version || 'agenda-v1',
      summary,
      days: normalizedDays,
      unassigned_items: sortAgendaItems(rawUnassigned.filter((item) => !item.is_overdue)),
      unassigned_events: sortAgendaItems(rawUnassignedEvents),
      overdue_items: sortAgendaItems(rawOverdue),
      calendar_events: Array.isArray(agenda.calendar_events) ? agenda.calendar_events.map(normalizeItem) : [],
      process_instance_cards: Array.isArray(agenda.process_instance_cards) ? agenda.process_instance_cards : [],
      notes: agenda.notes || null,
    };
  }

  function agendaTypeClass(item) {
    return COLOR_MAP[item.item_type] || 'agenda-card--manual';
  }

  function renderSummaryCards(summary) {
    const cards = [
      ['Carga prevista', formatMinutes(summary.planned_minutes)],
      ['Carga realizada', formatMinutes(summary.worked_minutes)],
      ['Sobrecarga', formatMinutes(summary.overload_minutes)],
      ['Eventos', summary.event_count || 0],
      ['Não alocadas', summary.unassigned_count || 0],
      ['Concluídas', summary.completed_count || 0],
      ['Pendentes', summary.pending_count || 0],
    ];

    return cards.map(([label, value]) => `
      <div class="journey-summary-card agenda-summary-card">
        <span class="text-secondary">${label}</span>
        <strong class="${label === 'Sobrecarga' && Number(summary.overload_minutes || 0) > 0 ? 'journey-overload' : ''}">${value}</strong>
      </div>
    `).join('');
  }

  function renderProcessInstanceCards(cards) {
    if (!Array.isArray(cards) || !cards.length) {
      return '<div class="agenda-empty-state">Nenhuma instância relevante no período atual.</div>';
    }

    return cards.map((card) => {
      const currentActivity = card.current_activity || {};
      const linkedTask = card.linked_operational_task || {};
      const instanceDueClass = card.is_instance_overdue ? 'agenda-instance-card__metric-value agenda-instance-card__metric-value--danger' : 'agenda-instance-card__metric-value';
      const activityDueClass = currentActivity.is_activity_overdue ? 'agenda-instance-card__metric-value agenda-instance-card__metric-value--danger' : 'agenda-instance-card__metric-value';
      const cardClass = card.is_instance_overdue ? 'agenda-instance-card agenda-instance-card--overdue' : 'agenda-instance-card';
      const activityDueLabel = currentActivity.activity_due_label || 'Sem prazo definido';
      const instanceDueLabel = card.instance_due_label || 'Sem prazo definido';
      return `
        <article class="${cardClass}">
          <div class="agenda-instance-card__header">
            <div>
              <span class="agenda-instance-card__eyebrow">Instância de processo</span>
              <h3 class="agenda-instance-card__title">${escapeHtml(card.instance_title || 'Instância sem título')}</h3>
              <div class="agenda-instance-card__code">${escapeHtml(card.instance_code || '')}</div>
              <div class="agenda-instance-card__process">${escapeHtml(card.process_name || 'Processo não identificado')}</div>
            </div>
            <div class="agenda-instance-card__badges">
              <span class="badge-pill">${escapeHtml(card.instance_status_label || card.instance_status || 'Status')}</span>
              <span class="badge-pill">${escapeHtml(card.instance_priority_label || card.instance_priority || 'Prioridade')}</span>
            </div>
          </div>
          <div class="agenda-instance-card__meta">
            <div class="agenda-instance-card__metric">
              <span class="agenda-instance-card__metric-label">Prazo da instância</span>
              <span class="${instanceDueClass}">${escapeHtml(instanceDueLabel)}</span>
            </div>
            <div class="agenda-instance-card__metric">
              <span class="agenda-instance-card__metric-label">Prazo da atividade atual</span>
              <span class="${activityDueClass}">${escapeHtml(activityDueLabel)}</span>
            </div>
          </div>
          <div class="agenda-instance-card__activity">
            <span class="agenda-instance-card__eyebrow">Atividade atual</span>
            <h4 class="agenda-instance-card__activity-title">${escapeHtml(currentActivity.activity_name || 'Sem atividade ativa')}</h4>
            <div class="agenda-instance-card__activity-meta">
              <span class="badge-pill">${escapeHtml(currentActivity.activity_status_label || 'Aguardando ativação')}</span>
              <span class="badge-pill">${escapeHtml(currentActivity.activity_execution_mode_label || 'Sem execução ativa')}</span>
              ${card.agenda_entry_count ? `<span class="badge-pill">${card.agenda_entry_count} alocação(ões)</span>` : ''}
              ${card.linked_event_count ? `<span class="badge-pill">${card.linked_event_count} evento(s)</span>` : ''}
            </div>
            ${linkedTask.title ? `
              <div class="agenda-instance-card__task-link">
                <span class="agenda-instance-card__metric-label">Evento operacional derivado</span>
                <strong>${escapeHtml(linkedTask.title)}</strong>
                <span class="text-secondary">${escapeHtml(linkedTask.due_label || 'Sem prazo operacional definido')}</span>
              </div>
            ` : ''}
          </div>
          <div class="agenda-instance-card__footer">
            <span class="text-secondary">${escapeHtml(card.routine_name || 'Sem rotina vinculada')}</span>
            ${card.source_url ? `<a class="btn btn-secondary" href="${card.source_url}">Abrir instância</a>` : ''}
          </div>
        </article>
      `;
    }).join('');
  }

  function escapeHtml(value) {
    return String(value || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function renderAgendaHTML(agenda, collapsedState, locked) {
    const days = agenda?.days || [];
    const overdueItems = agenda?.overdue_items || [];
    const unassignedItems = agenda?.unassigned_items || [];
    const unassignedEvents = agenda?.unassigned_events || [];
    const boardColumns = [];

    if (agenda?.scope === 'week') {
      boardColumns.push(renderOverdueColumn(overdueItems, locked, collapsedState));
    }
    boardColumns.push(...days.map((day) => renderDayColumn(day, locked, collapsedState)));
    boardColumns.push(renderUnassignedColumn(unassignedItems, unassignedEvents, locked, collapsedState));

    return {
      boardHTML: boardColumns.join(''),
    };
  }

  function renderOverdueColumn(overdueItems, locked, collapsedState) {
    const columnKey = 'overdue';
    const collapsed = collapsedState?.days?.has(columnKey);
    const blockCount = 0;
    const activityCount = overdueItems.length;
    const collapsedLabel = 'Atras.';

    return `
      <section class="agenda-day-column agenda-day-column--overdue ${collapsed ? 'is-collapsed' : ''}" data-agenda-day-key="${columnKey}">
        <header class="agenda-day-column__header">
          <div class="agenda-day-column__heading">
            <span class="agenda-day-column__eyebrow">Prioridade</span>
            <h3 class="agenda-day-column__title">Eventos operacionais atrasados</h3>
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">0B</span>
              <span class="badge-pill badge-pill--danger agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
          </div>
          <div class="agenda-day-column__actions">
            <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
            <span class="agenda-day-column__badge badge-pill badge-pill--danger">${activityCount} eventos</span>
            <button
              type="button"
              class="agenda-day-column__toggle"
              data-agenda-day-toggle="${columnKey}"
              aria-label="${collapsed ? 'Expandir atrasadas' : 'Colapsar atrasadas'}"
              aria-expanded="${collapsed ? 'false' : 'true'}"
            >
              <span class="agenda-block__chevron">▾</span>
            </button>
          </div>
        </header>
        <div class="agenda-day-column__body ${collapsed ? 'is-hidden' : ''}" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${activityCount
            ? overdueItems.map((item) => renderAgendaCard(item, { day: item.agenda_date || item.due_date || item.occurrence_date || '', blockId: item.block_id || null }, locked, false, 'overdue')).join('')
            : '<div class="agenda-empty-state">Nenhum evento operacional atrasado no contexto selecionado.</div>'}
        </div>
      </section>
    `;
  }

  function renderUnassignedColumn(unassignedItems, unassignedEvents, locked, collapsedState) {
    const columnKey = 'unassigned';
    const collapsed = collapsedState?.days?.has(columnKey);
    const blockCount = 0;
    const activityCount = unassignedItems.length + unassignedEvents.length;
    const collapsedLabel = 'N. aloc.';

    return `
      <section class="agenda-day-column agenda-day-column--unassigned ${collapsed ? 'is-collapsed' : ''}" data-agenda-day-key="${columnKey}">
        <header class="agenda-day-column__header">
          <div class="agenda-day-column__heading">
            <span class="agenda-day-column__eyebrow">Backlog</span>
            <h3 class="agenda-day-column__title">Não alocadas</h3>
            <p class="agenda-day-column__meta">Itens sem bloco definido. Arraste para um dia ou bloco conforme a necessidade.</p>
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">${blockCount}B</span>
              <span class="badge-pill agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
          </div>
          <div class="agenda-day-column__actions">
            <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
            <span class="agenda-day-column__badge badge-pill">${activityCount} eventos</span>
            <button
              type="button"
              class="agenda-day-column__toggle"
              data-agenda-day-toggle="${columnKey}"
              aria-label="${collapsed ? 'Expandir não alocadas' : 'Colapsar não alocadas'}"
              aria-expanded="${collapsed ? 'false' : 'true'}"
            >
              <span class="agenda-block__chevron">▾</span>
            </button>
          </div>
        </header>
        <div class="agenda-day-column__body ${collapsed ? 'is-hidden' : ''}" data-dropzone="unassigned" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${activityCount
            ? [...unassignedItems, ...unassignedEvents]
              .sort((left, right) => String(left.planned_start_time || '').localeCompare(String(right.planned_start_time || '')) || String(left.display_title || '').localeCompare(String(right.display_title || '')))
              .map((item) => renderAgendaCard(item, { day: item.agenda_date || item.due_date || item.occurrence_date || '', blockId: null }, locked, true, 'unassigned')).join('')
            : '<div class="agenda-empty-state">Nenhum evento fora dos blocos.</div>'}
        </div>
      </section>
    `;
  }

  function renderDayColumn(day, locked, collapsedState) {
    const blocks = day.blocks || [];
    const dayKey = day.key || day.date;
    const collapsed = collapsedState?.days?.has(dayKey);
    const blockCount = blocks.length;
    const activityCount = blocks.reduce((sum, block) => sum + ((block.items || []).length) + ((block.events || []).length), 0);
    const collapsedLabel = day.subtitle || 'Dia';
    const daySummary = buildDaySummary(day);
    const dayMeta = [
      `Carga Prevista: ${formatCapacityMinutes(daySummary.planned_minutes)}`,
      `Carga Realizada: ${formatCapacityMinutes(daySummary.worked_minutes)}`,
      `Sobrecarga: ${formatCapacityMinutes(daySummary.overload_minutes)}`,
    ].join(' | ');

    return `
      <section class="agenda-day-column ${collapsed ? 'is-collapsed' : ''} ${day.is_today ? 'agenda-day-column--today' : ''}" data-agenda-day="${day.date}" data-agenda-day-key="${dayKey}">
        <header class="agenda-day-column__header">
          <div class="agenda-day-column__heading">
            <span class="agenda-day-column__eyebrow">${day.subtitle || 'Dia'}</span>
            <h3 class="agenda-day-column__title">${day.label}</h3>
            <p class="agenda-day-column__meta">${dayMeta}</p>
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">${blockCount}B</span>
              <span class="badge-pill agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
          </div>
          <div class="agenda-day-column__actions">
            <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
            <span class="agenda-day-column__badge badge-pill">${activityCount} eventos</span>
            <button
              type="button"
              class="agenda-day-column__toggle"
              data-agenda-day-toggle="${dayKey}"
              aria-label="${collapsed ? 'Expandir dia' : 'Colapsar dia'}"
              aria-expanded="${collapsed ? 'false' : 'true'}"
            >
              <span class="agenda-block__chevron">▾</span>
            </button>
          </div>
        </header>
        <div class="agenda-day-column__body ${collapsed ? 'is-hidden' : ''}" data-dropzone="day" data-agenda-day="${day.date}" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${blocks.length ? blocks.map((block) => renderBlock(block, day, locked, collapsedState?.blocks)).join('') : '<div class="agenda-empty-state">Sem blocos para este dia.</div>'}
        </div>
      </section>
    `;
  }

  function renderBlock(block, day, locked, collapsedBlocks) {
    const blockId = block.id || `${day.date}-${block.start_time}-${block.end_time}`;
    const dayKey = day.key || day.date;
    const collapseKey = `${dayKey}:block:${blockId}`;
    const collapsed = collapsedBlocks?.has(collapseKey);
    const capacity = Number(block.operational_capacity_minutes || block.capacity_minutes || 0);
    const fallbackCapacity = Number(block.capacity_minutes || 0);
    const progressBase = capacity > 0 ? capacity : Math.max(fallbackCapacity, Number(block.planned_minutes || 0), 0);
    const planned = Number(block.planned_minutes || 0);
    const worked = Number(block.worked_minutes || 0);
    const overload = Number(block.overload_minutes || Math.max(0, planned - capacity));
    const fill = progressBase > 0 ? Math.min(100, Math.round((planned / progressBase) * 100)) : 0;
    const rangeLabel = `${block.start_time || '--:--'} às ${block.end_time || '--:--'}`;
    const occupancyLabel = capacity > 0 ? 'Cap. Ocup./Oper.' : 'Cap. Ocup./Bloco';
    const occupancyValue = `${formatMinutes(planned)} / ${formatMinutes(progressBase)}`;
    const blockStatus = block.block_mode === 'reserved_full'
      ? 'Capacidade bloqueada'
      : overload > 0
        ? `Sobrec.: +${formatMinutes(overload)}`
        : 'Dentro cap.';
    const cards = [...(block.items || []), ...(block.events || [])]
      .sort((left, right) => String(left.planned_start_time || '').localeCompare(String(right.planned_start_time || '')) || String(left.display_title || '').localeCompare(String(right.display_title || '')));

    return `
      <article class="agenda-block ${collapsed ? 'is-collapsed' : ''} agenda-block--${block.block_mode || 'operational'}" data-agenda-block="${blockId}" data-agenda-day="${day.date}" data-dropzone="block" data-block-id="${blockId}">
        <header class="agenda-block__header">
          <button
            type="button"
            class="agenda-block__toggle"
            data-agenda-toggle="${collapseKey}"
            aria-label="Alternar bloco"
            aria-expanded="${collapsed ? 'false' : 'true'}"
          >
            <span class="agenda-block__chevron">▾</span>
          </button>
          <div class="agenda-block__header-main">
            <div class="agenda-block__title-row">
              <strong>${block.name}</strong>
              <span class="badge-pill ${block.block_mode === 'reserved_full' ? 'badge-pill--warning' : block.block_mode === 'buffer' ? 'badge-pill--success' : ''}">${block.block_mode_label || block.block_mode}</span>
            </div>
            <div class="agenda-block__details">
              <div class="agenda-block__detail-line">
                <span class="agenda-block__detail-item agenda-block__detail-item--time">${rangeLabel}</span>
                <span class="agenda-block__detail-item">${occupancyLabel}: ${occupancyValue}</span>
              </div>
              <div class="agenda-block__detail-line">
                <span class="agenda-block__detail-item">Ativ.: ${formatMinutes(block.planned_task_minutes || 0)}</span>
                <span class="agenda-block__detail-item">Eventos: ${formatMinutes(block.planned_event_minutes || 0)}</span>
                <span class="agenda-block__detail-item ${overload > 0 ? 'is-overload' : ''}">${blockStatus}</span>
              </div>
            </div>
          </div>
        </header>
        <div class="agenda-block__progress">
          <span class="agenda-block__progress-fill ${overload > 0 ? 'is-overload' : ''}" style="width:${fill}%"></span>
        </div>
        <div class="agenda-block__content ${collapsed ? 'is-hidden' : ''}" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${cards.length ? cards.map((item) => renderAgendaCard(item, { day: day.date, blockId }, locked, false, 'block')).join('') : '<div class="agenda-empty-state agenda-empty-state--compact">Nenhum evento neste bloco.</div>'}
        </div>
      </article>
    `;
  }

  function renderAgendaCard(item, location, locked, inUnassigned, listScope = 'block') {
    const warnings = [];
    if (item.item_type === 'meeting') warnings.push('Alterar no módulo de reuniões');
    if (locked && listScope === 'block') warnings.push('Agenda travada');
    if (item.source_warning) warnings.push(item.source_warning);
    if (item.is_overdue) warnings.push(item.item_kind === 'calendar_event' ? 'Evento vencido' : 'Evento operacional atrasado');
    if (item.item_kind === 'calendar_event' && item.execution_notes) warnings.push(item.execution_notes);

    const dateLabel = item.agenda_date || item.due_date || item.occurrence_date || '';
    const metaChips = [
      item.source_label ? { value: item.source_label, kind: 'source' } : null,
      item.estimated_minutes ? { value: formatMinutes(item.estimated_minutes), kind: 'effort' } : null,
      item.planned_window_label ? { value: item.planned_window_label, kind: 'window' } : null,
    ].filter(Boolean);

    return `
      <article
        class="agenda-card ${agendaTypeClass(item)} ${listScope === 'overdue' ? 'agenda-card--side agenda-card--side-overdue' : ''} ${listScope === 'unassigned' ? 'agenda-card--side agenda-card--side-unassigned' : ''}"
        data-agenda-item="${item.id}"
        data-item-type="${item.item_type}"
        data-list-scope="${listScope}"
        data-source-day="${location.day || item.agenda_date || item.due_date || ''}"
        data-source-block="${location.blockId || item.block_id || ''}"
        draggable="${!locked && item.item_type !== 'meeting' && item.item_kind !== 'calendar_event' ? 'true' : 'false'}"
      >
        <div class="agenda-card__top">
          <div class="agenda-card__title-wrap">
            ${dateLabel ? `<span class="agenda-card__date">${dateLabel}</span>` : ''}
            <h4 class="agenda-card__title">${item.display_title || item.title}</h4>
            <span class="agenda-card__code">${item.display_code || item.source_label || item.item_type_label || item.item_type}</span>
          </div>
          <div class="agenda-card__badges">
            <span class="agenda-card__type">${item.item_type_label || item.item_type}</span>
            <span class="agenda-card__status ${item.status === 'completed' ? 'is-success' : item.is_overdue ? 'is-danger' : ''}">${item.status_label || item.status}</span>
          </div>
        </div>
        <div class="agenda-card__meta">
          ${metaChips.map((chip) => `<span class="agenda-card__meta-chip agenda-card__meta-chip--${chip.kind}">${chip.value}</span>`).join('')}
        </div>
        ${item.description ? `<p class="agenda-card__desc">${item.description}</p>` : ''}
        ${warnings.length ? `<div class="agenda-card__warning">${warnings.join(' · ')}</div>` : ''}
        <div class="agenda-card__actions">
          ${item.source_url && item.item_type !== 'meeting' ? `<a class="btn btn-secondary btn-sm" href="${item.source_url}" target="_blank" rel="noopener">Abrir origem</a>` : ''}
          ${item.item_type === 'meeting' ? `<button type="button" class="btn btn-secondary btn-sm" data-action="meeting-hint" disabled>Resolver no módulo de reuniões</button>` : ''}
        </div>
      </article>
    `;
  }

  window.WorkJourneyAgendasRenderer = {
    normalizeAgenda,
    normalizeItem,
    normalizeBlock,
    buildSummaryFromDays,
    renderSummaryCards,
    renderProcessInstanceCards,
    renderAgendaHTML,
    renderDayColumn,
    renderBlock,
    renderAgendaCard,
    agendaTypeClass,
    formatDayLabel,
    sortAgendaItems,
    collectAgendaItems,
  };
})();
