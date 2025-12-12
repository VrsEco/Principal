/**
 * MY WORK PAGE - Interactive Features
 * Gerenciamento de atividades do executor
 */

// ========================================
// Estado da Aplicação
// ========================================

const DELIVERY_FILTER_OPTIONS = [
  { value: 'open', label: 'Em aberto' },
  { value: 'completed', label: 'Concluídas' }
];
const DELIVERY_FILTER_VALUES = DELIVERY_FILTER_OPTIONS.map(option => option.value);

const state = {
  currentScope: 'me', // 'me', 'team', 'company'
  searchQuery: '',
  sortBy: 'deadline',
  activities: [],
  teamData: null,
  companyData: null,
  companies: [], // Lista de empresas do usuário
  collaborators: [],
  projectsDirectory: [],
  processesDirectory: [],
  processOwnersDirectory: [], // Lista de donos de processos
  selectedCompanyIds: [],
  selectedResponsibleIds: [],
  selectedExecutorIds: [],
  selectedProjectIds: [],
  selectedProcessIds: [],
  selectedProcessOwnerIds: [],
  selectedDeliveryTags: DELIVERY_FILTER_VALUES.slice(),
  dueDateStart: '',
  dueDateEnd: '',
  filtersCollapsed: false,
  activitiesCollapsed: false,
  processInstanceCache: {},
  processesByCompany: {}
};

function toggleFilterHighlight(element, isActive) {
  if (!element) return;
  element.classList.toggle('filter-control--active', Boolean(isActive));
}

const FILTER_CACHE_KEY = 'mywork_filters';

function saveFiltersToCache() {
  try {
    const filtersData = {
      selectedCompanyIds: state.selectedCompanyIds,
      selectedResponsibleIds: state.selectedResponsibleIds,
      selectedExecutorIds: state.selectedExecutorIds,
      selectedProjectIds: state.selectedProjectIds,
      selectedProcessIds: state.selectedProcessIds,
      selectedProcessOwnerIds: state.selectedProcessOwnerIds,
      selectedDeliveryTags: state.selectedDeliveryTags,
      dueDateStart: state.dueDateStart,
      dueDateEnd: state.dueDateEnd,
      searchQuery: state.searchQuery,
      sortBy: state.sortBy
    };
    localStorage.setItem(FILTER_CACHE_KEY, JSON.stringify(filtersData));
    // Atualizar link do relatório quando os filtros mudarem
    if (typeof updateReportLink === 'function') {
      updateReportLink();
    }
  } catch (error) {
    console.warn('Erro ao salvar filtros no cache:', error);
  }
}

function loadFiltersFromCache() {
  try {
    const cached = localStorage.getItem(FILTER_CACHE_KEY);
    if (!cached) return false;

    const filtersData = JSON.parse(cached);
    state.selectedCompanyIds = filtersData.selectedCompanyIds || [];
    state.selectedResponsibleIds = filtersData.selectedResponsibleIds || [];
    state.selectedExecutorIds = filtersData.selectedExecutorIds || [];
    state.selectedProjectIds = filtersData.selectedProjectIds || [];
    state.selectedProcessIds = filtersData.selectedProcessIds || [];
    state.selectedProcessOwnerIds = filtersData.selectedProcessOwnerIds || [];
    state.selectedDeliveryTags = filtersData.selectedDeliveryTags || DELIVERY_FILTER_VALUES.slice();
    state.dueDateStart = filtersData.dueDateStart || '';
    state.dueDateEnd = filtersData.dueDateEnd || '';
    state.searchQuery = filtersData.searchQuery || '';
    state.sortBy = filtersData.sortBy || 'deadline';

    // Atualizar link do relatório após carregar filtros
    if (typeof updateReportLink === 'function') {
      setTimeout(updateReportLink, 100);
    }

    return true;
  } catch (error) {
    console.warn('Erro ao carregar filtros do cache:', error);
    return false;
  }
}

function clearAllFilters() {
  // Resetar todos os filtros para valores padrão
  state.selectedCompanyIds = state.companies.map(c => c.company_id);
  state.selectedResponsibleIds = state.collaborators.map(c => c.id);
  state.selectedExecutorIds = state.collaborators.map(c => c.id);
  state.selectedProjectIds = state.projectsDirectory.map(p => p.id);
  state.selectedProcessIds = state.processesDirectory.map(p => p.id);
  state.selectedProcessOwnerIds = state.processOwnersDirectory.map(o => o.id);
  state.selectedDeliveryTags = DELIVERY_FILTER_VALUES.slice();
  state.dueDateStart = '';
  state.dueDateEnd = '';
  state.searchQuery = '';
  state.sortBy = 'deadline';

  // Atualizar UI
  const searchInput = document.getElementById('searchInput');
  if (searchInput) searchInput.value = '';

  const startInput = document.getElementById('filterDueDateStart');
  if (startInput) startInput.value = '';

  const endInput = document.getElementById('filterDueDateEnd');
  if (endInput) endInput.value = '';

  const sortSelect = document.getElementById('sortSelect');
  if (sortSelect) sortSelect.value = '';

  // Re-inicializar todos os multiselects
  FILTER_MULTISELECTS.forEach(config => setupMultiselect(config));

  // Atualizar highlights
  const wrapper = searchInput?.closest('.filter-input-wrapper');
  toggleFilterHighlight(wrapper, false);

  const dueDateCard = startInput?.closest('.filter-card');
  toggleFilterHighlight(dueDateCard, false);

  // Salvar e recarregar atividades
  saveFiltersToCache();
  loadActivitiesData();

  window.showMessage?.('Todos os filtros foram limpos', 'success');
}

const processInstanceFetchPromises = Object.create(null);
const processListFetchPromises = Object.create(null);

const SELECTION_MODE_NONE = 'none';

const DEFAULT_DAILY_CAPACITY = 8;
const WEEK_BAR_KEYS = ['seg', 'ter', 'qua', 'qui', 'sex'];
const DEFAULT_WEEKLY_CAPACITY = DEFAULT_DAILY_CAPACITY * WEEK_BAR_KEYS.length;
const CLOSED_STATUS_SET = new Set(['completed', 'done', 'cancelled', 'canceled', 'archived']);

function getActivityStatusCategory(activity) {
  const status = (activity?.status || '').toLowerCase();
  return CLOSED_STATUS_SET.has(status) ? 'completed' : 'open';
}

// ========================================
// Inicialização
// ========================================

document.addEventListener('DOMContentLoaded', async function () {
  await bootstrapFilterDashboard();
  initializeDueDateFilters();
  initializeSearch();
  initializeFilterCollapse();
  initializeActivitiesCollapse();
  initializeSorting();
  initializeActivityActions();
  initializeClearFiltersButton();
  initializeReportLink();
  updateSidebarCompactMode();
  animateOnScroll();
  loadActivitiesData();
});

const dropdownRegistry = [];

