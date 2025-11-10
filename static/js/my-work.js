/**
 * MY WORK PAGE - Interactive Features
 * Gerenciamento de atividades do executor
 */

// ========================================
// Estado da Aplicação
// ========================================

const state = {
  currentFilter: 'all',
  currentView: 'list',
  currentScope: 'me', // 'me', 'team', 'company'
  searchQuery: '',
  sortBy: 'deadline',
  activities: [],
  teamData: null,
  companyData: null
};

// ========================================
// Inicialização
// ========================================

document.addEventListener('DOMContentLoaded', function() {
  initializeViewTabs();
  initializeFilters();
  initializeSearch();
  initializeViewSwitcher();
  initializeSorting();
  initializeActivityActions();
  initializeTimeTracker();
  animateOnScroll();
  loadActivitiesData();
});

// ========================================
// View Tabs (Minhas | Equipe | Empresa)
// ========================================

function initializeViewTabs() {
  const viewTabs = document.querySelectorAll('.view-tab');
  
  viewTabs.forEach(tab => {
    tab.addEventListener('click', function() {
      // Remove active class from all tabs
      viewTabs.forEach(t => t.classList.remove('view-tab--active'));
      
      // Add active class to clicked tab
      this.classList.add('view-tab--active');
      
      // Get view scope
      const scope = this.dataset.view;
      state.currentScope = scope;
      
      // Update page title and subtitle
      updatePageTitle(scope);
      
      // Update context info
      updateContextInfo(scope);
      
      // Show/hide team overview
      toggleTeamOverview(scope);
      
      // Reload data for new scope
      loadActivitiesData();
      
      console.log('Switched to view:', scope);
    });
  });
}

function toggleTeamOverview(scope) {
  const teamOverview = document.getElementById('teamOverview');
  const companyOverview = document.getElementById('companyOverview');
  
  // Esconder ambos primeiro
  if (teamOverview) teamOverview.style.display = 'none';
  if (companyOverview) companyOverview.style.display = 'none';
  
  // Mostrar conforme scope
  if (scope === 'team' && teamOverview) {
    teamOverview.style.display = 'block';
  } else if (scope === 'company' && companyOverview) {
    companyOverview.style.display = 'block';
  }
}

function updatePageTitle(scope) {
  const titleEl = document.getElementById('pageTitle');
  const subtitleEl = document.getElementById('pageSubtitle');
  
  if (!titleEl || !subtitleEl) return;
  
  const titles = {
    me: {
      title: 'Minhas Atividades',
      subtitle: 'Gerencie sua rotina e acompanhe seu desempenho'
    },
    team: {
      title: 'Atividades da Equipe',
      subtitle: 'Acompanhe o desempenho e progresso da sua equipe'
    },
    company: {
      title: 'Atividades da Empresa',
      subtitle: 'Visão estratégica de todas as atividades organizacionais'
    }
  };
  
  titleEl.textContent = titles[scope].title;
  subtitleEl.textContent = titles[scope].subtitle;
}

function updateContextInfo(scope) {
  const contextValueEl = document.getElementById('contextValue');
  if (!contextValueEl) return;
  
  const contexts = {
    me: 'Suas atividades',
    team: 'Atividades da equipe',
    company: 'Todas as atividades da empresa'
  };
  
  contextValueEl.textContent = contexts[scope];
}

function updateViewTabCounts(data) {
  /**
   * Atualiza os contadores nas abas
   */
  if (data.counts) {
    const countMe = document.getElementById('countMe');
    const countTeam = document.getElementById('countTeam');
    const countCompany = document.getElementById('countCompany');
    
    if (countMe && data.counts.me !== undefined) {
      countMe.textContent = data.counts.me;
    }
    if (countTeam && data.counts.team !== undefined) {
      countTeam.textContent = data.counts.team;
    }
    if (countCompany && data.counts.company !== undefined) {
      countCompany.textContent = data.counts.company;
    }
  }
}

// ========================================
// Filtros
// ========================================

function initializeFilters() {
  const filterTabs = document.querySelectorAll('.filter-tab');
  
  filterTabs.forEach(tab => {
    tab.addEventListener('click', function() {
      filterTabs.forEach(t => t.classList.remove('filter-tab--active'));
      this.classList.add('filter-tab--active');
      state.currentFilter = this.dataset.filter || 'all';
      renderActivities();
      updateFilterCountBadges();
    });
  });
}

function initializeSearch() {
  const searchInput = document.getElementById('searchInput');
  if (!searchInput) return;
  
  searchInput.addEventListener('input', function() {
    state.searchQuery = (this.value || '').toLowerCase();
    renderActivities();
  });
}

function initializeViewSwitcher() {
  const viewButtons = document.querySelectorAll('.view-btn');
  
  viewButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      viewButtons.forEach(b => b.classList.remove('view-btn--active'));
      this.classList.add('view-btn--active');
      state.currentView = this.dataset.view || 'list';
      applyView(state.currentView);
    });
  });
}

function applyView(view) {
  const activitiesList = document.getElementById('activitiesList');
  
  if (!activitiesList) return;
  
  if (view === 'kanban') {
    window.showMessage('Visualização Kanban em desenvolvimento', 'info');
  } else {
    activitiesList.style.display = 'flex';
  }
}

