/**
 * Processes Module JS
 */

const state = {
    processes: [],
    areas: [],
    macros: [],
    filters: {
        company_id: '',
        area_id: '',
        stage: ''
    }
};

document.addEventListener('DOMContentLoaded', () => {
    initProcesses();

    // Form listeners
    document.getElementById('areaForm')?.addEventListener('submit', handleAreaSubmit);
    document.getElementById('macroForm')?.addEventListener('submit', handleMacroSubmit);
});

async function initProcesses() {
    console.log('Initializing processes list...');
    try {
        await Promise.all([
            fetchAreas(),
            fetchFilterOptions()
        ]);

        // Areas must be fetched before we can render them or fetch processes filtered
        renderAreas();
        await fetchProcesses();
        renderProcesses();
        console.log('Processes initialization complete.');
    } catch (e) {
        console.error("Critical error in initProcesses:", e);
        const grid = document.getElementById('processesGrid');
        if (grid) grid.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados: ${e.message}</div>`;
    }
}

async function fetchAreas() {
    try {
        const res = await fetch('/api/process-areas');
        state.areas = await res.json();
    } catch (e) {
        console.error("Error fetching areas:", e);
    }
}

async function fetchMacros(areaId) {
    try {
        const res = await fetch(`/api/macro-processes?area_id=${areaId}`);
        state.macros = await res.json();
    } catch (e) {
        console.error("Error fetching macros:", e);
    }
}

async function fetchProcesses() {
    try {
        let url = '/api/processes?';
        if (state.filters.company_id) url += `company_id=${state.filters.company_id}&`;

        // Note: The API treats area_id as a filter for macros, 
        // will need to filter processes by macro's area on client or improve API
        const res = await fetch(url);
        let data = await res.json();

        if (state.filters.area_id) {
            // Find macros for this area first
            const mRes = await fetch(`/api/macro-processes?area_id=${state.filters.area_id}`);
            const areaMacros = await mRes.json();
            const macroIds = areaMacros.map(m => m.id);
            data = data.filter(p => macroIds.includes(p.macro_id));
        }

        state.processes = data;
    } catch (e) {
        console.error("Error fetching processes:", e);
    }
}

async function fetchFilterOptions() {
    try {
        const res = await fetch('/api/companies');
        const companies = await res.json();
        const select = document.getElementById('filterCompany');
        if (!select) return; // Exit gracefully if not on list page

        // Keep "Todas"
        while (select.options.length > 1) select.remove(1);
        companies.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error("Error fetching companies:", e);
    }
}

function renderAreas() {
    const list = document.getElementById('processAreasList');
    if (!list) return;

    let html = `
        <div class="area-item ${!state.filters.area_id ? 'active' : ''}" onclick="selectArea('')">
            <span class="area-color-dot" style="background: #cbd5e1;"></span>
            Todas as Áreas
        </div>
    `;

    state.areas.forEach(area => {
        html += `
            <div class="area-item ${state.filters.area_id == area.id ? 'active' : ''}" onclick="selectArea(${area.id})">
                <span class="area-color-dot" style="background: ${area.color || '#3b82f6'};"></span>
                ${area.name}
            </div>
        `;
    });

    list.innerHTML = html;
}

function renderMacros() {
    const list = document.getElementById('macroProcessesList');
    const btnNew = document.getElementById('btnNewMacro');
    if (!list) return;

    if (!state.filters.area_id) {
        list.innerHTML = '<p class="text-tertiary p-2" style="font-size: 0.8rem;">Selecione uma área para ver macros.</p>';
        if (btnNew) btnNew.disabled = true;
        return;
    }

    if (btnNew) btnNew.disabled = false;

    if (state.macros.length === 0) {
        list.innerHTML = '<p class="text-tertiary p-2" style="font-size: 0.8rem;">Nenhum macroprocesso.</p>';
        return;
    }

    list.innerHTML = state.macros.map(m => `
        <div class="area-item" style="padding-left: 2rem; font-size: 0.85rem;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity: 0.5">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
            </svg>
            ${m.name}
        </div>
    `).join('');
}

function renderProcesses() {
    const grid = document.getElementById('processesGrid');
    const emptyState = document.getElementById('emptyState');
    if (!grid) return;

    const filtered = state.processes.filter(p => {
        if (state.filters.stage && p.kanban_stage !== state.filters.stage) return false;
        return true;
    });

    if (filtered.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'flex';
        return;
    }

    grid.style.display = 'grid';
    emptyState.style.display = 'none';

    grid.innerHTML = filtered.map(p => {
        const stageLabel = getStageLabel(p.kanban_stage);
        const stageClass = `stage-${p.kanban_stage}`;
        const initials = p.responsible ? p.responsible.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : '??';

        return `
            <article class="process-card">
                <div class="process-header">
                    <span class="process-code">${p.code || 'S/C'}</span>
                    <span class="process-stage-badge ${stageClass}">${stageLabel}</span>
                </div>
                
                <a href="/processes/${p.id}" style="text-decoration: none; color: inherit;">
                    <h3 class="process-title">${p.name}</h3>
                </a>
                
                <div class="process-owner">
                    <div class="process-owner-avatar">${initials}</div>
                    <span>Resp: ${p.responsible || 'Não definido'}</span>
                </div>
                
                <div class="process-stats">
                    <div class="stat-item">
                        <span class="stat-value">--</span>
                        <span class="stat-label">Roteiros</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">--</span>
                        <span class="stat-label">Passos</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">--</span>
                        <span class="stat-label">Indicadores</span>
                    </div>
                </div>

                <div style="margin-top: auto; display: flex; justify-content: flex-end;">
                    <a href="/processes/${p.id}" class="btn btn-secondary btn-sm">Painel</a>
                </div>
            </article>
        `;
    }).join('');
}

function getStageLabel(stage) {
    const stages = {
        'inbox': 'Entrada',
        'designing': 'Modelando',
        'deploying': 'Implantando',
        'stabilizing': 'Estabilizando',
        'stable': 'Estável'
    };
    return stages[stage] || 'Experimental';
}

async function selectArea(id) {
    state.filters.area_id = id;
    renderAreas();
    if (id) {
        await fetchMacros(id);
    } else {
        state.macros = [];
    }
    renderMacros();
    await fetchProcesses();
    renderProcesses();
}

function applyFilters() {
    state.filters.company_id = document.getElementById('filterCompany').value;
    state.filters.stage = document.getElementById('filterStage').value;

    initProcesses();

    if (window.innerWidth <= 1200) {
        toggleSidebar('right');
    }
}

// Modals
function openAreaModal() { document.getElementById('areaModal').style.display = 'block'; }
function openMacroModal() {
    if (!state.filters.area_id) return;
    const area = state.areas.find(a => a.id == state.filters.area_id);
    document.getElementById('modalMacroAreaId').value = area.id;
    document.getElementById('modalMacroAreaName').value = area.name;
    document.getElementById('macroModal').style.display = 'block';
}
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

async function handleAreaSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // Default to first company for demo
    data.company_id = state.filters.company_id || 1;

    try {
        const res = await fetch('/api/process-areas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            closeModal('areaModal');
            await fetchAreas();
            renderAreas();
        }
    } catch (e) { console.error(e); }
}

async function handleMacroSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    data.area_id = parseInt(data.area_id);
    data.company_id = state.filters.company_id || 1;

    try {
        const res = await fetch('/api/macro-processes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            closeModal('macroModal');
            await fetchMacros(data.area_id);
            renderMacros();
        }
    } catch (e) { console.error(e); }
}
