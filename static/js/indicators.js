/**
 * Indicators Module - JS for V2 Layout
 */

document.addEventListener('DOMContentLoaded', () => {
    initIndicators();
});

let state = {
    indicators: [],
    groups: [],
    filters: {
        company_id: '',
        plan_id: '',
        group_id: ''
    }
};

async function initIndicators() {
    await Promise.all([
        fetchGroups(),
        fetchIndicators(),
        fetchFilterOptions()
    ]);

    renderGroups();
    renderIndicators();
}

async function fetchIndicators() {
    try {
        const params = new URLSearchParams();
        if (state.filters.company_id) params.append('company_id', state.filters.company_id);
        if (state.filters.plan_id) params.append('plan_id', state.filters.plan_id);

        const response = await fetch(`/api/indicators?${params.toString()}`);
        state.indicators = await response.json();
    } catch (error) {
        console.error('Error fetching indicators:', error);
    }
}

async function fetchGroups() {
    try {
        const response = await fetch('/api/indicator-groups');
        state.groups = await response.json();
    } catch (error) {
        console.error('Error fetching groups:', error);
    }
}

async function fetchFilterOptions() {
    try {
        const [compRes, planRes] = await Promise.all([
            fetch('/api/companies'),
            fetch('/api/plans')
        ]);

        const companies = await compRes.json();
        const plans = await planRes.json();

        populateSelect('filterCompany', companies, 'id', 'name');
        populateSelect('filterPlan', plans, 'id', 'name');
    } catch (error) {
        console.error('Error fetching filter options:', error);
    }
}

function populateSelect(id, items, valueKey, textKey) {
    const select = document.getElementById(id);
    if (!select) return;

    // Clear existing (except first)
    while (select.options.length > 1) {
        select.remove(1);
    }

    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item[valueKey];
        opt.textContent = item[textKey];
        select.appendChild(opt);
    });
}

function renderGroups() {
    const list = document.getElementById('indicatorGroupsList');
    if (!list) return;

    let html = `
        <div class="group-item ${!state.filters.group_id ? 'active' : ''}" onclick="selectGroup('')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 9h16M4 15h16"></path></svg>
            Todos os Grupos
        </div>
    `;

    state.groups.forEach(group => {
        html += `
            <div class="group-item ${state.filters.group_id == group.id ? 'active' : ''}" onclick="selectGroup(${group.id})">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="color: var(--primary)"><circle cx="12" cy="12" r="2"></circle></svg>
                ${group.name}
            </div>
        `;
    });

    list.innerHTML = html;
}

function renderIndicators() {
    const grid = document.getElementById('indicatorsGrid');
    const empty = document.getElementById('emptyState');
    if (!grid) return;

    let filtered = state.indicators;
    if (state.filters.group_id) {
        filtered = filtered.filter(ind => ind.group_id == state.filters.group_id);
    }

    if (filtered.length === 0) {
        grid.style.display = 'none';
        empty.style.display = 'flex';
        empty.style.flexDirection = 'column';
        empty.style.alignItems = 'center';
        return;
    }

    grid.style.display = 'grid';
    empty.style.display = 'none';

    grid.innerHTML = filtered.map(ind => `
        <article class="indicator-card">
            <div class="indicator-header">
                <span class="indicator-code">${ind.code}</span>
                <div class="dropdown" style="position: relative;">
                    <button class="btn-icon" onclick="toggleDropdown(event, ${ind.id})">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>
                    </button>
                    <div id="dropdown-${ind.id}" class="dropdown-content" style="display: none; position: absolute; right: 0; background: white; border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow-md); z-index: 10;">
                        <a href="/indicators/${ind.id}/edit" style="display: block; padding: 0.5rem 1rem; color: var(--text-primary); text-decoration: none; font-size: 0.85rem;">Editar</a>
                        <a href="#" onclick="deleteIndicator(event, ${ind.id})" style="display: block; padding: 0.5rem 1rem; color: var(--danger); text-decoration: none; font-size: 0.85rem;">Excluir</a>
                    </div>
                </div>
            </div>
            
            <a href="/indicators/${ind.id}" style="text-decoration: none; color: inherit;">
                <h3 class="indicator-title">${ind.name}</h3>
            </a>
            
            <div class="indicator-meta">
                <span>POL: ${ind.polarity === 'positive' ? 'Crescente' : 'Decrescente'}</span>
                <span>•</span>
                <span>META: ${ind.goals && ind.goals.length > 0 ? formatBR((ind.goals.find(g => g.status === 'active') || ind.goals[0]).goal_value) : '--'}</span>
            </div>
            
            <div class="indicator-value-main">
                <span class="current-value">${ind.last_value !== null ? formatBR(ind.last_value) : '0,00'}</span>
                <span class="value-unit">${ind.unit || ''}</span>
            </div>
            
            <div class="indicator-footer">
                <span class="text-sm ${ind.performance >= 100 ? 'text-success' : 'text-primary'}" style="font-weight: 600;">Progresso: ${ind.performance !== null ? formatBR(ind.performance) + '%' : '--'}</span>
                <a href="/indicators/${ind.id}" class="btn btn-secondary btn-sm">Detalhes</a>
            </div>

        </article>
    `).join('');
}

function formatBR(val) {
    if (val === null || val === undefined) return '';
    const numeric = typeof val === 'string' ? parseFloat(val) : val;
    return numeric.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function selectGroup(id) {
    state.filters.group_id = id;
    renderGroups();
    renderIndicators();
}

function applyFilters() {
    state.filters.company_id = document.getElementById('filterCompany').value;
    state.filters.plan_id = document.getElementById('filterPlan').value;

    initIndicators();
    // Close sidebar on mobile
    if (window.innerWidth <= 1200) {
        toggleSidebar('right');
    }
}

function toggleDropdown(event, id) {
    event.stopPropagation();
    const dropdown = document.getElementById(`dropdown-${id}`);
    const isVisible = dropdown.style.display === 'block';

    // Close all other dropdowns
    document.querySelectorAll('.dropdown-content').forEach(d => d.style.display = 'none');

    dropdown.style.display = isVisible ? 'none' : 'block';
}

async function deleteIndicator(event, id) {
    event.preventDefault();
    event.stopPropagation();

    if (!confirm('Tem certeza que deseja excluir este indicador? Todos os dados vinculados serão perdidos.')) return;

    try {
        const res = await fetch(`/api/indicators/${id}`, { method: 'DELETE' });
        if (res.ok) {
            initIndicators();
        } else {
            alert('Erro ao excluir indicador.');
        }
    } catch (e) {
        console.error(e);
    }
}

// Close dropdowns on outside click
document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-content').forEach(d => d.style.display = 'none');
});