function initializeSorting() {
  const sortSelect = document.getElementById('sortSelect');
  if (!sortSelect) return;
  
  sortSelect.addEventListener('change', function() {
    state.sortBy = this.value || 'deadline';
    renderActivities();
  });
}

function handleStartActivity(activityId, activityTitle, activityElement) {
  console.log('Iniciando atividade:', activityId);
  
  // Simular início de atividade
  const statusIndicator = activityElement.querySelector('.status-indicator');
  statusIndicator.classList.remove('status-indicator--pending');
  statusIndicator.classList.add('status-indicator--progress');
  
  // Adicionar status "Em Andamento"
  const meta = activityElement.querySelector('.activity-item__meta');
  if (!meta.querySelector('.activity-status')) {
    const statusSpan = document.createElement('span');
    statusSpan.className = 'activity-status';
    statusSpan.textContent = '⏳ Em Andamento';
    meta.appendChild(statusSpan);
  }
  
  // Trocar botão
  const actions = activityElement.querySelector('.activity-item__actions');
  const startBtn = actions.querySelector('.action-btn--start, .action-btn--urgent');
  if (startBtn) {
    startBtn.classList.remove('action-btn--start', 'action-btn--urgent');
    startBtn.classList.add('action-btn--pause');
    startBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="6" y="4" width="4" height="16"></rect>
        <rect x="14" y="4" width="4" height="16"></rect>
      </svg>
    `;
    startBtn.title = 'Pausar';
  }
  
  window.showMessage(`Atividade "${activityTitle}" iniciada!`, 'success');
  
  // TODO: Chamar API para atualizar status
  // updateActivityStatus(activityId, 'in_progress');
}

function handlePauseActivity(activityId, activityTitle, activityElement) {
  console.log('Pausando atividade:', activityId);
  
  // Simular pausa
  const statusIndicator = activityElement.querySelector('.status-indicator');
  statusIndicator.classList.remove('status-indicator--progress');
  statusIndicator.classList.add('status-indicator--pending');
  
  // Remover status "Em Andamento"
  const statusSpan = activityElement.querySelector('.activity-status');
  if (statusSpan) statusSpan.remove();
  
  // Trocar botão
  const pauseBtn = activityElement.querySelector('.action-btn--pause');
  if (pauseBtn) {
    pauseBtn.classList.remove('action-btn--pause');
    pauseBtn.classList.add('action-btn--continue');
    pauseBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
      Continuar
    `;
    pauseBtn.title = 'Continuar';
  }
  
  window.showMessage(`Atividade "${activityTitle}" pausada`, 'info');
  
  // TODO: Chamar API
  // updateActivityStatus(activityId, 'paused');
}

function handleViewActivity(activityId, activityElement) {
  console.log('Visualizando atividade:', activityId);
  
  const activityType = activityElement.dataset.type;
  
  if (activityType === 'project') {
    // Redirecionar para página de detalhes da atividade de projeto
    window.location.href = `/my-work/activity/${activityId}`;
  } else if (activityType === 'process') {
    // Redirecionar para página de detalhes da instância de processo
    window.location.href = `/my-work/process-instance/${activityId}`;
  }
}

function handleApproveActivity(activityId, activityTitle) {
  console.log('Aprovando atividade:', activityId);
  
  if (!confirm(`Deseja aprovar "${activityTitle}"?`)) {
    return;
  }
  
  window.showMessage(`Atividade "${activityTitle}" aprovada!`, 'success');
  
  // TODO: Chamar API
  // approveProcessInstance(activityId);
  
  // Remover atividade da lista após 1 segundo
  setTimeout(() => {
    const activity = document.querySelector(`[data-activity-id="${activityId}"]`);
    if (activity) {
      activity.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => activity.remove(), 300);
    }
  }, 1000);
}

function handleRejectActivity(activityId, activityTitle) {
  console.log('Rejeitando atividade:', activityId);
  
  const reason = prompt(`Por que você está rejeitando "${activityTitle}"?`);
  if (!reason) return;
  
  window.showMessage(`Atividade "${activityTitle}" rejeitada`, 'info');
  
  // TODO: Chamar API
  // rejectProcessInstance(activityId, reason);
  
  // Remover atividade da lista
  setTimeout(() => {
    const activity = document.querySelector(`[data-activity-id="${activityId}"]`);
    if (activity) {
      activity.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => activity.remove(), 300);
    }
  }, 1000);
}

function handleUrgentActivity(activityId, activityTitle, activityElement) {
  console.log('Priorizando atividade:', activityId);
  handleStartActivity(activityId, activityTitle, activityElement);
}

// ========================================
// Carregar Dados (API)
// ========================================

async function loadActivitiesData() {
  try {
    console.log('Carregando dados para scope:', state.currentScope);
    
    setActivitiesLoading(true);
    
    const params = new URLSearchParams({
      scope: state.currentScope
    });
    
    const response = await fetch(`/my-work/api/activities?${params.toString()}`);
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar atividades');
    }
    
    state.activities = Array.isArray(data.data) ? data.data : [];
    
    updateStats(data.stats);
    updateViewTabCounts(data);
    updateFilterCountBadges();
    updateTimeTracking(calculateTimeFromActivities(state.activities));
    renderActivities();
    
    if (state.currentScope === 'team') {
      state.teamData = null;
      loadTeamOverview();
    } else if (state.currentScope === 'company') {
      state.companyData = null;
      loadCompanyOverview();
    }
    
    console.log(`✅ Carregados ${state.activities.length} registros para scope: ${state.currentScope}`);
  } catch (error) {
    console.error('Erro ao carregar atividades:', error);
    window.showMessage(error.message || 'Erro ao carregar atividades', 'error');
    state.activities = [];
    updateStats({ pending: 0, in_progress: 0, overdue: 0, completed: 0 });
    updateFilterCountBadges();
    renderActivities();
  } finally {
    setActivitiesLoading(false);
  }
}

