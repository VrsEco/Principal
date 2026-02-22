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
    grid.style.display = 'grid';
    grid.innerHTML = filteredCompanies.map(c => `
        <div class="card fade-in" onclick="window.location.href='/companies/${c.id}/edit'" style="cursor: pointer;">
            <div class="card-body">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem;">
                    <div class="company-logo-circle" style="background: var(--special-gradient); color: white;">
                        ${getInitials(c.name)}
                    </div>
                    ${c.is_active !== false
            ? '<span class="badge" style="background: #ecfdf5; color: #059669; border-radius: 8px;">Ativa</span>'
            : '<span class="badge" style="background: #fef2f2; color: #dc2626; border-radius: 8px;">Inativa</span>'}
                </div>
                
                <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.25rem;">${escapeHtml(c.name)}</h3>
                <p style="color: var(--text-tertiary); font-weight: 600; font-size: 0.8rem; margin-bottom: 1rem;">CÓDIGO: ${escapeHtml(c.client_code)}</p>
                
                <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--text-secondary); font-size: 0.9rem;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
                        ${escapeHtml(c.segment || 'Não definido')}
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--text-secondary); font-size: 0.9rem;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg>
                        Porte: ${escapeHtml(c.size || 'Não definido')}
                    </div>
                </div>
                
                <div style="display: flex; gap: 0.5rem; border-top: 1.5px solid var(--border); padding-top: 1.25rem;">
                    <button class="btn btn-secondary" style="flex: 1; padding: 0.5rem;" onclick="event.stopPropagation(); window.location.href='/companies/${c.id}/edit'">
                        Editar
                    </button>
                    <button class="btn btn-secondary" style="color: var(--danger); border-color: transparent;" onclick="deleteCompany(event, ${c.id}, '${escapeHtml(c.name)}')">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
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
