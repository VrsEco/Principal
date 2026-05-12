/**
 * Process Architecture Management JS
 * Handles Tabs, Forms and Map Rendering
 */

// Handle 'null' string or other invalid values from data attribute
const rawCompanyId = document.getElementById('processArchitectureContainer')?.dataset.companyId;
const isCollaborator = document.getElementById('processArchitectureContainer')?.dataset.isCollaborator === 'true';
let normalizedCompanyId = rawCompanyId;
if (!rawCompanyId || rawCompanyId === 'null' || rawCompanyId === 'undefined' || rawCompanyId === '') {
    normalizedCompanyId = null;
}

const state = {
    areas: [],
    macros: [],
    processes: [],
    employees: [],
    companyId: normalizedCompanyId,
    viewType: localStorage.getItem('arch_view_type') || 'classic'
};

const FORM_ALLOWED_FIELDS = {
    formArea: ['id', 'code', 'name', 'color', 'description'],
    formMacro: ['id', 'area_id', 'order_index', 'owner', 'name', 'description'],
    formProcess: ['id', 'macro_id', 'order_index', 'responsible', 'name', 'performance_level', 'description']
};

document.addEventListener('DOMContentLoaded', () => {
    initArchitecture();
    setupFormListeners();
    checkUrlParams();
    updateViewToggleUI();
});

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function buildEmployeeOptions(employees, placeholder) {
    const options = Array.isArray(employees) ? employees : [];
    return `<option value="">${escapeHtml(placeholder)}</option>` +
        options
            .filter(e => e && e.name)
            .map(e => `<option value="${escapeHtml(e.name)}">${escapeHtml(e.name)}</option>`)
            .join('');
}

function updateViewToggleUI() {
    document.querySelectorAll('.btn-view-type').forEach(btn => {
        const type = btn.getAttribute('onclick').match(/'(.*)'/)[1];
        btn.classList.toggle('active', type === state.viewType);
    });
}

function switchMapView(type) {
    state.viewType = type;
    localStorage.setItem('arch_view_type', type);
    updateViewToggleUI();
    renderMap();
}

async function initArchitecture() {
    console.log("Initializing Architecture. Current state.companyId:", state.companyId);
    if (!state.companyId) {
        console.warn("No companyId found in state! Attempting to refresh from container...");
        state.companyId = document.getElementById('processArchitectureContainer')?.dataset.companyId;
        if (!state.companyId || state.companyId === 'null' || state.companyId === 'undefined' || state.companyId === '') {
            state.companyId = null;
        }
    }
    await refreshData();
    renderMap();
    renderTables();
    populateSelects();
    updatePrintDate();
}

function updatePrintDate() {
    const el = document.getElementById('printDate');
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleString('pt-BR');
    }
}

async function refreshData() {
    try {
        const fetchId = state.companyId;
        console.log("Refreshing architecture data. Final ID used for Fetch:", fetchId);

        const cb = `_cb=${Date.now()}`;
        const responses = await Promise.all([
            fetch(`/api/process-areas?company_id=${fetchId || ''}&${cb}`),
            fetch(`/api/macro-processes?company_id=${fetchId || ''}&${cb}`),
            fetch(`/api/processes?company_id=${fetchId || ''}&${cb}`)
        ]);

        for (const res of responses) {
            if (!res.ok) {
                const text = await res.text();
                console.error(`API Error (${res.url}): ${res.status}`, text);
                throw new Error(`API returned ${res.status} for ${new URL(res.url).pathname}`);
            }
        }

        const [areas, macros, processes] = await Promise.all(responses.map(r => r.json()));
        console.log("Data loaded:", { areasCount: areas.length, macrosCount: macros.length, processesCount: processes.length });

        state.areas = Array.isArray(areas) ? areas : [];
        state.macros = Array.isArray(macros) ? macros : [];
        state.processes = Array.isArray(processes) ? processes : [];
    } catch (e) {
        console.error("Error refreshing architecture data:", e);
        window.showMessage?.("Erro ao carregar dados da arquitetura. Verifique o console.", "error");
    }
}

function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) {
        switchTab(tab);
    }
}

