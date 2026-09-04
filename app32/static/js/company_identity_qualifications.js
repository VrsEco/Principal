(() => {
    'use strict';
    const form = document.getElementById('identityQualificationForm');
    if (!form) return;
    const byId = id => document.getElementById(id);
    const companyId = Number(document.querySelector('.identity-shell')?.dataset.companyId || 0);
    const status = byId('identityQualificationStatus');
    const listStatus = byId('identityQualificationListStatus');
    const rows = byId('identityQualificationRows');
    const statusLabel = {no_expiry: 'Sem validade', expired: 'Expirada', expires_soon: 'Vence em breve', valid: 'Válida'};
    function showEvidence(items) {
        rows.replaceChildren();
        if (!items.length) {
            const cell = document.createElement('td'); cell.colSpan = 3; cell.textContent = 'Nenhuma evidência registrada.';
            rows.append(document.createElement('tr')).append(cell); return;
        }
        for (const item of items) {
            const row = document.createElement('tr');
            const qualification = item.level ? `${item.qualification_name} — ${item.level}` : item.qualification_name;
            for (const value of [qualification, item.evidence_source, `${statusLabel[item.validity_status] || 'Não informado'}${item.expires_on ? ` (${item.expires_on})` : ''}`]) {
                const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
            }
            rows.append(row);
        }
    }
    async function loadEvidence() {
        const employeeId = Number(byId('identityQualificationEmployee').value);
        if (!employeeId) return;
        listStatus.textContent = 'Carregando evidências…';
        try {
            const response = await fetch(`/api/companies/${companyId}/employees/${employeeId}/qualification-evidences`, {headers: {Accept: 'application/json'}});
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.error || 'Não foi possível carregar as evidências.');
            showEvidence(result.items || []);
            listStatus.textContent = 'A situação exibida é somente da validade; aderência ao cargo não foi avaliada.';
        } catch (error) { listStatus.textContent = error.message; }
    }
    async function loadEmployees() {
        try {
            const response = await fetch(`/api/companies/${companyId}/identity/summary`, {headers: {Accept: 'application/json'}});
            if (!response.ok) throw new Error('Não foi possível carregar colaboradores.');
            const result = await response.json();
            const select = byId('identityQualificationEmployee');
            select.replaceChildren(new Option('Selecione o colaborador', ''));
            for (const employee of result.employees || []) select.add(new Option(employee.name, String(employee.id)));
        } catch (error) { status.textContent = error.message; }
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const button = byId('identityQualificationSave');
        if (button.disabled) return;
        const employeeId = Number(byId('identityQualificationEmployee').value);
        const payload = {qualification_name: byId('identityQualificationName').value.trim(), level: byId('identityQualificationLevel').value.trim() || null, evidence_source: byId('identityQualificationSource').value, evidence_reference: byId('identityQualificationReference').value.trim() || null, expires_on: byId('identityQualificationExpiry').value || null};
        if (!window.confirm(`Registrar a evidência “${payload.qualification_name}”? Isto não confirma aderência ao cargo.`)) return;
        button.disabled = true; status.textContent = 'Registrando…';
        try {
            const headers = {'Content-Type': 'application/json', Accept: 'application/json'};
            const token = document.querySelector('meta[name="csrf-token"]')?.content;
            if (token) headers['X-CSRFToken'] = token;
            const response = await fetch(`/api/companies/${companyId}/employees/${employeeId}/qualification-evidences`, {method: 'POST', headers, body: JSON.stringify(payload)});
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.error || 'Não foi possível registrar a evidência.');
            const selectedEmployee = byId('identityQualificationEmployee').value;
            form.reset(); byId('identityQualificationEmployee').value = selectedEmployee;
            status.textContent = 'Evidência registrada. A aderência ao cargo continua pendente de análise.';
            await loadEvidence();
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = false; }
    });
    byId('identityQualificationEmployee').addEventListener('change', loadEvidence);
    loadEmployees();
})();
