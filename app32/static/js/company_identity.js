(() => {
    'use strict';

    const shell = document.querySelector('.identity-shell');
    if (!shell) return;

    const companyId = Number(shell.dataset.companyId || 0);
    const canEdit = shell.dataset.canEdit === 'true';
    const state = {
        summary: null,
        tree: [],
        currentTree: [],
        rolesById: new Map(),
        treeNodesById: new Map(),
        collapsedIds: new Set(),
        layoutMode: localStorage.getItem(`gv:org-chart:${companyId}:layout`) || 'auto',
        layoutOverrides: new Map(),
        selectedRoleId: null,
        scale: 1,
        search: '',
        department: '',
    };

    try {
        const savedOverrides = JSON.parse(localStorage.getItem(`gv:org-chart:${companyId}:layout-overrides`) || '{}');
        state.layoutOverrides = new Map(Object.entries(savedOverrides).map(([id, mode]) => [Number(id), mode]));
    } catch (_) {
        state.layoutOverrides = new Map();
    }

    const byId = (id) => document.getElementById(id);

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function normalize(value) {
        return String(value ?? '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .trim()
            .toLowerCase();
    }

    function safeColor(value) {
        const color = String(value || '').trim();
        return /^#[0-9a-f]{6}$/i.test(color) ? color.toUpperCase() : '#D9ECFF';
    }

    function depthClass(depth) {
        return `identity-node--depth-${Math.min(Math.max(Number(depth) || 0, 0), 3)}`;
    }

    function formatDateTime(value) {
        if (!value) return '—';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '—';
        return new Intl.DateTimeFormat('pt-BR', {
            dateStyle: 'short',
            timeStyle: 'short',
        }).format(date);
    }

    function formatReferenceDate(value = new Date()) {
        return new Intl.DateTimeFormat('pt-BR', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
        }).format(value);
    }

    function formatInstitutionalValues(value, detailed = false) {
        const raw = String(value || '').trim();
        if (!raw) return '';
        try {
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return raw;
            return parsed.map((item) => {
                const name = String(item?.name || item?.key || '').trim();
                const definition = String(item?.definition || '').trim();
                if (!name) return definition;
                return detailed && definition ? `${name} — ${definition}` : name;
            }).filter(Boolean).join(detailed ? '\n' : ' • ');
        } catch (_) {
            return raw;
        }
    }

    function renderReportTreeNode(node) {
        const children = node.children || [];
        return `<li>
            <article class="identity-report-role" style="--identity-report-role-color:${safeColor(node.color)}">
                <strong>${escapeHtml(node.title)}</strong>
                <small>${escapeHtml(node.department || 'Área não informada')}</small>
                <div><b>${node.headcount_planned || 0}</b> previstos <i></i> <b>${node.active_employee_count || 0}</b> efetivos</div>
            </article>
            ${children.length ? `<ul class="${shouldStackChildren(node) ? 'is-stacked' : ''}">${children.map((child) => renderReportTreeNode(child)).join('')}</ul>` : ''}
        </li>`;
    }

    function renderIdentityReport(summary) {
        const metrics = summary.metrics || {};
        byId('identityReportReferenceDate').textContent = formatReferenceDate();
        byId('identityReportUpdatedAt').textContent = formatDateTime(metrics.org_chart_updated_at);
        byId('identityReportMission').textContent = summary.company.mission || 'Não definida.';
        byId('identityReportVision').textContent = summary.company.vision || 'Não definida.';
        byId('identityReportValues').textContent = formatInstitutionalValues(summary.company.values) || 'Não definidos.';
        byId('identityReportRolesTotal').textContent = metrics.roles_total || 0;
        byId('identityReportEmployeesTotal').textContent = metrics.active_employees_total || 0;
        byId('identityReportOrgChart').innerHTML = state.tree.length
            ? `<div class="identity-report-tree"><ul>${state.tree.map((node) => renderReportTreeNode(node)).join('')}</ul></div>`
            : '<p>Nenhum cargo cadastrado para compor o organograma.</p>';
    }

    async function fetchJson(url, options = {}) {
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.body ? { 'Content-Type': 'application/json' } : {}),
            ...(options.headers || {}),
        };
        const response = await fetch(url, { ...options, headers });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.error || payload.message || `Falha na requisição (${response.status}).`);
        }
        return payload;
    }

    function activateTab(tabId) {
        document.querySelectorAll('.identity-tab-btn').forEach((button) => {
            const active = button.dataset.identityTab === tabId;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-selected', String(active));
        });
        document.querySelectorAll('.identity-tab-panel').forEach((panel) => {
            panel.classList.toggle('is-active', panel.dataset.identityPanel === tabId);
        });
        if (tabId) window.location.hash = tabId;
        if (tabId === 'organograma') {
            requestAnimationFrame(() => requestAnimationFrame(() => window.IdentityOrgChart?.fit()));
        }
    }

    function renderSummary(summary) {
        byId('metricRoles').textContent = summary.metrics.roles_total || 0;
        byId('metricEmployees').textContent = summary.metrics.active_employees_total || 0;
        byId('metricDepartments').textContent = summary.metrics.departments_total || 0;
        byId('metricHeadcount').textContent = summary.metrics.planned_headcount_total || 0;
        byId('identityChartTotalPlanned').textContent = summary.roles.reduce((total, role) => total + (Number(role.headcount_planned) || 0), 0);
        byId('identityChartTotalEffective').textContent = summary.roles.reduce((total, role) => total + (Number(role.active_employee_count) || 0), 0);
        byId('identityChartCreatedAt').textContent = formatDateTime(summary.metrics.org_chart_created_at);
        byId('identityChartUpdatedAt').textContent = formatDateTime(summary.metrics.org_chart_updated_at);
        byId('identityMission').textContent = summary.company.mission || 'Ainda não definida.';
        byId('identityVision').textContent = summary.company.vision || 'Ainda não definida.';
        byId('identityValues').textContent = formatInstitutionalValues(summary.company.values, true) || 'Ainda não definidos.';
        byId('rolesTableCount').textContent = `${summary.roles.length} registros`;
        byId('employeesTableCount').textContent = `${summary.employees.length} registros`;
        renderIdentityReport(summary);

        byId('identityRolesBody').innerHTML = summary.roles.length ? summary.roles.map((role) => `
            <tr>
                <td><strong>${escapeHtml(role.title)}</strong><div class="text-secondary">${role.vacancy_count || 0} vagas livres</div></td>
                <td>${escapeHtml(role.department || '—')}</td>
                <td>${role.active_employee_count || 0} ativos</td>
                <td>${role.headcount_planned || 0}</td>
            </tr>
        `).join('') : '<tr><td colspan="4" class="identity-empty-row">Nenhum cargo cadastrado.</td></tr>';

        byId('identityEmployeesBody').innerHTML = summary.employees.length ? summary.employees.map((employee) => `
            <tr>
                <td><strong>${escapeHtml(employee.name)}</strong><div class="text-secondary">${escapeHtml(employee.email || employee.phone || 'Sem contato')}</div></td>
                <td>${escapeHtml(employee.role_title || 'Sem cargo')}</td>
                <td>${escapeHtml(employee.role_department || employee.department || '—')}</td>
                <td>${escapeHtml(employee.status_label || 'Não informado')}</td>
            </tr>
        `).join('') : '<tr><td colspan="4" class="identity-empty-row">Nenhum colaborador cadastrado.</td></tr>';
    }

    function flattenTree(nodes, depth = 0, output = []) {
        (nodes || []).forEach((node) => {
            output.push({ ...node, depth });
            flattenTree(node.children, depth + 1, output);
        });
        return output;
    }

    function descendantsOf(roleId) {
        const descendants = new Set();
        const visit = (id) => {
            state.summary.roles
                .filter((role) => Number(role.parent_role_id) === Number(id))
                .forEach((role) => {
                    descendants.add(Number(role.id));
                    visit(role.id);
                });
        };
        visit(roleId);
        return descendants;
    }

    function roleMatches(node) {
        const query = normalize(state.search);
        const matchesQuery = !query || normalize(`${node.title} ${node.department}`).includes(query);
        const matchesDepartment = !state.department || node.department === state.department;
        return matchesQuery && matchesDepartment;
    }

    function hasOnlyTerminalChildren(node) {
        return Boolean(node?.children?.length) && node.children.every((child) => !child.children?.length);
    }

    function shouldStackChildren(node) {
        if (!hasOnlyTerminalChildren(node)) return false;
        const override = state.layoutOverrides.get(Number(node.id));
        if (override === 'stacked') return true;
        if (override === 'horizontal') return false;
        if (state.layoutMode === 'horizontal') return false;
        if (state.layoutMode === 'terminal-stacked') return true;
        return node.children.length >= 3;
    }

    function persistLayoutPreferences() {
        localStorage.setItem(`gv:org-chart:${companyId}:layout`, state.layoutMode);
        localStorage.setItem(
            `gv:org-chart:${companyId}:layout-overrides`,
            JSON.stringify(Object.fromEntries(state.layoutOverrides)),
        );
    }

    function filteredTree(nodes) {
        if (!state.search && !state.department) return nodes;
        return (nodes || []).reduce((result, node) => {
            const children = filteredTree(node.children || []);
            const matches = roleMatches(node);
            if (matches || children.length) result.push({ ...node, children, _matched: matches });
            return result;
        }, []);
    }

    function renderTreeNode(node, depth = 0) {
        const hasChildren = Boolean(node.children?.length);
        const isCollapsed = state.collapsedIds.has(Number(node.id));
        const selected = Number(node.id) === Number(state.selectedRoleId);
        const contextClass = node._matched === false ? ' is-filter-context' : '';
        return `
            <li>
                <div class="identity-node-wrap">
                    <article class="identity-node ${depthClass(depth)}${selected ? ' is-selected' : ''}${contextClass}" data-node-id="${node.id}" data-depth="${depth}" style="--identity-node-color:${safeColor(node.color)}" tabindex="0" role="button" aria-label="Ver detalhes de ${escapeHtml(node.title)}">
                        <div class="identity-node__head">
                            <span class="identity-node__eyebrow">Cargo</span>
                            <span class="identity-node__title">${escapeHtml(node.title)}</span>
                            <span class="identity-node__department">${escapeHtml(node.department || 'Departamento não informado')}</span>
                        </div>
                        <div class="identity-node__body">
                            <div class="identity-node__metrics">
                                <div class="identity-node__metric"><span class="identity-node__metric-label">Previstos</span><span class="identity-node__metric-value">${node.headcount_planned || 0}</span></div>
                                <div class="identity-node__metric"><span class="identity-node__metric-label">Efetivos</span><span class="identity-node__metric-value">${node.active_employee_count || 0}</span></div>
                            </div>
                        </div>
                    </article>
                    ${hasChildren ? `<button type="button" class="identity-node__toggle" data-toggle-node="${node.id}" aria-label="${isCollapsed ? 'Expandir' : 'Recolher'} subordinados de ${escapeHtml(node.title)}" aria-expanded="${!isCollapsed}">${isCollapsed ? '+' : '−'}</button>` : ''}
                </div>
                ${hasChildren && !isCollapsed ? `<ul class="identity-tree-children${shouldStackChildren(node) ? ' is-stacked' : ''}">${node.children.map((child) => renderTreeNode(child, depth + 1)).join('')}</ul>` : ''}
            </li>`;
    }

    function bindTreeInteractions() {
        document.querySelectorAll('[data-node-id]').forEach((element) => {
            const select = () => selectChartRole(Number(element.dataset.nodeId));
            element.addEventListener('click', select);
            element.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    select();
                }
            });
        });
        document.querySelectorAll('[data-toggle-node]').forEach((button) => {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                const id = Number(button.dataset.toggleNode);
                state.collapsedIds.has(id) ? state.collapsedIds.delete(id) : state.collapsedIds.add(id);
                renderTree();
            });
        });
    }

    function renderTree() {
        const mount = byId('identityOrgChart');
        const tree = filteredTree(state.tree);
        state.currentTree = tree;
        if (!tree.length) {
            mount.innerHTML = '<div class="identity-org-chart__empty">Nenhum cargo encontrado com os filtros informados.</div>';
            return;
        }
        mount.innerHTML = `<div class="identity-org-chart__viewport"><div class="identity-org-chart__scale" id="identityOrgChartScale"><div class="identity-tree-shell" id="identityTreeShell"><ul>${tree.map(renderTreeNode).join('')}</ul></div></div></div>`;
        bindTreeInteractions();
        applyScale();
    }

    function applyScale() {
        const host = byId('identityOrgChartScale');
        const treeShell = byId('identityTreeShell');
        const viewport = host?.closest('.identity-org-chart__viewport');
        const mount = byId('identityOrgChart');
        if (!host || !treeShell) return;
        const naturalWidth = treeShell.scrollWidth;
        const naturalHeight = treeShell.scrollHeight;
        const scaledWidth = Math.ceil(naturalWidth * state.scale);
        const scaledHeight = Math.ceil(naturalHeight * state.scale);

        // O contêiner participa do layout já com o tamanho final. A transformação
        // fica somente na árvore para não preservar uma largura invisível sem escala.
        host.style.width = `${scaledWidth}px`;
        host.style.height = `${scaledHeight}px`;
        host.style.transform = 'none';
        treeShell.style.position = 'absolute';
        treeShell.style.inset = '0 auto auto 0';
        treeShell.style.transformOrigin = 'top left';
        treeShell.style.transform = `scale(${state.scale})`;
        if (viewport && mount) {
            viewport.style.width = `${Math.max(mount.clientWidth - 40, scaledWidth)}px`;
        }
        byId('identityChartZoomValue').textContent = `${Math.round(state.scale * 100)}%`;
    }

    function fitTree() {
        const mount = byId('identityOrgChart');
        const treeShell = byId('identityTreeShell');
        if (!mount || !treeShell) return;
        const available = Math.max(300, mount.clientWidth - 48);
        state.scale = Math.max(0.1, Math.min(1, available / treeShell.scrollWidth));
        applyScale();
        requestAnimationFrame(() => {
            const centeredLeft = Math.max(0, (mount.scrollWidth - mount.clientWidth) / 2);
            mount.scrollTo({ left: centeredLeft, top: 0, behavior: 'smooth' });
        });
    }

    function setZoom(nextScale) {
        state.scale = Math.max(0.1, Math.min(1.5, Number(nextScale.toFixed(2))));
        applyScale();
    }

    function selectChartRole(roleId) {
        state.selectedRoleId = roleId;
        const role = state.rolesById.get(roleId);
        if (!role) return;
        renderChartContext();
        renderTree();
    }

    function renderChartContext() {
        const role = state.rolesById.get(Number(state.selectedRoleId));
        const treeNode = state.treeNodesById.get(Number(state.selectedRoleId));
        if (!role) return;
        const context = byId('identityChartContext');
        const canChooseChildrenLayout = hasOnlyTerminalChildren(treeNode);
        const childrenAreStacked = canChooseChildrenLayout && shouldStackChildren(treeNode);
        context.hidden = false;
        context.innerHTML = `
            <div class="identity-chart-context__copy"><strong>${escapeHtml(role.title)}</strong><small>${escapeHtml(role.department || 'Sem departamento')}</small><small>${role.active_employee_count || 0} efetivos de ${role.headcount_planned || 0} previstos</small></div>
            <div class="identity-chart-context__actions">
                ${canChooseChildrenLayout ? `<button type="button" class="btn btn-secondary" id="identityChartToggleChildrenLayout">Subordinados: ${childrenAreStacked ? 'empilhados' : 'horizontais'}</button>` : ''}
                ${canEdit ? '<button type="button" class="btn btn-secondary" id="identityChartEditRole">Editar cargo</button>' : ''}
            </div>`;
        byId('identityChartToggleChildrenLayout')?.addEventListener('click', () => {
            state.layoutOverrides.set(Number(treeNode.id), childrenAreStacked ? 'horizontal' : 'stacked');
            persistLayoutPreferences();
            renderTree();
            renderChartContext();
            requestAnimationFrame(() => window.IdentityOrgChart?.fit());
        });
        byId('identityChartEditRole')?.addEventListener('click', () => {
            activateTab('editor');
            openRoleEditor(Number(state.selectedRoleId));
        });
    }

    function renderEditorTree() {
        const container = byId('identityEditorTree');
        const query = normalize(byId('identityEditorSearch').value);
        const roles = flattenTree(state.tree).filter((role) => !query || normalize(`${role.title} ${role.department}`).includes(query));
        container.innerHTML = roles.length ? roles.map((role) => `
            <button type="button" class="identity-editor-tree__item${Number(role.id) === Number(state.selectedRoleId) ? ' is-active' : ''}" data-editor-role="${role.id}" style="padding-left:${0.75 + (role.depth * 1.05)}rem">
                <span class="identity-editor-tree__branch">${role.depth ? '└' : '●'}</span>
                <span class="identity-editor-tree__copy"><strong>${escapeHtml(role.title)}</strong><small>${escapeHtml(role.department || 'Sem departamento')}</small></span>
            </button>`).join('') : '<div class="identity-org-chart__empty">Nenhum cargo encontrado.</div>';
        container.querySelectorAll('[data-editor-role]').forEach((button) => {
            button.addEventListener('click', () => openRoleEditor(Number(button.dataset.editorRole)));
        });
    }

    function populateParentOptions(roleId = null) {
        const blocked = roleId ? descendantsOf(roleId) : new Set();
        if (roleId) blocked.add(Number(roleId));
        const options = state.summary.roles
            .filter((role) => !blocked.has(Number(role.id)))
            .sort((a, b) => String(a.title).localeCompare(String(b.title), 'pt-BR'));
        byId('identityRoleParent').innerHTML = '<option value="">Topo da estrutura (sem superior)</option>' + options.map((role) => `<option value="${role.id}">${escapeHtml(role.title)}${role.department ? ` · ${escapeHtml(role.department)}` : ''}</option>`).join('');
    }

    function setEditorEnabled(enabled) {
        ['identityRoleTitle', 'identityRoleDepartment', 'identityRoleParent', 'identityRoleHeadcount', 'identityRoleWeeklyHours', 'identityRoleNotes', 'identityRoleQualifications', 'identityRoleColor', 'identityEditorSave']
            .forEach((id) => { if (byId(id)) byId(id).disabled = !enabled; });
        document.querySelectorAll('[data-role-color]').forEach((button) => { button.disabled = !enabled; });
    }

    function openRoleEditor(roleId = null) {
        const role = roleId ? state.rolesById.get(Number(roleId)) : null;
        state.selectedRoleId = role?.id || null;
        updateNewEmployeeTarget(role);
        byId('identityEditorEmpty').hidden = true;
        byId('identityEditorFields').hidden = false;
        byId('identityRoleId').value = role?.id || '';
        byId('identityRoleTitle').value = role?.title || '';
        byId('identityRoleDepartment').value = role?.department || '';
        byId('identityRoleHeadcount').value = role?.headcount_planned ?? 1;
        byId('identityRoleWeeklyHours').value = role?.weekly_hours ?? '';
        byId('identityRoleNotes').value = role?.notes ?? '';
        byId('identityRoleQualifications').value = role?.qualification_requirements ?? '';
        byId('identityRoleColor').value = safeColor(role?.color);
        byId('identityRoleColorValue').textContent = safeColor(role?.color);
        byId('identityEditorMode').textContent = role ? 'Editando cargo' : 'Novo cargo';
        byId('identityEditorTitle').textContent = role?.title || 'Novo cargo';
        byId('identityEditorSaveState').textContent = '';
        byId('identityEditorSaveState').className = 'identity-save-state';
        populateParentOptions(role?.id);
        byId('identityRoleParent').value = role?.parent_role_id || '';
        setEditorEnabled(canEdit);
        if (!canEdit && !byId('identityEditorReadonly')) {
            byId('identityEditorFields').insertAdjacentHTML('afterbegin', '<div class="identity-editor-readonly" id="identityEditorReadonly">Você possui acesso de leitura. Solicite a permissão <strong>companies:edit</strong> para alterar a estrutura.</div>');
        }
        renderEditorPreview();
        renderEditorTree();
        byId('identityRoleTitle').focus();
    }

    function closeRoleEditor() {
        updateNewEmployeeTarget(null);
        state.selectedRoleId = null;
        byId('identityEditorFields').hidden = true;
        byId('identityEditorEmpty').hidden = false;
        byId('identityRoleEditorForm').reset();
        renderEditorTree();
    }

    function renderEditorPreview() {
        const title = byId('identityRoleTitle').value.trim() || 'Título do cargo';
        const department = byId('identityRoleDepartment').value.trim() || 'Departamento não informado';
        const planned = Math.max(0, Number(byId('identityRoleHeadcount').value) || 0);
        const color = safeColor(byId('identityRoleColor').value);
        const parentId = Number(byId('identityRoleParent').value) || null;
        const parentNode = parentId ? state.treeNodesById.get(parentId) : null;
        const previewDepth = parentNode ? Number(parentNode.depth || 0) + 1 : 0;
        const currentRole = state.rolesById.get(Number(byId('identityRoleId').value));
        byId('identityRoleColorValue').textContent = color;
        byId('identityEditorTitle').textContent = title;
        byId('identityEditorPreview').innerHTML = `
            <span class="identity-editor-preview__label">Prévia no organograma</span>
            <article class="identity-node ${depthClass(previewDepth)} identity-editor-preview__card" style="--identity-node-color:${color}">
                <div class="identity-node__head"><span class="identity-node__eyebrow">Cargo</span><span class="identity-node__title">${escapeHtml(title)}</span><span class="identity-node__department">${escapeHtml(department)}</span></div>
                <div class="identity-node__body"><div class="identity-node__metrics"><div class="identity-node__metric"><span class="identity-node__metric-label">Previstos</span><span class="identity-node__metric-value">${planned}</span></div><div class="identity-node__metric"><span class="identity-node__metric-label">Efetivos</span><span class="identity-node__metric-value">${currentRole?.active_employee_count || 0}</span></div></div></div>
            </article>`;
    }

    async function saveRole(event) {
        event.preventDefault();
        if (!canEdit) return;
        if (!byId('identityRoleEditorForm').reportValidity()) return;
        const title = byId('identityRoleTitle').value.trim();
        if (!title) {
            byId('identityRoleTitle').focus();
            byId('identityRoleTitle').reportValidity();
            return;
        }
        const roleId = Number(byId('identityRoleId').value) || null;
        const parentRoleId = Number(byId('identityRoleParent').value) || null;
        const payload = {
            title,
            department: byId('identityRoleDepartment').value.trim() || null,
            parent_role_id: parentRoleId,
            headcount_planned: Number(byId('identityRoleHeadcount').value),
            weekly_hours: byId('identityRoleWeeklyHours').value === '' ? null : Number(byId('identityRoleWeeklyHours').value),
            notes: byId('identityRoleNotes').value.trim() || null,
            qualification_requirements: byId('identityRoleQualifications').value.trim() || null,
            color: safeColor(byId('identityRoleColor').value),
        };
        const saveButton = byId('identityEditorSave');
        const status = byId('identityEditorSaveState');
        saveButton.disabled = true;
        status.textContent = 'Salvando…';
        status.className = 'identity-save-state';
        try {
            const saved = await fetchJson(roleId ? `/api/companies/${companyId}/roles/${roleId}` : `/api/companies/${companyId}/roles`, {
                method: roleId ? 'PUT' : 'POST',
                body: JSON.stringify(payload),
            });
            status.textContent = 'Salvo com sucesso';
            status.className = 'identity-save-state is-success';
            await loadPage({ preserveRoleId: Number(saved.id) });
            openRoleEditor(Number(saved.id));
        } catch (error) {
            status.textContent = error.message;
            status.className = 'identity-save-state is-error';
        } finally {
            saveButton.disabled = false;
        }
    }

    function populateDepartmentFilter() {
        const select = byId('identityChartDepartment');
        const current = select.value;
        const departments = [...new Set(state.summary.roles.map((role) => role.department).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
        select.innerHTML = '<option value="">Todos os departamentos</option>' + departments.map((department) => `<option value="${escapeHtml(department)}">${escapeHtml(department)}</option>`).join('');
        select.value = departments.includes(current) ? current : '';
    }

    function downloadText(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1200);
    }

    function buildOrgChartSvg() {
        const treeShell = byId('identityTreeShell');
        if (!treeShell) throw new Error('Organograma não encontrado para exportação.');
        const treeClone = treeShell.cloneNode(true);
        const headerClone = byId('identityChartDocumentHeader').cloneNode(true);
        const footerClone = byId('identityChartDocumentFooter').cloneNode(true);
        treeClone.querySelectorAll('button').forEach((button) => button.remove());
        treeClone.style.position = 'static';
        treeClone.style.inset = 'auto';
        treeClone.style.transform = 'none';
        treeClone.style.transformOrigin = 'initial';
        const padding = 56;
        const contentWidth = Math.max(760, Math.ceil(treeShell.scrollWidth));
        const headerHeight = Math.max(100, byId('identityChartDocumentHeader').scrollHeight);
        const footerHeight = Math.max(44, byId('identityChartDocumentFooter').scrollHeight);
        const width = contentWidth + padding * 2;
        const height = Math.ceil(treeShell.scrollHeight) + headerHeight + footerHeight + padding * 2 + 32;
        const styles = [...document.styleSheets]
            .filter((sheet) => sheet.href?.includes('company_identity.css'))
            .flatMap((sheet) => { try { return [...sheet.cssRules].map((rule) => rule.cssText); } catch (_) { return []; } })
            .join('\n');
        const headerHtml = new XMLSerializer().serializeToString(headerClone);
        const treeHtml = new XMLSerializer().serializeToString(treeClone);
        const footerHtml = new XMLSerializer().serializeToString(footerClone);
        return `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;background:#fff;box-sizing:border-box;padding:${padding}px;font-family:Arial,sans-serif"><style>${styles}</style><div style="width:${contentWidth}px">${headerHtml}<div style="display:flex;justify-content:center;padding:16px 0">${treeHtml}</div>${footerHtml}</div></div></foreignObject></svg>`;
    }

    window.IdentityOrgChart = {
        collapseAll() {
            flattenTree(state.tree).filter((node) => node.children?.length).forEach((node) => state.collapsedIds.add(Number(node.id)));
            renderTree();
        },
        expandAll() { state.collapsedIds.clear(); renderTree(); },
        fit: fitTree,
        zoomIn() { setZoom(state.scale + 0.1); },
        zoomOut() { setZoom(state.scale - 0.1); },
        resetZoom() { setZoom(1); },
        downloadSvg() {
            const filename = (shell.dataset.companyName || 'organograma').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'organograma';
            downloadText(`${filename}-organograma.svg`, buildOrgChartSvg(), 'image/svg+xml;charset=utf-8');
        },
    };

    window.IdentityExecutiveReport = {
        print() {
            document.body.classList.add('identity-report-printing');
            window.print();
        },
    };

    window.addEventListener('afterprint', () => {
        document.body.classList.remove('identity-report-printing');
    });

    async function loadPage(options = {}) {
        try {
            const [summary, treeResponse] = await Promise.all([
                fetchJson(`/api/companies/${companyId}/identity/summary`),
                fetchJson(`/api/companies/${companyId}/roles/tree`),
            ]);
            state.summary = summary;
            renderLinkCandidates();
            state.tree = treeResponse.data || [];
            state.rolesById = new Map(summary.roles.map((role) => [Number(role.id), role]));
            state.treeNodesById = new Map(flattenTree(state.tree).map((role) => [Number(role.id), role]));
            state.selectedRoleId = options.preserveRoleId || state.selectedRoleId;
            renderSummary(summary);
            populateDepartmentFilter();
            renderEditorTree();
            renderTree();
        } catch (error) {
            console.error(error);
            byId('identityOrgChart').innerHTML = `<div class="identity-org-chart__empty">${escapeHtml(error.message || 'Falha ao carregar organograma.')}</div>`;
            byId('identityEditorTree').innerHTML = '<div class="identity-org-chart__empty">Falha ao carregar cargos.</div>';
            byId('identityRolesBody').innerHTML = '<tr><td colspan="4" class="identity-empty-row">Falha ao carregar cargos.</td></tr>';
            byId('identityEmployeesBody').innerHTML = '<tr><td colspan="4" class="identity-empty-row">Falha ao carregar colaboradores.</td></tr>';
        }
    }

    function updateNewEmployeeTarget(role) {
        const button = byId('identityNewEmployeeSave');
        if (!button) return;
        button.disabled = !canEdit || !role;
        byId('identityLinkEmployeeSave').disabled = !canEdit || !role;
        byId('identityNewEmployeeRole').textContent = role ? `Cargo: ${role.title}` : 'Selecione e salve um cargo no editor.';
        byId('identityNewEmployeeStatus').textContent = '';
    }

    async function createEmployeeWithoutLogin(event) {
        event.preventDefault();
        const roleId = Number(byId('identityRoleId').value);
        if (!canEdit || !roleId || !state.rolesById.has(roleId)) return;
        const button = byId('identityNewEmployeeSave');
        if (button.disabled) return;
        const status = byId('identityNewEmployeeStatus');
        const name = byId('identityNewEmployeeName').value.trim();
        if (!name) { status.textContent = 'Informe o nome do colaborador.'; return; }
        if (!window.confirm(`Cadastrar ${name} sem login no cargo ${state.rolesById.get(roleId).title}?`)) return;
        button.disabled = true;
        try {
            await fetchJson(`/api/companies/${companyId}/roles/${roleId}/employees`, {
                method: 'POST', body: JSON.stringify({ name }),
            });
            byId('identityNewEmployeeName').value = '';
            await loadPage({ preserveRoleId: roleId });
            status.textContent = 'Colaborador cadastrado sem login. Confira a lotação no organograma.';
        } catch (error) {
            status.textContent = error.message;
        } finally {
            button.disabled = !canEdit || !Number(byId('identityRoleId').value);
        }
    }

    function renderLinkCandidates() {
        const select = byId('identityExistingEmployee');
        if (!select) return;
        const employees = (state.summary?.employees || []).filter(employee =>
            !employee.role_id && !employee.user_id && ['', 'active', 'ativo'].includes(String(employee.status || '').trim().toLowerCase()));
        select.innerHTML = '<option value="">Selecione um colaborador</option>' + employees.map(employee =>
            `<option value="${Number(employee.id)}">${escapeHtml(employee.name)}</option>`).join('');
    }

    async function linkExistingEmployee(event) {
        event.preventDefault();
        const roleId = Number(byId('identityRoleId').value);
        const employeeId = Number(byId('identityExistingEmployee').value);
        const button = byId('identityLinkEmployeeSave');
        if (!canEdit || button.disabled || !employeeId || !state.rolesById.has(roleId)) return;
        const name = byId('identityExistingEmployee').selectedOptions[0].textContent;
        if (!window.confirm(`Vincular ${name} ao cargo ${state.rolesById.get(roleId).title}?`)) return;
        button.disabled = true;
        const status = byId('identityLinkEmployeeStatus');
        try {
            await fetchJson(`/api/companies/${companyId}/roles/${roleId}/employees`, {
                method: 'PUT', body: JSON.stringify({ employee_id: employeeId }),
            });
            await loadPage({ preserveRoleId: roleId });
            status.textContent = 'Colaborador vinculado. Nenhum login foi criado.';
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = !canEdit || !Number(byId('identityRoleId').value); }
    }

    async function queryOccupancies(event) {
        event.preventDefault();
        const date = byId('identityOccupancyDate').value;
        const button = byId('identityOccupancySearch');
        if (!date || button.disabled) return;
        button.disabled = true;
        const status = byId('identityOccupancyStatus');
        const rows = byId('identityOccupancyRows');
        rows.innerHTML = '<tr><td colspan="4">Carregando...</td></tr>';
        status.textContent = 'Consultando vigências registradas…';
        try {
            const result = await fetchJson(`/api/companies/${companyId}/occupancy-snapshot?as_of=${encodeURIComponent(date)}`);
            const assignments = result.assignments || [];
            const pending = (result.legacy_pending_employee_ids || []).length;
            status.textContent = `${result.as_of}: ${result.distinct_people_count} pessoa(s) distinta(s), ${assignments.length} ocupação(ões). ${pending} colaborador(es) com legado pendente de reconciliação.`;
            rows.innerHTML = assignments.length ? assignments.map(item => `<tr>
                <td>${escapeHtml(item.employee_name)}</td><td>${escapeHtml(item.role_title)}</td>
                <td>${escapeHtml(item.weekly_hours ?? 'Não informada')}</td>
                <td>${item.source === 'temporal' ? 'Vigência registrada' : 'Legado não verificado'}${item.capacity_pending ? ' · dedicação pendente' : ''}</td>
            </tr>`).join('') : '<tr><td colspan="4">Sem ocupações comprovadas ou legadas elegíveis nesta data.</td></tr>';
        } catch (error) {
            status.textContent = error.message || 'Não foi possível consultar ocupações.';
            rows.innerHTML = '<tr><td colspan="4">Consulta indisponível. Não interprete esta falha como ausência de colaboradores.</td></tr>';
        } finally { button.disabled = false; }
    }

    function bindEvents() {
        byId('identityOccupancyQuery').addEventListener('submit', queryOccupancies);
        const today = new Date();
        byId('identityOccupancyDate').value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        byId('identityLinkEmployeeForm')?.addEventListener('submit', linkExistingEmployee);
        byId('identityNewEmployeeForm')?.addEventListener('submit', createEmployeeWithoutLogin);
        document.querySelectorAll('.identity-tab-btn').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.identityTab)));
        byId('identityEditorNewRole')?.addEventListener('click', () => openRoleEditor());
        byId('identityEditorCancel').addEventListener('click', closeRoleEditor);
        byId('identityRoleEditorForm').addEventListener('submit', saveRole);
        byId('identityEditorSearch').addEventListener('input', renderEditorTree);
        ['identityRoleTitle', 'identityRoleDepartment', 'identityRoleHeadcount', 'identityRoleColor'].forEach((id) => byId(id).addEventListener('input', renderEditorPreview));
        byId('identityRoleParent').addEventListener('change', renderEditorPreview);
        document.querySelectorAll('[data-role-color]').forEach((button) => {
            button.addEventListener('click', () => {
                byId('identityRoleColor').value = safeColor(button.dataset.roleColor);
                renderEditorPreview();
            });
        });
        byId('identityChartSearch').addEventListener('input', (event) => { state.search = event.target.value; renderTree(); });
        byId('identityChartDepartment').addEventListener('change', (event) => { state.department = event.target.value; renderTree(); });
        byId('identityChartLayout').value = ['auto', 'horizontal', 'terminal-stacked'].includes(state.layoutMode) ? state.layoutMode : 'auto';
        byId('identityChartLayout').addEventListener('change', (event) => {
            state.layoutMode = event.target.value;
            persistLayoutPreferences();
            renderTree();
            if (state.selectedRoleId) renderChartContext();
            requestAnimationFrame(() => window.IdentityOrgChart?.fit());
        });
        window.addEventListener('resize', () => { if (location.hash === '#organograma') fitTree(); });
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindEvents();
        const hashTab = (window.location.hash || '').replace('#', '').trim();
        const allowedTabs = Array.from(document.querySelectorAll('[data-identity-tab]')).map(button => button.dataset.identityTab);
        activateTab(allowedTabs.includes(hashTab) ? hashTab : 'mvv');
        loadPage();
    });
})();
