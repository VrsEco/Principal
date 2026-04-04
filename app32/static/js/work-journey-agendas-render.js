(() => {
  const { formatMinutes } = window.WorkJourneyUtils;

  const COLOR_MAP = {
    process_instance: 'agenda-card--process',
    project_task: 'agenda-card--project',
    meeting: 'agenda-card--meeting',
    manual: 'agenda-card--manual',
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
    };
  }

  function normalizeBlock(block) {
    const items = Array.isArray(block.items) ? block.items.map(normalizeItem) : [];
    const capacity = Number(block.operational_capacity_minutes || block.capacity_minutes || 0);
    const planned = Number(block.planned_minutes || 0);
    return {
      id: block.id,
      name: block.name,
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

  function buildSummaryFromDays(days) {
    const blocks = days.flatMap((day) => day.blocks || []);
    const items = days.flatMap((day) => day.blocks || []).flatMap((block) => block.items || []).concat(days.flatMap((day) => day.unassigned_items || []));
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
      locked: false,
    };
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
      return {
        key: day.key || dayDate || `day-${index}`,
        date: dayDate,
        label: day.label || day.day_label || formatDayLabel(dayDate, index),
        subtitle: day.subtitle || day.period || '',
        blocks: (Array.isArray(day.blocks) ? day.blocks : []).map(normalizeBlock),
        unassigned_items: Array.isArray(day.unassigned_items) ? day.unassigned_items.map(normalizeItem) : [],
      };
    });

    if (!normalizedDays.length && agenda.blocks) {
      normalizedDays.push({
        key: selectedDate,
        date: selectedDate,
        label: formatDayLabel(selectedDate, 0),
        subtitle: '',
        blocks: (agenda.blocks || []).map(normalizeBlock),
        unassigned_items: (agenda.unassigned_items || []).map(normalizeItem),
      });
    }

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
      unassigned_items: Array.isArray(agenda.unassigned_items) ? agenda.unassigned_items.map(normalizeItem) : normalizedDays.flatMap((day) => day.unassigned_items || []),
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

  function renderAgendaHTML(agenda, collapsedBlocks, locked) {
    const days = agenda?.days || [];
    return {
      boardHTML: days.map((day) => renderDayColumn(day, locked, collapsedBlocks)).join(''),
      unassignedHTML: agenda?.unassigned_items?.length
        ? agenda.unassigned_items.map((item) => renderAgendaCard(item, { day: null, blockId: null }, locked, true)).join('')
        : '<div class="agenda-empty-state">Nenhuma tarefa fora dos blocos.</div>',
    };
  }

  function renderDayColumn(day, locked, collapsedBlocks) {
    const blocks = day.blocks || [];
    return `
      <section class="agenda-day-column" data-agenda-day="${day.date}">
        <header class="agenda-day-column__header">
          <div>
            <span class="agenda-day-column__eyebrow">${day.subtitle || 'Dia'}</span>
            <h3 class="agenda-day-column__title">${day.label}</h3>
            <p class="agenda-day-column__meta">${day.date || ''}</p>
          </div>
          <span class="agenda-day-column__badge badge-pill">${blocks.length} blocos</span>
        </header>
        <div class="agenda-day-column__body">
          ${blocks.length ? blocks.map((block) => renderBlock(block, day, locked, collapsedBlocks)).join('') : '<div class="agenda-empty-state">Sem blocos para este dia.</div>'}
        </div>
      </section>
    `;
  }

  function renderBlock(block, day, locked, collapsedBlocks) {
    const blockId = block.id || `${day.date}-${block.start_time}-${block.end_time}`;
    const collapseKey = `${day.date}:${blockId}`;
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
          <button type="button" class="agenda-block__toggle" data-agenda-toggle="${collapseKey}" aria-label="Alternar bloco" aria-expanded="${collapsed ? 'false' : 'true'}">
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
          ${block.items && block.items.length ? block.items.map((item) => renderAgendaCard(item, { day: day.date, blockId }, locked, false)).join('') : '<div class="agenda-empty-state agenda-empty-state--compact">Nenhuma tarefa neste bloco.</div>'}
        </div>
      </article>
    `;
  }

  function renderAgendaCard(item, location, locked, inUnassigned) {
    const warnings = [];
    if (item.item_type === 'meeting') warnings.push('Alterar no módulo de reuniões');
    if (locked && !inUnassigned) warnings.push('Agenda travada');
    return `
      <article class="agenda-card ${agendaTypeClass(item)}" data-agenda-item="${item.id}" data-item-type="${item.item_type}" data-source-day="${location.day || ''}" data-source-block="${location.blockId || ''}" draggable="${!locked && item.item_type !== 'meeting' ? 'true' : 'false'}">
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
  };
})();