const FILTER_MULTISELECTS = [
  {
    key: 'company',
    triggerId: 'companyMultiselectTrigger',
    dropdownId: 'companyMultiselectDropdown',
    labelId: 'companyMultiselectLabel',
    listId: 'companyList',
    searchId: 'companySearchInput',
    selectAllId: 'selectAllCompanies',
    stateKey: 'selectedCompanyIds',
    selectAllByDefault: true,
    requireSelection: false,  // ← Permitir desmarcar todas
    optionsProvider: () =>
      (state.companies || []).map(company => ({
        id: company.company_id,
        label: company.company_name || `Empresa ${company.company_id}`,
        helper: ''
      })),
    labels: {
      empty: 'Nenhuma empresa',
      all: 'Todas as empresas',
      summary: count => `${count} empresas`
    },
    onChange: handleCompanySelectionChange
  },
  {
    key: 'responsible',
    triggerId: 'responsibleMultiselectTrigger',
    dropdownId: 'responsibleMultiselectDropdown',
    labelId: 'responsibleMultiselectLabel',
    listId: 'responsibleList',
    searchId: 'responsibleSearchInput',
    selectAllId: 'selectAllResponsibles',
    stateKey: 'selectedResponsibleIds',
    selectAllByDefault: true,
    optionsProvider: () => getCollaboratorOptions(),
    labels: {
      empty: 'Todos os responsáveis',
      all: 'Todos os responsáveis',
      summary: count => `${count} responsáveis`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  },
  {
    key: 'executor',
    triggerId: 'executorMultiselectTrigger',
    dropdownId: 'executorMultiselectDropdown',
    labelId: 'executorMultiselectLabel',
    listId: 'executorList',
    searchId: 'executorSearchInput',
    selectAllId: 'selectAllExecutors',
    stateKey: 'selectedExecutorIds',
    selectAllByDefault: true,
    optionsProvider: () => getCollaboratorOptions(),
    labels: {
      empty: 'Todos os executores',
      all: 'Todos os executores',
      summary: count => `${count} executores`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  },
  {
    key: 'projects',
    triggerId: 'projectMultiselectTrigger',
    dropdownId: 'projectMultiselectDropdown',
    labelId: 'projectMultiselectLabel',
    listId: 'projectList',
    searchId: 'projectSearchInput',
    selectAllId: 'selectAllProjects',
    stateKey: 'selectedProjectIds',
    selectAllByDefault: true,
    optionsProvider: () => getProjectOptions(),
    labels: {
      empty: 'Nenhum projeto',
      all: 'Todos os projetos',
      summary: count => `${count} projetos`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  },
  {
    key: 'processes',
    triggerId: 'processMultiselectTrigger',
    dropdownId: 'processMultiselectDropdown',
    labelId: 'processMultiselectLabel',
    listId: 'processList',
    searchId: 'processSearchInput',
    selectAllId: 'selectAllProcesses',
    stateKey: 'selectedProcessIds',
    selectAllByDefault: true,
    optionsProvider: () => getProcessOptions(),
    labels: {
      empty: 'Nenhum processo',
      all: 'Todos os processos',
      summary: count => `${count} processos`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  },
  {
    key: 'processOwners',
    triggerId: 'processOwnerMultiselectTrigger',
    dropdownId: 'processOwnerMultiselectDropdown',
    labelId: 'processOwnerMultiselectLabel',
    listId: 'processOwnerList',
    searchId: 'processOwnerSearchInput',
    selectAllId: 'selectAllProcessOwners',
    stateKey: 'selectedProcessOwnerIds',
    selectAllByDefault: true,
    requireSelection: false,
    optionsProvider: () => getProcessOwnerOptions(),
    labels: {
      empty: 'Nenhum dono',
      all: 'Todos os donos',
      summary: count => `${count} donos`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  },
  {
    key: 'delivery',
    triggerId: 'deliveryMultiselectTrigger',
    dropdownId: 'deliveryMultiselectDropdown',
    labelId: 'deliveryMultiselectLabel',
    listId: 'deliveryList',
    searchId: 'deliverySearchInput',
    selectAllId: 'selectAllDeliveryTags',
    stateKey: 'selectedDeliveryTags',
    selectAllByDefault: true,
    requireSelection: false,
    optionsProvider: () =>
      DELIVERY_FILTER_OPTIONS.map(option => ({
        id: option.value,
        label: option.label,
        helper: ''
      })),
    labels: {
      empty: 'Nenhum status disponível',
      all: 'Todos os status',
      summary: count => `${count} status`
    },
    onChange: () => { saveFiltersToCache(); loadActivitiesData(); }
  }
];

async function bootstrapFilterDashboard() {
  try {
    await loadFilterOptions();
    initializeMultiselects();
  } catch (error) {
    console.error('Erro ao inicializar painel de filtros', error);
  }
}

async function loadFilterOptions() {
  try {
    const response = await fetch('/my-work/api/filter-options');
    const payload = await response.json();
    if (!payload.success) {
      throw new Error(payload.error || 'Erro ao buscar filtros');
    }
    const data = payload.data || {};
    state.companies = data.companies || [];
    state.collaborators = data.collaborators || [];
    state.projectsDirectory = data.projects || [];
    state.processesDirectory = data.processes || [];

    // Tentar carregar filtros do cache
    const hasCache = loadFiltersFromCache();

    // Se não houver cache, inicializar com TODAS selecionadas por padrão
    if (!hasCache) {
      // Sempre inicializar com todas as empresas selecionadas na primeira vez
      state.selectedCompanyIds = state.companies.map(company => company.company_id);
      state.selectedResponsibleIds = state.collaborators.map(c => c.id);
      state.selectedExecutorIds = state.collaborators.map(c => c.id);
      state.selectedProjectIds = state.projectsDirectory.map(p => p.id);
      state.selectedProcessIds = state.processesDirectory.map(p => p.id);
    }

    // Aplicar os valores dos filtros restaurados nos campos do UI
    const searchInput = document.getElementById('searchInput');
    if (searchInput && state.searchQuery) {
      searchInput.value = state.searchQuery;
    }

    const startInput = document.getElementById('filterDueDateStart');
    if (startInput && state.dueDateStart) {
      startInput.value = state.dueDateStart;
    }

    const endInput = document.getElementById('filterDueDateEnd');
    if (endInput && state.dueDateEnd) {
      endInput.value = state.dueDateEnd;
    }

    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect && state.sortBy && state.sortBy !== 'deadline') {
      sortSelect.value = state.sortBy;
    }

  } catch (error) {
    console.error('Erro ao carregar opções de filtro:', error);
    window.showMessage?.('Não foi possível carregar as opções de filtro.', 'error');
  }
}

function initializeMultiselects() {
  FILTER_MULTISELECTS.forEach(config => setupMultiselect(config));
}

function setupMultiselect(config) {
  const trigger = document.getElementById(config.triggerId);
  const dropdown = document.getElementById(config.dropdownId);
  const labelEl = document.getElementById(config.labelId);
  const listEl = document.getElementById(config.listId);
  const searchInput = document.getElementById(config.searchId);
  const selectAllInput = document.getElementById(config.selectAllId);
  const options = (typeof config.optionsProvider === 'function' ? config.optionsProvider() : []) || [];

  if (!trigger || !dropdown || !labelEl || !listEl) {
    return;
  }

  const selectedSet = new Set(state[config.stateKey] || []);
  if (config.selectAllByDefault && !selectedSet.size && options.length) {
    options.forEach(option => selectedSet.add(option.id));
    state[config.stateKey] = Array.from(selectedSet);
  }

  function updateTriggerHighlight() {
    if (!trigger) return;
    const total = options.length;
    if (!total) {
      toggleFilterHighlight(trigger, false);
      return;
    }
    let isActive = selectedSet.size < total;
    if (!config.requireSelection) {
      isActive = selectedSet.size === 0 || selectedSet.size < total;
    }
    toggleFilterHighlight(trigger, isActive);
  }

  function updateLabel() {
    updateTriggerHighlight();
    const total = options.length;
    const selectedCount = selectedSet.size;
    if (!total) {
      labelEl.textContent = 'Sem opções';
      return;
    }
    if (!selectedCount && config.labels?.empty) {
      labelEl.textContent = config.labels.empty;
      return;
    }
    if (selectedCount === total && config.labels?.all) {
      labelEl.textContent = config.labels.all;
      return;
    }
    if (selectedCount === 1) {
      const option = options.find(opt => selectedSet.has(opt.id));
      labelEl.textContent = option?.label || '1 item';
      return;
    }
    if (config.labels?.summary) {
      labelEl.textContent = config.labels.summary(selectedCount);
      return;
    }
    labelEl.textContent = `${selectedCount} selecionados`;
  }

  function updateSelectAll() {
    if (!selectAllInput) return;
    const total = options.length;
    const selectedCount = selectedSet.size;
    selectAllInput.checked = total > 0 && selectedCount === total;
    selectAllInput.indeterminate = selectedCount > 0 && selectedCount < total;
  }

  function renderOptions(filterText = '') {
    const normalizedFilter = (filterText || '').trim().toLowerCase();
    listEl.innerHTML = '';

    if (!options.length) {
      const empty = document.createElement('div');
      empty.className = 'multiselect-option';
      empty.textContent = 'Nenhum item disponível';
      listEl.appendChild(empty);
      return;
    }

    options.forEach(option => {
      const searchable = `${option.label || ''} ${option.helper || ''}`.toLowerCase();
      if (normalizedFilter && !searchable.includes(normalizedFilter)) {
        return;
      }
      const label = document.createElement('label');
      label.className = 'multiselect-option';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = option.id;
      checkbox.checked = selectedSet.has(option.id);
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          selectedSet.add(option.id);
        } else {
          selectedSet.delete(option.id);
        }

        if (config.requireSelection && !selectedSet.size && options.length) {
          options.forEach(opt => selectedSet.add(opt.id));
        }

        state[config.stateKey] = Array.from(selectedSet);
        updateLabel();
        updateSelectAll();
        if (typeof config.onChange === 'function') {
          config.onChange();
        }
      });

      const span = document.createElement('span');
      span.innerHTML = option.helper
        ? `${option.label}<small>${option.helper}</small>`
        : option.label;

      label.appendChild(checkbox);
      label.appendChild(span);
      listEl.appendChild(label);
    });
  }

  renderOptions();
  updateLabel();
  updateSelectAll();

  if (selectAllInput) {
    selectAllInput.addEventListener('change', () => {
      if (selectAllInput.checked) {
        options.forEach(option => selectedSet.add(option.id));
      } else if (config.requireSelection) {
        options.forEach(option => selectedSet.add(option.id));
        selectAllInput.checked = true;
      } else {
        selectedSet.clear();
      }

      state[config.stateKey] = Array.from(selectedSet);
      renderOptions(searchInput?.value || '');
      updateLabel();
      updateSelectAll();
      if (typeof config.onChange === 'function') {
        config.onChange();
      }
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', event => {
      renderOptions(event.target.value || '');
    });
  }

  const closeHandler = () => {
    dropdown.classList.remove('is-open');
    trigger.classList.remove('active');
  };

  dropdownRegistry.push(closeHandler);

  trigger.addEventListener('click', event => {
    event.stopPropagation();
    dropdownRegistry.forEach(close => close());
    dropdown.classList.toggle('is-open');
    trigger.classList.toggle('active');
  });

  document.addEventListener('click', event => {
    if (!dropdown.contains(event.target) && !trigger.contains(event.target)) {
      closeHandler();
    }
  });
}

function getCollaboratorOptions() {
  return (state.collaborators || []).map(collaborator => ({
    id: collaborator.id,
    label: collaborator.name || 'Colaborador sem nome',
    helper: collaborator.company_name || ''
  }));
}

function getProjectOptions() {
  return (state.projectsDirectory || []).map(project => ({
    id: project.id,
    label: project.title || 'Projeto sem título',
    helper: project.company_name || ''
  }));
}

function getProcessOptions() {
  return (state.processesDirectory || []).map(process => ({
    id: process.id,
    label: process.title || 'Processo sem título',
    helper: process.company_name || ''
  }));
}

function getProcessOwnerOptions() {
  return (state.processOwnersDirectory || []).map(owner => ({
    id: owner.id,
    label: owner.name || 'Dono sem nome',
    helper: owner.company_name || ''
  }));
}

function updateProcessOwnersFromActivities() {
  // Extrair donos únicos das atividades de processos
  const ownersMap = new Map();

  (state.activities || []).forEach(activity => {
    if (activity.type === 'process') {
      const ownerName = (activity.owner_name || activity.process_owner_name || '').trim();
      if (ownerName && !ownersMap.has(ownerName)) {
        ownersMap.set(ownerName, {
          id: ownerName, // Usar o nome como ID para simplificar
          name: ownerName,
          company_name: activity.company_name || ''
        });
      }
    }
  });

  const newOwnersList = Array.from(ownersMap.values());
  const ownersChanged = JSON.stringify(state.processOwnersDirectory) !== JSON.stringify(newOwnersList);
  state.processOwnersDirectory = newOwnersList;

  // Se a lista mudou, atualizar o multiselect
  if (ownersChanged) {
    const ownerMultiselectConfig = FILTER_MULTISELECTS.find(m => m.key === 'processOwners');
    if (ownerMultiselectConfig) {
      // Verificar se há seleções válidas
      if (state.selectedProcessOwnerIds.length > 0) {
        const validOwnerIds = newOwnersList.map(o => o.id);
        state.selectedProcessOwnerIds = state.selectedProcessOwnerIds.filter(id => validOwnerIds.includes(id));
      }

      // Se não há mais seleções mas há opções e está configurado para selecionar todos por padrão
      if (state.selectedProcessOwnerIds.length === 0 && newOwnersList.length > 0 && ownerMultiselectConfig.selectAllByDefault) {
        state.selectedProcessOwnerIds = newOwnersList.map(o => o.id);
      }

      // Re-inicializar o multiselect
      setupMultiselect(ownerMultiselectConfig);
    }
  }
}

function handleCompanySelectionChange() {
  // Permitir que nenhuma empresa seja selecionada
  // (O backend/filtros irão lidar com isso adequadamente)
  saveFiltersToCache();
  loadActivitiesData();
  if (state.currentScope === 'team') {
    loadTeamOverview();
  } else if (state.currentScope === 'company') {
    loadCompanyOverview();
  }
}

// ========================================
// Company Selector (Seletor de Empresa)
// ========================================


function initializeDueDateFilters() {
  const startInput = document.getElementById('filterDueDateStart');
  const endInput = document.getElementById('filterDueDateEnd');
  const clearButton = document.getElementById('filterDueDateClear');
  const todayButton = document.getElementById('filterDueDateToday');
  const untilYesterdayButton = document.getElementById('filterDueDateUntilYesterday');
  const weekButton = document.getElementById('filterDueDateWeek');
  const monthButton = document.getElementById('filterDueDateMonth');

  if (!startInput || !endInput) {
    return;
  }

  const dueDateCard = startInput.closest('.filter-card');
  const updateDateHighlight = () => {
    toggleFilterHighlight(dueDateCard, Boolean(state.dueDateStart || state.dueDateEnd));
  };

  const applyLimits = () => {
    if (state.dueDateStart) {
      endInput.min = state.dueDateStart;
    } else {
      endInput.removeAttribute('min');
    }

    if (state.dueDateEnd) {
      startInput.max = state.dueDateEnd;
    } else {
      startInput.removeAttribute('max');
    }
  };

  const onChange = () => {
    state.dueDateStart = startInput.value || '';
    state.dueDateEnd = endInput.value || '';

    if (
      state.dueDateStart &&
      state.dueDateEnd &&
      state.dueDateStart > state.dueDateEnd
    ) {
      state.dueDateEnd = state.dueDateStart;
      endInput.value = state.dueDateEnd;
    }

    applyLimits();
    updateDateHighlight();
    saveFiltersToCache();
    loadActivitiesData();
  };

  startInput.addEventListener('change', onChange);
  endInput.addEventListener('change', onChange);

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      state.dueDateStart = '';
      state.dueDateEnd = '';
      startInput.value = '';
      endInput.value = '';
      applyLimits();
      updateDateHighlight();
      saveFiltersToCache();
      loadActivitiesData();
    });
  }

  const applyRange = (startDate, endDate) => {
    state.dueDateStart = formatDateInput(startDate);
    state.dueDateEnd = formatDateInput(endDate);
    startInput.value = state.dueDateStart;
    endInput.value = state.dueDateEnd;
    applyLimits();
    updateDateHighlight();
    saveFiltersToCache();
    loadActivitiesData();
  };

  if (todayButton) {
    todayButton.addEventListener('click', () => {
      const today = new Date();
      applyRange(today, today);
    });
  }

  if (untilYesterdayButton) {
    untilYesterdayButton.addEventListener('click', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      state.dueDateStart = '';
      state.dueDateEnd = formatDateInput(yesterday);
      startInput.value = '';
      endInput.value = state.dueDateEnd;
      applyLimits();
      updateDateHighlight();
      saveFiltersToCache();
      loadActivitiesData();
    });
  }

  if (weekButton) {
    weekButton.addEventListener('click', () => {
      const today = new Date();
      const day = today.getDay(); // 0 (Sun) .. 6 (Sat)
      const diffToMonday = (day === 0 ? -6 : 1) - day;
      const start = new Date(today);
      start.setDate(today.getDate() + diffToMonday);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      applyRange(start, end);
    });
  }

  if (monthButton) {
    monthButton.addEventListener('click', () => {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      applyRange(start, end);
    });
  }

  applyLimits();
  updateDateHighlight();
}

