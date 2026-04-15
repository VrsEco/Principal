(function () {
    const app = document.getElementById('factoryApp');
    if (!app) return;

    const parseJson = (name) => {
        try {
            return JSON.parse(app.dataset[name] || '{}');
        } catch (error) {
            console.error(`Falha ao ler dataset ${name}`, error);
            return {};
        }
    };

    const state = {
        actor: parseJson('actor'),
        registry: parseJson('registry'),
        surface: parseJson('surface'),
        assessment: parseJson('assessment'),
    };

    const metricsEl = document.getElementById('factoryMetrics');
    const actorSummaryEl = document.getElementById('factoryActorSummary');
    const capabilitiesEl = document.getElementById('factoryCapabilities');
    const externalSurfaceEl = document.getElementById('externalSurfacePanel');
    const assessmentEl = document.getElementById('factoryAssessment');
    const examplesEl = document.getElementById('factoryExamples');
    const form = document.getElementById('factoryForm');
    const resetBtn = document.getElementById('factoryReset');

    const examples = [
        'Precisamos evoluir o workflow XYZ pois não está entregando corretamente os resultados.',
        'Precisamos melhorar a cognição do Sapiens para entender melhor o que se está perguntando.',
        'Precisamos criar uma nova função completa para consultar os resultados financeiros da empresa.',
        'Precisamos dar manutenção na tool xyz pois está dando erro.',
    ];

    function riskClass(risk) {
        if (risk === 'high' || risk === 'critical') return 'factory-badge-risk risk-high';
        if (risk === 'medium') return 'factory-badge-risk risk-medium';
        return 'factory-badge-risk risk-low';
    }

    function renderMetrics() {
        const summary = state.registry.summary || {};
        const metrics = [
            { label: 'Capacidades', value: summary.capabilities || 0 },
            { label: 'Domínios', value: summary.domains || 0 },
            { label: 'Pilotos', value: summary.pilot_capabilities || 0 },
            { label: 'Tenant ativo', value: state.actor.company_id || 'n/d' },
        ];
        metricsEl.innerHTML = metrics.map((item) => `
            <div class="factory-metric">
                <div class="factory-metric-label">${item.label}</div>
                <div class="factory-metric-value">${item.value}</div>
            </div>
        `).join('');
    }

    function renderActor() {
        actorSummaryEl.innerHTML = `
            <div><strong>Usuário:</strong> ${state.actor.user_id || 'n/d'}</div>
            <div><strong>Perfil:</strong> ${state.actor.role || 'n/d'}</div>
            <div><strong>Canal:</strong> ${state.actor.channel || 'web'}</div>
            <div><strong>Empresa ativa:</strong> ${state.actor.company_id || 'n/d'}</div>
            <div><strong>Escopos acessíveis:</strong> ${(state.actor.accessible_company_ids || []).join(', ') || 'n/d'}</div>
        `;
    }

    function renderCapabilities() {
        const capabilities = state.registry.capabilities || [];
        capabilitiesEl.innerHTML = capabilities.map((item) => `
            <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50">
                <div class="flex items-center justify-between gap-3">
                    <div>
                        <div class="font-bold text-slate-900">${item.title}</div>
                        <div class="text-sm text-slate-500">${item.key} • ${item.domain}</div>
                    </div>
                    <span class="factory-chip">${item.status}</span>
                </div>
                <p class="text-sm text-slate-700 mt-3">${item.description}</p>
                <div class="factory-chip-row">
                    ${(item.layers || []).map((layer) => `<span class="factory-chip">${layer}</span>`).join('')}
                </div>
            </div>
        `).join('');
    }

    function renderSurface() {
        const strategy = state.surface.current_strategy || {};
        externalSurfaceEl.innerHTML = `
            <div class="factory-highlight">
                <div><strong>Estratégia:</strong> ${strategy.mode || 'n/d'}</div>
                <div class="mt-2">${strategy.decision || ''}</div>
            </div>
            <div>
                <h3 class="factory-result-title">Escopo atual</h3>
                <ul class="factory-list">${(state.surface.current_scope || []).map((item) => `<li>${item}</li>`).join('')}</ul>
            </div>
            <div>
                <h3 class="factory-result-title">Próxima expansão</h3>
                <ul class="factory-list">${(state.surface.future_scope || []).map((item) => `<li>${item}</li>`).join('')}</ul>
            </div>
            <div>
                <h3 class="factory-result-title">Guardrails</h3>
                <ul class="factory-list">${(state.surface.guardrails || []).map((item) => `<li>${item}</li>`).join('')}</ul>
            </div>
        `;
    }

    function renderAssessment() {
        const data = state.assessment || {};
        if (!data.request) {
            assessmentEl.innerHTML = '<div class="text-sm text-slate-500">Nenhum assessment disponível.</div>';
            return;
        }
        const dependencies = (data.related_capabilities || []).length
            ? (data.related_capabilities || []).map((item) => `<li>${item}</li>`).join('')
            : '<li>Nenhuma capability relacionada mapeada.</li>';
        assessmentEl.innerHTML = `
            <div class="border border-slate-200 rounded-2xl p-4 bg-white">
                <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                        <div class="text-xs uppercase tracking-[0.24em] text-slate-500">Pedido classificado</div>
                        <div class="font-bold text-slate-900 mt-1">${data.request.target_object || data.request.request_text}</div>
                    </div>
                    <span class="${riskClass(data.risk_level)}">risco ${data.risk_level || 'n/d'}</span>
                </div>
                <div class="factory-chip-row">
                    <span class="factory-chip">${data.request.change_type || 'diagnose'}</span>
                    ${(data.request.target_layers || []).map((layer) => `<span class="factory-chip">${layer}</span>`).join('')}
                </div>
                <div class="grid md:grid-cols-2 gap-4 mt-4">
                    <div>
                        <h3 class="factory-result-title">Próximos passos</h3>
                        <ul class="factory-list">${(data.next_steps || []).map((item) => `<li>${item}</li>`).join('')}</ul>
                    </div>
                    <div>
                        <h3 class="factory-result-title">Artefatos recomendados</h3>
                        <ul class="factory-list">${(data.recommended_artifacts || []).map((item) => `<li>${item}</li>`).join('')}</ul>
                    </div>
                </div>
                <div class="grid md:grid-cols-2 gap-4 mt-4">
                    <div>
                        <h3 class="factory-result-title">Governança</h3>
                        <ul class="factory-list">
                            <li>Human gate: ${data.human_gate_required ? 'obrigatório' : 'não obrigatório'}</li>
                            <li>Domínio: ${data.request.domain || 'engineering'}</li>
                            <li>Modo: ${data.request.execution_mode || 'diagnose'}</li>
                        </ul>
                    </div>
                    <div>
                        <h3 class="factory-result-title">Dependências traçadas</h3>
                        <ul class="factory-list">${dependencies}</ul>
                    </div>
                </div>
            </div>
        `;
    }

    function renderExamples() {
        examplesEl.innerHTML = examples.map((text) => `
            <button type="button" class="factory-example" data-example="${text.replace(/"/g, '&quot;')}">${text}</button>
        `).join('');
        examplesEl.querySelectorAll('[data-example]').forEach((button) => {
            button.addEventListener('click', () => {
                form.request_text.value = button.dataset.example || '';
                form.request_text.focus();
            });
        });
    }

    async function loadContext() {
        try {
            const response = await fetch('/api/configs/ai/factory/context');
            const payload = await response.json();
            if (payload.success) {
                state.actor = payload.actor || state.actor;
                state.registry = payload.registry || state.registry;
                state.surface = payload.external_surface || state.surface;
                renderMetrics();
                renderActor();
                renderCapabilities();
                renderSurface();
            }
        } catch (error) {
            console.error('Falha ao carregar contexto da factory', error);
        }
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const payload = {
            request_text: form.request_text.value,
            change_type: form.change_type.value || null,
            execution_mode: form.execution_mode.value,
            urgency: form.urgency.value,
            domain: form.domain.value || null,
            target_object: form.target_object.value || null,
            desired_outcome: form.desired_outcome.value || null,
        };
        assessmentEl.innerHTML = '<div class="text-sm text-slate-500">Validando solicitação...</div>';
        try {
            const response = await fetch('/api/configs/ai/factory/assess-change', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(Array.isArray(data.error) ? JSON.stringify(data.error) : (data.error || 'Falha ao validar solicitação.'));
            }
            state.assessment = data.assessment || {};
            renderAssessment();
        } catch (error) {
            assessmentEl.innerHTML = `<div class="text-sm text-red-600 font-semibold">Falha ao validar: ${error.message}</div>`;
        }
    });

    resetBtn.addEventListener('click', () => {
        form.reset();
        state.assessment = parseJson('assessment');
        renderAssessment();
    });

    renderMetrics();
    renderActor();
    renderCapabilities();
    renderSurface();
    renderAssessment();
    renderExamples();
    loadContext();
})();
