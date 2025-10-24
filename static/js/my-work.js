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
      // Remove active class from all tabs
      filterTabs.forEach(t => t.classList.remove('filter-tab--active'));
      
      // Add active class to clicked tab
      this.classList.add('filter-tab--active');
      
      // Get filter value
      const filter = this.dataset.filter;
      state.currentFilter = filter;
      
      // Apply filter
      applyFilters();
    });
  });
}

function applyFilters() {
  const activitiesList = document.getElementById('activitiesList');
  const emptyState = document.getElementById('emptyState');
  const activities = activitiesList.querySelectorAll('.activity-item');
  
  let visibleCount = 0;
  
  activities.forEach(activity => {
    const filters = activity.dataset.filter || '';
    const matchesFilter = state.currentFilter === 'all' || filters.includes(state.currentFilter);
    const matchesSearch = matchesSearchQuery(activity);
    
    if (matchesFilter && matchesSearch) {
      activity.style.display = '';
      visibleCount++;
    } else {
      activity.style.display = 'none';
    }
  });
  
  // Show/hide empty state
  if (visibleCount === 0) {
    activitiesList.style.display = 'none';
    emptyState.style.display = 'block';
  } else {
    activitiesList.style.display = '';
    emptyState.style.display = 'none';
  }
}

// ========================================
// Busca
// ========================================

function initializeSearch() {
  const searchInput = document.getElementById('searchInput');
  
  searchInput.addEventListener('input', function() {
    state.searchQuery = this.value.toLowerCase();
    applyFilters();
  });
}

function matchesSearchQuery(activity) {
  if (!state.searchQuery) return true;
  
  const title = activity.querySelector('.activity-item__title')?.textContent.toLowerCase() || '';
  const description = activity.querySelector('.activity-item__description')?.textContent.toLowerCase() || '';
  
  return title.includes(state.searchQuery) || description.includes(state.searchQuery);
}

// ========================================
// Troca de Visualização
// ========================================

function initializeViewSwitcher() {
  const viewButtons = document.querySelectorAll('.view-btn');
  
  viewButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      // Remove active class from all buttons
      viewButtons.forEach(b => b.classList.remove('view-btn--active'));
      
      // Add active class to clicked button
      this.classList.add('view-btn--active');
      
      // Get view type
      const view = this.dataset.view;
      state.currentView = view;
      
      // Apply view
      applyView(view);
    });
  });
}

function applyView(view) {
  const activitiesList = document.getElementById('activitiesList');
  
  if (view === 'kanban') {
    // TODO: Implementar visualização Kanban
    window.showMessage('Visualização Kanban em desenvolvimento', 'info');
  } else {
    // Lista (padrão)
    activitiesList.style.display = 'flex';
  }
}

// ========================================
// Ordenação
// ========================================

function initializeSorting() {
  const sortSelect = document.getElementById('sortSelect');
  
  sortSelect.addEventListener('change', function() {
    state.sortBy = this.value;
    sortActivities();
  });
}

function sortActivities() {
  const activitiesList = document.getElementById('activitiesList');
  const activities = Array.from(activitiesList.querySelectorAll('.activity-item'));
  
  activities.sort((a, b) => {
    switch (state.sortBy) {
      case 'priority':
        return comparePriority(a, b);
      case 'status':
        return compareStatus(a, b);
      case 'recent':
        return -1; // Mais recentes primeiro (ordem inversa do DOM)
      case 'deadline':
      default:
        return compareDeadline(a, b);
    }
  });
  
  // Reordenar no DOM
  activities.forEach(activity => activitiesList.appendChild(activity));
}

function comparePriority(a, b) {
  const priorityOrder = { high: 3, medium: 2, low: 1 };
  const aPriority = a.classList.contains('activity-item--high') ? 'high' : 
                    a.classList.contains('activity-item--medium') ? 'medium' : 'low';
  const bPriority = b.classList.contains('activity-item--high') ? 'high' : 
                    b.classList.contains('activity-item--medium') ? 'medium' : 'low';
  
  return (priorityOrder[bPriority] || 0) - (priorityOrder[aPriority] || 0);
}

