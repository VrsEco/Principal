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
    viewType: localStorage.getItem('arch_view_type') || 'classic',
    macroSipoc: {
        selectedMacroId: null,
        bundles: {}
    }
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
    await populateSelects();
    await initializeMacroSipoc();
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
    if (tabId === 'macro-sipoc') renderMacroSipoc();

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
    const areaById = new Map(state.areas.map(area => [Number(area.id), area]));

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

    // Books dos macroprocessos
    const listMacroBooks = document.getElementById('listMacroBooks');
    if (listMacroBooks) {
        const orderedMacros = [...state.macros].sort((left, right) => {
            const leftArea = areaById.get(Number(left.area_id));
            const rightArea = areaById.get(Number(right.area_id));
            const leftAreaOrder = Number(leftArea?.order_index || 0);
            const rightAreaOrder = Number(rightArea?.order_index || 0);
            if (leftAreaOrder !== rightAreaOrder) return leftAreaOrder - rightAreaOrder;
            return String(left.name || '').localeCompare(String(right.name || ''), 'pt-BR');
        });

        if (!orderedMacros.length) {
            listMacroBooks.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align:center; color: var(--text-tertiary);">
                        Nenhum macroprocesso cadastrado para gerar books.
                    </td>
                </tr>
            `;
        } else {
            listMacroBooks.innerHTML = orderedMacros.map(macro => {
                const area = areaById.get(Number(macro.area_id));
                const processCount = state.processes.filter(process => Number(process.macro_id) === Number(macro.id)).length;
                const areaLabel = area
                    ? `${area.code ? `${area.code} - ` : ''}${area.name}`
                    : 'Área não vinculada';

                return `
                    <tr>
                        <td>${escapeHtml(areaLabel)}</td>
                        <td>
                            <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">
                                <span style="color: var(--text-tertiary);">${escapeHtml(macro.code || 'S/C')}</span> - ${escapeHtml(macro.name)}
                            </div>
                            ${macro.description ? `<div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.2rem;">${escapeHtml(macro.description)}</div>` : ''}
                        </td>
                        <td style="font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(macro.owner || '-')}</td>
                        <td>${processCount}</td>
                        <td>
                            <div style="display:flex; gap: 0.5rem; flex-wrap: wrap;">
                                <a class="btn btn-primary btn-sm" href="/macro-processes/${macro.id}/book">Abrir Book</a>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
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

async function initializeMacroSipoc() {
    const selector = document.getElementById('macroSipocSelector');
    if (!selector) return;
    if (!state.macros.length) {
        state.macroSipoc.selectedMacroId = null;
        renderMacroSipoc();
        return;
    }
    if (!state.macroSipoc.selectedMacroId) {
        state.macroSipoc.selectedMacroId = String(state.macros[0].id);
    }
    selector.value = String(state.macroSipoc.selectedMacroId);
    await fetchMacroSipoc(state.macroSipoc.selectedMacroId);
    renderMacroSipoc();
}

async function fetchMacroSipoc(macroId) {
    if (!macroId) return null;
    const res = await fetch(`/api/macro-processes/${macroId}/sipoc`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao carregar SIPOC do macroprocesso.');
    state.macroSipoc.bundles[String(macroId)] = data;
    return data;
}

function getCurrentMacroSipocBundle() {
    const macroId = String(state.macroSipoc.selectedMacroId || '');
    return state.macroSipoc.bundles[macroId] || null;
}

function getCurrentMacroSipocSnapshot() {
    return getCurrentMacroSipocBundle()?.current_snapshot || null;
}

function renderMacroSipoc() {
    const workspace = document.getElementById('macroSipocWorkspace');
    if (!workspace) return;

    if (!state.macros.length) {
        workspace.innerHTML = `<div class="sipoc-empty-state">Cadastre ao menos um macroprocesso para começar o SIPOC executivo da cadeia.</div>`;
        return;
    }

    const macroId = String(state.macroSipoc.selectedMacroId || '');
    const macro = state.macros.find(item => String(item.id) === macroId);
    const bundle = getCurrentMacroSipocBundle();
    const snapshot = bundle?.current_snapshot || null;

    if (!macro) {
        workspace.innerHTML = `<div class="sipoc-empty-state">Selecione um macroprocesso para visualizar ou modelar o SIPOC.</div>`;
        return;
    }

    if (!snapshot) {
        workspace.innerHTML = `
            <div class="sipoc-empty-state">
                <strong>${escapeHtml(macro.name)}</strong><br>
                Este macroprocesso ainda não possui SIPOC. Crie um rascunho para iniciar a modelagem executiva.
            </div>
        `;
        return;
    }

    const laneNames = {
        supplier: 'Suppliers · Fornecedores',
        input: 'Inputs · Entradas',
        process: 'Process · Processos filhos',
        output: 'Outputs · Saídas',
        customer: 'Customers · Clientes'
    };
    const laneHelp = {
        supplier: 'Quem fornece insumos, aprovações, dados ou requisitos para a cadeia começar.',
        input: 'Entradas executivas, documentos, parâmetros e demandas que abastecem o macroprocesso.',
        process: 'Entre 3 e 7 processos filhos ou grandes etapas da cadeia. Aqui o SIPOC enquadra a arquitetura ponta a ponta.',
        output: 'Resultados, entregas e artefatos gerados pela cadeia do macroprocesso.',
        customer: 'Quem recebe, depende ou consome as saídas geradas pela cadeia.'
    };

    workspace.innerHTML = `
        <div class="sipoc-meta-grid">
            ${renderSipocMetaCard('Status', `${snapshot.status || 'draft'} · v${snapshot.version || 1}`, false)}
            ${renderSipocMetaCard('Objetivo', snapshot.objective || '', true, 'Descreva o objetivo executivo do macroprocesso...', 'macroSipocObjective')}
            ${renderSipocMetaCard('Início', snapshot.start_boundary || '', true, 'Marco inicial da cadeia...', 'macroSipocStart')}
            ${renderSipocMetaCard('Fim', snapshot.end_boundary || '', true, 'Marco final da cadeia...', 'macroSipocEnd')}
        </div>
        <div class="sipoc-meta-grid">
            ${renderSipocMetaCard('Evento disparador', snapshot.trigger_event || '', true, 'Gatilho de início do macroprocesso...', 'macroSipocTrigger')}
            ${renderSipocMetaCard('Requisitos do cliente', snapshot.customer_requirements || '', true, 'Critérios e expectativas principais...', 'macroSipocCustomerReq')}
            ${renderSipocMetaCard('Restrições', snapshot.constraints_notes || '', true, 'Restrições, políticas e limites...', 'macroSipocConstraints')}
            ${renderSipocMetaCard('Medidas / indicadores', snapshot.measures_notes || '', true, 'KPIs e medidas executivas...', 'macroSipocMeasures')}
        </div>
        <div class="sipoc-lanes-grid">
            ${Object.keys(laneNames).map(lane => renderSipocLane(snapshot, lane, laneNames[lane], laneHelp[lane], true)).join('')}
        </div>
        <div class="sipoc-support-grid">
            <div class="sipoc-support-card">
                <label>Requisitos regulatórios aplicáveis</label>
                <h3>Compliance do macroprocesso</h3>
                <div class="sipoc-support-actions">
                    <button class="btn btn-secondary btn-sm" type="button" onclick="createMacroSipocRegulatoryItem()">Novo requisito regulatório</button>
                </div>
                ${renderSipocRegulatoryTable(snapshot, true)}
            </div>
            <div class="sipoc-support-card">
                <label>Complementos executivos</label>
                <h3>Observações e riscos</h3>
                <textarea id="macroSipocRisks" class="form-control" rows="5" placeholder="Riscos executivos, handoffs sensíveis e pontos de atenção...">${escapeHtml(snapshot.risks_notes || '')}</textarea>
                <textarea id="macroSipocNotes" class="form-control" rows="5" placeholder="Observações complementares do macroprocesso...">${escapeHtml(snapshot.notes || '')}</textarea>
            </div>
        </div>
        ${snapshot.status === 'draft' && snapshot.publication_errors?.length ? `
            <div class="alert alert-warning" style="margin-top: 1rem;">
                <strong>Pendências para publicação:</strong>
                <ul style="margin: 0.5rem 0 0 1rem;">
                    ${snapshot.publication_errors.map(error => `<li>${escapeHtml(error)}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;
}

function renderSipocMetaCard(label, value, editable = false, placeholder = '', fieldId = '') {
    if (!editable) {
        return `<div class="sipoc-meta-card"><label>${escapeHtml(label)}</label><div>${escapeHtml(value || 'Não informado')}</div></div>`;
    }
    return `
        <div class="sipoc-meta-card">
            <label>${escapeHtml(label)}</label>
            <textarea id="${fieldId}" class="form-control" rows="3" placeholder="${escapeHtml(placeholder)}">${escapeHtml(value || '')}</textarea>
        </div>
    `;
}

function renderSipocLane(snapshot, lane, title, help, isMacro = false) {
    const items = snapshot.items?.[lane] || [];
    return `
        <div class="sipoc-lane">
            <div class="sipoc-lane-head">
                <strong>${escapeHtml(title)}</strong>
                <small>${escapeHtml(help)}</small>
            </div>
            <div class="sipoc-lane-list">
                ${items.length ? items.map(item => `
                    <div class="sipoc-item-card">
                        ${item.is_critical ? '<span class="sipoc-badge-critical">Crítico</span>' : ''}
                        <strong>${escapeHtml(item.title)}</strong>
                        <p>${escapeHtml(item.description || 'Sem descrição complementar.')}</p>
                        <div class="sipoc-item-card__actions">
                            <button class="btn btn-secondary btn-sm" type="button" onclick="${isMacro ? `editMacroSipocItem(${snapshot.id}, ${item.id})` : ''}">Editar</button>
                            <button class="btn btn-secondary btn-sm" type="button" onclick="${isMacro ? `deleteMacroSipocItem(${snapshot.id}, ${item.id})` : ''}">Remover</button>
                        </div>
                    </div>
                `).join('') : '<div class="sipoc-inline-muted">Nenhum item cadastrado.</div>'}
            </div>
            <div class="sipoc-lane-create">
                <button class="btn btn-primary btn-sm" type="button" onclick="${isMacro ? `createMacroSipocItem('${lane}')` : ''}">Adicionar item</button>
            </div>
        </div>
    `;
}

function renderSipocRegulatoryTable(snapshot, isMacro = false) {
    const items = snapshot.regulatory_items || [];
    if (!items.length) {
        return `<div class="sipoc-inline-muted">Nenhum requisito regulatório registrado.</div>`;
    }
    return `
        <table class="sipoc-regulatory-table">
            <thead>
                <tr>
                    <th>Domínio</th>
                    <th>Norma / Regra</th>
                    <th>Órgão</th>
                    <th>Escopo</th>
                    <th>Criticidade</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
                ${items.map(item => `
                    <tr>
                        <td>${escapeHtml(item.regulatory_domain || '-')}</td>
                        <td><strong>${escapeHtml(item.regulatory_code || '')}</strong>${item.regulatory_code ? '<br>' : ''}${escapeHtml(item.regulatory_name || '-')}</td>
                        <td>${escapeHtml(item.regulator_entity || '-')}</td>
                        <td>${item.sipoc_item_id ? 'Processo filho vinculado' : 'Macroprocesso'}</td>
                        <td>${escapeHtml(item.risk_level || 'medium')}</td>
                        <td>
                            <div class="sipoc-item-card__actions">
                                <button class="btn btn-secondary btn-sm" type="button" onclick="${isMacro ? `editMacroSipocRegulatoryItem(${snapshot.id}, ${item.id})` : ''}">Editar</button>
                                <button class="btn btn-secondary btn-sm" type="button" onclick="${isMacro ? `deleteMacroSipocRegulatoryItem(${snapshot.id}, ${item.id})` : ''}">Remover</button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
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

    const macroSipocSelector = document.getElementById('macroSipocSelector');
    if (macroSipocSelector) {
        const current = macroSipocSelector.value || state.macroSipoc.selectedMacroId || '';
        macroSipocSelector.innerHTML = '<option value="">Selecione um macroprocesso...</option>' +
            state.macros.map(m => `<option value="${m.id}">${m.code ? m.code + ' - ' : ''}${escapeHtml(m.name)}</option>`).join('');
        if (current) macroSipocSelector.value = String(current);
        macroSipocSelector.onchange = async (event) => {
            state.macroSipoc.selectedMacroId = event.target.value || null;
            if (state.macroSipoc.selectedMacroId) {
                await fetchMacroSipoc(state.macroSipoc.selectedMacroId);
            }
            renderMacroSipoc();
        };
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
    const form = e.currentTarget || e.target;
    const formId = form.getAttribute('id') || '';

    if (!state.companyId || state.companyId === 'null') {
        console.warn("Company ID not found in JS state. Proceeding and letting backend attempt session fallback.");
    }

    const formData = new FormData(form);
    const rawData = Object.fromEntries(formData.entries());
    const allowedFields = FORM_ALLOWED_FIELDS[formId] || [];
    const data = Object.fromEntries(
        Object.entries(rawData).filter(([key]) => allowedFields.includes(key))
    );

    const recordId = (form.querySelector('input[name="id"]')?.value || '').trim();
    if (!recordId) {
        delete data.id;
    } else {
        data.id = recordId;
    }

    const method = recordId ? 'PUT' : 'POST';
    const url = recordId ? `${endpoint}/${recordId}` : endpoint;

    // Only send company_id on create; on update let backend trust the record company
    if (method === 'POST' && state.companyId && state.companyId !== 'null' && state.companyId !== 'undefined') {
        data.company_id = state.companyId;
    } else {
        delete data.company_id;
    }

    // Convert numeric fields to integers
    if (data.order_index) data.order_index = parseInt(data.order_index, 10);
    // For Area, code is currently used as the sequence (like in app31)
    if (formId === 'formArea' && data.code) {
        data.order_index = parseInt(data.code, 10);
    }
    if (data.area_id) data.area_id = parseInt(data.area_id, 10);
    if (data.macro_id) data.macro_id = parseInt(data.macro_id, 10);

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

function getMacroSipocMetaPayload() {
    return {
        objective: document.getElementById('macroSipocObjective')?.value?.trim() || '',
        start_boundary: document.getElementById('macroSipocStart')?.value?.trim() || '',
        end_boundary: document.getElementById('macroSipocEnd')?.value?.trim() || '',
        trigger_event: document.getElementById('macroSipocTrigger')?.value?.trim() || '',
        customer_requirements: document.getElementById('macroSipocCustomerReq')?.value?.trim() || '',
        constraints_notes: document.getElementById('macroSipocConstraints')?.value?.trim() || '',
        measures_notes: document.getElementById('macroSipocMeasures')?.value?.trim() || '',
        risks_notes: document.getElementById('macroSipocRisks')?.value?.trim() || '',
        notes: document.getElementById('macroSipocNotes')?.value?.trim() || ''
    };
}

async function createMacroSipocDraft() {
    const macroId = state.macroSipoc.selectedMacroId;
    if (!macroId) {
        alert('Selecione um macroprocesso antes de criar o SIPOC.');
        return;
    }
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao criar rascunho SIPOC do macroprocesso.');
        state.macroSipoc.bundles[String(macroId)] = {
            ...(state.macroSipoc.bundles[String(macroId)] || {}),
            current_snapshot: data,
            draft_snapshot: data,
            has_sipoc: true
        };
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao criar SIPOC do macroprocesso.');
    }
}

async function saveMacroSipocMeta() {
    const macroId = state.macroSipoc.selectedMacroId;
    const snapshot = getCurrentMacroSipocSnapshot();
    if (!macroId || !snapshot) {
        alert('Crie um rascunho SIPOC antes de salvar.');
        return false;
    }
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${snapshot.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(getMacroSipocMetaPayload())
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao salvar SIPOC do macroprocesso.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
        return true;
    } catch (error) {
        alert(error.message || 'Erro ao salvar SIPOC do macroprocesso.');
        return false;
    }
}

async function createMacroSipocItem(lane) {
    const macroId = state.macroSipoc.selectedMacroId;
    const snapshot = getCurrentMacroSipocSnapshot();
    if (!macroId || !snapshot) {
        alert('Crie um rascunho SIPOC antes de adicionar itens.');
        return;
    }
    const title = prompt('Título do item SIPOC:', '');
    if (!title) return;
    const description = prompt('Descrição complementar do item:', '') || '';
    const isCritical = confirm('Este item é crítico?');
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${snapshot.id}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lane, title, description, is_critical: isCritical })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao criar item SIPOC.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao criar item SIPOC.');
    }
}

function findMacroSipocItemById(itemId) {
    const items = getCurrentMacroSipocSnapshot()?.items || {};
    for (const lane of Object.keys(items)) {
        const found = (items[lane] || []).find(entry => Number(entry.id) === Number(itemId));
        if (found) return found;
    }
    return null;
}

async function editMacroSipocItem(sipocId, itemId) {
    const macroId = state.macroSipoc.selectedMacroId;
    const item = findMacroSipocItemById(itemId);
    if (!macroId || !item) return;
    const title = prompt('Título do item SIPOC:', item.title || '');
    if (!title) return;
    const description = prompt('Descrição complementar do item:', item.description || '') || '';
    const isCritical = confirm('Marcar item como crítico?\n\nOK = crítico | Cancelar = não crítico');
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${sipocId}/items/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, lane: item.lane, order_index: item.order_index, is_critical: isCritical })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao atualizar item SIPOC.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao atualizar item SIPOC.');
    }
}

async function deleteMacroSipocItem(sipocId, itemId) {
    const macroId = state.macroSipoc.selectedMacroId;
    if (!macroId || !confirm('Deseja remover este item SIPOC?')) return;
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${sipocId}/items/${itemId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao remover item SIPOC.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao remover item SIPOC.');
    }
}

async function createMacroSipocRegulatoryItem() {
    const macroId = state.macroSipoc.selectedMacroId;
    const snapshot = getCurrentMacroSipocSnapshot();
    if (!macroId || !snapshot) {
        alert('Crie um rascunho SIPOC antes de adicionar requisitos regulatórios.');
        return;
    }
    const domain = prompt('Domínio regulatório (ex.: Trabalhista, Fiscal, ANP, ANM):', '');
    if (!domain) return;
    const code = prompt('Código/lei/norma:', '') || '';
    const name = prompt('Nome curto da norma ou obrigação:', code || '');
    if (!name) return;
    const entity = prompt('Órgão regulador / entidade:', '') || '';
    const summary = prompt('Resumo da obrigação e impacto operacional:', '') || '';
    const risk = prompt('Criticidade (low, medium, high, critical):', 'medium') || 'medium';
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${snapshot.id}/regulatory-items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                regulatory_domain: domain,
                regulatory_code: code,
                regulatory_name: name,
                regulator_entity: entity,
                requirement_summary: summary,
                risk_level: risk
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao adicionar requisito regulatório.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao adicionar requisito regulatório.');
    }
}

async function editMacroSipocRegulatoryItem(sipocId, regulatoryItemId) {
    const macroId = state.macroSipoc.selectedMacroId;
    const item = (getCurrentMacroSipocSnapshot()?.regulatory_items || []).find(entry => Number(entry.id) === Number(regulatoryItemId));
    if (!macroId || !item) return;
    const domain = prompt('Domínio regulatório:', item.regulatory_domain || '');
    if (domain === null || !domain) return;
    const code = prompt('Código/lei/norma:', item.regulatory_code || '') || '';
    const name = prompt('Nome curto da norma ou obrigação:', item.regulatory_name || '');
    if (!name) return;
    const entity = prompt('Órgão regulador / entidade:', item.regulator_entity || '') || '';
    const summary = prompt('Resumo da obrigação e impacto operacional:', item.requirement_summary || '') || '';
    const risk = prompt('Criticidade (low, medium, high, critical):', item.risk_level || 'medium') || 'medium';
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${sipocId}/regulatory-items/${regulatoryItemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                regulatory_domain: domain,
                regulatory_code: code,
                regulatory_name: name,
                regulator_entity: entity,
                requirement_summary: summary,
                risk_level: risk
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao atualizar requisito regulatório.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao atualizar requisito regulatório.');
    }
}

async function deleteMacroSipocRegulatoryItem(sipocId, regulatoryItemId) {
    const macroId = state.macroSipoc.selectedMacroId;
    if (!macroId || !confirm('Deseja remover este requisito regulatório?')) return;
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${sipocId}/regulatory-items/${regulatoryItemId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao remover requisito regulatório.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
    } catch (error) {
        alert(error.message || 'Erro ao remover requisito regulatório.');
    }
}

async function publishMacroSipoc() {
    const macroId = state.macroSipoc.selectedMacroId;
    const snapshot = getCurrentMacroSipocSnapshot();
    if (!macroId || !snapshot) {
        alert('Crie um rascunho SIPOC antes de publicar.');
        return;
    }
    const saved = await saveMacroSipocMeta();
    if (!saved) return;
    try {
        const res = await fetch(`/api/macro-processes/${macroId}/sipoc/${snapshot.id}/publish`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Falha ao publicar SIPOC do macroprocesso.');
        await fetchMacroSipoc(macroId);
        renderMacroSipoc();
        alert('SIPOC do macroprocesso publicado com sucesso.');
    } catch (error) {
        alert(error.message || 'Erro ao publicar SIPOC do macroprocesso.');
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