function formatDateInput(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return '';
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// ========================================
// Filtros
// ========================================

function initializeSearch() {
  const searchInput = document.getElementById('searchInput');
  if (!searchInput) return;

  const wrapper = searchInput.closest('.filter-input-wrapper');
  const syncHighlight = () => {
    const hasValue = Boolean((searchInput.value || '').trim());
    toggleFilterHighlight(wrapper, hasValue);
  };

  searchInput.addEventListener('input', function () {
    state.searchQuery = (this.value || '').toLowerCase();
    syncHighlight();
    saveFiltersToCache();
    renderActivities();
  });

  syncHighlight();
}

function initializeFilterCollapse() {
  const toggleButton = document.getElementById('filtersPanelToggle');
  const panelBody = document.getElementById('filtersPanelBody');
  if (!toggleButton || !panelBody) {
    return;
  }

  const textEl = toggleButton.querySelector('.toggle-text');

  const updateUI = () => {
    const collapsed = state.filtersCollapsed;
    panelBody.classList.toggle('is-collapsed', collapsed);
    toggleButton.classList.toggle('is-collapsed', collapsed);
    toggleButton.setAttribute('aria-expanded', (!collapsed).toString());
    if (textEl) {
      textEl.textContent = collapsed ? 'Exibir filtros' : 'Ocultar filtros';
    }
    updateSidebarCompactMode();
  };

  toggleButton.addEventListener('click', () => {
    state.filtersCollapsed = !state.filtersCollapsed;
    updateUI();
  });

  updateUI();
}

function initializeClearFiltersButton() {
  const clearButton = document.getElementById('filtersClearButton');
  if (!clearButton) return;

  clearButton.addEventListener('click', () => {
    if (confirm('Tem certeza que deseja limpar todos os filtros?')) {
      clearAllFilters();
    }
  });
}

function initializeActivitiesCollapse() {
  const toggleButton = document.getElementById('activitiesPanelToggle');
  const panelBody = document.getElementById('activitiesPanelBody');
  if (!toggleButton || !panelBody) {
    return;
  }

  const textEl = toggleButton.querySelector('.activities-toggle-text');

  const updateUI = () => {
    const collapsed = state.activitiesCollapsed;
    panelBody.classList.toggle('is-collapsed', collapsed);
    toggleButton.classList.toggle('is-collapsed', collapsed);
    toggleButton.setAttribute('aria-expanded', (!collapsed).toString());
    if (textEl) {
      textEl.textContent = collapsed ? 'Exibir atividades' : 'Ocultar atividades';
    }
    updateSidebarCompactMode();
  };

  toggleButton.addEventListener('click', () => {
    state.activitiesCollapsed = !state.activitiesCollapsed;
    updateUI();
  });

  updateUI();
}

function updateSidebarCompactMode() {
  const panel = document.querySelector('.time-tracker-panel');
  if (!panel) return;
  panel.classList.remove('time-tracker-panel--compact');
}

function initializeSorting() {
  const sortSelect = document.getElementById('sortSelect');
  if (!sortSelect) return;

  sortSelect.value = '';
  sortSelect.addEventListener('change', function () {
    const selectedValue = this.value || '';
    state.sortBy = selectedValue || 'deadline';
    if (!selectedValue) {
      this.value = '';
    }
    saveFiltersToCache();
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

    // Adicionar company_ids se houver seleção
    if (state.selectedCompanyIds && state.selectedCompanyIds.length > 0) {
      params.append('company_ids', state.selectedCompanyIds.join(','));
    }

    const collaboratorTotal = state.collaborators?.length || 0;
    if (
      state.selectedResponsibleIds.length &&
      state.selectedResponsibleIds.length < collaboratorTotal
    ) {
      params.append('responsible_ids', state.selectedResponsibleIds.join(','));
    }

    if (
      state.selectedExecutorIds.length &&
      state.selectedExecutorIds.length < collaboratorTotal
    ) {
      params.append('executor_ids', state.selectedExecutorIds.join(','));
    }

    const projectsTotal = state.projectsDirectory?.length || 0;
    const projectNoneSelected =
      projectsTotal > 0 && state.selectedProjectIds.length === 0;
    if (projectNoneSelected) {
      params.append('project_selection', SELECTION_MODE_NONE);
    } else if (
      state.selectedProjectIds.length &&
      state.selectedProjectIds.length < projectsTotal
    ) {
      params.append('project_ids', state.selectedProjectIds.join(','));
    }

    const processesTotal = state.processesDirectory?.length || 0;
    const processNoneSelected =
      processesTotal > 0 && state.selectedProcessIds.length === 0;
    if (processNoneSelected) {
      params.append('process_selection', SELECTION_MODE_NONE);
    } else if (
      state.selectedProcessIds.length &&
      state.selectedProcessIds.length < processesTotal
    ) {
      params.append('process_ids', state.selectedProcessIds.join(','));
    }

    if (state.dueDateStart) {
      params.append('due_date_start', state.dueDateStart);
    }

    if (state.dueDateEnd) {
      params.append('due_date_end', state.dueDateEnd);
    }

    const deliveryFilters = state.selectedDeliveryTags || [];
    if (deliveryFilters.length < DELIVERY_FILTER_VALUES.length) {
      params.append('delivery_tags', deliveryFilters.join(','));
    }

    const response = await fetch(`/my-work/api/activities?${params.toString()}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar atividades');
    }

    state.activities = Array.isArray(data.data) ? data.data : [];

    try {
      await hydrateProcessActivities();
    } catch (hydrationError) {
      console.warn('Erro ao enriquecer dados de processos no My Work:', hydrationError);
    }

    // Atualizar lista de donos de processos a partir das atividades carregadas
    updateProcessOwnersFromActivities();

    updateStats(data.stats);
    updateInsightCards();
    await updateIncidentSummary();
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
    updateInsightCards([]);
    renderActivities();
  } finally {
    setActivitiesLoading(false);
  }
}

// ========================================
// Process activity hydration
// ========================================

async function hydrateProcessActivities() {
  const processActivities = (state.activities || []).filter(
    activity => activity && activity.type === 'process' && activity.company_id
  );

  if (!processActivities.length) {
    return;
  }

  const companyIds = Array.from(
    new Set(processActivities.map(activity => activity.company_id).filter(Boolean))
  );

  if (!companyIds.length) {
    return;
  }

  await Promise.all(
    companyIds.map(companyId =>
      Promise.all([
        ensureCompanyProcessInstances(companyId),
        ensureCompanyProcesses(companyId)
      ])
    )
  );

  processActivities.forEach(activity => {
    const instanceDetails = getCachedProcessInstance(activity.company_id, activity.id);
    const processDetails = getCachedProcessDefinition(
      activity.company_id,
      activity.process_id || instanceDetails?.process_id
    );
    mergeProcessActivityDetails(activity, instanceDetails, processDetails);
  });
}

function mergeProcessActivityDetails(activity, instanceDetails, processDetails) {
  if (!activity || activity.type !== 'process') {
    return;
  }

  if (processDetails) {
    if (processDetails.id && !activity.process_id) {
      activity.process_id = processDetails.id;
    }
    activity.process_name = processDetails.name || activity.process_name;
    activity.process_code = processDetails.code || activity.process_code;
  }

  if (instanceDetails) {
    activity.instance_code = instanceDetails.instance_code || activity.instance_code;
    activity.title = instanceDetails.title || activity.title;
    activity.instance_title = instanceDetails.title || activity.instance_title || activity.title;
    activity.description = instanceDetails.description || activity.description;
    activity.deadline = instanceDetails.due_date || instanceDetails.deadline || activity.deadline;
    activity.deadline_label = formatDateLabel(activity.deadline) || activity.deadline_label;
    const estimatedHours = resolveHoursValue([
      instanceDetails.estimated_hours,
      instanceDetails.estimated_time,
      activity.estimated_hours
    ]);
    if (estimatedHours !== null) {
      activity.estimated_hours = estimatedHours;
    }
    const workedHours = resolveHoursValue([
      instanceDetails.actual_hours,
      instanceDetails.worked_hours,
      instanceDetails.hours_worked,
      activity.worked_hours
    ]);
    if (workedHours !== null) {
      activity.worked_hours = workedHours;
    }
    activity.owner_name =
      instanceDetails.process_owner_display ||
      instanceDetails.owner_display ||
      activity.owner_name ||
      findFirstCollaboratorByRole(instanceDetails.parsed_collaborators, 'owner') ||
      activity.owner_name;
    activity.responsible_name =
      instanceDetails.process_responsible_display ||
      instanceDetails.responsible_display ||
      activity.responsible_name ||
      findFirstCollaboratorByRole(instanceDetails.parsed_collaborators, 'responsible') ||
      activity.responsible_name;

    const executorNames = buildExecutorNames(instanceDetails);
    if (executorNames.length) {
      activity.executor_names = executorNames;
      activity.executor_name = executorNames.join(', ');
    }

    if (!activity.collaborators?.length && instanceDetails.parsed_collaborators?.length) {
      activity.collaborators = instanceDetails.parsed_collaborators;
    }

    if (instanceDetails.company_name && !activity.company_name) {
      activity.company_name = instanceDetails.company_name;
    }
  }

  if (!activity.owner_name && activity.collaborators?.length) {
    activity.owner_name =
      findFirstCollaboratorByRole(activity.collaborators, 'owner') || activity.owner_name;
  }

  if (!activity.responsible_name && activity.collaborators?.length) {
    activity.responsible_name =
      findFirstCollaboratorByRole(activity.collaborators, 'responsible') || activity.responsible_name;
  }
}

function formatDateLabel(value) {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleDateString('pt-BR');
}

function buildExecutorNames(record) {
  const names = [];
  if (Array.isArray(record?.executor_names) && record.executor_names.length) {
    names.push(...record.executor_names);
  }
  if (record?.parsed_collaborators?.length) {
    record.parsed_collaborators.forEach(collaborator => {
      const role = (collaborator?.role || 'executor').toLowerCase();
      if (role === 'executor' && collaborator?.name) {
        names.push(collaborator.name);
      }
    });
  }
  return dedupeNames(names);
}

function findFirstCollaboratorByRole(collaborators, role) {
  if (!collaborators || !role) {
    return '';
  }
  const normalizedRole = role.toLowerCase();
  const match = (collaborators || []).find(
    collaborator => (collaborator?.role || '').toLowerCase() === normalizedRole
  );
  return match?.name || '';
}

function getCachedProcessInstance(companyId, instanceId) {
  if (!companyId || instanceId == null) {
    return null;
  }
  return state.processInstanceCache?.[companyId]?.byId?.[instanceId] || null;
}

function getCachedProcessDefinition(companyId, processId) {
  if (!companyId || processId == null) {
    return null;
  }
  return state.processesByCompany?.[companyId]?.byId?.[processId] || null;
}

async function ensureCompanyProcessInstances(companyId) {
  if (!companyId) {
    return null;
  }

  state.processInstanceCache = state.processInstanceCache || {};
  if (state.processInstanceCache[companyId]?.byId) {
    return state.processInstanceCache[companyId];
  }

  if (processInstanceFetchPromises[companyId]) {
    return processInstanceFetchPromises[companyId];
  }

  const fetchPromise = (async () => {
    try {
      const response = await fetch(`/api/companies/${companyId}/process-instances`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || (payload && payload.success === false)) {
        throw new Error(payload.error || 'Erro ao carregar instâncias');
      }
      const instances = Array.isArray(payload)
        ? payload
        : (payload.instances || payload.data || []);
      const normalized = instances
        .map(instance => normalizeProcessInstanceRecord(instance))
        .filter(Boolean);
      const byId = normalized.reduce((acc, instance) => {
        if (instance && instance.id != null) {
          acc[instance.id] = instance;
        }
        return acc;
      }, {});
      state.processInstanceCache[companyId] = {
        loadedAt: Date.now(),
        list: normalized,
        byId
      };
      return state.processInstanceCache[companyId];
    } catch (error) {
      console.error(`Erro ao carregar instâncias de processos da empresa ${companyId}:`, error);
      state.processInstanceCache[companyId] = {
        loadedAt: Date.now(),
        list: [],
        byId: {}
      };
      return state.processInstanceCache[companyId];
    } finally {
      delete processInstanceFetchPromises[companyId];
    }
  })();

  processInstanceFetchPromises[companyId] = fetchPromise;
  return fetchPromise;
}

async function ensureCompanyProcesses(companyId) {
  if (!companyId) {
    return null;
  }

  state.processesByCompany = state.processesByCompany || {};
  if (state.processesByCompany[companyId]?.byId) {
    return state.processesByCompany[companyId];
  }

  if (processListFetchPromises[companyId]) {
    return processListFetchPromises[companyId];
  }

  const fetchPromise = (async () => {
    try {
      const response = await fetch(`/api/companies/${companyId}/processes`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || 'Erro ao carregar processos');
      }
      const list = Array.isArray(payload.data) ? payload.data : payload.processes || [];
      const byId = (list || []).reduce((acc, process) => {
        if (process && process.id != null) {
          acc[process.id] = process;
        }
        return acc;
      }, {});
      state.processesByCompany[companyId] = {
        loadedAt: Date.now(),
        list: list || [],
        byId
      };
      return state.processesByCompany[companyId];
    } catch (error) {
      console.error(`Erro ao carregar processos da empresa ${companyId}:`, error);
      state.processesByCompany[companyId] = {
        loadedAt: Date.now(),
        list: [],
        byId: {}
      };
      return state.processesByCompany[companyId];
    } finally {
      delete processListFetchPromises[companyId];
    }
  })();

  processListFetchPromises[companyId] = fetchPromise;
  return fetchPromise;
}

function normalizeProcessInstanceRecord(instance) {
  if (!instance) {
    return null;
  }
  const normalized = { ...instance };
  normalized.parsed_collaborators = parseInstanceCollaborators(
    instance.normalized_collaborators || instance.assigned_collaborators
  );
  normalized.executor_names = buildExecutorNames(normalized);
  normalized.process_owner_display =
    instance.process_owner_display ||
    instance.owner_display ||
    findFirstCollaboratorByRole(normalized.parsed_collaborators, 'owner');
  normalized.process_responsible_display =
    instance.process_responsible_display ||
    instance.responsible_display ||
    findFirstCollaboratorByRole(normalized.parsed_collaborators, 'responsible');
  return normalized;
}

function parseInstanceCollaborators(rawValue) {
  if (!rawValue) {
    return [];
  }
  if (Array.isArray(rawValue)) {
    return rawValue.filter(Boolean);
  }
  if (typeof rawValue === 'string') {
    try {
      const parsed = JSON.parse(rawValue);
      return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
    } catch (_err) {
      return [];
    }
  }
  return [];
}

function dedupeNames(names) {
  const seen = new Set();
  const ordered = [];
  (names || []).forEach(name => {
    const normalized = (name || '').trim();
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    ordered.push(normalized);
  });
  return ordered;
}

async function updateIncidentSummary() {
  try {
    const params = new URLSearchParams();
    if (state.selectedCompanyIds?.length) {
      params.append('company_ids', state.selectedCompanyIds.join(','));
    }
    const response = await fetch(`/my-work/api/occurrences/summary?${params.toString()}`);
    const payload = await response.json();
    if (!payload.success) {
      throw new Error(payload.error || 'Erro ao carregar ocorrências');
    }
    const { positive = { count: 0, score: 0 }, negative = { count: 0, score: 0 } } = payload.data || {};
    const totalScore = (positive.score || 0) + (negative.score || 0);
    setElementText('incidentPositiveValue', formatIncidentScore(positive.score) + ` (${positive.count || 0})`);
    setElementText('incidentNegativeValue', formatIncidentScore(negative.score) + ` (${negative.count || 0})`);
    setElementText('incidentResultValue', formatIncidentScore(totalScore));
    const summary = buildIncidentSummary(positive, negative);
    setElementText('incidentSummary', summary);
  } catch (error) {
    console.error('Erro ao atualizar ocorrências:', error);
    setElementText('incidentSummary', 'Não foi possível carregar os dados de ocorrências.');
  }
}

function formatIncidentScore(score) {
  if (score == null) {
    return '0 pts';
  }
  const value = Number(score);
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value} pts`;
}

function buildIncidentSummary(positive, negative) {
  const posCount = positive.count || 0;
  const negCount = negative.count || 0;
  if (!posCount && !negCount) {
    return 'Sem ocorrências registradas';
  }
  const parts = [];
  if (posCount) {
    parts.push(`${posCount} positivas`);
  }
  if (negCount) {
    parts.push(`${negCount} negativas`);
  }
  return `Impacto recente: ${parts.join(' · ')}`;
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
  updateInsightCards(filteredActivities);
  updateTimeTracking(calculateTimeFromActivities(filteredActivities));

  activitiesList.querySelectorAll('.activity-item').forEach(item => item.remove());

  if (!filteredActivities.length) {
    activitiesList.style.display = 'none';
    emptyState.style.display = 'flex';
    return;
  }

  activitiesList.style.display = 'flex';
  emptyState.style.display = 'none';

  const fragment = document.createDocumentFragment();
  filteredActivities.forEach(activity => {
    fragment.appendChild(createActivityElement(activity));
  });

  activitiesList.appendChild(fragment);
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

  const totalCompanies = state.companies?.length || 0;
  const collaboratorTotal = state.collaborators?.length || 0;
  const projectsTotal = state.projectsDirectory?.length || 0;
  const processesTotal = state.processesDirectory?.length || 0;
  const projectNoneSelected =
    projectsTotal > 0 && state.selectedProjectIds.length === 0;
  const processNoneSelected =
    processesTotal > 0 && state.selectedProcessIds.length === 0;
  const deliveryFilters = state.selectedDeliveryTags || [];
  if (!deliveryFilters.length) {
    return [];
  }
  const restrictDelivery = deliveryFilters.length < DELIVERY_FILTER_VALUES.length;

  if (restrictDelivery) {
    activities = activities.filter(activity =>
      deliveryFilters.includes(getActivityStatusCategory(activity))
    );
  }

  if (
    state.selectedCompanyIds.length &&
    totalCompanies &&
    state.selectedCompanyIds.length < totalCompanies
  ) {
    activities = activities.filter(activity =>
      state.selectedCompanyIds.includes(activity.company_id)
    );
  }

  if (
    state.selectedResponsibleIds.length &&
    state.selectedResponsibleIds.length < collaboratorTotal
  ) {
    activities = activities.filter(activity =>
      activityMatchesPeopleFilter(activity, state.selectedResponsibleIds, 'responsible')
    );
  }

  if (
    state.selectedExecutorIds.length &&
    state.selectedExecutorIds.length < collaboratorTotal
  ) {
    activities = activities.filter(activity =>
      activityMatchesPeopleFilter(activity, state.selectedExecutorIds, 'executor')
    );
  }

  if (projectNoneSelected) {
    activities = activities.filter(activity => activity.type !== 'project');
  } else if (
    state.selectedProjectIds.length &&
    state.selectedProjectIds.length < projectsTotal
  ) {
    activities = activities.filter(activity => {
      if (activity.type !== 'project') {
        return true;
      }
      const projectId = Number(activity.project_id ?? activity.id);
      if (!projectId) {
        return false;
      }
      return state.selectedProjectIds.includes(projectId);
    });
  }

  if (processNoneSelected) {
    activities = activities.filter(activity => activity.type !== 'process');
  } else if (
    state.selectedProcessIds.length &&
    state.selectedProcessIds.length < processesTotal
  ) {
    activities = activities.filter(activity =>
      activity.type !== 'process' || state.selectedProcessIds.includes(activity.id)
    );
  }

  // Filtro por donos de processos
  const processOwnersTotal = state.processOwnersDirectory?.length || 0;
  if (processOwnersTotal > 0) {
    if (state.selectedProcessOwnerIds.length === 0) {
      // Se nenhum dono está selecionado mas há donos disponíveis, excluir todos os processos
      activities = activities.filter(activity => activity.type !== 'process');
    } else if (state.selectedProcessOwnerIds.length < processOwnersTotal) {
      // Se alguns donos estão selecionados, mostrar apenas processos desses donos
      activities = activities.filter(activity => {
        if (activity.type !== 'process') {
          return true; // Não filtrar atividades de projeto por dono de processo
        }
        const ownerName = (activity.owner_name || activity.process_owner_name || '').trim();
        if (!ownerName) {
          return false; // Se não tem dono definido, excluir quando filtro está ativo
        }
        return state.selectedProcessOwnerIds.includes(ownerName);
      });
    }
    // Se todos os donos estão selecionados, não filtrar (mostrar todos os processos)
  }

  if (state.dueDateStart || state.dueDateEnd) {
    const startDate = state.dueDateStart ? new Date(state.dueDateStart) : null;
    const endDate = state.dueDateEnd ? new Date(state.dueDateEnd) : null;

    activities = activities.filter(activity => {
      if (!activity.deadline) {
        return false;
      }
      const deadlineDate = new Date(activity.deadline);
      if (startDate && deadlineDate < startDate) {
        return false;
      }
      if (endDate && deadlineDate > endDate) {
        return false;
      }
      return true;
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
      case 'company':
        return compareStrings(a.company_name || '', b.company_name || '');
      case 'responsible':
        return compareStrings(
          getActivityPersonName(a, 'responsible'),
          getActivityPersonName(b, 'responsible')
        );
      case 'executor':
        return compareStrings(
          getActivityPersonName(a, 'executor'),
          getActivityPersonName(b, 'executor')
        );
      case 'project':
        return sortByTypeAndTitle(a, b, 'project');
      case 'process':
        return sortByTypeAndTitle(a, b, 'process');
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
  wrapper.dataset.companyId = activity.company_id || '';
  wrapper.dataset.projectId = activity.project_id || '';
  wrapper.dataset.instanceId = activity.instance_id || activity.id;

  const statusIndicatorClass = getStatusIndicatorClass(activity);
  const assignmentLabel = activity.assignment?.label || '';
  const metaBadge = '';
  const typeLabel = activity.type === 'process' ? 'PROCESSO' : 'PROJETO';
  const priorityLabel = getPriorityLabel(activity.priority);
  const deadlineInfo = formatDeadline(activity);
  const secondaryInfo = formatSecondaryInfo(activity);
  const progressBar = renderProgressBar(activity);
  const isProcess = activity.type === 'process';
  const actionButtons = isProcess
    ? `
          <button class="action-btn action-btn--add-hours" title="Adicionar horas e ver informações" data-action="open-info">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            + Horas / Info
          </button>
          <button class="action-btn action-btn--complete" title="Finalizar" data-action="complete">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Finalizar
          </button>
      `
    : `
          <button class="action-btn action-btn--edit" title="Editar atividade" data-action="edit">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5c-.393-.393-1.03-.393-1.424 0L6.5 12.086v3.914h3.914l8.576-8.576c.393-.393.393-1.03 0-1.424l-2.49-2.49z"></path>
            </svg>
            Editar
          </button>
          <button class="action-btn action-btn--complete" title="Finalizar" data-action="complete">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Finalizar
          </button>
      `;

  const activityCodeMarkup = formatActivityCode(activity);
  const hasActivityCode = Boolean((activityCodeMarkup || '').trim());

  // Formatação especial para processos
  let titleContent = '';
  let instanceContent = '';
  if (activity.type === 'process') {
    const processName = (activity.process_name || '').trim();
    let processCode = (activity.process_code || '').trim();
    const instanceCode = (activity.instance_code || '').trim();
    const instanceTitle = (activity.instance_title || activity.title || '').trim();

    if (!processCode && processName) {
      const processMatch = processName.match(/^([A-Z0-9.]+)\s*-\s*(.+)$/);
      if (processMatch) {
        processCode = processMatch[1].trim();
      } else if (/^[A-Z0-9.]+$/.test(processName)) {
        processCode = processName.trim();
      }
    }

    if (!processCode && instanceCode) {
      const codeMatch = instanceCode.match(/^([A-Z0-9.]+)\.\d+/);
      if (codeMatch) {
        processCode = codeMatch[1];
      }
    }

    const processDisplayName =
      processCode && processName.startsWith(processCode)
        ? processName.slice(processCode.length).replace(/^\s*[-–]\s*/, '').trim()
        : processName || activity.process_display_name || 'Processo sem nome';

    const needsSeparator = processCode && processDisplayName;
    const instanceDisplayName = instanceTitle || 'Instância sem nome';
    const instanceHasInfo = hasActivityCode || instanceTitle;

    titleContent = `
      <span class="activity-label">Processo:</span>
      ${processCode
        ? `<span class="activity-code">${processCode}</span>${needsSeparator ? '<span class="process-separator">-</span>' : ''}`
        : ''
      }
      <span class="process-name">${processDisplayName || ''}</span>
    `.trim();

    instanceContent = instanceHasInfo
      ? `
        <div class="activity-item__instance">
          <span class="activity-label">Instância:</span>
          <span class="instance-name">
            ${hasActivityCode ? activityCodeMarkup : ''}
            ${instanceDisplayName}
          </span>
        </div>
      `.trim()
      : '';
  } else {
    const projectCode = (activity.project_code || '').trim();
    const projectName =
      (activity.project_title || activity.plan_name || 'Projeto sem nome').trim();
    const activityTitle = activity.title || 'Atividade sem título';
    const needsSeparator = projectCode && projectName;

    titleContent = `
      <span class="activity-label">Projeto:</span>
      ${projectCode
        ? `<span class="activity-code">${projectCode}</span>${needsSeparator ? '<span class="process-separator">-</span>' : ''}`
        : ''
      }
      <span class="process-name">${projectName}</span>
    `.trim();

    instanceContent = `
      <div class="activity-item__instance">
        <span class="activity-label">Atividade:</span>
        <span class="instance-name">
          ${hasActivityCode ? activityCodeMarkup : ''}
          ${activityTitle}
        </span>
      </div>
    `.trim();
  }

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
      <h3 class="activity-item__title">
        ${titleContent}
      </h3>
      ${instanceContent}
      ${activity.type !== 'process' && activity.description ? `<p class="activity-item__description">${activity.description}</p>` : ''}
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
          ${actionButtons}
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
  try {
    return new Date(activity.deadline).toLocaleDateString('pt-BR');
  } catch (e) {
    return 'Sem prazo definido';
  }
}

function formatSecondaryInfo(activity) {
  const infoItems = [];

  // Sempre mostrar a empresa primeiro (importante quando ha multiplas empresas)
  if (activity.company_name) {
    infoItems.push(`
      <span class="info-item info-item--company">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
        ${activity.company_name}
      </span>
    `);
  }

  if (activity.type === 'process') {
    const ownerName = activity.owner_name || 'Sem dono definido';
    infoItems.push(`
      <span class="info-item info-item--owner">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M2 17l4-10 4 6 4-6 4 10z"></path>
          <circle cx="12" cy="19" r="2"></circle>
        </svg>
        Dono: ${ownerName}
      </span>
    `);

    const responsibleName = activity.responsible_name || 'Sem responsável definido';
    infoItems.push(`
      <span class="info-item info-item--responsible">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        Responsável: ${responsibleName}
      </span>
    `);

    const executorNames = getProcessExecutorNames(activity) || 'Sem executores definidos';
    infoItems.push(`
      <span class="info-item info-item--executor">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        Executores: ${executorNames}
      </span>
    `);
    const processHoursLabel = buildProcessHoursLabel(activity);
    if (processHoursLabel) {
      infoItems.push(`
        <span class="info-item info-item--time">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          ${processHoursLabel}
        </span>
      `);
    }
  } else {
    const responsibleName = activity.responsible_name || 'Sem responsável definido';
    infoItems.push(`
      <span class="info-item info-item--responsible">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        Responsável: ${responsibleName}
      </span>
    `);

    const executorName = activity.executor_name || 'Sem executor definido';
    infoItems.push(`
      <span class="info-item info-item--executor">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        Executor: ${executorName}
      </span>
    `);

    if (activity.plan_name) {
      infoItems.push(`
        <span class="info-item info-item--project">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
          ${activity.plan_name}
        </span>
      `);
    }
  }

  if (activity.type !== 'process' && activity.estimated_hours) {
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
  if (!activity || activity.type === 'process' || !activity.progress_percent) return '';
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

function getProcessExecutorNames(activity) {
  if (!activity || activity.type !== 'process') return '';
  if (Array.isArray(activity.executor_names) && activity.executor_names.length) {
    return activity.executor_names.join(', ');
  }
  if (activity.executor_name) {
    return activity.executor_name;
  }
  const collabNames = (activity.collaborators || [])
    .map(collab => collab?.name)
    .filter(Boolean);

  if (collabNames.length) {
    return collabNames.join(', ');
  }

  return '';
}

function buildProcessHoursLabel(activity) {
  if (!activity || activity.type !== 'process') {
    return '';
  }
  const plannedHours = resolveHoursValue([
    activity.estimated_hours,
    activity.estimated_time
  ]);
  const actualHours = resolveHoursValue([
    activity.worked_hours,
    activity.actual_hours
  ]);
  const segments = [];
  if (plannedHours !== null) {
    segments.push(`Prev.: ${formatHours(plannedHours)}`);
  }
  if (actualHours !== null) {
    segments.push(`Real.: ${formatHours(actualHours)}`);
  }
  if (!segments.length) {
    return '';
  }
  return `Horas: ${segments.join(' | ')}`;
}

function activityMatchesPeopleFilter(activity, ids, role) {
  if (!ids || !ids.length) return true;
  if (activity.type === 'project') {
    if (role === 'responsible') {
      return ids.includes(activity.responsible_id);
    }
    if (role === 'executor') {
      return ids.includes(activity.executor_id);
    }
    return true;
  }

  if (activity.type === 'process' && role === 'executor') {
    const collaborators = (activity.collaborators || []).map(collab => collab.id).filter(Boolean);
    return collaborators.some(collaboratorId => ids.includes(collaboratorId));
  }

  return true;
}

function getActivityPersonName(activity, role) {
  if (activity.type === 'project') {
    if (role === 'responsible') {
      return (activity.responsible_name || '').toLowerCase();
    }
    if (role === 'executor') {
      return (activity.executor_name || '').toLowerCase();
    }
  }

  if (activity.type === 'process' && role === 'executor') {
    const collaborator = (activity.collaborators || [])[0];
    return (collaborator?.name || '').toLowerCase();
  }

  return '';
}

function compareStrings(a, b) {
  return (a || '').localeCompare(b || '', 'pt-BR', { sensitivity: 'base' });
}

function sortByTypeAndTitle(a, b, prioritizedType) {
  const aPriority = a.type === prioritizedType ? 0 : 1;
  const bPriority = b.type === prioritizedType ? 0 : 1;
  if (aPriority !== bPriority) {
    return aPriority - bPriority;
  }
  return compareStrings(a.title || '', b.title || '');
}

function formatActivityCode(activity) {
  const code = (activity.activity_code || activity.instance_code || activity.process_code || '').trim();
  if (!code) return '';
  return `<span class="activity-code">${code}</span> `;
}

async function loadTeamOverview() {
  // Para team overview, usar primeira empresa se múltiplas selecionadas
  const companyId = state.selectedCompanyIds && state.selectedCompanyIds.length > 0
    ? state.selectedCompanyIds[0]
    : null;

  const cacheKey = `team_${companyId || 'all'}`;
  if (state.teamData && state.teamData._cacheKey === cacheKey) {
    renderTeamOverview(state.teamData);
    return;
  }

  const loader = document.getElementById('teamOverviewLoader');
  const body = document.getElementById('teamOverviewBody');
  if (!loader || !body) return;

  loader.style.display = 'flex';
  body.style.display = 'none';

  try {
    const params = new URLSearchParams();
    if (companyId) {
      params.append('company_id', companyId);
    }

    const url = `/my-work/api/team-overview${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar visão da equipe');
    }

    state.teamData = data.data || {};
    state.teamData._cacheKey = cacheKey;
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
  // Para company overview, usar primeira empresa se múltiplas selecionadas
  const companyId = state.selectedCompanyIds && state.selectedCompanyIds.length > 0
    ? state.selectedCompanyIds[0]
    : null;

  const cacheKey = `company_${companyId || 'all'}`;
  if (state.companyData && state.companyData._cacheKey === cacheKey) {
    renderCompanyOverview(state.companyData);
    return;
  }

  const loader = document.getElementById('companyOverviewLoader');
  const body = document.getElementById('companyOverviewBody');
  if (!loader || !body) return;

  loader.style.display = 'flex';
  body.style.display = 'none';

  try {
    const params = new URLSearchParams();
    if (companyId) {
      params.append('company_id', companyId);
    }

    const url = `/my-work/api/company-overview${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Erro ao carregar visão da empresa');
    }

    state.companyData = data.data || {};
    state.companyData._cacheKey = cacheKey;
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
  const statOverdue = document.getElementById('stat-overdue');

  // Card "Abertas" deve mostrar todas as atividades não concluídas (pending + in_progress)
  const openActivities = (stats.pending || 0) + (stats.in_progress || 0);
  if (statPending) animateValue(statPending, 0, openActivities, 1000);
  if (statOverdue) animateValue(statOverdue, 0, stats.overdue, 1000);
}

function updateInsightCards(filteredActivities) {
  const activities = filteredActivities || getFilteredActivities();
  const total = activities.length;
  const completedActivities = activities.filter(activity => isStatus(activity, 'completed'));
  const completedCount = completedActivities.length;
  const completionRate = total ? Math.round((completedCount / total) * 100) : 0;

  updatePerformanceCard(completedCount, total);
  updateWeeklyProductivityCard(activities);
  updateAverageCompletionCard(completedActivities);
  updateCompletionRateCard(completionRate, completedCount, total);
}

function updatePerformanceScore(performance) {
  if (!performance) return;

  const earned = Number(performance.score) || 0;
  const maxScore =
    Number(performance.max_score ?? performance.total ?? performance.capacity ?? 100) || 0;
  updatePerformanceCard(earned, maxScore);
}

function updatePerformanceCard(completedPoints, totalPoints) {
  const scoreCircle = document.querySelector('.score-circle');
  const pointsValueEl = document.getElementById('performancePointsValue');
  const pointsMaxEl = document.getElementById('performancePointsMax');
  const percentEl = document.getElementById('performancePointsPercent');
  const statusEl = document.getElementById('performanceStatusText');

  if (!scoreCircle || !pointsValueEl || !pointsMaxEl || !percentEl || !statusEl) {
    return;
  }

  const safeTotal = Math.max(0, Number(totalPoints) || 0);
  const safeCompleted = Math.max(0, Number(completedPoints) || 0);
  const percent = safeTotal ? (safeCompleted / safeTotal) * 100 : 0;
  const clampedPercent = Math.min(Math.max(percent, 0), 100);

  const currentPoints = Number(pointsValueEl.textContent) || 0;
  animateValue(pointsValueEl, currentPoints, safeCompleted, 800);

  pointsMaxEl.textContent = `de ${safeTotal} pts`;
  const hasDecimal = Number.isFinite(clampedPercent) && !Number.isInteger(clampedPercent);
  const percentFormatted = clampedPercent.toLocaleString('pt-BR', {
    minimumFractionDigits: hasDecimal ? 1 : 0,
    maximumFractionDigits: 1
  });
  percentEl.textContent = `(${percentFormatted}%)`;

  scoreCircle.style.setProperty('--score', clampedPercent);

  const statusLevels = [
    { threshold: 80, text: 'Excelente desempenho!', className: 'performance-status--good' },
    { threshold: 50, text: 'Bom desempenho', className: 'performance-status--warning' },
    { threshold: 0, text: 'Precisa de atenção', className: 'performance-status--danger' }
  ];
  const selectedLevel =
    statusLevels.find(level => clampedPercent >= level.threshold) ||
    statusLevels[statusLevels.length - 1];

  statusEl.textContent = safeTotal ? selectedLevel.text : 'Sem dados para o período';
  statusEl.classList.remove('performance-status--good', 'performance-status--warning', 'performance-status--danger');
  statusEl.classList.add(selectedLevel.className);
}

function updateWeeklyProductivityCard(activities) {
  const bars = document.querySelectorAll('.mini-bar-chart .bar');
  const summaryEl = document.getElementById('weeklySummaryText');
  const badgeEl = document.getElementById('weeklyTrendBadge');

  if (!bars.length || !summaryEl) {
    return;
  }

  const today = new Date();
  const weekStart = startOfWeek(today);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);

  const counts = Array(7).fill(0);
  const previousWeekCounts = Array(7).fill(0);
  const previousWeekStart = new Date(weekStart);
  previousWeekStart.setDate(previousWeekStart.getDate() - 7);
  const previousWeekEnd = new Date(weekEnd);
  previousWeekEnd.setDate(previousWeekEnd.getDate() - 7);

  activities.forEach(activity => {
    const deadline = parseISODate(activity.deadline);
    if (!deadline) return;

    const dayIndex = deadline.getDay();
    if (deadline >= weekStart && deadline <= weekEnd) {
      counts[dayIndex] += 1;
    } else if (deadline >= previousWeekStart && deadline <= previousWeekEnd) {
      previousWeekCounts[dayIndex] += 1;
    }
  });

  const maxCount = Math.max(...counts, 1);
  bars.forEach(bar => {
    const dayIndex = Number(bar.dataset.dayIndex);
    const value = counts[dayIndex] || 0;
    const height = value ? Math.max((value / maxCount) * 100, 15) : 8;
    bar.style.height = `${height}%`;
    bar.title = `${value} atividades`;
  });

  const totalWeek = counts.reduce((sum, val) => sum + val, 0);
  summaryEl.textContent = totalWeek
    ? `${totalWeek} atividades com prazo nesta semana`
    : 'Nenhuma atividade com prazo nesta semana';

  if (badgeEl) {
    const previousTotal = previousWeekCounts.reduce((sum, val) => sum + val, 0);
    let trendText = '0%';
    let trendClass = 'insight-card__badge--neutral';
    if (previousTotal === 0 && totalWeek > 0) {
      trendText = '+100%';
      trendClass = 'insight-card__badge--positive';
    } else if (previousTotal > 0) {
      const delta = ((totalWeek - previousTotal) / previousTotal) * 100;
      const rounded = Math.round(delta);
      trendText = `${rounded > 0 ? '+' : ''}${rounded}%`;
      trendClass = rounded >= 0 ? 'insight-card__badge--positive' : 'insight-card__badge--negative';
    }
    badgeEl.textContent = trendText;
    badgeEl.classList.remove('insight-card__badge--positive', 'insight-card__badge--negative', 'insight-card__badge--neutral');
    badgeEl.classList.add(trendClass);
  }
}

function updateAverageCompletionCard(completedActivities) {
  const valueEl = document.getElementById('avgCompletionValue');
  const unitEl = document.getElementById('avgCompletionUnit');
  const summaryEl = document.getElementById('avgCompletionSummary');

  if (!valueEl || !unitEl || !summaryEl) {
    return;
  }

  const durations = completedActivities
    .map(activity => {
      const created = parseISODate(activity.created_at);
      const updated = parseISODate(activity.updated_at);
      if (!created || !updated) {
        return null;
      }
      const diffMs = updated.getTime() - created.getTime();
      return diffMs >= 0 ? diffMs / (1000 * 60 * 60 * 24) : null;
    })
    .filter(value => value !== null);

  if (!durations.length) {
    valueEl.textContent = '--';
    unitEl.textContent = 'dias';
    summaryEl.textContent = 'Sem atividades concluídas no filtro atual';
    return;
  }

  const averageDays = durations.reduce((sum, val) => sum + val, 0) / durations.length;
  if (averageDays >= 1) {
    valueEl.textContent = averageDays.toFixed(1);
    unitEl.textContent = 'dias';
  } else {
    valueEl.textContent = (averageDays * 24).toFixed(1);
    unitEl.textContent = 'horas';
  }

  summaryEl.textContent = `${durations.length} atividades concluídas consideradas`;
}

function updateCompletionRateCard(rate, completedCount, total) {
  const donutStroke = document.getElementById('completionDonutStroke');
  const donutValue = document.getElementById('completionDonutValue');
  const summaryEl = document.getElementById('completionRateSummary');
  const circleLength = 251.2;

  if (donutStroke) {
    donutStroke.style.strokeDashoffset = circleLength - (circleLength * rate) / 100;
  }
  if (donutValue) {
    donutValue.textContent = `${rate}%`;
  }
  if (summaryEl) {
    summaryEl.textContent = total
      ? `${completedCount} de ${total} atividades concluídas`
      : 'Nenhuma atividade no filtro';
  }
}

function isStatus(activity, targetStatus) {
  return ((activity.status || '').toLowerCase() === targetStatus.toLowerCase());
}

function parseISODate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfWeek(referenceDate) {
  const date = new Date(referenceDate);
  const day = date.getDay();
  const diff = (day === 0 ? -6 : 1) - day;
  date.setDate(date.getDate() + diff);
  date.setHours(0, 0, 0, 0);
  return date;
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

function updateTimeTracking(data) {
  if (!data) {
    updateDayView(null);
    return;
  }

  if (data.day) {
    updateDayView(data.day);
  } else {
    updateDayView(null);
  }
}

function updateDayView(dayData) {
  const data = dayData || createEmptySummary(DEFAULT_DAILY_CAPACITY);

  setElementText('dayCapacityValue', formatHours(data.capacity));
  setElementText('dayPlannedValue', formatHours(data.planned));
  setElementText('dayDoneValue', formatHours(data.done));

  const donePercent = calculatePercent(data.done, data.capacity);
  const remainingPlanned = Math.max(data.planned - data.done, 0);
  const plannedPercent = Math.min(
    calculatePercent(remainingPlanned, data.capacity),
    100 - donePercent
  );

  const dayProgressDone = document.getElementById('dayProgressDone');
  const dayProgressPlanned = document.getElementById('dayProgressPlanned');

  if (dayProgressDone) {
    dayProgressDone.style.width = `${donePercent}%`;
    dayProgressDone.title = `${formatHours(data.done)} / ${formatHours(data.capacity)}`;
  }

  if (dayProgressPlanned) {
    dayProgressPlanned.style.width = `${plannedPercent}%`;
    dayProgressPlanned.title = `${formatHours(remainingPlanned)} restante`;
  }

  setElementText('dayProgressPercent', `${Math.round(donePercent)}%`);

  setElementText('dayProjectsCount', formatCount(data.projects.count, 'atividade'));
  setElementText('dayProjectsPlanned', formatHours(data.projects.planned));
  setElementText('dayProjectsDone', formatHours(data.projects.done));
  setMiniBarPercent('dayProjectsBar', data.projects.done, data.projects.planned);

  setElementText('dayProcessesCount', formatCount(data.processes.count, 'instância', 'instâncias'));
  setElementText('dayProcessesPlanned', formatHours(data.processes.planned));
  setElementText('dayProcessesDone', formatHours(data.processes.done));
  setMiniBarPercent('dayProcessesBar', data.processes.done, data.processes.planned);

  const available = Math.max(data.capacity - data.planned, 0);
  setElementText('dayAvailableValue', formatHours(available));

  const alert = document.getElementById('overloadAlert');
  if (alert) {
    alert.style.display = data.planned > data.capacity ? 'block' : 'none';
  }
}

function calculateTimeFromActivities(activities) {
  const today = startOfDay(new Date());
  const daySummary = createEmptySummary(DEFAULT_DAILY_CAPACITY);

  (activities || []).forEach(activity => {
    const estimated = safeNumber(activity.estimated_hours || activity.estimated_time);
    const worked = safeNumber(activity.worked_hours || activity.actual_hours);
    const type = normalizeActivityType(activity);
    const dueDate = parseActivityDate(activity);

    const includeInDay = dueDate ? isSameDay(dueDate, today) : true;

    if (includeInDay) {
      accumulateSummary(daySummary, type, estimated, worked);
    }
  });

  daySummary.available = Math.max(daySummary.capacity - daySummary.planned, 0);

  return {
    day: daySummary,
    week: null
  };
}

function createEmptySummary(capacity, withDays = false) {
  const summary = {
    capacity,
    planned: 0,
    done: 0,
    available: capacity,
    projects: { planned: 0, done: 0, count: 0 },
    processes: { planned: 0, done: 0, count: 0 }
  };

  if (withDays) {
    summary.days = WEEK_BAR_KEYS.reduce((acc, key) => {
      acc[key] = { planned: 0, done: 0 };
      return acc;
    }, {});
  }

  return summary;
}

function accumulateSummary(summary, type, estimated, worked) {
  summary.planned += estimated;
  summary.done += worked;

  const bucket = type === 'process' ? summary.processes : summary.projects;
  bucket.planned += estimated;
  bucket.done += worked;
  bucket.count += 1;
}

function normalizeActivityType(activity) {
  const rawType = (activity.type || activity.activity_type || '').toLowerCase();
  if (rawType === 'process' || rawType === 'project') {
    return rawType;
  }
  if (activity.process_id || activity.process_instance_id) {
    return 'process';
  }
  return 'project';
}

function parseActivityDate(activity) {
  const dateValue =
    activity.deadline_date ||
    activity.due_date ||
    activity.activity_deadline ||
    activity.next_run;

  if (!dateValue) {
    return null;
  }

  const parsed = new Date(dateValue);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function updateWeekChartBars() {
  // gráfico semanal removido
}

function setElementText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setMiniBarPercent(elementId, doneValue, plannedValue) {
  const element = typeof elementId === 'string' ? document.getElementById(elementId) : elementId;
  if (!element) return;
  if (!plannedValue) {
    element.style.width = '0%';
    return;
  }
  const percent = Math.min(calculatePercent(doneValue, plannedValue), 100);
  element.style.width = `${percent}%`;
}

function formatHours(value) {
  const num = safeNumber(value);
  if (num <= 0) {
    return '0h';
  }
  const hours = Math.floor(num);
  const minutes = Math.round((num - hours) * 60);
  const parts = [];
  if (hours) {
    parts.push(`${hours}h`);
  }
  if (minutes) {
    parts.push(`${minutes}min`);
  }
  return parts.join(' ') || '0h';
}

function formatCount(count, singular, pluralOverride) {
  const value = safeNumber(count);
  const plural = pluralOverride || `${singular}s`;
  if (value === 1) {
    return `1 ${singular}`;
  }
  return `${value} ${plural}`;
}

function safeNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function coerceHours(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function resolveHoursValue(values) {
  for (const value of values || []) {
    const coerced = coerceHours(value);
    if (coerced !== null) {
      return coerced;
    }
  }
  return null;
}

function calculatePercent(value, total) {
  const numerator = safeNumber(value);
  const denominator = safeNumber(total);
  if (!denominator) {
    return 0;
  }
  return Math.max(0, Math.min(100, (numerator / denominator) * 100));
}

function startOfDay(date) {
  const clone = new Date(date);
  clone.setHours(0, 0, 0, 0);
  return clone;
}

function getStartOfWeek(date) {
  const clone = startOfDay(date);
  const day = clone.getDay(); // 0 domingo
  const diff = day === 0 ? -6 : 1 - day;
  clone.setDate(clone.getDate() + diff);
  return clone;
}

function isSameDay(dateA, dateB) {
  return (
    dateA &&
    dateB &&
    dateA.getFullYear() === dateB.getFullYear() &&
    dateA.getMonth() === dateB.getMonth() &&
    dateA.getDate() === dateB.getDate()
  );
}

function getWeekDayKey(date) {
  const keys = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sab'];
  return keys[date.getDay()] || 'seg';
}

// ========================================
// Keyboard Shortcuts
// ========================================

document.addEventListener('keydown', function (e) {
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
  modal.addEventListener('click', function (e) {
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
document.getElementById('formAddHours')?.addEventListener('submit', async function (e) {
  e.preventDefault();

  const formData = new FormData(this);
  const hoursToAdd = parseFloat(formData.get('hours'));
  const description = formData.get('description');
  const date = formData.get('work_date'); // Changed from 'date' to 'work_date' to match form field name

  if (!currentActivity) {
    window.showMessage('❌ Dados da atividade incompletos', 'error');
    return;
  }

  console.log('Adding hours to activity:', currentActivity.id, 'Type:', currentActivity.type);

  try {
    // Para PROJETOS: usar nova API de colaboradores
    if (currentActivity.type === 'project' && currentActivity.company_id && currentActivity.project_id) {
      // Registrar horas via nova API de colaboradores
      const response = await fetch(
        `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities/${currentActivity.id}/collaborators`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            employee_id: null,  // TODO: pegar do current_user quando disponível
            role: 'executor',
            hours: hoursToAdd,
            notes: description || `Adicionado ${hoursToAdd}h em ${new Date(date).toLocaleDateString('pt-BR')}`
          })
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Erro ao registrar horas');
      }

      window.showMessage(`✅ ${hoursToAdd}h registradas com sucesso!`, 'success');
      closeModal('modalAddHours');
      loadActivitiesData();
      return; // IMPORTANTE: return aqui para não executar o código antigo
    }

    // Para PROCESSOS ou fallback: usar método antigo
    if (!currentActivity.company_id || !currentActivity.project_id) {
      window.showMessage('❌ Dados da atividade incompletos', 'error');
      return;
    }

    // Fetch current activity data
    const fetchResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities`
    );
    const fetchData = await fetchResponse.json();

    if (!fetchResponse.ok || !fetchData.success) {
      throw new Error('Erro ao buscar dados da atividade');
    }

    const activities = fetchData.activities || [];
    const activity = activities.find(a => a.id === currentActivity.id);

    if (!activity) {
      throw new Error('Atividade não encontrada');
    }

    // Add log entry (hours tracking will be implemented later with proper API)
    const logs = activity.logs || [];
    logs.push({
      timestamp: new Date().toISOString(),
      text: description || `Adicionado ${hoursToAdd}h em ${new Date(date).toLocaleDateString('pt-BR')}`,
      type: 'hours',
      hours: hoursToAdd,
      date: date
    });

    // Update activity - only updating logs, NOT touching amount or worked_hours
    const updateResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities/${currentActivity.id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          what: activity.what,
          who: activity.who,
          when: activity.when,
          how: activity.how,
          amount: activity.amount,  // Keep original budget value
          score_weight: activity.score_weight || 1,
          observations: activity.observations,
          logs: logs
        })
      }
    );

    const updateData = await updateResponse.json();

    if (!updateResponse.ok || !updateData.success) {
      throw new Error(updateData.message || 'Erro ao atualizar atividade');
    }

    window.showMessage(`✅ ${hoursToAdd}h registradas com sucesso! (Registro em log apenas)`, 'info');
    closeModal('modalAddHours');
    loadActivitiesData();
  } catch (error) {
    console.error('Erro ao adicionar horas:', error);
    window.showMessage(`❌ ${error.message}`, 'error');
  }
});

// Form: Adicionar Comentário
document.getElementById('formAddComment')?.addEventListener('submit', async function (e) {
  e.preventDefault();

  const formData = new FormData(this);
  const comment = formData.get('comment');
  const commentType = formData.get('comment_type');

  if (!currentActivity || !currentActivity.company_id || !currentActivity.project_id) {
    window.showMessage('❌ Dados da atividade incompletos', 'error');
    return;
  }

  console.log('Adding comment to activity:', currentActivity.id);

  try {
    // Fetch current activity data
    const fetchResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities`
    );
    const fetchData = await fetchResponse.json();

    if (!fetchResponse.ok || !fetchData.success) {
      throw new Error('Erro ao buscar dados da atividade');
    }

    const activities = fetchData.activities || [];
    const activity = activities.find(a => a.id === currentActivity.id);

    if (!activity) {
      throw new Error('Atividade não encontrada');
    }

    // Add log entry
    const logs = activity.logs || [];
    logs.push({
      timestamp: new Date().toISOString(),
      text: comment,
      type: commentType || 'manual'
    });

    // Update activity
    const updateResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities/${currentActivity.id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          what: activity.what,
          who: activity.who,
          when: activity.when,
          how: activity.how,
          amount: activity.amount,
          score_weight: activity.score_weight || 1,
          observations: activity.observations,
          logs: logs
        })
      }
    );

    const updateData = await updateResponse.json();

    if (!updateResponse.ok || !updateData.success) {
      throw new Error(updateData.message || 'Erro ao atualizar atividade');
    }

    window.showMessage('✅ Comentário adicionado com sucesso!', 'success');
    closeModal('modalAddComment');
    loadActivitiesData();
  } catch (error) {
    console.error('Erro ao adicionar comentário:', error);
    window.showMessage(`❌ ${error.message}`, 'error');
  }
});

// Form: Finalizar Atividade
document.getElementById('formComplete')?.addEventListener('submit', async function (e) {
  e.preventDefault();

  const formData = new FormData(this);
  const completionComment = formData.get('completion_comment');
  const today = new Date().toISOString().split('T')[0];

  if (!currentActivity || !currentActivity.company_id || !currentActivity.project_id) {
    window.showMessage('❌ Dados da atividade incompletos', 'error');
    return;
  }

  console.log('Completing activity:', currentActivity.id);

  try {
    // Fetch current activity data to get logs
    const fetchResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities`
    );
    const fetchData = await fetchResponse.json();

    if (!fetchResponse.ok || !fetchData.success) {
      throw new Error('Erro ao buscar dados da atividade');
    }

    const activities = fetchData.activities || [];
    const activity = activities.find(a => a.id === currentActivity.id);

    if (!activity) {
      throw new Error('Atividade não encontrada');
    }

    // Add completion log
    const logs = activity.logs || [];
    logs.push({
      timestamp: new Date().toISOString(),
      text: completionComment || `Atividade concluída em ${new Date(today).toLocaleDateString('pt-BR')}`,
      type: 'completion',
      date: today
    });

    // Update activity stage to completed
    const updateResponse = await fetch(
      `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities/${currentActivity.id}/stage`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stage: 'completed',
          completion_date: today,
          logs: logs
        })
      }
    );

    const updateData = await updateResponse.json();

    if (!updateResponse.ok || !updateData.success) {
      throw new Error(updateData.message || 'Erro ao finalizar atividade');
    }

    window.showMessage('✅ Atividade finalizada com sucesso!', 'success');
    closeModal('modalComplete');

    // Remover atividade da lista
    setTimeout(() => {
      const activityElement = document.querySelector(`[data-activity-id="${currentActivity.id}"]`);
      if (activityElement) {
        activityElement.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => activityElement.remove(), 300);
      }
    }, 500);

    // Recarregar dados
    setTimeout(() => {
      loadActivitiesData();
    }, 1000);
  } catch (error) {
    console.error('Erro ao finalizar atividade:', error);
    window.showMessage(`❌ ${error.message}`, 'error');
  }
});

// Atualizar função de actions para usar os modals
function initializeActivityActions() {
  // Delegar eventos para ações
  document.addEventListener('click', function (e) {
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
    const companyId = activity.dataset.companyId ? parseInt(activity.dataset.companyId, 10) : null;
    const instanceId = activity.dataset.instanceId ? parseInt(activity.dataset.instanceId, 10) : activityId;

    // Extract project_id from dataset
    const projectId = activity.dataset.projectId ? parseInt(activity.dataset.projectId, 10) : null;

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
      description,
      company_id: companyId,
      project_id: projectId,
      instance_id: instanceId
    };

    // Identificar ação pelo data-action
    const action = btn.dataset.action;

    if (action === 'open-info') {
      if (!companyId || !instanceId) {
        window.showMessage?.('Não foi possível abrir as informações desta instância.', 'error');
        return;
      }
      const params = new URLSearchParams({ from: 'my-work' });
      window.location.href = `/grv/company/${companyId}/process/instances/${instanceId}/manage?${params.toString()}`;
      return;
    } else if (action === 'edit') {
      if (!companyId || !projectId || !activityId) {
        window.showMessage?.('Nao foi possivel abrir o editor desta atividade.', 'error');
        return;
      }
      const params = new URLSearchParams({ activity_id: activityId });
      params.append('from', 'my-work');
      window.location.href = `/grv/company/${companyId}/projects/${projectId}/manage?${params.toString()}`;
      return;
    } else if (action === 'add-hours') {
      openModal('modalAddHours', activityData);
    } else if (action === 'add-comment') {
      openModal('modalAddComment', activityData);
    } else if (action === 'complete') {
      openModal('modalComplete', activityData);
    }
  });
}

// Função para construir payload de filtros para o relatório
function buildReportFiltersPayload() {
  const filters = {};
  
  // Company IDs
  if (state.selectedCompanyIds && state.selectedCompanyIds.length > 0) {
    filters.company_ids = state.selectedCompanyIds.map(id => parseInt(id));
  }
  
  // Responsible IDs
  if (state.selectedResponsibleIds && state.selectedResponsibleIds.length > 0) {
    filters.responsible_ids = state.selectedResponsibleIds.map(id => parseInt(id));
  }
  
  // Executor IDs
  if (state.selectedExecutorIds && state.selectedExecutorIds.length > 0) {
    filters.executor_ids = state.selectedExecutorIds.map(id => parseInt(id));
  }
  
  // Project IDs
  if (state.selectedProjectIds && state.selectedProjectIds.length > 0) {
    filters.project_ids = state.selectedProjectIds.map(id => parseInt(id));
  }
  
  // Process IDs
  if (state.selectedProcessIds && state.selectedProcessIds.length > 0) {
    filters.process_ids = state.selectedProcessIds.map(id => parseInt(id));
  }
  
  // Process Owner IDs
  if (state.selectedProcessOwnerIds && state.selectedProcessOwnerIds.length > 0) {
    filters.process_owner_ids = state.selectedProcessOwnerIds.map(id => parseInt(id));
  }
  
  // Delivery Tags
  if (state.selectedDeliveryTags && state.selectedDeliveryTags.length > 0) {
    const allTags = DELIVERY_FILTER_VALUES;
    const hasAllTags = state.selectedDeliveryTags.length === allTags.length && 
                       allTags.every(tag => state.selectedDeliveryTags.includes(tag));
    if (!hasAllTags) {
      filters.delivery_tags = state.selectedDeliveryTags;
    }
  }
  
  // Due Date Range
  if (state.dueDateStart) {
    filters.due_date_start = state.dueDateStart;
  }
  if (state.dueDateEnd) {
    filters.due_date_end = state.dueDateEnd;
  }
  
  // Search
  if (state.searchQuery && state.searchQuery.trim()) {
    filters.search = state.searchQuery.trim();
  }
  
  return filters;
}

// Função para atualizar o link do relatório com os filtros atuais
function updateReportLink() {
  const reportLink = document.querySelector('.stat-card__link[href*="report"]');
  if (!reportLink) return;
  
  const baseUrl = reportLink.getAttribute('href').split('?')[0];
  const scope = state.currentScope || 'me';
  const filters = buildReportFiltersPayload();
  
  const params = new URLSearchParams();
  params.set('scope', scope);
  
  if (Object.keys(filters).length > 0) {
    params.set('filters', JSON.stringify(filters));
  }
  
  const newUrl = baseUrl + '?' + params.toString();
  reportLink.setAttribute('href', newUrl);
}

// Atualizar link do relatório quando os filtros mudarem
function initializeReportLink() {
  updateReportLink();
  
  // Observar mudanças nos campos de data diretamente
  const dueDateStartInput = document.getElementById('filterDueDateStart');
  const dueDateEndInput = document.getElementById('filterDueDateEnd');
  
  if (dueDateStartInput) {
    dueDateStartInput.addEventListener('change', () => {
      state.dueDateStart = dueDateStartInput.value || '';
      updateReportLink();
    });
  }
  
  if (dueDateEndInput) {
    dueDateEndInput.addEventListener('change', () => {
      state.dueDateEnd = dueDateEndInput.value || '';
      updateReportLink();
    });
  }
  
  // Observar mudanças no estado para atualizar o link
  let lastState = JSON.stringify({
    selectedCompanyIds: state.selectedCompanyIds,
    selectedResponsibleIds: state.selectedResponsibleIds,
    selectedExecutorIds: state.selectedExecutorIds,
    selectedProjectIds: state.selectedProjectIds,
    selectedProcessIds: state.selectedProcessIds,
    selectedProcessOwnerIds: state.selectedProcessOwnerIds,
    selectedDeliveryTags: state.selectedDeliveryTags,
    dueDateStart: state.dueDateStart,
    dueDateEnd: state.dueDateEnd,
    searchQuery: state.searchQuery,
    currentScope: state.currentScope
  });
  
  setInterval(() => {
    const currentState = JSON.stringify({
      selectedCompanyIds: state.selectedCompanyIds,
      selectedResponsibleIds: state.selectedResponsibleIds,
      selectedExecutorIds: state.selectedExecutorIds,
      selectedProjectIds: state.selectedProjectIds,
      selectedProcessIds: state.selectedProcessIds,
      selectedProcessOwnerIds: state.selectedProcessOwnerIds,
      selectedDeliveryTags: state.selectedDeliveryTags,
      dueDateStart: state.dueDateStart,
      dueDateEnd: state.dueDateEnd,
      searchQuery: state.searchQuery,
      currentScope: state.currentScope
    });
    
    if (currentState !== lastState) {
      lastState = currentState;
      updateReportLink();
    }
  }, 1000);
}

// Tornar funções globais para serem chamadas do HTML
window.openModal = openModal;
window.closeModal = closeModal;
window.updateReportLink = updateReportLink;

console.log('✅ My Work page initialized');