function renderActivities() {
  const activitiesList = document.getElementById('activitiesList');
  const emptyState = document.getElementById('emptyState');
  if (!activitiesList || !emptyState) return;
  
  const loader = activitiesList.querySelector('.activity-placeholder');
  if (loader) {
    loader.style.display = 'none';
  }
  
  const filteredActivities = getFilteredActivities();
  
  activitiesList.querySelectorAll('.activity-item').forEach(item => item.remove());
  
  if (!filteredActivities.length) {
    activitiesList.style.display = 'none';
    emptyState.style.display = 'flex';
    updateFilterCountBadges();
    return;
  }
  
  activitiesList.style.display = 'flex';
  emptyState.style.display = 'none';
  
  const fragment = document.createDocumentFragment();
  filteredActivities.forEach(activity => {
    fragment.appendChild(createActivityElement(activity));
  });
  
  activitiesList.appendChild(fragment);
  updateFilterCountBadges();
  animateOnScroll();
}

function setActivitiesLoading(isLoading) {
  const activitiesList = document.getElementById('activitiesList');
  const loader = activitiesList?.querySelector('.activity-placeholder');
  if (!activitiesList || !loader) return;
  
  if (isLoading) {
    activitiesList.dataset.state = 'loading';
    loader.style.display = 'flex';
  } else {
    activitiesList.dataset.state = 'loaded';
    loader.style.display = 'none';
  }
}

function getFilteredActivities() {
  let activities = Array.from(state.activities || []);
  
  if (state.currentFilter && state.currentFilter !== 'all') {
    activities = activities.filter(activity => {
      const tags = activity.filter_tags || [];
      return tags.includes(state.currentFilter);
    });
  }
  
  if (state.searchQuery) {
    const query = state.searchQuery;
    activities = activities.filter(activity => {
      const haystack = [
        activity.title,
        activity.description,
        activity.plan_name,
        activity.company_name
      ].join(' ').toLowerCase();
      return haystack.includes(query);
    });
  }
  
  activities.sort((a, b) => {
    switch (state.sortBy) {
      case 'priority':
        return (b.priority_order || 0) - (a.priority_order || 0);
      case 'status':
        return (a.status_order || 99) - (b.status_order || 99);
      case 'recent':
        return (b.updated_sort_key || 0) - (a.updated_sort_key || 0);
      case 'deadline':
      default:
        return (a.deadline_sort_key || 9999999) - (b.deadline_sort_key || 9999999);
    }
  });
  
  return activities;
}

function createActivityElement(activity) {
  const wrapper = document.createElement('div');
  const typeClass = activity.type === 'process' ? 'activity-item--process' : 'activity-item--project';
  const priorityClass = getPriorityClass(activity.priority);
  const overdueClass = activity.is_overdue ? 'activity-item--overdue' : '';
  
  wrapper.className = `activity-item ${typeClass} ${priorityClass} ${overdueClass}`.trim();
  wrapper.dataset.activityId = activity.id;
  wrapper.dataset.type = activity.type;
  wrapper.dataset.estimatedHours = activity.estimated_hours || 0;
  wrapper.dataset.workedHours = activity.worked_hours || 0;
  wrapper.dataset.status = activity.status || '';
  wrapper.dataset.priority = activity.priority || '';
  wrapper.dataset.deadline = activity.deadline || '';
  wrapper.dataset.deadlineLabel = activity.deadline_label || '';
  wrapper.dataset.assignmentLabel = activity.assignment?.label || '';
  wrapper.dataset.companyName = activity.company_name || '';
  wrapper.dataset.planName = activity.plan_name || '';
  wrapper.dataset.title = activity.title || '';
  wrapper.dataset.description = activity.description || '';
  
  const statusIndicatorClass = getStatusIndicatorClass(activity);
  const assignmentLabel = activity.assignment?.label || '';
  const metaBadge = assignmentLabel ? `<span class="activity-role">${assignmentLabel}</span>` : '';
  const typeLabel = activity.type === 'process' ? 'PROCESSO' : 'PROJETO';
  const priorityLabel = getPriorityLabel(activity.priority);
  const deadlineInfo = formatDeadline(activity);
  const secondaryInfo = formatSecondaryInfo(activity);
  const progressBar = renderProgressBar(activity);
  
  wrapper.innerHTML = `
    <div class="activity-item__status">
      <div class="status-indicator ${statusIndicatorClass}"></div>
    </div>
    <div class="activity-item__content">
      <div class="activity-item__header">
        <div class="activity-item__type">
          <span class="type-badge type-badge--${activity.type}">${typeLabel}</span>
          ${priorityLabel}
          ${activity.is_overdue ? '<span class="overdue-badge">⚠️ Atrasada</span>' : ''}
        </div>
        <div class="activity-item__meta">
          ${metaBadge}
        </div>
      </div>
      <h3 class="activity-item__title">${activity.title || 'Atividade sem título'}</h3>
      ${activity.description ? `<p class="activity-item__description">${activity.description}</p>` : ''}
      ${progressBar}
      <div class="activity-item__footer">
        <div class="activity-item__info">
          <span class="info-item info-item--deadline ${activity.is_overdue ? 'info-item--overdue' : ''}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
            ${deadlineInfo}
          </span>
          ${secondaryInfo}
        </div>
        <div class="activity-item__actions">
          <button class="action-btn action-btn--add-hours" title="Adicionar Horas" data-action="add-hours">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            + Horas
          </button>
          <button class="action-btn action-btn--comment" title="Adicionar Comentário" data-action="add-comment">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Comentar
          </button>
          <button class="action-btn action-btn--complete" title="Finalizar" data-action="complete">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Finalizar
          </button>
        </div>
      </div>
    </div>
  `;
  
  return wrapper;
}

