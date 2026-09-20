/**
 * Companies Management - Versus Corporate Design
 * Handles API interactions for the companies module
 */

let allCompanies = [];
let companyToDelete = null;
let companyPagination = { page: 1, per_page: 50, total: 0, has_more: false };
let companiesFilterTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    loadCompanies();
});

async function loadCompanies({ append = false } = {}) {
    try {
        const grid = document.getElementById('companies-grid');
        const emptyState = document.getElementById('empty-state');
        const loadingState = document.getElementById('loading-state');

        if (!append) {
            loadingState.style.display = 'block';
            grid.style.display = 'none';
            emptyState.style.display = 'none';
        }

        const page = append ? companyPagination.page + 1 : 1;
        const params = new URLSearchParams({
            all: 'true',
            paginated: 'true',
            page: String(page),
            per_page: '50',
        });
        const search = document.getElementById('filter-search')?.value.trim();
        const segment = document.getElementById('filter-segment')?.value;
        const size = document.getElementById('filter-size')?.value;
        if (search) params.set('search', search);
        if (segment) params.set('segment', segment);
        if (size) params.set('size', size);
        const response = await fetch(`/api/companies?${params.toString()}`);
        if (!response.ok) throw new Error();

        const payload = await response.json();
        if (!Array.isArray(payload.items) || !payload.pagination) throw new Error();
        if (append) {
            const knownIds = new Set(allCompanies.map((company) => Number(company.id)));
            allCompanies = allCompanies.concat(payload.items.filter((company) => !knownIds.has(Number(company.id))));
        } else {
            allCompanies = payload.items;
        }
        companyPagination = payload.pagination;

        loadingState.style.display = 'none';
        renderCompanies();
        return true;
    } catch (error) {
        console.error('Error:', error);
        if (!append) {
            document.getElementById('loading-state').innerHTML = '<p style="color:red">Erro ao carregar dados.</p>';
        }
        return false;
    }
}

function filterCompanies() {
    window.clearTimeout(companiesFilterTimer);
    companiesFilterTimer = window.setTimeout(() => loadCompanies(), 250);
}

function renderCompanies() {
    const grid = document.getElementById('companies-grid');
    const emptyState = document.getElementById('empty-state');

    if (allCompanies.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'flex';
        document.getElementById('companies-pagination')?.replaceChildren();
        return;
    }

    emptyState.style.display = 'none';
    grid.style.display = 'flex';
    grid.innerHTML = allCompanies.map(c => `
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
                    <button class="btn-instance-action" onclick="event.stopPropagation(); window.location.href='/companies/${c.id}/identity'" title="Identidade Organizacional">
                        <span class="d-none d-md-inline">Identidade</span>
                        <span class="d-inline d-md-none">🧭</span>
                    </button>
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
    renderCompaniesPagination();
}

function renderCompaniesPagination() {
    const container = document.getElementById('companies-pagination');
    if (!container) return;
    container.replaceChildren();
    if (!companyPagination.has_more) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-secondary';
    button.textContent = `Carregar mais (${allCompanies.length} de ${companyPagination.total})`;
    button.addEventListener('click', async () => {
        button.disabled = true;
        button.textContent = 'Carregando...';
        const loaded = await loadCompanies({ append: true });
        if (!loaded) {
            button.disabled = false;
            button.textContent = 'Tentar novamente';
        }
    });
    container.appendChild(button);
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
