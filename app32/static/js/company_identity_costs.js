(() => {
    'use strict';
    const form = document.getElementById('identityCostQuery');
    if (!form) return; // Usuário sem permissão: nenhuma requisição de custo.
    const byId = id => document.getElementById(id);
    const companyId = Number(document.querySelector('.identity-shell').dataset.companyId);
    const today = new Date();
    byId('identityCostDate').value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    function renderRow(label, amount) {
        const row = document.createElement('tr');
        for (const value of [label, amount]) {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        }
        byId('identityCostRows').appendChild(row);
    }
    function amount(value, currency) {
        if (value === null || value === undefined) return 'Não informado';
        // Preserva representação decimal recebida, sem perda de precisão por Number.
        return `${currency || ''} ${String(value)}`.trim();
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const button = byId('identityCostSearch');
        if (button.disabled) return;
        const reference = byId('identityCostDate').value;
        button.disabled = true;
        byId('identityCostRows').replaceChildren();
        byId('identityCostTotals').textContent = '';
        byId('identityCostStatus').textContent = 'Consultando custos…';
        try {
            const response = await fetch(`/api/companies/${companyId}/planned-role-costs?as_of=${encodeURIComponent(reference)}`, { headers: { Accept: 'application/json' } });
            if (!response.ok) {
                const body = await response.json().catch(() => ({}));
                throw new Error(body.error || 'Consulta de custos indisponível.');
            }
            const result = await response.json();
            byId('identityCostStatus').textContent = `${result.as_of}: ${result.costed_roles_count} de ${result.total_roles_count} cargos com custo completo.`;
            byId('identityCostTotals').textContent = result.planned_monthly_total === null
                ? `Total incompleto. Subtotal conhecido: ${amount(result.known_planned_monthly_subtotal, result.currency)}.`
                : `Total mensal planejado: ${amount(result.planned_monthly_total, result.currency)}.`;
            for (const role of result.roles || []) renderRow(role.role_title || `Cargo ${role.role_id}`, amount(role.planned_monthly_cost, result.currency));
            if (!(result.roles || []).length) renderRow('Nenhum cargo cadastrado', '—');
        } catch (error) {
            byId('identityCostStatus').textContent = error.message;
            byId('identityCostTotals').textContent = 'Não foi possível apurar os custos. Não interprete a falha como custo zero.';
        } finally { button.disabled = false; }
    });
})();