function compareStatus(a, b) {
  const statusIndicatorA = a.querySelector('.status-indicator');
  const statusIndicatorB = b.querySelector('.status-indicator');
  
  const statusOrder = { 'overdue': 4, 'pending': 3, 'progress': 2, 'completed': 1 };
  
  const getStatus = (indicator) => {
    if (indicator.classList.contains('status-indicator--overdue')) return 'overdue';
    if (indicator.classList.contains('status-indicator--pending')) return 'pending';
    if (indicator.classList.contains('status-indicator--progress')) return 'progress';
    return 'completed';
  };
  
  return (statusOrder[getStatus(statusIndicatorA)] || 0) - (statusOrder[getStatus(statusIndicatorB)] || 0);
}

function compareDeadline(a, b) {
  // Atividades atrasadas primeiro
  if (a.classList.contains('activity-item--overdue') && !b.classList.contains('activity-item--overdue')) {
    return -1;
  }
  if (!a.classList.contains('activity-item--overdue') && b.classList.contains('activity-item--overdue')) {
    return 1;
  }
  return 0;
}

// ========================================
// Ações das Atividades
// ========================================

function initializeActivityActions() {
  // Delegar eventos para ações
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.action-btn');
    if (!btn) return;
    
    const activity = btn.closest('.activity-item');
    const activityId = activity?.dataset.activityId;
    const activityTitle = activity?.querySelector('.activity-item__title')?.textContent;
    
    // Identificar tipo de ação
    if (btn.classList.contains('action-btn--start') || btn.classList.contains('action-btn--continue')) {
      handleStartActivity(activityId, activityTitle, activity);
    } else if (btn.classList.contains('action-btn--pause')) {
      handlePauseActivity(activityId, activityTitle, activity);
    } else if (btn.classList.contains('action-btn--view')) {
      handleViewActivity(activityId, activity);
    } else if (btn.classList.contains('action-btn--approve')) {
      handleApproveActivity(activityId, activityTitle);
    } else if (btn.classList.contains('action-btn--reject')) {
      handleRejectActivity(activityId, activityTitle);
    } else if (btn.classList.contains('action-btn--urgent')) {
      handleUrgentActivity(activityId, activityTitle, activity);
    }
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
    
    // Chamar API real com scope
    const response = await fetch(`/my-work/api/activities?scope=${state.currentScope}`);
    const data = await response.json();
    
    if (data.success) {
      state.activities = data.data;
      // renderActivities(data.data); // TODO: Implementar renderização dinâmica
      updateStats(data.stats);
      // updatePerformanceScore(data.performance); // TODO: Implementar
      updateViewTabCounts(data);
      
      console.log(`✅ Carregados ${data.data.length} atividades para scope: ${state.currentScope}`);
    } else {
      throw new Error(data.error || 'Erro ao carregar atividades');
    }
    
  } catch (error) {
    console.error('Erro ao carregar atividades:', error);
    window.showMessage('Erro ao carregar atividades', 'error');
    
    // Fallback: Usar contadores mock
    const mockCounts = {
      me: 17,
      team: 45,
      company: 180
    };
    updateViewTabCounts({ counts: mockCounts });
  }
}

function renderActivities(activities) {
  const activitiesList = document.getElementById('activitiesList');
  
  // TODO: Renderizar atividades dinamicamente
  // Por enquanto, estamos usando HTML estático
  
  console.log('Renderizando', activities.length, 'atividades');
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
      applyFilters();
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
  
  infoDiv.innerHTML = `
    <h4>${activity.title}</h4>
    <p>${activity.type === 'project' ? '📁 Atividade de Projeto' : '⚙️ Instância de Processo'}</p>
  `;
}

function updateHoursSummary() {
  const newHours = parseFloat(document.getElementById('hoursWorked').value) || 0;
  const currentHours = currentActivity?.worked_hours || 0;
  const estimatedHours = currentActivity?.estimated_hours || 0;
  const totalAfter = currentHours + newHours;
  
  document.getElementById('currentHours').textContent = `${currentHours}h`;
  document.getElementById('estimatedHours').textContent = `${estimatedHours}h`;
  document.getElementById('totalHoursAfter').textContent = `${totalAfter}h`;
  
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
    const activityId = activity?.dataset.activityId;
    const activityTitle = activity?.querySelector('.activity-item__title')?.textContent;
    const activityType = activity?.dataset.type;
    
    // Montar objeto de atividade
    const activityData = {
      id: activityId,
      title: activityTitle,
      type: activityType,
      worked_hours: 0, // TODO: buscar do backend
      estimated_hours: 8 // TODO: buscar do backend
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

