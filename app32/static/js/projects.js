/**
 * Projects Module - Versus Corporate Style
 */

let allProjects = [];
let allPortfolios = [];
let allPlans = [];
let currentView = 'grid'; // Default view: 'grid' now refers to the List/Row view

// Read company_id injected by Jinja2 into the page
const PAGE_COMPANY_ID = document.querySelector('meta[name="company-id"]')?.content || '';

document.addEventListener('DOMContentLoaded', () => {
    initPage();
});

async function initPage() {
    try {
        // Load additional filter data
        await Promise.all([
            loadPortfolios(),
            loadPlans()
        ]);

        // Load projects
        await loadProjects();

        // Populate specific filters after loading projects
        populateResponsibleFilter();
    } catch (error) {
        console.error('Error initializing projects page:', error);
    }
}

async function loadPortfolios() {
    try {
        // Use the company_id from the page (injected by Jinja2)
        let companyId = PAGE_COMPANY_ID;

        if (!companyId) {
            // Fallback: fetch from /api/companies
            const response = await fetch('/api/companies');
            const companies = await response.json();
            const firstCompany = Array.isArray(companies) ? companies[0] : (companies.data ? companies.data[0] : null);
            if (firstCompany) companyId = firstCompany.id || firstCompany.company_id;
        }

        if (companyId) {
            const portResponse = await fetch(`/api/companies/${companyId}/portfolios`);
            const portData = await portResponse.json();
            allPortfolios = portData.portfolios || [];

            const optgroup = document.getElementById('optgroup-portfolios');
            if (optgroup) {
                allPortfolios.forEach(p => {
                    const option = document.createElement('option');
                    option.value = `portfolio-${p.id}`;
                    option.textContent = p.name || p.title || p.code;
                    optgroup.appendChild(option);
                });
            }
        }
    } catch (e) {
        console.error('Error loading portfolios:', e);
    }
}

async function loadPlans() {
    try {
        const plansUrl = PAGE_COMPANY_ID ? `/api/plans?company_id=${PAGE_COMPANY_ID}` : '/api/plans';
        const response = await fetch(plansUrl);
        if (!response.ok) {
            console.warn('Could not load plans:', response.status);
            allPlans = [];
            return;
        }
        const data = await response.json();
        allPlans = Array.isArray(data) ? data : (data.data || []);

        const optgroup = document.getElementById('optgroup-plans');
        if (optgroup) {
            allPlans.forEach(p => {
                const option = document.createElement('option');
                option.value = `plan-${p.id}`;
                option.textContent = p.name || p.title;
                optgroup.appendChild(option);
            });
        }
    } catch (e) {
        console.error('Error loading plans:', e);
        allPlans = [];
    }
}


function populateResponsibleFilter() {
    const list = document.getElementById('filter-responsible');
    if (!list) return;

    // Clear except first
    list.innerHTML = '<option value="">Todos os Responsáveis</option>';

    const owners = [...new Set(allProjects.map(p => p.owner).filter(Boolean))].sort();
    owners.forEach(owner => {
        const option = document.createElement('option');
        option.value = owner;
        option.textContent = owner;
        list.appendChild(option);
    });
}

async function loadProjects() {
    const loading = document.getElementById('loading-state');
    const empty = document.getElementById('empty-state');
    const listContainer = document.getElementById('projects-list-container');
    const kanban = document.getElementById('projects-kanban');

    if (loading) loading.style.display = 'block';
    if (listContainer) listContainer.style.display = 'none';
    if (kanban) kanban.style.display = 'none';
    if (empty) empty.style.display = 'none';

    try {
        // Pass company_id explicitly to avoid session dependency
        const url = PAGE_COMPANY_ID ? `/api/projects?company_id=${PAGE_COMPANY_ID}` : '/api/projects';
        const response = await fetch(url);
        const data = await response.json();
        allProjects = Array.isArray(data) ? data : (data.data || []);

        updateStats();
        applyFilters();
    } catch (error) {
        console.error('Error fetching projects:', error);
        loading.style.display = 'none';
        empty.style.display = 'flex';
    }
}

function updateStats() {
    const active = allProjects.filter(p => p.status === 'in_progress').length;
    const now = new Date();
    const delayed = allProjects.filter(p => {
        if (!p.deadline || p.status === 'completed') return false;
        return new Date(p.deadline) < now;
    }).length;

    const totalEl = document.getElementById('project-count-total');
    if (totalEl) totalEl.textContent = allProjects.length;

    const activeEl = document.getElementById('stats-active');
    if (activeEl) activeEl.textContent = active;

    const delayedEl = document.getElementById('stats-delayed');
    if (delayedEl) delayedEl.textContent = delayed;
}