function switchTab(tabId) {
    // Buttons
    document.querySelectorAll('.arch-tab').forEach(btn => {
        const isActive = btn.getAttribute('onclick').includes(`'${tabId}'`);
        btn.classList.toggle('active', isActive);
    });
    // Panels
    document.querySelectorAll('.arch-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${tabId}`);
    });

    if (tabId === 'visual') renderMap();

    // Smooth scroll to top of panel
    const tabsEl = document.querySelector('.arch-tabs');
    if (tabsEl) tabsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Rendering
function renderMap() {
    const container = document.getElementById('processMap');
    if (!container) return;

    if (state.areas.length === 0) {
        container.innerHTML = '<div class="empty-state p-5 text-center"><p class="text-tertiary">Nenhuma área cadastrada.</p></div>';
        return;
    }

    if (state.viewType === 'mp2') {
        renderMapMP2(container);
    } else {
        renderMapClassic(container);
    }
}

function renderMapClassic(container) {
    container.classList.remove('mp2-view');
    container.innerHTML = state.areas.map(area => {
        const areaMacros = state.macros.filter(m => m.area_id === area.id);
        return `
            <div class="area-column">
                <div class="area-header" style="background: ${area.color || '#3b82f6'}">
                    <h2>${area.code ? area.code + ' · ' : ''}${area.name}</h2>
                </div>
                ${areaMacros.map(macro => {
            const macroProcesses = state.processes.filter(p => p.macro_id === macro.id);
            return `
                        <div class="macro-group">
                            <div class="macro-title">${macro.code ? `<span style='font-family:monospace; color: var(--text-tertiary); font-size:0.75em;'>${macro.code}</span> ` : ''}${macro.name}</div>
                            ${macroProcesses.map(p => {
            const linkTag = isCollaborator ? 'div' : 'a';
            const linkAttr = isCollaborator ? '' : `href="/processes/${p.id}"`;
            return `
                                <${linkTag} ${linkAttr} class="process-link-card" ${isCollaborator ? 'style="cursor: default;"' : ''}>
                                    <span class="process-link-name">${p.code ? p.code + ' - ' : ''}${p.name}</span>
                                    <div class="process-link-meta">
                                        <div style="display: flex; gap: 6px; align-items: center;">
                                            ${p.has_incentive ? '<span title="Possui Incentivo" style="font-size: 0.75rem; filter: drop-shadow(0 0 2px #fbbf24);">🏆</span>' : ''}
                                            <span class="indicator-stage" style="background: ${getStageColor(p.kanban_stage)}" title="Etapa"></span>
                                            <span class="indicator-perf" style="background: ${getPerfColor(p.performance_level)}" title="Desempenho"></span>
                                        </div>
                                        <span>👤 ${p.responsible ? p.responsible.split(' ')[0] : '-'}</span>
                                    </div>
                                </${linkTag}>
                            `;
        }).join('')}
                            <div class="macro-footer">Dono: ${macro.owner || '-'}</div>
                        </div>
                    `;
        }).join('')}
            </div>
        `;
    }).join('');
}