function getPriorityClass(priority) {
  const normalized = (priority || 'normal').toLowerCase();
  if (normalized === 'urgent' || normalized === 'high') return 'activity-item--high';
  if (normalized === 'medium' || normalized === 'normal') return 'activity-item--medium';
  return 'activity-item--low';
}

function getPriorityLabel(priority) {
  const normalized = (priority || 'normal').toLowerCase();
  const labels = {
    urgent: 'Urgente',
    high: 'Alta Prioridade',
    medium: 'Média Prioridade',
    normal: 'Prioridade Normal',
    low: 'Baixa Prioridade'
  };
  return `<span class="priority-badge priority-badge--${normalized}">${labels[normalized] || 'Prioridade'}</span>`;
}

function getStatusIndicatorClass(activity) {
  const status = (activity.status || '').toLowerCase();
  if (activity.is_overdue && status !== 'completed') return 'status-indicator--overdue';
  if (status === 'in_progress' || status === 'executing' || status === 'ongoing') return 'status-indicator--progress';
  if (status === 'completed') return 'status-indicator--completed';
  return 'status-indicator--pending';
}

function formatDeadline(activity) {
  if (activity.deadline_label) {
    return activity.deadline_label;
  }
  if (!activity.deadline) {
    return 'Sem prazo definido';
  }
  return new Date(activity.deadline).toLocaleDateString('pt-BR');
}

function formatSecondaryInfo(activity) {
  const infoItems = [];
  
  if (activity.type === 'project' && activity.plan_name) {
    infoItems.push(`
      <span class="info-item info-item--project">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        ${activity.plan_name}
      </span>
    `);
  }
  
  if (activity.type === 'process' && activity.instance_code) {
    infoItems.push(`
      <span class="info-item info-item--process">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
        ${activity.instance_code}
      </span>
    `);
  }
  
  if (activity.estimated_hours) {
    infoItems.push(`
      <span class="info-item info-item--time">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        ${formatHours(activity.estimated_hours)} estimadas
      </span>
    `);
  }
  
  return infoItems.join('');
}

function renderProgressBar(activity) {
  if (!activity.progress_percent) return '';
  return `
    <div class="activity-progress">
      <div class="progress-bar">
        <div class="progress-bar__fill" style="width: ${activity.progress_percent}%;"></div>
      </div>
      <span class="progress-label">${activity.progress_percent}% concluído</span>
    </div>
  `;
}

function formatHours(value) {
  const hours = parseFloat(value || 0);
  if (!hours) return '0h';
  return `${hours.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}h`;
}

function updateFilterCountBadges() {
  const counters = document.querySelectorAll('[data-filter-count]');
  if (!counters.length) return;
  
  const counts = {
    all: state.activities.length,
    today: 0,
    week: 0,
    overdue: 0
  };
  
  state.activities.forEach(activity => {
    const tags = activity.filter_tags || [];
    if (tags.includes('today')) counts.today += 1;
    if (tags.includes('week')) counts.week += 1;
    if (tags.includes('overdue')) counts.overdue += 1;
  });
  
  counters.forEach(counter => {
    const key = counter.dataset.filterCount;
    if (key && counts[key] !== undefined) {
      counter.textContent = counts[key];
    }
  });
}

async function loadTeamOverview() {
  if (state.teamData) {
    renderTeamOverview(state.teamData);
    return;
  }
  
  const loader = document.getElementById('teamOverviewLoader');
  const body = document.getElementById('teamOverviewBody');
  if (!loader || !body) return;
  
  loader.style.display = 'flex';
  body.style.display = 'none';
  
  try {
    const response = await fetch('/my-work/api/team-overview');
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar visão da equipe');
    }
    
    state.teamData = data.data || {};
    renderTeamOverview(state.teamData);
  } catch (error) {
    console.error('Erro ao carregar Team Overview:', error);
    loader.innerHTML = `<p class="text-error">${error.message || 'Não foi possível carregar os dados da equipe.'}</p>`;
  }
}

