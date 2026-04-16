/**
 * Companies Management - Versus Corporate Design
 * Handles API interactions for the companies module
 */

let allCompanies = [];
let filteredCompanies = [];
let companyToDelete = null;

document.addEventListener('DOMContentLoaded', () => {
    loadCompanies();
});

async function loadCompanies() {
    try {
        const grid = document.getElementById('companies-grid');
        const emptyState = document.getElementById('empty-state');
        const loadingState = document.getElementById('loading-state');

        loadingState.style.display = 'block';
        grid.style.display = 'none';
        emptyState.style.display = 'none';

        const response = await fetch('/api/companies?all=true');
        if (!response.ok) throw new Error();

        allCompanies = await response.json();
        filteredCompanies = [...allCompanies];

        loadingState.style.display = 'none';
        renderCompanies();
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loading-state').innerHTML = '<p style="color:red">Erro ao carregar dados.</p>';
    }
}

function filterCompanies() {
    const search = document.getElementById('filter-search').value.toLowerCase();
    const segment = document.getElementById('filter-segment').value;
    const size = document.getElementById('filter-size').value;

    filteredCompanies = allCompanies.filter(c => {
        const matchesSearch = !search || c.name.toLowerCase().includes(search) || (c.client_code && c.client_code.toLowerCase().includes(search));
        const matchesSegment = !segment || c.segment === segment;
        const matchesSize = !size || c.size === size;
        return matchesSearch && matchesSegment && matchesSize;
    });

    renderCompanies();
}

function renderCompanies() {
    const grid = document.getElementById('companies-grid');
    const emptyState = document.getElementById('empty-state');

    if (filteredCompanies.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'flex';
        return;
    }

    emptyState.style.display = 'none';
    grid.style.display = 'flex';
    grid.innerHTML = filteredCompanies.map(c => `
        <div class="instance-card fade-in" onclick="window.location.href='/companies/${c.id}/edit'" style="cursor: pointer;">
            <!-- Line 1: Code | Title | Status -->
            <div class="compact-row" style="margin-bottom: 2px;">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    ${c.client_code ? `<div class="instance-code">${escapeHtml(c.client_code)}</div>` : ''}
                    <h3 class="instance-name">${escapeHtml(c.name)}</h3>
                </div>
                
                <div class="instance-badges">
                    ${c.is_active !== false
            ? '<span class="badge status-active">Ativa</span>'
            : '<span class="badge status-inactive">Inativa</span>'}
                </div>
            </div>

            <!-- Line 2: Meta | Actions -->
            <div class="compact-row" style="justify-content: flex-start; align-items: center; margin-top: 2px;">
                <div class="compact-meta">
                    <span style="display: flex; align-items: center; gap: 4px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
                        <strong>Seg:</strong> ${escapeHtml(c.segment || 'Não definido')}
                    </span>
                    <span class="sep">|</span>
                    <span style="display: flex; align-items: center; gap: 4px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg>
                        <strong>Porte:</strong> ${escapeHtml(c.size || 'Não definido')}
                    </span>
                </div>

                <div class="instance-actions">
                    <button class="btn-instance-action action-edit" onclick="event.stopPropagation(); window.location.href='/companies/${c.id}/edit'" title="Editar">
                        <span class="d-none d-md-inline">Editar</span>
                        <span class="d-inline d-md-none">✏️</span>
                    </button>
                    <button class="btn-instance-action action-delete" onclick="deleteCompany(event, ${c.id}, '${escapeHtml(c.name)}')" title="Excluir">
                        <span class="d-none d-md-inline">Excluir</span>
                        <span class="d-inline d-md-none">🗑️</span>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function resetCompaniesFilters() {
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-segment').value = '';
    document.getElementById('filter-size').value = '';
    filterCompanies();
}

function getInitials(name) {
    if (!name) return '??';
    const s = name.trim().split(' ');
    return s.length > 1 ? (s[0][0] + s[s.length - 1][0]).toUpperCase() : s[0].substring(0, 2).toUpperCase();
}

function escapeHtml(t) {
    if (!t) return '';
    const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return t.replace(/[&<>"']/g, s => m[s]);
}

function deleteCompany(event, id, name) {
    event.stopPropagation();
    companyToDelete = id;
    document.getElementById('delete-company-name').textContent = name;
    document.getElementById('delete-modal').style.display = 'flex';
}

function closeDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
}

async function confirmDelete() {
    try {
        const r = await fetch(`/api/companies/${companyToDelete}`, { method: 'DELETE' });
        if (!r.ok) throw new Error();
        closeDeleteModal();
        loadCompanies();
    } catch (e) { alert('Erro ao excluir.'); }
}