function renderMapMP2(container) {
    container.classList.add('mp2-view');
    container.innerHTML = state.areas.map(area => {
        const areaMacros = state.macros.filter(m => m.area_id === area.id);
        return `
            <div class="mp2-area-section" style="border-color: ${area.color || '#3b82f6'}">
                <div class="mp2-area-sidebar" style="background: ${area.color || '#3b82f6'}">
                    <div class="mp2-area-name">${area.code ? area.code + ' ' : ''}${area.name}</div>
                </div>
                <div class="mp2-macros-grid">
                    ${areaMacros.map(macro => {
            const macroProcesses = state.processes.filter(p => p.macro_id === macro.id);
            return `
                            <div class="mp2-macro-box">
                                <div class="mp2-macro-title">${macro.code ? macro.code + ' - ' : ''}${macro.name}</div>
                                <div class="mp2-processes-list">
                                    ${macroProcesses.map(p => {
                const linkTag = isCollaborator ? 'div' : 'a';
                const linkAttr = isCollaborator ? '' : `href="/processes/${p.id}"`;
                return `
                                        <${linkTag} ${linkAttr} class="mp2-process-card" ${isCollaborator ? 'style="cursor: default;"' : ''}>
                                            <div class="mp2-process-badges">
                                                ${p.has_incentive ? '<span title="Possui Incentivo" style="font-size: 0.6rem; margin-bottom: 2px;">🏆</span>' : ''}
                                                <div class="indicator-stage" style="background: ${getStageColor(p.kanban_stage)}; width: 10px; height: 10px;"></div>
                                                <div class="indicator-perf" style="background: ${getPerfColor(p.performance_level)}; width: 9px; height: 9px;"></div>
                                            </div>
                                            <div class="mp2-process-name">${p.code ? p.code + ' - ' : ''}${p.name}</div>
                                        </${linkTag}>
                                    `;
            }).join('')}
                                    ${macroProcesses.length === 0 ? '<div style="grid-column: 1/-1; text-align:center; font-size:0.6rem; color:var(--text-tertiary)">Sem processos</div>' : ''}
                                </div>
                                <div class="macro-footer">Dono: ${macro.owner || '-'}</div>
                            </div>
                        `;
        }).join('')}
                    ${areaMacros.length === 0 ? '<div class="p-4 text-tertiary" style="font-size:0.8rem">Nenhum macroprocesso nesta área</div>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

function getStageColor(stage) {
    const colors = {
        'inbox': '#cbd5e1', // Fora de Escopo
        'designing': '#93c5fd', // Desenho
        'deploying': '#3b82f6', // Implantação
        'stabilizing': '#a855f7', // Estabilização
        'stable': '#6366f1' // Estabilizado
    };
    return colors[stage] || '#cbd5e1';
}

function getPerfColor(perf) {
    const colors = {
        'critical': '#ef4444',
        'below': '#f59e0b',
        'satisfactory': '#10b981'
    };
    return colors[perf] || '#f1f5f9';
}

function renderTables() {
    // Areas
    const listAreas = document.getElementById('listAreas');
    if (listAreas) {
        listAreas.innerHTML = state.areas.map(a => `
            <tr>
                <td>
                    <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">
                        <span style="color: ${a.color || 'var(--primary)'}; opacity: 0.8;">${a.code || 'S/C'}</span> - ${a.name}
                    </div>
                </td>
                <td>
                    <div style="display: flex; gap: 4px;">
                        <button class="btn btn-secondary btn-sm" onclick="editArea(${a.id})">Editar</button>
                        <button class="btn btn-icon btn-sm text-danger" onclick="deleteArea(${a.id})">🗑️</button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    // Macros
    const listMacros = document.getElementById('listMacros');
    if (listMacros) {
        listMacros.innerHTML = state.macros.map(m => {
            return `
                <tr>
                    <td>
                        <div style="font-weight: 600; font-size: 0.9rem;">
                            <span style="color: var(--text-tertiary);">${m.code || 'S/C'}</span> - ${m.name}
                        </div>
                    </td>
                    <td style="font-size: 0.85rem; color: var(--text-secondary);">${m.owner || '-'}</td>
                    <td>
                        <div style="display: flex; gap: 4px;">
                            <button class="btn btn-secondary btn-sm" onclick="editMacro(${m.id})">Editar</button>
                            <button class="btn btn-icon btn-sm text-danger" onclick="deleteMacro(${m.id})">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Processes
    const listProcesses = document.getElementById('listProcesses');
    if (listProcesses) {
        listProcesses.innerHTML = state.processes.map(p => {
            return `
                <tr>
                    <td>
                        <div style="font-weight: 600; font-size: 0.9rem;">
                            <span style="color: var(--text-tertiary);">${p.code || 'S/C'}</span> - ${p.name}
                        </div>
                    </td>
                    <td style="font-size: 0.85rem; color: var(--text-secondary);">${p.responsible || '-'}</td>
                    <td>
                        <div style="display: flex; gap: 4px;">
                            <button class="btn btn-secondary btn-sm" onclick="editProcess(${p.id})">Editar</button>
                            <button class="btn btn-icon btn-sm text-danger" onclick="deleteProcess(${p.id})">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }
}

async function populateSelects() {
    const sMacroArea = document.getElementById('selectMacroArea');
    const sMacroOwner = document.getElementById('selectMacroOwner');
    const sProcessMacro = document.getElementById('selectProcessMacro');
    const sProcessResponsible = document.getElementById('selectProcessResponsible');

    if (sMacroArea) {
        sMacroArea.innerHTML = '<option value="">Selecione a área...</option>' +
            state.areas.map(a => `<option value="${a.id}">${a.code ? a.code + ' - ' : ''}${a.name}</option>`).join('');
    }

    if (sProcessMacro) {
        sProcessMacro.innerHTML = '<option value="">Selecione o macro...</option>' +
            state.macros.map(m => `<option value="${m.id}">${m.code ? m.code + ' - ' : ''}${m.name}</option>`).join('');
    }

    if (sMacroOwner || sProcessResponsible) {
        try {
            const res = await fetch(`/api/dashboard/filter-options?company_id=${state.companyId || ''}`).then(r => r.json());
            const employees = Array.isArray(res.employees) ? res.employees : [];
            state.employees = employees;

            if (sMacroOwner) {
                const current = sMacroOwner.value;
                sMacroOwner.innerHTML = buildEmployeeOptions(employees, 'Selecione um colaborador...');
                if (current) sMacroOwner.value = current;
            }

            if (sProcessResponsible) {
                const current = sProcessResponsible.value;
                sProcessResponsible.innerHTML = buildEmployeeOptions(employees, 'Selecione um colaborador...');
                if (current) sProcessResponsible.value = current;
            }
        } catch (e) {
            console.error("Error loading employees for selects:", e);
        }
    }
}

// Form Handlers
function setupFormListeners() {
    document.getElementById('formArea')?.addEventListener('submit', (e) => handleFormSubmit(e, '/api/process-areas'));
    document.getElementById('formMacro')?.addEventListener('submit', (e) => handleFormSubmit(e, '/api/macro-processes'));
    document.getElementById('formProcess')?.addEventListener('submit', (e) => handleFormSubmit(e, '/api/processes'));

    // Fix for Reset buttons to clear hidden ID
    document.querySelectorAll('button[type="reset"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const form = e.target.closest('form');
            if (form) {
                const idInput = form.querySelector('input[name="id"]');
                if (idInput) idInput.value = '';
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    const originalText = submitBtn.textContent.includes('Atualizar') ? 'Salvar' : submitBtn.textContent;
                    submitBtn.textContent = originalText;
                }
            }
        });
    });
}