function renderTeamOverview(data) {
  const loader = document.getElementById('teamOverviewLoader');
  const body = document.getElementById('teamOverviewBody');
  if (!loader || !body) return;
  
  loader.style.display = 'none';
  body.style.display = data && Object.keys(data).length ? 'grid' : 'none';
  
  if (!data || !Object.keys(data).length) {
    loader.innerHTML = '<p>Sem dados para exibir.</p>';
    loader.style.display = 'flex';
    return;
  }
  
  body.innerHTML = `
    <div class="team-card">
      <h3>📊 Distribuição de Carga</h3>
      <div class="team-members-list">
        ${renderTeamMembers(data.members)}
      </div>
    </div>
    <div class="team-card">
      <h3>⚠️ Alertas</h3>
      <div class="team-alerts">
        ${renderTeamAlerts(data.alerts)}
      </div>
    </div>
    <div class="team-card">
      <h3>📈 Performance</h3>
      <div class="team-performance-compact">
        ${renderTeamPerformance(data.performance)}
      </div>
    </div>
  `;
}

function renderTeamMembers(members = []) {
  if (!members.length) {
    return '<p class="text-muted">Nenhum membro encontrado.</p>';
  }
  
  return members.map(member => `
    <div class="team-member-item">
      <div class="member-info">
        <span class="member-name">${member.name || 'Colaborador'}</span>
        <span class="member-role">${member.role || ''}</span>
      </div>
      <div class="member-load">
        <div class="load-bar">
          <div class="load-bar-fill ${member.utilization_percent >= 90 ? 'load-bar-fill--warning' : ''}" style="width: ${Math.min(member.utilization_percent || 0, 100)}%"></div>
        </div>
        <span class="load-percentage ${member.utilization_percent >= 90 ? 'load-percentage--warning' : ''}">
          ${member.utilization_percent || 0}%
        </span>
      </div>
      <span class="member-hours">${formatHours(member.allocated)} / ${formatHours(member.capacity)}</span>
    </div>
  `).join('');
}

function renderTeamAlerts(alerts = []) {
  if (!alerts.length) {
    return '<p class="text-muted">Nenhum alerta no momento.</p>';
  }
  
  return alerts.map(alert => `
    <div class="team-alert team-alert--${alert.severity || 'info'}">
      <span class="alert-icon">${alert.type === 'overload' ? '⚠️' : alert.type === 'available' ? '✅' : 'ℹ️'}</span>
      <div class="alert-content">
        <strong>${alert.message}</strong>
        <p>${alert.details || ''}</p>
      </div>
    </div>
  `).join('');
}

function renderTeamPerformance(performance = {}) {
  const metrics = [
    { label: 'Score', value: performance.avg_score },
    { label: 'No Prazo', value: performance.completion_rate ? `${performance.completion_rate}%` : '--' },
    { label: 'Utilização', value: performance.capacity_utilization ? `${performance.capacity_utilization}%` : '--' }
  ];
  
  return metrics.map(metric => `
    <div class="perf-item">
      <div class="perf-value">${metric.value !== undefined ? metric.value : '--'}</div>
      <div class="perf-label">${metric.label}</div>
    </div>
  `).join('');
}

async function loadCompanyOverview() {
  if (state.companyData) {
    renderCompanyOverview(state.companyData);
    return;
  }
  
  const loader = document.getElementById('companyOverviewLoader');
  const body = document.getElementById('companyOverviewBody');
  if (!loader || !body) return;
  
  loader.style.display = 'flex';
  body.style.display = 'none';
  
  try {
    const response = await fetch('/my-work/api/company-overview');
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar visão da empresa');
    }
    
    state.companyData = data.data || {};
    renderCompanyOverview(state.companyData);
  } catch (error) {
    console.error('Erro ao carregar Company Overview:', error);
    loader.innerHTML = `<p class="text-error">${error.message || 'Não foi possível carregar a visão da empresa.'}</p>`;
  }
}

function renderCompanyOverview(data) {
  const loader = document.getElementById('companyOverviewLoader');
  const body = document.getElementById('companyOverviewBody');
  if (!loader || !body) return;
  
  loader.style.display = 'none';
  body.style.display = data && Object.keys(data).length ? 'grid' : 'none';
  
  if (!data || !Object.keys(data).length) {
    loader.innerHTML = '<p>Sem dados para exibir.</p>';
    loader.style.display = 'flex';
    return;
  }
  
  body.innerHTML = `
    <div class="company-card company-card--summary">
      <h3>📌 Indicadores Principais</h3>
      <div class="executive-stats">
        ${renderCompanySummary(data.summary)}
      </div>
    </div>
    <div class="company-card company-card--large">
      <h3>🗺️ Mapa de Calor por Equipe</h3>
      <div class="heatmap-grid">
        ${renderCompanyHeatmap(data.heatmap)}
      </div>
    </div>
    <div class="company-card">
      <h3>🏆 Ranking de Performance</h3>
      <div class="ranking-list">
        ${renderCompanyRanking(data.ranking)}
      </div>
    </div>
  `;
}

function renderCompanySummary(summary = {}) {
  const metrics = [
    { label: 'Equipes Ativas', value: summary.active_teams },
    { label: 'Colaboradores', value: summary.total_employees },
    { label: 'Capacidade Média', value: summary.avg_capacity_utilization ? `${summary.avg_capacity_utilization}%` : '--' },
    { label: 'Atividades Abertas', value: summary.total_activities }
  ];
  
  return metrics.map(metric => `
    <div class="exec-stat">
      <div class="exec-stat-value">${metric.value !== undefined ? metric.value : '--'}</div>
      <div class="exec-stat-label">${metric.label}</div>
    </div>
  `).join('');
}

