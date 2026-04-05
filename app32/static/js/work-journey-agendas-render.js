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
    };
  }

  function normalizeBlock(block) {
    const items = Array.isArray(block.items) ? block.items.map(normalizeItem) : [];
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
      worked_minutes: Number(block.worked_minutes || 0),
      overload_minutes: Number(block.overload_minutes || Math.max(0, planned - capacity)),
      items,
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
      });
      (day.unassigned_items || []).forEach((item) => {
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
      unassigned_count: days.reduce((sum, day) => sum + (day.unassigned_items || []).length, 0),
      overdue_count: items.filter((item) => item.is_overdue).length,
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
      overdue_items: sortAgendaItems(rawOverdue),
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

  function renderDaySummaryCards(summary) {
    const metrics = [
      ['Prevista', formatCapacityMinutes(summary.planned_minutes)],
      ['Realizada', formatCapacityMinutes(summary.worked_minutes)],
      ['Sobrecarga', formatCapacityMinutes(summary.overload_minutes)],
    ];

    return metrics.map(([label, value]) => `
      <div class="agenda-day-column__summary-card ${label === 'Sobrecarga' && Number(summary.overload_minutes || 0) > 0 ? 'is-overload' : ''}">
        <span class="agenda-day-column__summary-label">${label}</span>
        <strong class="agenda-day-column__summary-value">${value}</strong>
      </div>
    `).join('');
  }

  function renderAgendaHTML(agenda, collapsedState, locked) {
    const days = agenda?.days || [];
    const overdueItems = agenda?.overdue_items || [];
    const unassignedItems = agenda?.unassigned_items || [];
    const boardColumns = [];

    if (agenda?.scope === 'week') {
      boardColumns.push(renderOverdueColumn(overdueItems, locked, collapsedState));
    }
    boardColumns.push(...days.map((day) => renderDayColumn(day, locked, collapsedState)));
    boardColumns.push(renderUnassignedColumn(unassignedItems, locked, collapsedState));

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
          <div class="agenda-day-column__topline">
            <div class="agenda-day-column__heading">
              <span class="agenda-day-column__eyebrow">Prioridade</span>
              <h3 class="agenda-day-column__title">Tarefas atrasadas</h3>
            </div>
            <div class="agenda-day-column__actions">
              <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
              <span class="agenda-day-column__badge badge-pill badge-pill--danger">${activityCount} tarefas</span>
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
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">0B</span>
              <span class="badge-pill badge-pill--danger agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
          </div>
        </header>
        <div class="agenda-day-column__body ${collapsed ? 'is-hidden' : ''}" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${activityCount
            ? overdueItems.map((item) => renderAgendaCard(item, { day: item.agenda_date || item.due_date || item.occurrence_date || '', blockId: item.block_id || null }, locked, false, 'overdue')).join('')
            : '<div class="agenda-empty-state">Nenhuma tarefa atrasada no contexto selecionado.</div>'}
        </div>
      </section>
    `;
  }

  function renderUnassignedColumn(unassignedItems, locked, collapsedState) {
    const columnKey = 'unassigned';
    const collapsed = collapsedState?.days?.has(columnKey);
    const blockCount = 0;
    const activityCount = unassignedItems.length;
    const collapsedLabel = 'N. aloc.';

    return `
      <section class="agenda-day-column agenda-day-column--unassigned ${collapsed ? 'is-collapsed' : ''}" data-agenda-day-key="${columnKey}">
        <header class="agenda-day-column__header">
          <div class="agenda-day-column__topline">
            <div class="agenda-day-column__heading">
              <span class="agenda-day-column__eyebrow">Backlog</span>
              <h3 class="agenda-day-column__title">Não alocadas</h3>
              <p class="agenda-day-column__meta">Itens sem bloco definido. Arraste para um dia ou bloco conforme a necessidade.</p>
            </div>
            <div class="agenda-day-column__actions">
              <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
              <span class="agenda-day-column__badge badge-pill">${activityCount} tarefas</span>
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
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">${blockCount}B</span>
              <span class="badge-pill agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
          </div>
        </header>
        <div class="agenda-day-column__body ${collapsed ? 'is-hidden' : ''}" data-dropzone="unassigned" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${activityCount
            ? unassignedItems.map((item) => renderAgendaCard(item, { day: item.agenda_date || item.due_date || item.occurrence_date || '', blockId: null }, locked, true, 'unassigned')).join('')
            : '<div class="agenda-empty-state">Nenhuma tarefa fora dos blocos.</div>'}
        </div>
      </section>
    `;
  }

  function renderDayColumn(day, locked, collapsedState) {
    const blocks = day.blocks || [];
    const dayKey = day.key || day.date;
    const collapsed = collapsedState?.days?.has(dayKey);
    const blockCount = blocks.length;
    const activityCount = blocks.reduce((sum, block) => sum + ((block.items || []).length), 0);
    const collapsedLabel = day.subtitle || 'Dia';
    const daySummary = buildDaySummary(day);

    return `
      <section class="agenda-day-column ${collapsed ? 'is-collapsed' : ''} ${day.is_today ? 'agenda-day-column--today' : ''}" data-agenda-day="${day.date}" data-agenda-day-key="${dayKey}">
        <header class="agenda-day-column__header">
          <div class="agenda-day-column__topline">
            <div class="agenda-day-column__heading">
              <span class="agenda-day-column__eyebrow">${day.subtitle || 'Dia'}</span>
              <h3 class="agenda-day-column__title">${day.label}</h3>
            </div>
            <div class="agenda-day-column__actions">
              <span class="agenda-day-column__badge badge-pill">${blockCount} blocos</span>
              <span class="agenda-day-column__badge badge-pill">${activityCount} tarefas</span>
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
          </div>
          <div class="agenda-day-column__summary" aria-hidden="${collapsed ? 'true' : 'false'}">
            ${renderDaySummaryCards(daySummary)}
          </div>
          <div class="agenda-day-column__collapsed-title" aria-hidden="${collapsed ? 'false' : 'true'}">
            <span class="agenda-day-column__collapsed-label">${collapsedLabel}</span>
            <div class="agenda-day-column__collapsed-metrics">
              <span class="badge-pill agenda-day-column__collapsed-count">${blockCount}B</span>
              <span class="badge-pill agenda-day-column__collapsed-count">${activityCount}A</span>
            </div>
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
    const occupancyValue = `${formatMinutes(worked)} / ${formatMinutes(progressBase)}`;
    const blockStatus = block.block_mode === 'reserved_full'
      ? 'Capacidade bloqueada'
      : overload > 0
        ? `Sobrec.: +${formatMinutes(overload)}`
        : 'Dentro cap.';

    return `
      <article class="agenda-block ${collapsed ? 'is-collapsed' : ''} agenda-block--${block.block_mode || 'operational'}" data-agenda-block="${blockId}" data-agenda-day="${day.date}">
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
                <span class="agenda-block__detail-item">Cap. Plan.: ${formatMinutes(planned)}</span>
                <span class="agenda-block__detail-item">Ocup: ${formatMinutes(worked)}</span>
                <span class="agenda-block__detail-item ${overload > 0 ? 'is-overload' : ''}">${blockStatus}</span>
              </div>
            </div>
          </div>
        </header>
        <div class="agenda-block__progress">
          <span class="agenda-block__progress-fill ${overload > 0 ? 'is-overload' : ''}" style="width:${fill}%"></span>
        </div>
        <div class="agenda-block__content ${collapsed ? 'is-hidden' : ''}" data-dropzone="block" data-agenda-day="${day.date}" data-block-id="${blockId}" aria-hidden="${collapsed ? 'true' : 'false'}">
          ${block.items && block.items.length ? block.items.map((item) => renderAgendaCard(item, { day: day.date, blockId }, locked, false, 'block')).join('') : '<div class="agenda-empty-state agenda-empty-state--compact">Nenhuma tarefa neste bloco.</div>'}
        </div>
      </article>
    `;
  }

  function renderAgendaCard(item, location, locked, inUnassigned, listScope = 'block') {
    const warnings = [];
    if (item.item_type === 'meeting') warnings.push('Alterar no módulo de reuniões');
    if (locked && listScope === 'block') warnings.push('Agenda travada');
    if (item.source_warning) warnings.push(item.source_warning);
    if (item.is_overdue) warnings.push('Tarefa atrasada');

    return `
      <article
        class="agenda-card ${agendaTypeClass(item)} ${listScope === 'overdue' ? 'agenda-card--side agenda-card--side-overdue' : ''} ${listScope === 'unassigned' ? 'agenda-card--side agenda-card--side-unassigned' : ''}"
        data-agenda-item="${item.id}"
        data-item-type="${item.item_type}"
        data-source-day="${location.day || item.agenda_date || item.due_date || ''}"
        data-source-block="${location.blockId || item.block_id || ''}"
        draggable="${!locked && item.item_type !== 'meeting' ? 'true' : 'false'}"
      >
        <div class="agenda-card__top">
          <div class="agenda-card__title-wrap">
            <span class="agenda-card__code">${item.display_code || item.source_label || item.item_type_label || item.item_type}</span>
            <h4 class="agenda-card__title">${item.display_title || item.title}</h4>
          </div>
          <div class="agenda-card__badges">
            <span class="agenda-card__type">${item.item_type_label || item.item_type}</span>
            <span class="agenda-card__status ${item.status === 'completed' ? 'is-success' : item.is_overdue ? 'is-danger' : ''}">${item.status_label || item.status}</span>
          </div>
        </div>
        <div class="agenda-card__meta">
          ${item.source_label ? `<span>${item.source_label}</span>` : ''}
          ${item.estimated_minutes ? `<span>${formatMinutes(item.estimated_minutes)}</span>` : ''}
          ${(item.agenda_date || item.due_date || item.occurrence_date) ? `<span>${item.agenda_date || item.due_date || item.occurrence_date}</span>` : ''}
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
