/**
 * Processes Kanban JS
 */

const state = {
    processes: [],
    areas: [],
    macros: [],
    companyId: document.getElementById('kanbanContainer')?.dataset.companyId || null,
    filters: {
        areaId: null,
        macroId: null,
        search: '',
        responsible: ''
    },
    abbreviations: {
        'inbox': 'F',
        'waiting': 'A',
        'designing': 'M',
        'deploying': 'I',
        'stabilizing': 'E',
        'stable': 'E'
    }
};

// Handle null strings
if (state.companyId === 'null' || state.companyId === 'undefined') state.companyId = null;

console.log("Kanban State Initialized. companyId:", state.companyId);

document.addEventListener('DOMContentLoaded', () => {
    initKanban();
});

async function initKanban() {
    await Promise.all([
        fetchAreas(),
        fetchProcesses()
    ]);
    renderAreas();
    renderKanban();
}

async function fetchAreas() {
    const fetchId = state.companyId;
    console.log("Fetching areas for Kanban. ID:", fetchId);
    const res = await fetch(`/api/process-areas?company_id=${fetchId || ''}`);
    state.areas = await res.json();
}

async function fetchProcesses() {
    const fetchId = state.companyId;
    let url = `/api/processes?company_id=${fetchId || ''}`;
    if (state.filters.macroId) url += `&macro_id=${state.filters.macroId}`;
    console.log("Fetching processes for Kanban. URL:", url);
    const res = await fetch(url);
    state.processes = await res.json();
}

function renderAreas() {
    const list = document.getElementById('processAreasList');
    if (!list) return;
    list.innerHTML = state.areas.map(a => `
        <div class="area-item ${state.filters.areaId == a.id ? 'active' : ''}" onclick="selectArea(${a.id})">
            <span class="area-color-dot" style="background: ${a.color}"></span>
            ${a.name}
        </div>
    `).join('');
}

async function selectArea(id) {
    state.filters.areaId = id;
    state.filters.macroId = null;
    renderAreas();

    // Fetch macros for this area
    const res = await fetch(`/api/macro-processes?area_id=${id}`);
    state.macros = await res.json();

    const mList = document.getElementById('macroProcessesList');
    if (!mList) {
        await fetchProcesses();
        renderKanban();
        return;
    }
    mList.innerHTML = state.macros.map(m => `
        <div class="area-item ${state.filters.macroId == m.id ? 'active' : ''}" onclick="selectMacro(${m.id})">
            ${m.name}
        </div>
    `).join('');

    await fetchProcesses();
    renderKanban();
}

async function selectMacro(id) {
    state.filters.macroId = id;
    // Update active class
    document.querySelectorAll('#macroProcessesList .area-item').forEach(el => {
        el.classList.toggle('active', el.textContent.trim() === state.macros.find(m => m.id == id).name);
    });
    await fetchProcesses();
    renderKanban();
}