function renderCompanyHeatmap(heatmap = []) {
  if (!heatmap.length) {
    return '<p class="text-muted">Nenhuma equipe disponível.</p>';
  }
  
  return heatmap.map(item => `
    <div class="heatmap-item heatmap-item--${item.status || 'medium'}">
      <div class="heatmap-header">
        <span class="heatmap-name">${item.team_name}</span>
        <span class="heatmap-people">${item.employee_count || 0} pessoas</span>
      </div>
      <div class="heatmap-bar">
        <div class="heatmap-fill" style="width: ${Math.min(item.utilization_percent || 0, 100)}%"></div>
      </div>
      <div class="heatmap-stats">
        <span class="heatmap-count">${item.activities_count || 0} atividades</span>
        <span class="heatmap-load">${item.utilization_percent || 0}% ocupação</span>
      </div>
    </div>
  `).join('');
}

function renderCompanyRanking(ranking = []) {
  if (!ranking.length) {
    return '<p class="text-muted">Sem ranking disponível.</p>';
  }
  
  return ranking.map(item => `
    <div class="ranking-item">
      <div class="ranking-position">${item.rank || '-'}</div>
      <div class="ranking-info">
        <span class="ranking-name">${item.team_name || 'Equipe'}</span>
        <div class="ranking-metrics">
          <span class="metric-chip metric-chip--score">Score: ${item.score || '--'}</span>
          <span class="metric-chip metric-chip--completion">${item.completion_rate !== undefined ? `${item.completion_rate}%` : '--'} no prazo</span>
        </div>
      </div>
      <div class="ranking-score">${item.score || '--'}</div>
    </div>
  `).join('');
}

function updateStats(stats) {
  if (!stats) return;
  
  const statPending = document.getElementById('stat-pending');
  const statProgress = document.getElementById('stat-progress');
  const statOverdue = document.getElementById('stat-overdue');
  const statCompleted = document.getElementById('stat-completed');
  
  if (statPending) animateValue(statPending, 0, stats.pending, 1000);
  if (statProgress) animateValue(statProgress, 0, stats.in_progress, 1000);
  if (statOverdue) animateValue(statOverdue, 0, stats.overdue, 1000);
  if (statCompleted) animateValue(statCompleted, 0, stats.completed, 1000);
}

function updatePerformanceScore(performance) {
  if (!performance) return;
  
  const scoreCircle = document.querySelector('.score-circle');
  const scoreNumber = document.querySelector('.score-number');
  
  if (scoreCircle && scoreNumber) {
    scoreCircle.style.setProperty('--score', performance.score);
    animateValue(scoreNumber, 0, performance.score, 1500);
  }
}

// ========================================
// Utilitários
// ========================================

function animateValue(element, start, end, duration) {
  const range = end - start;
  const increment = range / (duration / 16);
  let current = start;
  
  const timer = setInterval(() => {
    current += increment;
    if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
      current = end;
      clearInterval(timer);
    }
    element.textContent = Math.round(current);
  }, 16);
}

function animateOnScroll() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, {
    threshold: 0.1
  });
  
  // Observar cards e atividades
  document.querySelectorAll('.stat-card, .activity-item, .report-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });
}

// ========================================
// API Calls (Para implementação futura)
// ========================================