function applyFilters() {
    const searchTerm = document.getElementById('filter-search')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('filter-status')?.value || '';
    const priorityFilter = document.getElementById('filter-priority')?.value || '';
    const responsibleFilter = document.getElementById('filter-responsible')?.value || '';
    const portfolioPlanValue = document.getElementById('filter-portfolio-plan')?.value || '';
    const showArchived = document.getElementById('filter-archived')?.checked || false;

    const filtered = allProjects.filter(project => {
        // 1. Archive filter logic
        const isArchived = project.status === 'archived';
        if (!showArchived && isArchived) return false;

        // 2. Search text
        const matchesSearch = (project.name || project.title || '').toLowerCase().includes(searchTerm) ||
            (project.owner || '').toLowerCase().includes(searchTerm) ||
            (project.notes || '').toLowerCase().includes(searchTerm) ||
            (project.code || '').toLowerCase().includes(searchTerm);

        // 3. Status
        const matchesStatus = statusFilter === "" || project.status === statusFilter;

        // 4. Responsible
        const matchesResponsible = responsibleFilter === "" || project.owner === responsibleFilter;

        // 5. Portfolio/Plan
        let matchesPortfolioPlan = true;
        if (portfolioPlanValue.startsWith('portfolio-')) {
            const pid = portfolioPlanValue.replace('portfolio-', '');
            matchesPortfolioPlan = project.portfolio_id == pid;
        } else if (portfolioPlanValue.startsWith('plan-')) {
            const plid = portfolioPlanValue.replace('plan-', '');
            matchesPortfolioPlan = project.plan_id == plid;
        }

        // 6. Priority (Assuming it might be added or we just check if it matches if exists)
        const matchesPriority = priorityFilter === "" || (project.priority && project.priority === priorityFilter);

        return matchesSearch && matchesStatus && matchesResponsible && matchesPortfolioPlan && matchesPriority;
    });

    const loading = document.getElementById('loading-state');
    const empty = document.getElementById('empty-state');
    const listContainer = document.getElementById('projects-list-container');

    if (loading) loading.style.display = 'none';

    if (filtered.length === 0) {
        if (listContainer) listContainer.style.display = 'none';
        if (empty) empty.style.display = 'block';
        return;
    }

    if (empty) empty.style.display = 'none';
    renderListView(filtered);
}

function renderListView(projects) {
    const list = document.getElementById('projects-list-container');
    const kanban = document.getElementById('projects-kanban');

    if (list) {
        list.style.display = 'flex';
        list.style.flexDirection = 'column';
        list.innerHTML = '';
    }
    if (kanban) kanban.style.display = 'none';

    projects.forEach(project => {
        const row = document.createElement('div');
        row.className = 'project-row fade-in';

        const statusConfig = getStatusConfig(project.status);
        const priorityConfig = getPriorityConfig(project.priority);
        const stats = project.task_stats || { total: 0, open: 0, delayed: 0 };
        const deadlineLabel = formatDate(project.deadline);
        const isProjectDelayed = isDelayed(project.deadline) && project.status !== 'completed';

        row.innerHTML = `
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <div style="width: 4px; height: 32px; background: ${priorityConfig.color}; border-radius: 2px;" title="Prioridade: ${priorityConfig.label}"></div>
                <div class="project-status-pills">
                    <span class="pill pill--${project.status || 'planned'}">${statusConfig.label}</span>
                </div>
            </div>
            <div class="project-info">
                <h3 class="project-title">
                    ${project.code ? `<span style="color: var(--text-tertiary); font-weight: 500; font-size: 0.9em; margin-right: 0.5rem;">${project.code}</span>` : ''} 
                    ${project.name || project.title}
                </h3>
                <div class="project-meta-pills">
                    <span class="project-subtitle" title="${project.owner || 'Sem responsável'}">
                        👤 ${project.owner || 'Responsável não definido'}
                    </span>
                    <span class="sep">•</span>
                    <span class="project-subtitle" style="color: ${isProjectDelayed ? 'var(--danger)' : 'var(--text-tertiary)'}; font-weight: ${isProjectDelayed ? '700' : '400'}">
                        📅 ${deadlineLabel} ${isProjectDelayed ? '(Atrasado)' : ''}
                    </span>
                </div>
            </div>
            
            <div class="project-progress-compact" style="min-width: 150px; border-left: 1px solid var(--border-light); padding-left: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 0.65rem; font-weight: 800; color: var(--text-tertiary); text-transform: uppercase;">Avanço</span>
                    <span style="font-size: 0.75rem; font-weight: 800; color: var(--primary);">${stats.progress || 0}%</span>
                </div>
                <div class="progress-track-mini">
                    <div class="progress-fill-mini" style="width: ${stats.progress || 0}%; background: ${statusConfig.barColor}"></div>
                </div>
            </div>

            <div class="project-stats-display" style="min-width: 140px; border-left: 1px solid var(--border-light); padding-left: 1.5rem;">
                <span style="font-size: 0.65rem; font-weight: 800; color: var(--text-tertiary); text-transform: uppercase;">Atividades</span>
                <div style="display: flex; gap: 16px; margin-top: 4px;">
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 700; color: var(--text-primary); line-height: 1;">${stats.total}</span>
                        <span style="font-size: 0.6rem; font-weight: 600; color: var(--text-tertiary); margin-top: 2px;">Total</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 700; color: var(--primary); line-height: 1;">${stats.completed || 0}</span>
                        <span style="font-size: 0.6rem; font-weight: 600; color: var(--text-tertiary); margin-top: 2px;">Feito</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 700; color: ${stats.delayed > 0 ? 'var(--danger)' : 'var(--text-primary)'}; line-height: 1;">${stats.delayed}</span>
                        <span style="font-size: 0.6rem; font-weight: 600; color: var(--text-tertiary); margin-top: 2px;">Atraso</span>
                    </div>
                </div>
            </div>

            <div class="project-actions">
                <button class="btn btn-icon" onclick="manageProject(${project.id})" title="Gerir Atividades (Kanban)">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="9" y1="3" x2="9" y2="21"></line>
                        <line x1="15" y1="3" x2="15" y2="21"></line>
                        <line x1="3" y1="9" x2="21" y2="9"></line>
                    </svg>
                </button>
                <button class="btn btn-icon" onclick="editProject(${project.id})" title="Editar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                </button>
                <button class="btn btn-icon text-danger" onclick="deleteProject(${project.id})" title="Excluir">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>
        `;
        list.appendChild(row);
    });
}