function renderKanban() {
    const stages = ['inbox', 'waiting', 'designing', 'deploying', 'stabilizing', 'stable'];

    // Clear dropzones
    stages.forEach(s => {
        const dz = document.getElementById(`dz-${s}`);
        dz.innerHTML = '';
        document.getElementById(`count-${s}`).textContent = '0';
    });

    // Filter processes by state.filters (search, responsible, area, macro)
    const filtered = state.processes.filter(p => {
        const searchMatch = !state.filters.search ||
            p.name.toLowerCase().includes(state.filters.search.toLowerCase()) ||
            (p.code && p.code.toLowerCase().includes(state.filters.search.toLowerCase()));
        const respMatch = !state.filters.responsible || p.responsible == state.filters.responsible;

        // Area filtering (if macroId is not set, we filter by areaId)
        const areaMatch = !state.filters.areaId || (p.macro && p.macro.area_id == state.filters.areaId);

        // macroId is already filtered by fetchProcesses if set, but we can double check here
        const macroMatch = !state.filters.macroId || p.macro_id == state.filters.macroId;

        return searchMatch && respMatch && areaMatch && macroMatch;
    });

    filtered.forEach(p => {
        let stage = p.kanban_stage || 'inbox';
        // Map common legacy or unknown stages to inbox
        if (stage === 'out_of_scope') stage = 'inbox';

        const dz = document.getElementById(`dz-${stage}`);
        if (!dz) return;

        // Calculate Technical Badges
        const hasFlux = p.flow_mermaid || p.flow_document;
        const routines = p.routines || [];
        const hasRoutine = routines.length > 0;
        const hasPop = routines.some(r => r.steps && r.steps.length > 0);
        const indicators = p.indicators || [];
        const hasInd = indicators.length > 0;

        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.draggable = true;
        card.dataset.id = p.id;
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                <span class="kanban-card-code">${p.code || 'S/C'}</span>
                <div class="tech-badges">
                    <span class="tech-badge ${hasFlux ? 'active' : ''}" title="Fluxograma">FLX</span>
                    <span class="tech-badge ${hasRoutine ? 'active' : ''}" title="Rotinas">RTN</span>
                    <span class="tech-badge ${hasPop ? 'active' : ''}" title="POP">POP</span>
                    <span class="tech-badge ${hasInd ? 'active' : ''}" title="Indicadores">IND</span>
                </div>
            </div>
            <div class="kanban-card-name">${p.name}</div>
            
            <div class="kanban-card-people">
                <div class="person-tag" title="Dono do Macroprocesso">
                    <span class="label">D:</span> ${p.macro?.owner ? p.macro.owner.split(' ')[0] : '-'}
                </div>
                <div class="person-tag" title="Responsável pelo Processo">
                    <span class="label">R:</span> ${p.responsible ? p.responsible.split(' ')[0] : '-'}
                </div>
            </div>
            
            <div class="kanban-card-meta">
                <a href="/processes/${p.id}" class="text-primary" style="text-decoration:none">Detalhes →</a>
            </div>
        `;

        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
        dz.appendChild(card);
    });

    // Update counts and collapsed titles
    stages.forEach(s => {
        const count = document.getElementById(`dz-${s}`).children.length;
        document.getElementById(`count-${s}`).textContent = count;

        const collapsedSpan = document.getElementById(`collapsed-title-${s}`);
        if (collapsedSpan) {
            const letter = state.abbreviations[s] || '?';
            collapsedSpan.textContent = `${letter} - ${count}`;
        }
    });

    setupDragAndDrop();
}

// Drag & Drop
let draggedCard = null;

function handleDragStart(e) {
    draggedCard = e.currentTarget;
    draggedCard.classList.add('dragging');
}

function handleDragEnd(e) {
    draggedCard.classList.remove('dragging');
    draggedCard = null;
}

function setupDragAndDrop() {
    document.querySelectorAll('.kanban-dropzone').forEach(dz => {
        dz.addEventListener('dragover', e => {
            e.preventDefault();
            dz.classList.add('drag-over');
        });

        dz.addEventListener('dragleave', () => {
            dz.classList.remove('drag-over');
        });

        dz.addEventListener('drop', async e => {
            e.preventDefault();
            dz.classList.remove('drag-over');
            if (draggedCard) {
                const processId = draggedCard.dataset.id;
                const targetStage = dz.parentElement.dataset.stage;

                // Update UI optimistically
                dz.appendChild(draggedCard);
                updateAllCounts();

                // Update Backend
                await updateProcessStage(processId, targetStage);
            }
        });
    });
}

function updateAllCounts() {
    ['inbox', 'waiting', 'designing', 'deploying', 'stabilizing', 'stable'].forEach(s => {
        const count = document.getElementById(`dz-${s}`).children.length;
        document.getElementById(`count-${s}`).textContent = count;

        const collapsedSpan = document.getElementById(`collapsed-title-${s}`);
        if (collapsedSpan) {
            const letter = state.abbreviations[s] || '?';
            collapsedSpan.textContent = `${letter} - ${count}`;
        }
    });
}

async function updateProcessStage(id, stage) {
    try {
        await fetch(`/api/processes/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kanban_stage: stage })
        });
    } catch (e) {
        console.error("Error updating process stage:", e);
    }
}

// Filters
function applyKanbanFilters() {
    const sInput = document.getElementById('filterSearch');
    const rInput = document.getElementById('filterResponsible');
    if (sInput) state.filters.search = sInput.value;
    if (rInput) state.filters.responsible = rInput.value;
    renderKanban();
}

function resetKanbanFilters() {
    const sInput = document.getElementById('filterSearch');
    const rInput = document.getElementById('filterResponsible');
    if (sInput) sInput.value = '';
    if (rInput) rInput.value = '';

    state.filters.search = '';
    state.filters.responsible = '';
    state.filters.areaId = null;
    state.filters.macroId = null;

    // Clear macros list
    const mList = document.getElementById('macroProcessesList');
    if (mList) mList.innerHTML = '<p class="text-tertiary text-sm">Selecione uma área para ver os macroprocessos.</p>';

    renderAreas();
    fetchProcesses().then(() => renderKanban());
}

// Sidebar Styles helpers
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('area-item')) {
        // Toggle active class is handled in selectArea/selectMacro
    }
});