async function handleFormSubmit(e, endpoint) {
    e.preventDefault();
    const form = e.target;

    if (!state.companyId || state.companyId === 'null') {
        console.warn("Company ID not found in JS state. Proceeding and letting backend attempt session fallback.");
    }

    const formData = new FormData(form);
    const rawData = Object.fromEntries(formData.entries());
    const allowedFields = FORM_ALLOWED_FIELDS[form.id] || [];
    const data = Object.fromEntries(
        Object.entries(rawData).filter(([key]) => allowedFields.includes(key))
    );

    // Only send company_id if it's valid, otherwise let backend fetch from session
    if (state.companyId && state.companyId !== 'null' && state.companyId !== 'undefined') {
        data.company_id = state.companyId;
    }

    // Convert numeric fields to integers
    if (data.order_index) data.order_index = parseInt(data.order_index, 10);
    // For Area, code is currently used as the sequence (like in app31)
    if (form.id === 'formArea' && data.code) {
        data.order_index = parseInt(data.code, 10);
    }
    if (data.area_id) data.area_id = parseInt(data.area_id, 10);
    if (data.macro_id) data.macro_id = parseInt(data.macro_id, 10);

    const id = data.id;
    if (!id) delete data.id;

    const method = id ? 'PUT' : 'POST';
    const url = id ? `${endpoint}/${id}` : endpoint;

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            form.reset();
            const idInput = form.querySelector('input[name="id"]');
            if (idInput) idInput.value = '';

            // Revert button text
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const formId = form.getAttribute('id') || '';
                const type = formId.replace('form', '').toLowerCase();
                submitBtn.textContent = `Salvar ${type.charAt(0).toUpperCase() + type.slice(1)}`;
            }

            await initArchitecture();
        } else {
            const err = await res.json().catch(() => ({ error: "Erro desconhecido no servidor" }));
            alert("Erro: " + JSON.stringify(err.errors || err.error || err));
        }
    } catch (e) {
        console.error(e);
        alert("Erro técnico: Não foi possível processar a requisição. Verifique o console ou a conexão.");
    }
}

// Edits
function editArea(id) {
    const item = state.areas.find(a => a.id === id);
    const form = document.getElementById('formArea');

    // Extract sequence from code (e.g., "AO.C.1" -> "1")
    let sequenceNumber = '';
    if (item.code) {
        const parts = item.code.split('.');
        sequenceNumber = parts[parts.length - 1] || '';
    } else {
        sequenceNumber = item.order_index || '';
    }

    form.querySelector('[name="id"]').value = item.id;
    form.name.value = item.name || '';
    form.code.value = sequenceNumber;
    form.color.value = item.color || '#3b82f6';
    form.description.value = item.description || '';

    form.querySelector('button[type="submit"]').textContent = 'Atualizar Área';
    form.scrollIntoView({ behavior: 'smooth' });
}

