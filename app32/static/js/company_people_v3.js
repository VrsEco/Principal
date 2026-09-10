(() => {
  'use strict';
  const root = document.querySelector('.people-page');
  if (!root) return;
  const companyId = Number(root.dataset.companyId);
  const canManage = root.dataset.canManage === 'true';
  const canViewCosts = root.dataset.canViewCosts === 'true';
  const state = { workspace: null, activeTab: 'users', roleView: 'profile', employeeView: 'profile', reportView: 'capacity', org: { collapsedIds: new Set(), layout: 'auto', scale: 1, search: '', department: '' } };
  const byId = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const profileLabel = (profile) => ({administrator: 'Administrador', client: 'Cliente', collaborator: 'Colaborador'}[profile] || 'Colaborador');
  const statusLabel = (status) => ({active: 'Ativo', ativo: 'Ativo', inactive: 'Inativo', inativo: 'Inativo', vacation: 'Férias', 'férias': 'Férias', ferias: 'Férias'}[String(status || '').toLowerCase()] || 'Não informado');
  const today = () => new Date().toISOString().slice(0, 10);

  async function request(url, options = {}) {
    const response = await fetch(url, {headers: {'Accept':'application/json', ...(options.body ? {'Content-Type':'application/json'} : {})}, ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a operação.');
    return data;
  }
  function openDialog(id) { const dialog = byId(id); if (dialog?.showModal) dialog.showModal(); }
  function closeDialog(id) { byId(id)?.close?.(); }
  function roleOptions(selected = '', includeBlank = true) {
    const roles = state.workspace?.roles || [];
    return `${includeBlank ? '<option value="">Sem superior</option>' : '<option value="">Selecione um cargo</option>'}${roles.map(role => `<option value="${role.id}" ${Number(selected) === Number(role.id) ? 'selected' : ''}>${esc(role.title)}${role.department ? ` · ${esc(role.department)}` : ''}</option>`).join('')}`;
  }
  function employeeOptions(selected = '') {
    const employees = state.workspace?.employees || [];
    return `<option value="">Sem vínculo</option>${employees.map(employee => `<option value="${employee.id}" ${Number(selected) === Number(employee.id) ? 'selected' : ''}>${esc(employee.name)}${employee.role_title ? ` · ${esc(employee.role_title)}` : ''}</option>`).join('')}`;
  }
  async function loadWorkspace() {
    state.workspace = await request(`/api/companies/${companyId}/people/workspace`);
    renderAll();
  }
  function renderAll() { renderMetrics(); renderUsers(); renderRoles(); renderOrg(); renderEmployees(); renderCapacityReport(); }
  function renderMetrics() {
    const metrics = state.workspace.metrics || {};
    byId('peopleMetricUsers').textContent = metrics.users_total ?? 0;
    byId('peopleMetricUsersActive').textContent = `${metrics.active_users_total ?? 0} ativos`;
    byId('peopleMetricEmployees').textContent = metrics.active_employees_total ?? 0;
    byId('peopleMetricRoles').textContent = metrics.roles_total ?? 0;
    byId('peopleMetricVacancies').textContent = (state.workspace.roles || []).reduce((total, role) => total + Number(role.vacancy_count || 0), 0);
  }
  function filteredUsers() {
    const search = (byId('peopleUserSearch')?.value || '').trim().toLocaleLowerCase('pt-BR');
    const profile = byId('peopleUserProfile')?.value || '';
    return (state.workspace.users || []).filter(user => (!profile || user.access_profile === profile) && (!search || `${user.name} ${user.email}`.toLocaleLowerCase('pt-BR').includes(search)));
  }
  function renderUsers() {
    const body = byId('peopleUsersRows'); if (!body) return;
    const users = filteredUsers();
    body.innerHTML = users.length ? users.map(user => `<tr><td><span class="people-user-name">${esc(user.name)}</span><span class="people-user-email">${esc(user.email)}</span></td><td><span class="people-profile-pill">${profileLabel(user.access_profile)}</span></td><td>${user.employee ? `<b>${esc(user.employee.name)}</b><span class="people-cell-note">${esc(user.employee.role_title || 'Sem cargo')}</span>` : '<span class="people-cell-note">Sem vínculo</span>'}</td><td><span class="people-status-pill ${(!user.is_active || !user.user_is_active) ? 'is-inactive' : ''}">${(!user.is_active || !user.user_is_active) ? 'Inativo' : 'Ativo'}</span></td><td class="people-actions-col">${canManage ? `<button class="people-action" type="button" data-edit-user="${user.user_id}">Editar</button>` : ''}</td></tr>`).join('') : '<tr><td colspan="5">Nenhum usuário vinculado a esta empresa.</td></tr>';
  }
  function coverage(role) { const planned = Number(role.headcount_planned || 0); const occupied = Number(role.active_employee_count || 0); return planned ? `${Math.min(100, Math.round((occupied / planned) * 100))}%` : (occupied ? 'Sem previsão' : '—'); }
  function roleEditAction(role) { return canManage ? `<button class="people-action" type="button" data-edit-role="${role.id}">Editar</button>` : ''; }
  function renderRoles() {
    const profileBody = byId('peopleRoleProfileRows'); const quantityBody = byId('peopleRoleQuantityRows'); if (!profileBody || !quantityBody) return;
    const roles = state.workspace.roles || [];
    const byIdRole = new Map(roles.map(role => [Number(role.id), role]));
    profileBody.innerHTML = roles.length ? roles.map(role => `<tr><td><b>${esc(role.title)}</b></td><td>${esc(role.department || '—')}</td><td>${esc(byIdRole.get(Number(role.parent_role_id))?.title || '—')}</td><td>${role.weekly_hours == null ? 'Não informada' : `${esc(role.weekly_hours)} h`}</td><td>${esc(role.qualification_requirements || 'Não informadas')}</td><td class="people-actions-col">${roleEditAction(role)}</td></tr>`).join('') : '<tr><td colspan="6">Nenhum cargo cadastrado.</td></tr>';
    quantityBody.innerHTML = roles.length ? roles.map(role => `<tr><td><b>${esc(role.title)}</b></td><td>${esc(role.department || '—')}</td><td>${role.headcount_planned ?? 0}</td><td>${role.active_employee_count ?? 0}</td><td>${role.vacancy_count ?? 0}</td><td><span class="people-status-pill ${Number(role.vacancy_count || 0) ? 'is-inactive' : ''}">${coverage(role)}</span></td><td class="people-actions-col">${roleEditAction(role)}</td></tr>`).join('') : '<tr><td colspan="7">Nenhum cargo cadastrado.</td></tr>';
  }
  function safeOrgColor(value) { return /^#[0-9a-f]{6}$/i.test(String(value || '').trim()) ? String(value).trim() : '#D9ECFF'; }
  function flattenOrgTree(nodes, output = []) { (nodes || []).forEach(node => { output.push(node); flattenOrgTree(node.children, output); }); return output; }
  function hasOnlyTerminalChildren(node) { return Boolean(node?.children?.length) && node.children.every(child => !child.children?.length); }
  function shouldStackOrgChildren(node) {
    if (!hasOnlyTerminalChildren(node)) return false;
    if (state.org.layout === 'horizontal') return false;
    if (state.org.layout === 'terminal-stacked') return true;
    return node.children.length >= 3;
  }
  function filterOrgTree(nodes) {
    const search = state.org.search.trim().toLocaleLowerCase('pt-BR');
    return (nodes || []).reduce((result, node) => {
      const children = filterOrgTree(node.children || []);
      const matchesSearch = !search || `${node.title || ''} ${node.department || ''}`.toLocaleLowerCase('pt-BR').includes(search);
      const matchesDepartment = !state.org.department || node.department === state.org.department;
      if ((matchesSearch && matchesDepartment) || children.length) result.push({...node, children, _matched: matchesSearch && matchesDepartment});
      return result;
    }, []);
  }
  function renderOrgNode(node, depth = 0) {
    const hasChildren = Boolean(node.children?.length);
    const collapsed = state.org.collapsedIds.has(Number(node.id));
    return `<li><div class="people-org-node-wrap"><article class="people-org-node people-org-node--depth-${Math.min(depth, 3)}${node._matched === false ? ' is-filter-context' : ''}" data-people-org-node="${node.id}" style="--people-node-color:${safeOrgColor(node.color)}" tabindex="0" role="button"><div class="people-org-node__head"><span class="people-org-node__eyebrow">Cargo</span><strong>${esc(node.title)}</strong><span>${esc(node.department || 'Departamento não informado')}</span></div><div class="people-org-node__body"><div><small>Previstos</small><b>${node.headcount_planned || 0}</b></div><div><small>Efetivos</small><b>${node.active_employee_count || 0}</b></div></div></article>${hasChildren ? `<button class="people-org-node__toggle" type="button" data-people-org-toggle="${node.id}" aria-label="${collapsed ? 'Expandir' : 'Recolher'} subordinados de ${esc(node.title)}" aria-expanded="${!collapsed}">${collapsed ? '+' : '−'}</button>` : ''}</div>${hasChildren && !collapsed ? `<ul class="people-org-tree-children${shouldStackOrgChildren(node) ? ' is-stacked' : ''}">${node.children.map(child => renderOrgNode(child, depth + 1)).join('')}</ul>` : ''}</li>`;
  }
  function updateOrgScale() {
    const scale = byId('peopleOrgChartScale'); const shell = byId('peopleOrgTreeShell'); const target = byId('peopleOrgChart');
    if (!scale || !shell || !target) return;
    const naturalWidth = shell.scrollWidth; const naturalHeight = shell.scrollHeight;
    scale.style.width = `${Math.ceil(naturalWidth * state.org.scale)}px`; scale.style.height = `${Math.ceil(naturalHeight * state.org.scale)}px`;
    shell.style.transform = `scale(${state.org.scale})`; byId('peopleOrgZoomValue').textContent = `${Math.round(state.org.scale * 100)}%`;
  }
  function fitOrgTree() {
    const target = byId('peopleOrgChart'); const shell = byId('peopleOrgTreeShell');
    if (!target || !shell || target.offsetParent === null) return;
    state.org.scale = Math.max(.35, Math.min(1, (target.clientWidth - 48) / shell.scrollWidth)); updateOrgScale();
  }
  function bindOrgTreeInteractions() {
    document.querySelectorAll('[data-people-org-node]').forEach(node => node.addEventListener('click', () => {
      const role = flattenOrgTree(state.workspace?.roles_tree || []).find(item => Number(item.id) === Number(node.dataset.peopleOrgNode));
      const context = byId('peopleOrgContext'); if (!role || !context) return;
      context.hidden = false; context.innerHTML = `<strong>${esc(role.title)}</strong><span>${esc(role.department || 'Sem departamento')} · ${role.active_employee_count || 0} efetivos de ${role.headcount_planned || 0} previstos</span>`;
    }));
    document.querySelectorAll('[data-people-org-toggle]').forEach(button => button.addEventListener('click', event => { event.stopPropagation(); const id = Number(button.dataset.peopleOrgToggle); state.org.collapsedIds.has(id) ? state.org.collapsedIds.delete(id) : state.org.collapsedIds.add(id); renderOrg(); }));
  }
  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1200);
  }
  function orgChartFilename() {
    const name = (root.dataset.companyName || 'empresa').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase();
    return `${name || 'empresa'}-organograma`;
  }
  function setOrgExportStatus(message, isError = false) {
    const status = byId('peopleOrgExportStatus'); if (!status) return;
    status.hidden = !message; status.textContent = message; status.classList.toggle('is-error', isError);
  }
  function svgTextLines(value, maxLength = 24) {
    const words = String(value || '').trim().split(/\s+/).filter(Boolean); const lines = []; let line = '';
    words.forEach(word => { const next = line ? `${line} ${word}` : word; if (line && next.length > maxLength) { lines.push(line); line = word; } else line = next; });
    if (line) lines.push(line); return lines.slice(0, 2);
  }
  function visibleOrgEntries(nodes, parentId = null, output = []) {
    (nodes || []).forEach(node => {
      output.push({ node, parentId });
      if (node.children?.length && !state.org.collapsedIds.has(Number(node.id))) visibleOrgEntries(node.children, Number(node.id), output);
    });
    return output;
  }
  function orgExportNodeSvg(item, originX, originY) {
    const { node, x, y, width, height } = item; const accent = safeOrgColor(node.color); const metricWidth = Math.max(58, Math.min(90, Math.round(width * .3))); const metricX = width - metricWidth - 10;
    const titleLines = svgTextLines(node.title, width < 260 ? 16 : 22); const titleMarkup = titleLines.map((line, index) => `<text x="16" y="${42 + index * 15}" fill="#10233f" font-size="${width < 260 ? 10.5 : 12.5}" font-weight="750">${esc(line)}</text>`).join('');
    const department = String(node.department || 'Departamento não informado'); const departmentY = Math.min(height - 10, 48 + titleLines.length * 15); const metricHeight = Math.max(26, Math.floor((height - 30) / 2)); const secondMetricY = 12 + metricHeight + 6;
    const metric = (top, label, value) => `<rect x="${metricX}" y="${top}" width="${metricWidth}" height="${metricHeight}" rx="8" fill="#f8fbff" stroke="#dbe5f1"/><text x="${metricX + 7}" y="${top + 9}" fill="#64748b" font-size="6.8" font-weight="800" letter-spacing=".4">${label}</text><text x="${metricX + 7}" y="${top + metricHeight - 6}" fill="#10233f" font-size="${height < 98 ? 11.5 : 13.5}" font-weight="800">${Number(value || 0)}</text>`;
    return `<g transform="translate(${Math.round(originX + x)},${Math.round(originY + y)})" filter="url(#app32NodeShadow)"><rect width="${Math.round(width)}" height="${Math.round(height)}" rx="14" fill="#ffffff" stroke="#d8e4f1"/><rect width="5" height="${Math.round(height)}" rx="2.5" fill="${accent}"/><text x="16" y="20" fill="#2563eb" font-size="7.5" font-weight="800" letter-spacing=".9">CARGO</text>${titleMarkup}<text x="16" y="${departmentY}" fill="#52657d" font-size="9.5">${esc(department.length > 30 ? `${department.slice(0, 27)}…` : department)}</text>${metric(12, 'PREVISTOS', node.headcount_planned)}${metric(secondMetricY, 'EFETIVOS', node.active_employee_count)}</g>`;
  }
  function buildOrgChartSvg() {
    const treeShell = byId('peopleOrgTreeShell'); if (!treeShell) throw new Error('Organograma não encontrado para exportação.');
    const entries = visibleOrgEntries(filterOrgTree(state.workspace?.roles_tree || [])); const shellRect = treeShell.getBoundingClientRect(); const scale = Math.max(.01, state.org.scale);
    const rendered = entries.map(entry => {
      const element = document.querySelector(`[data-people-org-node="${entry.node.id}"]`); if (!element) return null;
      const rect = element.getBoundingClientRect(); return { ...entry, x: (rect.left - shellRect.left) / scale, y: (rect.top - shellRect.top) / scale, width: rect.width / scale, height: rect.height / scale };
    }).filter(Boolean);
    if (!rendered.length) throw new Error('Nenhum cargo disponível para exportação.');
    const minX = Math.min(...rendered.map(item => item.x)); const minY = Math.min(...rendered.map(item => item.y)); const maxX = Math.max(...rendered.map(item => item.x + item.width)); const maxY = Math.max(...rendered.map(item => item.y + item.height));
    const padding = 56; const headerHeight = 150; const footerHeight = 54; const contentWidth = Math.max(860, Math.ceil(maxX - minX)); const treeOriginX = padding - minX; const treeOriginY = padding + headerHeight + 46 - minY;
    const width = contentWidth + padding * 2; const height = Math.ceil(treeOriginY + maxY + footerHeight + padding); const planned = byId('peopleOrgTotalPlanned')?.textContent?.trim() || '0'; const effective = byId('peopleOrgTotalEffective')?.textContent?.trim() || '0'; const companyName = root.dataset.companyName || 'Empresa';
    const byRoleId = new Map(rendered.map(entry => [Number(entry.node.id), entry]));
    const relationships = rendered.filter(entry => entry.parentId != null && byRoleId.has(Number(entry.parentId)));
    const connectors = relationships.map(entry => { const parent = byRoleId.get(Number(entry.parentId)); const fromX = treeOriginX + parent.x + parent.width / 2; const fromY = treeOriginY + parent.y + parent.height; const toX = treeOriginX + entry.x + entry.width / 2; const toY = treeOriginY + entry.y; const middleY = Math.round((fromY + toY) / 2); const path = `M${Math.round(fromX)} ${Math.round(fromY)}V${middleY}H${Math.round(toX)}V${Math.round(toY)}`; return `<path d="${path}" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><path d="${path}" fill="none" stroke="#2563eb" stroke-opacity=".82" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`; }).join('');
    const cards = rendered.map(entry => orgExportNodeSvg(entry, treeOriginX, treeOriginY)).join(''); const generatedAt = new Intl.DateTimeFormat('pt-BR').format(new Date()); const metricsX = padding + contentWidth - 222;
    const svg = `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><defs><linearGradient id="app32ExportHeader" x1="0" x2="1"><stop stop-color="#f7faff"/><stop offset="1" stop-color="#edf5ff"/></linearGradient><filter id="app32NodeShadow" x="-10%" y="-15%" width="120%" height="140%"><feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#17365d" flood-opacity=".12"/></filter></defs><rect width="100%" height="100%" fill="#f5f8fc"/><rect x="${padding}" y="${padding}" width="${contentWidth}" height="${height - padding * 2}" rx="24" fill="#ffffff" stroke="#dbe5f1"/><g font-family="Inter, Arial, sans-serif"><rect x="${padding}" y="${padding}" width="${contentWidth}" height="${headerHeight}" rx="24" fill="url(#app32ExportHeader)"/><path d="M${padding + 24} ${padding + 24}H${padding + 74}" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/><text x="${padding + 24}" y="${padding + 54}" fill="#2563eb" font-size="10" font-weight="800" letter-spacing="1.3">GESTÃO VERSUS · ESTRUTURA ORGANIZACIONAL</text><text x="${padding + 24}" y="${padding + 88}" fill="#10233f" font-size="26" font-weight="800">Organograma organizacional</text><text x="${padding + 24}" y="${padding + 113}" fill="#52657d" font-size="14">${esc(companyName)}</text><text x="${padding + 24}" y="${padding + 133}" fill="#7a8ba1" font-size="10.5">Atualizado em ${generatedAt}</text><rect x="${metricsX}" y="${padding + 34}" width="96" height="78" rx="14" fill="#ffffff" stroke="#dbe5f1"/><text x="${metricsX + 14}" y="${padding + 59}" fill="#64748b" font-size="9" font-weight="800" letter-spacing=".8">PREVISTOS</text><text x="${metricsX + 14}" y="${padding + 91}" fill="#10233f" font-size="24" font-weight="800">${esc(planned)}</text><rect x="${metricsX + 108}" y="${padding + 34}" width="96" height="78" rx="14" fill="#ffffff" stroke="#dbe5f1"/><text x="${metricsX + 122}" y="${padding + 59}" fill="#64748b" font-size="9" font-weight="800" letter-spacing=".8">EFETIVOS</text><text x="${metricsX + 122}" y="${padding + 91}" fill="#10233f" font-size="24" font-weight="800">${esc(effective)}</text>${cards}${connectors}<path d="M${padding + 28} ${height - padding - 34}H${width - padding - 28}" stroke="#e3ebf4"/><text x="${width / 2}" y="${height - padding - 14}" fill="#71839a" font-size="10.5" text-anchor="middle">Gestão Versus · Estrutura organizacional da empresa</text></g></svg>`;
    return { svg, width, height, relationshipCount: relationships.length };
  }
  async function exportOrgPng() {
    const { svg, width, height, relationshipCount } = buildOrgChartSvg(); const maxDimension = 8192;
    const scale = Math.min(2, maxDimension / Math.max(width, height));
    const imageUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
    try {
      const image = await new Promise((resolve, reject) => { const source = new Image(); source.onload = () => resolve(source); source.onerror = () => reject(new Error('Não foi possível preparar a imagem do organograma.')); source.src = imageUrl; });
      const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.floor(width * scale)); canvas.height = Math.max(1, Math.floor(height * scale));
      const context = canvas.getContext('2d'); if (!context) throw new Error('Navegador sem suporte para gerar a imagem.');
      context.fillStyle = '#ffffff'; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
      if (!blob) throw new Error('Não foi possível finalizar a imagem do organograma.');
      downloadBlob(`${orgChartFilename()}.png`, blob); return { width, height, relationshipCount: relationshipCount || 0 };
    } finally { URL.revokeObjectURL(imageUrl); }
  }
  function renderOrg() {
    const target = byId('peopleOrgChart'); if (!target) return;
    const rawTree = state.workspace?.roles_tree || []; const tree = filterOrgTree(rawTree); const roles = flattenOrgTree(rawTree);
    const department = byId('peopleOrgDepartment');
    if (department) { const current = state.org.department; const departments = [...new Set(roles.map(role => role.department).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR')); department.innerHTML = '<option value="">Todos os departamentos</option>' + departments.map(item => `<option value="${esc(item)}">${esc(item)}</option>`).join(''); department.value = departments.includes(current) ? current : ''; }
    byId('peopleOrgTotalPlanned').textContent = roles.reduce((total, role) => total + Number(role.headcount_planned || 0), 0);
    byId('peopleOrgTotalEffective').textContent = roles.reduce((total, role) => total + Number(role.active_employee_count || 0), 0);
    target.innerHTML = tree.length ? `<div class="people-org-chart__viewport"><div class="people-org-chart__scale" id="peopleOrgChartScale"><div class="people-org-tree-shell" id="peopleOrgTreeShell"><ul>${tree.map(node => renderOrgNode(node)).join('')}</ul></div></div></div>` : '<div class="people-org-chart__empty">Nenhum cargo encontrado para compor o organograma.</div>';
    bindOrgTreeInteractions(); if (state.activeTab === 'org') requestAnimationFrame(fitOrgTree);
  }
  function filteredEmployees() {
    const search = (byId('peopleEmployeeSearch')?.value || '').trim().toLocaleLowerCase('pt-BR');
    return (state.workspace.employees || []).filter(employee => !search || `${employee.name} ${employee.role_title || ''}`.toLocaleLowerCase('pt-BR').includes(search));
  }
  function renderEmployees() {
    const body = byId('peopleEmployeesRows'); if (!body) return;
    const employees = filteredEmployees();
    body.innerHTML = employees.length ? employees.map(employee => `<tr><td><span class="people-user-name">${esc(employee.name)}</span>${employee.user_id ? '<span class="people-cell-note">Conta vinculada</span>' : ''}</td><td>${esc(employee.role_title || 'Sem cargo')}</td><td>${esc(employee.role_department || employee.department || '—')}</td><td><span class="people-status-pill ${['inactive','inativo'].includes(String(employee.status).toLowerCase()) ? 'is-inactive' : ''}">${statusLabel(employee.status)}</span></td><td class="people-actions-col">${canManage ? `<button class="people-action" type="button" data-edit-employee="${employee.id}">Editar</button>` : ''}</td></tr>`).join('') : '<tr><td colspan="5">Nenhum colaborador cadastrado.</td></tr>';
  }
  function occupancySource(item) { return item.source === 'temporal' ? 'Vigência registrada' : 'Cadastro atual'; }
  function occupancyReliability(item) { return item.source === 'temporal' ? '<span class="people-status-pill">Formal</span>' : '<span class="people-status-pill is-inactive">Pendente de vigência</span>'; }
  function renderOccupancyRows(targetId, assignments, withReliability = false) {
    const target = byId(targetId); if (!target) return;
    const colspan = withReliability ? 5 : 4;
    target.innerHTML = assignments?.length ? assignments.map(item => `<tr><td>${esc(item.employee_name)}</td><td>${esc(item.role_title)}</td><td>${item.weekly_hours == null ? 'Não informada' : `${esc(item.weekly_hours)} h`}</td><td>${occupancySource(item)}</td>${withReliability ? `<td>${occupancyReliability(item)}</td>` : ''}</tr>`).join('') : `<tr><td colspan="${colspan}">Nenhuma ocupação encontrada na data.</td></tr>`;
  }
  function costAmount(item, currency) { return item.planned_monthly_cost == null ? 'Não informado' : `${esc(currency || 'BRL')} ${esc(item.planned_monthly_cost)}`; }
  function renderCostSnapshot(data, ids) {
    const rows = byId(ids.rows); const total = byId(ids.total); const status = byId(ids.status); if (!rows || !total || !status) return;
    rows.innerHTML = data.roles?.length ? data.roles.map(item => `<tr><td>${esc(item.role_title)}</td><td>${costAmount(item, data.currency)}</td><td>${item.planned_monthly_cost == null ? '<span class="people-status-pill is-inactive">Custo pendente</span>' : '<span class="people-status-pill">Completo</span>'}</td></tr>`).join('') : '<tr><td colspan="3">Nenhum cargo encontrado.</td></tr>';
    total.textContent = data.planned_monthly_total == null ? `Total incompleto. Subtotal conhecido: ${data.currency || '—'} ${data.known_planned_monthly_subtotal || '0.00'}.` : `Total mensal planejado: ${data.currency || '—'} ${data.planned_monthly_total}.`;
    status.textContent = `${data.as_of}: ${data.costed_roles_count || 0} de ${data.total_roles_count || 0} cargos com custo completo.`;
  }
  function renderCapacityReport() {
    const rows = byId('peopleCapacityReportRows'); const summary = byId('peopleCapacitySummary'); if (!rows || !summary) return;
    const roles = state.workspace?.roles || []; const planned = roles.reduce((sum, role) => sum + Number(role.headcount_planned || 0), 0); const occupied = roles.reduce((sum, role) => sum + Number(role.active_employee_count || 0), 0); const vacancies = roles.reduce((sum, role) => sum + Number(role.vacancy_count || 0), 0);
    summary.innerHTML = `<span><strong>${planned}</strong> previstos</span><span><strong>${occupied}</strong> ocupados</span><span><strong>${vacancies}</strong> vagas</span>`;
    rows.innerHTML = roles.length ? roles.map(role => `<tr><td>${esc(role.department || 'Sem área')}</td><td><b>${esc(role.title)}</b></td><td>${role.headcount_planned ?? 0}</td><td>${role.active_employee_count ?? 0}</td><td>${role.vacancy_count ?? 0}</td><td>${coverage(role)}</td></tr>`).join('') : '<tr><td colspan="6">Nenhum cargo cadastrado.</td></tr>';
  }
  function showTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('[data-people-tab]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleTab === tab));
    document.querySelectorAll('[data-people-panel]').forEach(panel => panel.classList.toggle('is-active', panel.dataset.peoplePanel === tab));
    if (tab === 'org') requestAnimationFrame(() => requestAnimationFrame(fitOrgTree));
  }
  function showEmployeeView(view) {
    state.employeeView = view;
    document.querySelectorAll('[data-people-employee-view]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleEmployeeView === view));
    document.querySelectorAll('[data-people-employee-panel]').forEach(panel => panel.hidden = panel.dataset.peopleEmployeePanel !== view);
  }
  function showRoleView(view) {
    state.roleView = view;
    document.querySelectorAll('[data-people-role-view]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleRoleView === view));
    document.querySelectorAll('[data-people-role-panel]').forEach(panel => panel.hidden = panel.dataset.peopleRolePanel !== view);
  }
  function showReportView(view) {
    state.reportView = view;
    document.querySelectorAll('[data-people-report-view]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleReportView === view));
    document.querySelectorAll('[data-people-report-panel]').forEach(panel => panel.hidden = panel.dataset.peopleReportPanel !== view);
    if (view === 'capacity') renderCapacityReport();
  }
  function openUser(userId = null) {
    const form = byId('peopleUserForm'); if (!form) return;
    form.reset(); byId('peopleUserFormStatus').textContent = '';
    const user = (state.workspace.users || []).find(item => Number(item.user_id) === Number(userId));
    byId('peopleUserId').value = user?.user_id || '';
    byId('peopleUserDialogTitle').textContent = user ? 'Editar vínculo de usuário' : 'Novo usuário';
    byId('peopleUserName').value = user?.name || '';
    byId('peopleUserEmail').value = user?.email || '';
    byId('peopleUserName').disabled = Boolean(user); byId('peopleUserEmail').disabled = Boolean(user);
    byId('peopleUserPassword').required = !user; byId('peoplePasswordField').hidden = Boolean(user);
    byId('peopleUserProfileInput').value = user?.access_profile || 'collaborator';
    byId('peopleUserEmployee').innerHTML = employeeOptions(user?.employee?.id || '');
    byId('peopleUserActive').checked = user ? Boolean(user.is_active) : true;
    openDialog('peopleUserDialog');
  }
  function openRole(roleId = null) {
    const form = byId('peopleRoleForm'); if (!form) return;
    form.reset(); byId('peopleRoleFormStatus').textContent = '';
    const role = (state.workspace.roles || []).find(item => Number(item.id) === Number(roleId));
    byId('peopleRoleId').value = role?.id || ''; byId('peopleRoleDialogTitle').textContent = role ? 'Editar cargo' : 'Novo cargo';
    byId('peopleRoleTitle').value = role?.title || ''; byId('peopleRoleDepartment').value = role?.department || '';
    byId('peopleRoleParent').innerHTML = roleOptions(role?.parent_role_id || '');
    byId('peopleRoleHeadcount').value = role?.headcount_planned ?? 1; byId('peopleRoleWeeklyHours').value = role?.weekly_hours ?? '';
    byId('peopleRoleQualifications').value = role?.qualification_requirements || ''; openDialog('peopleRoleDialog');
  }
  function openEmployee(employeeId = null) {
    const form = byId('peopleEmployeeForm'); if (!form) return;
    form.reset(); byId('peopleEmployeeFormStatus').textContent = '';
    const employee = (state.workspace.employees || []).find(item => Number(item.id) === Number(employeeId));
    byId('peopleEmployeeId').value = employee?.id || ''; byId('peopleEmployeeDialogTitle').textContent = employee ? 'Editar colaborador' : 'Novo colaborador';
    byId('peopleEmployeeName').value = employee?.name || ''; byId('peopleEmployeeRole').innerHTML = roleOptions(employee?.role_id || '', false);
    byId('peopleEmployeeDepartment').value = employee?.department || employee?.role_department || ''; byId('peopleEmployeeWeeklyHours').value = employee?.weekly_hours ?? '';
    byId('peopleEmployeeStatus').value = employee?.status || 'active'; openDialog('peopleEmployeeDialog');
  }
  function openOccupancy() {
    const form = byId('peopleOccupancyCreateForm'); if (!form) return;
    form.reset(); byId('peopleOccupancyCreateStatus').textContent = '';
    const activeEmployees = (state.workspace?.employees || []).filter(item => ['active', 'ativo'].includes(String(item.status || '').toLowerCase()));
    byId('peopleOccupancyEmployee').innerHTML = `<option value="">Selecione um colaborador</option>${activeEmployees.map(item => `<option value="${item.id}">${esc(item.name)}${item.role_title ? ` · ${esc(item.role_title)}` : ''}</option>`).join('')}`;
    byId('peopleOccupancyRole').innerHTML = roleOptions('', false);
    byId('peopleOccupancyStart').value = byId('peopleOccupancyDate')?.value || today();
    openDialog('peopleOccupancyDialog');
  }
  function openCost() {
    const form = byId('peopleCostForm'); if (!form) return;
    form.reset(); byId('peopleCostFormStatus').textContent = '';
    byId('peopleCostRole').innerHTML = roleOptions('', false); byId('peopleCostCurrency').value = 'BRL'; byId('peopleCostStart').value = byId('peopleCostsDate')?.value || today();
    openDialog('peopleCostDialog');
  }
  async function saveUser(event) {
    event.preventDefault(); const id = Number(byId('peopleUserId').value || 0); const status = byId('peopleUserFormStatus'); status.textContent = 'Salvando…';
    const body = {access_profile: byId('peopleUserProfileInput').value, is_active: byId('peopleUserActive').checked, employee_id: byId('peopleUserEmployee').value ? Number(byId('peopleUserEmployee').value) : null};
    if (!id) Object.assign(body, {name: byId('peopleUserName').value.trim(), email: byId('peopleUserEmail').value.trim(), password: byId('peopleUserPassword').value});
    try { await request(`/api/companies/${companyId}/people/users${id ? `/${id}` : ''}`, {method: id ? 'PUT' : 'POST', body: JSON.stringify(body)}); closeDialog('peopleUserDialog'); await loadWorkspace(); } catch (error) { status.textContent = error.message; }
  }
  async function saveRole(event) {
    event.preventDefault(); const id = Number(byId('peopleRoleId').value || 0); const status = byId('peopleRoleFormStatus'); status.textContent = 'Salvando…';
    const body = {title: byId('peopleRoleTitle').value.trim(), department: byId('peopleRoleDepartment').value.trim(), parent_role_id: byId('peopleRoleParent').value ? Number(byId('peopleRoleParent').value) : null, headcount_planned: Number(byId('peopleRoleHeadcount').value), weekly_hours: byId('peopleRoleWeeklyHours').value || null, qualification_requirements: byId('peopleRoleQualifications').value.trim() || null};
    try { await request(`/api/companies/${companyId}/roles${id ? `/${id}` : ''}`, {method: id ? 'PUT' : 'POST', body: JSON.stringify(body)}); closeDialog('peopleRoleDialog'); await loadWorkspace(); } catch (error) { status.textContent = error.message; }
  }
  async function saveEmployee(event) {
    event.preventDefault(); const id = Number(byId('peopleEmployeeId').value || 0); const status = byId('peopleEmployeeFormStatus'); status.textContent = 'Salvando…';
    const body = {name: byId('peopleEmployeeName').value.trim(), role_id: Number(byId('peopleEmployeeRole').value), department: byId('peopleEmployeeDepartment').value.trim(), weekly_hours: byId('peopleEmployeeWeeklyHours').value || null, status: byId('peopleEmployeeStatus').value};
    try { await request(`/api/companies/${companyId}/people/employees${id ? `/${id}` : ''}`, {method: id ? 'PUT' : 'POST', body: JSON.stringify(body)}); closeDialog('peopleEmployeeDialog'); await loadWorkspace(); } catch (error) { status.textContent = error.message; }
  }
  async function saveOccupancy(event) {
    event.preventDefault(); const status = byId('peopleOccupancyCreateStatus'); const employeeId = Number(byId('peopleOccupancyEmployee').value); status.textContent = 'Salvando…';
    const body = { role_id: Number(byId('peopleOccupancyRole').value), starts_on: byId('peopleOccupancyStart').value, ends_on: byId('peopleOccupancyEnd').value || null, weekly_hours: byId('peopleOccupancyWeeklyHours').value };
    try { await request(`/api/companies/${companyId}/employees/${employeeId}/occupancies`, {method: 'POST', body: JSON.stringify(body)}); closeDialog('peopleOccupancyDialog'); byId('peopleOccupancyDate').value = body.starts_on; await loadOccupancy(); }
    catch (error) { status.textContent = error.message; }
  }
  async function saveCost(event) {
    event.preventDefault(); const status = byId('peopleCostFormStatus'); const roleId = Number(byId('peopleCostRole').value); status.textContent = 'Salvando…';
    const body = { starts_on: byId('peopleCostStart').value, ends_on: byId('peopleCostEnd').value || null, currency: byId('peopleCostCurrency').value.trim().toUpperCase() };
    [['base_salary', 'peopleCostBaseSalary'], ['charges', 'peopleCostCharges'], ['benefits', 'peopleCostBenefits'], ['other_costs', 'peopleCostOtherCosts']].forEach(([key, id]) => { body[key] = byId(id).value || null; });
    try { await request(`/api/companies/${companyId}/roles/${roleId}/cost-profiles`, {method: 'POST', body: JSON.stringify(body)}); closeDialog('peopleCostDialog'); byId('peopleCostsDate').value = body.starts_on; await loadCosts(); }
    catch (error) { status.textContent = error.message; }
  }
  async function fetchOccupancy(date) { return request(`/api/companies/${companyId}/occupancy-snapshot?as_of=${encodeURIComponent(date)}`); }
  async function loadOccupancy(event) { if (event) event.preventDefault(); const status = byId('peopleOccupancyStatus'); const date = byId('peopleOccupancyDate').value; status.textContent = 'Consultando…'; try { const data = await fetchOccupancy(date); renderOccupancyRows('peopleOccupancyRows', data.assignments, true); status.textContent = `${data.as_of}: ${data.distinct_people_count || 0} pessoas. ${data.legacy_reconciliation_complete ? 'Histórico reconciliado.' : 'Há cadastros atuais pendentes de vigência formal.'}`; } catch (error) { status.textContent = error.message; } }
  async function fetchCosts(date) { return request(`/api/companies/${companyId}/planned-role-costs?as_of=${encodeURIComponent(date)}`); }
  async function loadCosts() { const status = byId('peopleCostsStatus'); const date = byId('peopleCostsDate').value; status.textContent = 'Consultando…'; try { renderCostSnapshot(await fetchCosts(date), { rows: 'peopleCostsRows', total: 'peopleCostsTotal', status: 'peopleCostsStatus' }); } catch (error) { status.textContent = error.message; } }
  async function loadReportOccupancy(event) { event.preventDefault(); const status = byId('peopleReportOccupancyStatus'); status.textContent = 'Gerando relatório…'; try { const data = await fetchOccupancy(byId('peopleReportOccupancyDate').value); renderOccupancyRows('peopleReportOccupancyRows', data.assignments); status.textContent = `${data.as_of}: ${data.distinct_people_count || 0} pessoas em ocupações.`; } catch (error) { status.textContent = error.message; } }
  async function loadReportCosts(event) { event.preventDefault(); const status = byId('peopleReportCostsStatus'); status.textContent = 'Gerando relatório…'; try { renderCostSnapshot(await fetchCosts(byId('peopleReportCostsDate').value), { rows: 'peopleReportCostsRows', total: 'peopleReportCostsTotal', status: 'peopleReportCostsStatus' }); } catch (error) { status.textContent = error.message; } }
  document.querySelectorAll('[data-people-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.peopleTab)));
  document.querySelectorAll('[data-people-open]').forEach(button => button.addEventListener('click', () => ({user:openUser, role:openRole, employee:openEmployee, occupancy:openOccupancy, cost:openCost}[button.dataset.peopleOpen]())));
  document.querySelectorAll('[data-people-close]').forEach(button => button.addEventListener('click', () => closeDialog(button.dataset.peopleClose)));
  document.querySelectorAll('[data-people-role-view]').forEach(button => button.addEventListener('click', () => showRoleView(button.dataset.peopleRoleView)));
  document.querySelectorAll('[data-people-employee-view]').forEach(button => button.addEventListener('click', () => showEmployeeView(button.dataset.peopleEmployeeView)));
  document.querySelectorAll('[data-people-report-view]').forEach(button => button.addEventListener('click', () => showReportView(button.dataset.peopleReportView)));
  byId('peopleUserSearch')?.addEventListener('input', renderUsers); byId('peopleUserProfile')?.addEventListener('change', renderUsers); byId('peopleEmployeeSearch')?.addEventListener('input', renderEmployees);
  byId('peopleOrgSearch')?.addEventListener('input', event => { state.org.search = event.target.value; renderOrg(); });
  byId('peopleOrgDepartment')?.addEventListener('change', event => { state.org.department = event.target.value; renderOrg(); });
  byId('peopleOrgLayout')?.addEventListener('change', event => { state.org.layout = event.target.value; renderOrg(); });
  document.querySelectorAll('[data-people-org-action]').forEach(button => button.addEventListener('click', async () => {
    const action = button.dataset.peopleOrgAction;
    if (action === 'fit') return fitOrgTree();
    if (action === 'expand') { state.org.collapsedIds.clear(); return renderOrg(); }
    if (action === 'collapse') { flattenOrgTree(state.workspace?.roles_tree || []).filter(node => node.children?.length).forEach(node => state.org.collapsedIds.add(Number(node.id))); return renderOrg(); }
    if (action === 'export-png') {
      button.disabled = true; setOrgExportStatus('Gerando imagem do organograma…');
      try { const exported = await exportOrgPng(); const relationships = Number(exported.relationshipCount || 0); setOrgExportStatus(`Imagem exportada com sucesso. ${relationships} vínculo${relationships === 1 ? '' : 's'} hierárquico${relationships === 1 ? '' : 's'} reproduzido${relationships === 1 ? '' : 's'}.`); }
      catch (error) { setOrgExportStatus(error.message || 'Não foi possível exportar a imagem.', true); }
      finally { button.disabled = false; }
      return;
    }
    if (action === 'zoom-in') state.org.scale = Math.min(1.5, state.org.scale + .1);
    if (action === 'zoom-out') state.org.scale = Math.max(.35, state.org.scale - .1);
    if (action === 'zoom-reset') state.org.scale = 1;
    updateOrgScale();
  }));
  byId('peopleUserForm')?.addEventListener('submit', saveUser); byId('peopleRoleForm')?.addEventListener('submit', saveRole); byId('peopleEmployeeForm')?.addEventListener('submit', saveEmployee); byId('peopleOccupancyCreateForm')?.addEventListener('submit', saveOccupancy); byId('peopleCostForm')?.addEventListener('submit', saveCost);
  byId('peopleOccupancyForm')?.addEventListener('submit', loadOccupancy); byId('peopleCostsSearch')?.addEventListener('click', loadCosts); byId('peopleReportOccupancyForm')?.addEventListener('submit', loadReportOccupancy); byId('peopleReportCostsForm')?.addEventListener('submit', loadReportCosts);
  document.addEventListener('click', event => { const user = event.target.closest('[data-edit-user]'); const role = event.target.closest('[data-edit-role]'); const employee = event.target.closest('[data-edit-employee]'); if (user) openUser(user.dataset.editUser); if (role) openRole(role.dataset.editRole); if (employee) openEmployee(employee.dataset.editEmployee); });
  ['peopleOccupancyDate', 'peopleCostsDate', 'peopleReportOccupancyDate', 'peopleReportCostsDate'].forEach(id => { if (byId(id)) byId(id).value = today(); });
  loadWorkspace().catch(error => { const target = byId('peopleUsersRows'); if (target) target.innerHTML = `<tr><td colspan="5">${esc(error.message)}</td></tr>`; });
})();
