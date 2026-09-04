(() => {
    'use strict';
    const form = document.getElementById('identityCostCreate');
    if (!form) return;
    const byId = id => document.getElementById(id);
    const companyId = Number(document.querySelector('.identity-shell').dataset.companyId);
    const status = byId('identityCostCreateStatus');
    byId('identityCostLoadRoles').addEventListener('click', async () => {
        const button = byId('identityCostLoadRoles');
        button.disabled = true;
        try {
            const response = await fetch(`/api/companies/${companyId}/identity/summary`);
            if (!response.ok) throw new Error('Não foi possível carregar cargos.');
            const data = await response.json();
            const select = byId('identityCostRole');
            select.replaceChildren(new Option('Selecione um cargo', ''));
            for (const role of data.roles || []) select.add(new Option(role.title, String(role.id)));
            status.textContent = '';
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = false; }
    });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const button = byId('identityCostCreateSave');
        if (button.disabled) return;
        const roleId = Number(byId('identityCostRole').value);
        const payload = { starts_on: byId('identityCostStart').value,
            ends_on: byId('identityCostEnd').value || null, currency: byId('identityCostCurrency').value };
        if (payload.ends_on && payload.ends_on <= payload.starts_on) {
            status.textContent = 'Fim deve ser posterior ao início.'; return;
        }
        for (const field of ['base_salary', 'charges', 'benefits', 'other_costs']) payload[field] = byId(`identityCost_${field}`).value || null;
        const label = byId('identityCostRole').selectedOptions[0].textContent;
        if (!window.confirm(`Salvar novo perfil de ${label}, moeda ${payload.currency}, início ${payload.starts_on}? Não substituirá perfis existentes.`)) return;
        button.disabled = true;
        status.textContent = 'Salvando…';
        try {
            const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
            const token = document.querySelector('meta[name="csrf-token"]')?.content;
            if (token) headers['X-CSRFToken'] = token;
            const response = await fetch(`/api/companies/${companyId}/roles/${roleId}/cost-profiles`, { method: 'POST', headers, body: JSON.stringify(payload) });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.error || 'Não foi possível salvar o perfil.');
            form.reset();
            status.textContent = `Perfil ${data.id} salvo. Consulte os custos na data de vigência para conferir.`;
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = false; }
    });
})();