function editMacro(id) {
    const item = state.macros.find(m => m.id === id);
    const form = document.getElementById('formMacro');

    // Extract sequence from code (e.g., "AO.C.1.1" -> "1")
    let sequenceNumber = '';
    if (item.code) {
        const parts = item.code.split('.');
        sequenceNumber = parts[parts.length - 1] || '';
    } else {
        sequenceNumber = item.order_index || '';
    }

    form.querySelector('[name="id"]').value = item.id;
    form.area_id.value = item.area_id || '';
    form.name.value = item.name || '';
    form.order_index.value = sequenceNumber;
    form.owner.value = item.owner || '';
    form.description.value = item.description || '';

    form.querySelector('button[type="submit"]').textContent = 'Atualizar Macro';
    form.scrollIntoView({ behavior: 'smooth' });
}

function editProcess(id) {
    const item = state.processes.find(p => p.id === id);
    const form = document.getElementById('formProcess');

    // Extract sequence from code (e.g., "AO.C.1.1.1" -> "1")
    let sequenceNumber = '';
    if (item.code) {
        const parts = item.code.split('.');
        sequenceNumber = parts[parts.length - 1] || '';
    } else {
        sequenceNumber = item.order_index || '';
    }

    form.querySelector('[name="id"]').value = item.id;
    form.macro_id.value = item.macro_id || '';
    form.name.value = item.name || '';
    form.order_index.value = sequenceNumber;
    form.responsible.value = item.responsible || '';
    form.performance_level.value = item.performance_level || '';
    form.description.value = item.description || '';

    form.querySelector('button[type="submit"]').textContent = 'Atualizar Processo';
    form.scrollIntoView({ behavior: 'smooth' });
}

// Deletes
async function parseDeleteResponse(res) {
    try {
        return await res.json();
    } catch (e) {
        return null;
    }
}

function extractDeleteErrorMessage(payload) {
    if (!payload) return 'Não foi possível excluir o registro.';
    if (typeof payload.error === 'string' && payload.error.trim()) return payload.error;
    if (typeof payload.message === 'string' && payload.message.trim()) return payload.message;
    if (payload.errors) return JSON.stringify(payload.errors);
    return 'Não foi possível excluir o registro.';
}

function notifyDeleteError(message) {
    if (window.showMessage) {
        window.showMessage(message, 'error');
        return;
    }
    alert(message);
}

async function requestDelete(url, confirmMessage) {
    if (!confirm(confirmMessage)) return false;

    try {
        const res = await fetch(url, { method: 'DELETE' });
        const payload = await parseDeleteResponse(res);

        if (!res.ok) {
            notifyDeleteError(extractDeleteErrorMessage(payload));
            return false;
        }

        if (payload?.message && window.showMessage) {
            window.showMessage(payload.message, 'success');
        }
        return true;
    } catch (e) {
        console.error('Erro ao excluir registro:', e);
        notifyDeleteError('Erro técnico: Não foi possível concluir a exclusão.');
        return false;
    }
}

async function deleteArea(id) {
    const deleted = await requestDelete(`/api/process-areas/${id}`, "Excluir área e todos os macros/processos vinculados?");
    if (!deleted) return;
    await initArchitecture();
}

async function deleteMacro(id) {
    const deleted = await requestDelete(`/api/macro-processes/${id}`, "Excluir macroprocesso e seus processos?");
    if (!deleted) return;
    await initArchitecture();
}

async function deleteProcess(id) {
    const deleted = await requestDelete(`/api/processes/${id}`, "Excluir este processo?");
    if (!deleted) return;
    await initArchitecture();
}

// Actions
function openMP2() {
    window.open(`/process-map/compact?company_id=${state.companyId}`, '_blank');
}

// Helpers
function getStageIcon(stage) {
    const icons = { 'inbox': '📥', 'designing': '📐', 'deploying': '🚀', 'stabilizing': '⚖️', 'stable': '✅' };
    return icons[stage] || '🔄';
}