async function updateActivityStatus(activityId, status) {
  try {
    const response = await fetch(`/my-work/api/activities/${activityId}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status })
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro ao atualizar status:', error);
    throw error;
  }
}

async function approveProcessInstance(instanceId) {
  try {
    const response = await fetch(`/my-work/api/process-instances/${instanceId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro ao aprovar instância:', error);
    throw error;
  }
}

async function rejectProcessInstance(instanceId, reason) {
  try {
    const response = await fetch(`/my-work/api/process-instances/${instanceId}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason })
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro ao rejeitar instância:', error);
    throw error;
  }
}

// ========================================
// Time Tracker (Sidebar)
// ========================================

function initializeTimeTracker() {
  const timeTabs = document.querySelectorAll('.time-tab');
  const timeViewDay = document.getElementById('timeViewDay');
  const timeViewWeek = document.getElementById('timeViewWeek');
  
  timeTabs.forEach(tab => {
    tab.addEventListener('click', function() {
      // Remove active class from all tabs
      timeTabs.forEach(t => t.classList.remove('time-tab--active'));
      
      // Add active class to clicked tab
      this.classList.add('time-tab--active');
      
      // Get period
      const period = this.dataset.period;
      
      // Show/hide views
      if (period === 'day') {
        timeViewDay.style.display = 'block';
        timeViewWeek.style.display = 'none';
      } else if (period === 'week') {
        timeViewDay.style.display = 'none';
        timeViewWeek.style.display = 'block';
      }
    });
  });
}

function updateTimeTracking(data) {
  /**
   * Atualiza os dados do painel de controle de horas
   * 
   * @param {Object} data - Dados de horas
   * @param {Object} data.day - Dados do dia
   * @param {Object} data.week - Dados da semana
   */
  
  if (!data) return;
  
  // Atualizar visão do dia
  if (data.day) {
    updateDayView(data.day);
  }
  
  // Atualizar visão da semana
  if (data.week) {
    updateWeekView(data.week);
  }
}

function updateDayView(dayData) {
  /**
   * Atualiza a visão do dia no painel de horas
   */
  
  // Atualizar resumo
  // TODO: Implementar atualização dinâmica dos valores
  
  // Verificar sobrecarga
  if (dayData.planned > dayData.capacity) {
    const alert = document.getElementById('overloadAlert');
    if (alert) alert.style.display = 'block';
  }
}

function updateWeekView(weekData) {
  /**
   * Atualiza a visão da semana no painel de horas
   */
  
  // TODO: Implementar atualização dinâmica dos gráficos
}

function calculateTimeFromActivities(activities) {
  /**
   * Calcula as horas previstas e realizadas baseado nas atividades
   * 
   * @param {Array} activities - Lista de atividades
   * @returns {Object} Objeto com horas calculadas
   */
  
  const result = {
    projects: {
      planned: 0,
      done: 0,
      count: 0
    },
    processes: {
      planned: 0,
      done: 0,
      count: 0
    },
    total: {
      capacity: 8, // 8h por dia padrão
      planned: 0,
      done: 0,
      available: 0
    }
  };
  
  activities.forEach(activity => {
    if (activity.type === 'project') {
      result.projects.planned += activity.estimated_hours || 0;
      result.projects.done += activity.worked_hours || 0;
      result.projects.count++;
    } else if (activity.type === 'process') {
      result.processes.planned += activity.estimated_hours || 0;
      result.processes.done += activity.worked_hours || 0;
      result.processes.count++;
    }
  });
  
  result.total.planned = result.projects.planned + result.processes.planned;
  result.total.done = result.projects.done + result.processes.done;
  result.total.available = result.total.capacity - result.total.planned;
  
  return result;
}

// ========================================
// Keyboard Shortcuts
// ========================================

document.addEventListener('keydown', function(e) {
  // Ctrl/Cmd + F: Focar no campo de busca
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    e.preventDefault();
    document.getElementById('searchInput').focus();
  }
  
  // Escape: Limpar busca
  if (e.key === 'Escape') {
    const searchInput = document.getElementById('searchInput');
    if (searchInput.value) {
      searchInput.value = '';
      state.searchQuery = '';
      renderActivities();
    }
  }
});

// ========================================
// Auto Refresh (Opcional)
// ========================================

// Atualizar dados a cada 5 minutos
// setInterval(loadActivitiesData, 5 * 60 * 1000);

// ========================================
// MODAL MANAGEMENT
// ========================================

let currentActivity = null;

function openModal(modalId, activity) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  currentActivity = activity;
  
  // Preencher informações da atividade no modal
  populateActivityInfo(modalId, activity);
  
  // Configurar data padrão como hoje
  if (modalId === 'modalAddHours') {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('workDate').value = today;
    
    // Atualizar resumo de horas
    updateHoursSummary();
    
    // Listener para calcular total ao digitar
    document.getElementById('hoursWorked').addEventListener('input', updateHoursSummary);
  }
  
  // Mostrar modal
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  
  // Fechar ao clicar no overlay
  modal.addEventListener('click', function(e) {
    if (e.target === modal) {
      closeModal(modalId);
    }
  });
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
  
  // Limpar formulários
  const forms = modal.querySelectorAll('form');
  forms.forEach(form => form.reset());
  
  currentActivity = null;
}

function populateActivityInfo(modalId, activity) {
  // Determinar qual div de info usar
  let infoDiv;
  if (modalId === 'modalAddHours') {
    infoDiv = document.getElementById('addHoursActivityInfo');
  } else if (modalId === 'modalAddComment') {
    infoDiv = document.getElementById('addCommentActivityInfo');
  } else if (modalId === 'modalComplete') {
    infoDiv = document.getElementById('completeActivityInfo');
  }
  
  if (!infoDiv || !activity) return;
  
  const details = [];
  
  if (activity.assignment_label) {
    details.push(`<li>${activity.assignment_label}</li>`);
  }
  if (activity.plan_name) {
    details.push(`<li>Plano: ${activity.plan_name}</li>`);
  }
  if (activity.company_name) {
    details.push(`<li>Empresa: ${activity.company_name}</li>`);
  }
  if (activity.deadline_label || activity.deadline) {
    const deadlineText = activity.deadline_label || new Date(activity.deadline).toLocaleDateString('pt-BR');
    details.push(`<li>Prazo: ${deadlineText}</li>`);
  }
  if (activity.description) {
    details.push(`<li>${activity.description}</li>`);
  }
  
  infoDiv.innerHTML = `
    <h4>${activity.title}</h4>
    <p>${activity.type === 'project' ? '📁 Atividade de Projeto' : '⚙️ Instância de Processo'}</p>
    ${details.length ? `<ul class="activity-details">${details.join('')}</ul>` : ''}
  `;
}

function updateHoursSummary() {
  const newHours = parseFloat(document.getElementById('hoursWorked').value) || 0;
  const currentHours = currentActivity?.worked_hours || 0;
  const estimatedHours = currentActivity?.estimated_hours || 0;
  const totalAfter = currentHours + newHours;
  
  document.getElementById('currentHours').textContent = formatHours(currentHours);
  document.getElementById('estimatedHours').textContent = formatHours(estimatedHours);
  document.getElementById('totalHoursAfter').textContent = formatHours(totalAfter);
  
  // Destacar se ultrapassar estimativa
  const totalAfterEl = document.getElementById('totalHoursAfter');
  if (totalAfter > estimatedHours && estimatedHours > 0) {
    totalAfterEl.style.color = 'var(--color-danger)';
  } else {
    totalAfterEl.style.color = 'var(--color-primary)';
  }
}

// ========================================
// FORM SUBMISSIONS
// ========================================

// Form: Adicionar Horas
document.getElementById('formAddHours')?.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(this);
  const data = {
    activity_id: parseInt(currentActivity.id),
    activity_type: currentActivity.type,
    work_date: formData.get('work_date'),
    hours: parseFloat(formData.get('hours')),
    description: formData.get('description')
  };
  
  console.log('Submitting hours:', data);
  
  try {
    const response = await fetch('/my-work/api/work-hours', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      window.showMessage(`✅ ${data.hours}h registradas com sucesso!`, 'success');
      closeModal('modalAddHours');
      
      // Recarregar dados
      loadActivitiesData();
    } else {
      window.showMessage(`❌ Erro: ${result.error}`, 'error');
    }
  } catch (error) {
    console.error('Erro ao adicionar horas:', error);
    window.showMessage('❌ Erro ao registrar horas', 'error');
  }
});

// Form: Adicionar Comentário
document.getElementById('formAddComment')?.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(this);
  const data = {
    activity_id: parseInt(currentActivity.id),
    activity_type: currentActivity.type,
    comment_type: formData.get('comment_type'),
    comment: formData.get('comment'),
    is_private: formData.get('is_private') === 'on'
  };
  
  console.log('Submitting comment:', data);
  
  try {
    const response = await fetch('/my-work/api/comments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      window.showMessage('✅ Comentário adicionado com sucesso!', 'success');
      closeModal('modalAddComment');
    } else {
      window.showMessage(`❌ Erro: ${result.error}`, 'error');
    }
  } catch (error) {
    console.error('Erro ao adicionar comentário:', error);
    window.showMessage('❌ Erro ao adicionar comentário', 'error');
  }
});

// Form: Finalizar Atividade
document.getElementById('formComplete')?.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(this);
  const data = {
    activity_id: parseInt(currentActivity.id),
    activity_type: currentActivity.type,
    completion_comment: formData.get('completion_comment'),
    status: 'completed'
  };
  
  console.log('Completing activity:', data);
  
  try {
    const response = await fetch('/my-work/api/complete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      window.showMessage('✅ Atividade finalizada com sucesso!', 'success');
      closeModal('modalComplete');
      
      // Remover atividade da lista
      setTimeout(() => {
        const activityElement = document.querySelector(`[data-activity-id="${data.activity_id}"]`);
        if (activityElement) {
          activityElement.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => activityElement.remove(), 300);
        }
      }, 500);
      
      // Recarregar dados
      setTimeout(() => {
        loadActivitiesData();
      }, 1000);
    } else {
      window.showMessage(`❌ Erro: ${result.error}`, 'error');
    }
  } catch (error) {
    console.error('Erro ao finalizar atividade:', error);
    window.showMessage('❌ Erro ao finalizar atividade', 'error');
  }
});

// Atualizar função de actions para usar os modals
function initializeActivityActions() {
  // Delegar eventos para ações
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.action-btn');
    if (!btn) return;
    
    const activity = btn.closest('.activity-item');
    if (!activity) return;
    
    const activityIdRaw = activity.dataset.activityId;
    const activityId = activityIdRaw ? parseInt(activityIdRaw, 10) : null;
    const activityTitle = activity.dataset.title || activity.querySelector('.activity-item__title')?.textContent || '';
    const activityType = activity.dataset.type || 'project';
    const workedHours = parseFloat(activity.dataset.workedHours || '0');
    const estimatedHours = parseFloat(activity.dataset.estimatedHours || '0');
    const deadline = activity.dataset.deadline || '';
    const deadlineLabel = activity.dataset.deadlineLabel || '';
    const assignmentLabel = activity.dataset.assignmentLabel || '';
    const status = activity.dataset.status || '';
    const companyName = activity.dataset.companyName || '';
    const planName = activity.dataset.planName || '';
    const description = activity.dataset.description || '';
    
    // Montar objeto de atividade
    const activityData = {
      id: activityId,
      title: activityTitle,
      type: activityType,
      worked_hours: workedHours,
      estimated_hours: estimatedHours,
      deadline,
      deadline_label: deadlineLabel,
      assignment_label: assignmentLabel,
      status,
      company_name: companyName,
      plan_name: planName,
      description
    };
    
    // Identificar ação pelo data-action
    const action = btn.dataset.action;
    
    if (action === 'add-hours') {
      openModal('modalAddHours', activityData);
    } else if (action === 'add-comment') {
      openModal('modalAddComment', activityData);
    } else if (action === 'complete') {
      openModal('modalComplete', activityData);
    }
  });
}

// Tornar funções globais para serem chamadas do HTML
window.openModal = openModal;
window.closeModal = closeModal;

console.log('✅ My Work page initialized');