function getPriorityConfig(priority) {
    const configs = {
        'high': { label: 'Alta', color: 'var(--danger)' },
        'medium': { label: 'Média', color: 'var(--warning)' },
        'low': { label: 'Baixa', color: 'var(--success)' }
    };
    return configs[priority] || configs['medium'];
}

function getStatusConfig(status) {
    const configs = {
        'planned': { label: 'Planejado', bg: '#f1f5f9', color: '#64748b', barColor: '#cbd5e1' },
        'in_progress': { label: 'Em Andamento', bg: '#dbeafe', color: '#2563eb', barColor: '#3b82f6' },
        'on_hold': { label: 'Em Pausa', bg: '#fef3c7', color: '#d97706', barColor: '#fbbf24' },
        'completed': { label: 'Concluído', bg: '#dcfce7', color: '#15803d', barColor: '#22c55e' },
        'cancelled': { label: 'Cancelado', bg: '#fee2e2', color: '#dc2626', barColor: '#f87171' },
        'archived': { label: 'Arquivado', bg: '#f1f5f9', color: '#94a3b8', barColor: '#94a3b8' }
    };
    return configs[status] || configs['planned'];
}

function isDelayed(deadline) {
    if (!deadline) return false;
    return new Date(deadline) < new Date();
}

function formatDate(dateString) {
    if (!dateString) return 'Sem prazo';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function filterProjects() {
    applyFilters();
}

function clearFilters() {
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-priority').value = '';
    document.getElementById('filter-responsible').value = '';
    document.getElementById('filter-portfolio-plan').value = '';
    document.getElementById('filter-archived').checked = false;
    filterProjects();
}

function editProject(id) {
    window.location.href = `/projects/${id}/edit`;
}

function manageProject(id) {
    window.location.href = `/projects/${id}/manage`;
}

async function deleteProject(id) {
    if (confirm('Tem certeza que deseja excluir este projeto? Esta ação não pode ser desfeita.')) {
        try {
            const response = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
            if (response.ok) {
                await loadProjects();
            }
        } catch (error) {
            console.error('Error deleting project:', error);
        }
    }
}

function toggleCollapsible(id) {
    const container = document.getElementById(id);
    if (!container) return;

    const content = container.querySelector('.dashboard-summary-content');
    const chevron = container.querySelector('.chevron');

    if (content.style.maxHeight) {
        content.style.maxHeight = null;
        chevron.style.transform = 'rotate(0deg)';
    } else {
        content.style.maxHeight = content.scrollHeight + 'px';
        chevron.style.transform = 'rotate(180deg)';
    }
}
