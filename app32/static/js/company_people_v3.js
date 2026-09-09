(() => {
  'use strict';
  const root = document.querySelector('.people-page');
  if (!root) return;
  const companyId = Number(root.dataset.companyId);
  const canManage = root.dataset.canManage === 'true';
  const canViewCosts = root.dataset.canViewCosts === 'true';
  const state = { workspace: null, activeTab: 'users', roleView: 'profile', employeeView: 'profile' };
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
  function renderAll() { renderMetrics(); renderUsers(); renderRoles(); renderOrg(); renderEmployees(); }
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
  function renderRoles() {
    const body = byId('peopleRolesRows'); if (!body) return;
    const roles = state.workspace.roles || [];
    const byIdRole = new Map(roles.map(role => [Number(role.id), role]));
    body.innerHTML = roles.length ? roles.map(role => `<tr><td><b>${esc(role.title)}</b>${state.roleView === 'profile' && role.qualification_requirements ? `<span class="people-cell-note">${esc(role.qualification_requirements)}</span>` : ''}</td><td>${esc(role.department || '—')}</td><td>${esc(byIdRole.get(Number(role.parent_role_id))?.title || '—')}</td><td>${role.headcount_planned ?? 0}</td><td>${role.active_employee_count ?? 0}</td><td>${role.vacancy_count ?? 0}</td><td class="people-actions-col">${canManage ? `<button class="people-action" type="button" data-edit-role="${role.id}">Editar</button>` : ''}</td></tr>`).join('') : '<tr><td colspan="7">Nenhum cargo cadastrado.</td></tr>';
  }
  function renderOrgNode(node) {
    return `<div class="people-org-node"><div class="people-org-node__card" style="--node-color:${esc(node.color || '#2563eb')}"><strong>${esc(node.title)}</strong><span>${esc(node.department || 'Área não informada')}</span><small>${node.active_employee_count || 0} de ${node.headcount_planned || 0} ocupadas</small></div>${node.children?.length ? `<div class="people-org-children">${node.children.map(renderOrgNode).join('')}</div>` : ''}</div>`;
  }
  function renderOrg() {
    const target = byId('peopleOrgChart'); if (!target) return;
    const tree = state.workspace.roles_tree || [];
    target.innerHTML = tree.length ? `<div class="people-org-root">${tree.map(renderOrgNode).join('')}</div>` : '<p class="people-status">Cadastre o primeiro cargo para formar o organograma.</p>';
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
  function showTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('[data-people-tab]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleTab === tab));
    document.querySelectorAll('[data-people-panel]').forEach(panel => panel.classList.toggle('is-active', panel.dataset.peoplePanel === tab));
  }
  function showEmployeeView(view) {
    state.employeeView = view;
    document.querySelectorAll('[data-people-employee-view]').forEach(button => button.classList.toggle('is-active', button.dataset.peopleEmployeeView === view));
    document.querySelectorAll('[data-people-employee-panel]').forEach(panel => panel.hidden = panel.dataset.peopleEmployeePanel !== view);
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
  async function loadOccupancy(event) { event.preventDefault(); const status = byId('peopleOccupancyStatus'); const date = byId('peopleOccupancyDate').value; status.textContent = 'Consultando…'; try { const data = await request(`/api/companies/${companyId}/occupancy-snapshot?as_of=${encodeURIComponent(date)}`); byId('peopleOccupancyRows').innerHTML = data.assignments?.length ? data.assignments.map(item => `<tr><td>${esc(item.employee_name)}</td><td>${esc(item.role_title)}</td><td>${esc(item.weekly_hours || '—')}</td><td>${item.source === 'temporal' ? 'Vigência registrada' : 'Cadastro atual'}</td></tr>`).join('') : '<tr><td colspan="4">Nenhuma ocupação encontrada na data.</td></tr>'; status.textContent = `Referência: ${esc(data.as_of)}.`; } catch (error) { status.textContent = error.message; } }
  async function loadCosts(event) { event.preventDefault(); const status = byId('peopleCostsStatus'); const date = byId('peopleCostsDate').value; status.textContent = 'Consultando…'; try { const data = await request(`/api/companies/${companyId}/planned-role-costs?as_of=${encodeURIComponent(date)}`); byId('peopleCostsRows').innerHTML = data.roles?.length ? data.roles.map(item => `<tr><td>${esc(item.role_title)}</td><td>${item.planned_monthly_cost == null ? 'Não informado' : `${esc(data.currency || 'BRL')} ${esc(item.planned_monthly_cost)}`}</td></tr>`).join('') : '<tr><td colspan="2">Nenhum cargo encontrado.</td></tr>'; byId('peopleCostsTotal').textContent = data.planned_monthly_total == null ? 'Total planejado: não informado.' : `Total mensal planejado: ${data.currency || 'BRL'} ${data.planned_monthly_total}`; status.textContent = `Referência: ${esc(data.as_of)}.`; } catch (error) { status.textContent = error.message; } }
  document.querySelectorAll('[data-people-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.peopleTab)));
  document.querySelectorAll('[data-people-open]').forEach(button => button.addEventListener('click', () => ({user:openUser, role:openRole, employee:openEmployee}[button.dataset.peopleOpen]())));
  document.querySelectorAll('[data-people-close]').forEach(button => button.addEventListener('click', () => closeDialog(button.dataset.peopleClose)));
  document.querySelectorAll('[data-people-role-view]').forEach(button => button.addEventListener('click', () => { state.roleView = button.dataset.peopleRoleView; document.querySelectorAll('[data-people-role-view]').forEach(item => item.classList.toggle('is-active', item === button)); renderRoles(); }));
  document.querySelectorAll('[data-people-employee-view]').forEach(button => button.addEventListener('click', () => showEmployeeView(button.dataset.peopleEmployeeView)));
  byId('peopleUserSearch')?.addEventListener('input', renderUsers); byId('peopleUserProfile')?.addEventListener('change', renderUsers); byId('peopleEmployeeSearch')?.addEventListener('input', renderEmployees);
  byId('peopleUserForm')?.addEventListener('submit', saveUser); byId('peopleRoleForm')?.addEventListener('submit', saveRole); byId('peopleEmployeeForm')?.addEventListener('submit', saveEmployee);
  byId('peopleOccupancyForm')?.addEventListener('submit', loadOccupancy); byId('peopleCostsForm')?.addEventListener('submit', loadCosts);
  document.addEventListener('click', event => { const user = event.target.closest('[data-edit-user]'); const role = event.target.closest('[data-edit-role]'); const employee = event.target.closest('[data-edit-employee]'); if (user) openUser(user.dataset.editUser); if (role) openRole(role.dataset.editRole); if (employee) openEmployee(employee.dataset.editEmployee); const report = event.target.closest('[data-people-report]'); if (report) { showTab('employees'); showEmployeeView(report.dataset.peopleReport === 'capacity' ? 'profile' : report.dataset.peopleReport); } });
  if (byId('peopleOccupancyDate')) byId('peopleOccupancyDate').value = today(); if (byId('peopleCostsDate')) byId('peopleCostsDate').value = today();
  loadWorkspace().catch(error => { const target = byId('peopleUsersRows'); if (target) target.innerHTML = `<tr><td colspan="5">${esc(error.message)}</td></tr>`; });
})();
