document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('aiMcpConsolePage');
    if (!root) return;
    const consoleState = (() => {
        try {
            return JSON.parse(root.dataset.console || '{}');
        } catch (_error) {
            return {};
        }
    })();

    const tabs = Array.from(root.querySelectorAll('[data-console-tab]'));
    const panels = Array.from(root.querySelectorAll('[data-console-panel]'));
    const searchInput = document.getElementById('aiMcpConsoleSearch');
    const wizardButtons = Array.from(document.querySelectorAll('[data-console-go-tab]'));
    const decisionCards = Array.from(root.querySelectorAll('.ai-mcp-decision-card'));
    const helpTitle = document.getElementById('aiMcpContextHelpTitle');
    const helpBody = document.getElementById('aiMcpContextHelpBody');
    const helpSteps = document.getElementById('aiMcpContextHelpSteps');
    const wizardChoiceCards = Array.from(root.querySelectorAll('[data-wizard-choice]'));
    const wizardStepPills = Array.from(root.querySelectorAll('[data-wizard-step-pill]'));
    const wizardSteps = Array.from(root.querySelectorAll('[data-wizard-step]'));
    const wizardResult = document.getElementById('aiMcpWizardResult');
    const wizardResultTitle = document.getElementById('aiMcpWizardResultTitle');
    const wizardResultText = document.getElementById('aiMcpWizardText');
    const wizardGo = document.getElementById('aiMcpWizardGo');
    const wizardSearch = document.getElementById('aiMcpWizardSearch');
    const wizardReset = document.getElementById('aiMcpWizardReset');
    const wizardTranscript = document.getElementById('aiMcpWizardTranscript');
    const wizardTranscriptList = document.getElementById('aiMcpWizardTranscriptList');
    const assistantActions = Array.from(root.querySelectorAll('[data-assistant-action]'));
    const collapsibleCards = Array.from(root.querySelectorAll('.ai-mcp-panels .ai-mcp-card'));
    const panelToggles = Array.from(root.querySelectorAll('[data-panel-toggle]'));
    const wizardStages = Array.from(root.querySelectorAll('[data-wizard-stage]'));
    const stageToggles = Array.from(root.querySelectorAll('[data-stage-toggle]'));
    const connectionGenerator = document.getElementById('aiMcpConnectionGenerator');
    const documentationBootstrap = document.getElementById('aiMcpDocumentationBootstrap');
    const bootstrapStatus = document.getElementById('aiMcpBootstrapStatus');
    const bootstrapMeta = document.getElementById('aiMcpBootstrapMeta');
    const bootstrapResultTitle = document.getElementById('aiMcpBootstrapResultTitle');
    const bootstrapResultText = document.getElementById('aiMcpBootstrapResultText');
    const bootstrapResultMeta = document.getElementById('aiMcpBootstrapResultMeta');
    const bootstrapFeatureList = document.getElementById('aiMcpBootstrapFeatureList');
    const bootstrapContextRequired = document.getElementById('aiMcpBootstrapContextRequired');
    const bootstrapContextResolved = document.getElementById('aiMcpBootstrapContextResolved');
    const bootstrapContextResolution = document.getElementById('aiMcpBootstrapContextResolution');
    const bootstrapContextSummary = document.getElementById('aiMcpBootstrapContextSummary');
    const runtimeContextSummary = document.getElementById('aiMcpRuntimeContextSummary');
    const runtimeContextMeta = document.getElementById('aiMcpRuntimeContextMeta');
    const runtimeContextSource = document.getElementById('aiMcpRuntimeContextSource');
    const runtimeContextBadges = document.getElementById('aiMcpRuntimeContextBadges');
    const connectionModeButtons = Array.from(root.querySelectorAll('[data-connection-mode]'));
    const connectionFeedback = document.getElementById('aiMcpConnectionFeedback');
    const connectionResult = document.getElementById('aiMcpConnectionResult');
    const connectionResultTitle = document.getElementById('aiMcpConnectionResultTitle');
    const connectionResultDescription = document.getElementById('aiMcpConnectionResultDescription');
    const connectionOutput = document.getElementById('aiMcpConnectionOutput');
    const connectionSourceJson = document.getElementById('aiMcpConnectionSourceJson');
    const connectionCopyButton = document.getElementById('aiMcpConnectionCopyButton');
    const registryEntriesCount = document.getElementById('aiMcpRegistryEntriesCount');
    const registryActiveEntriesCount = document.getElementById('aiMcpRegistryActiveEntriesCount');
    const registryTenantOverridesCount = document.getElementById('aiMcpRegistryTenantOverridesCount');
    const registryChannelsCount = document.getElementById('aiMcpRegistryChannelsCount');
    const registryChannelsList = document.getElementById('aiMcpRegistryChannelsList');
    const registryRuntimesCount = document.getElementById('aiMcpRegistryRuntimesCount');
    const registryRuntimesList = document.getElementById('aiMcpRegistryRuntimesList');
    const registryEntriesList = document.getElementById('aiMcpRegistryEntriesList');
    const registryAuditList = document.getElementById('aiMcpRegistryAuditList');
    const registryChangesList = document.getElementById('aiMcpRegistryChangesList');
    const registryFeedback = document.getElementById('aiMcpRegistryFeedback');
    const registrySaveButton = document.getElementById('aiMcpRegistrySaveButton');
    const registryRefreshButton = document.getElementById('aiMcpRegistryRefreshButton');
    const registryInvalidateButton = document.getElementById('aiMcpRegistryInvalidateButton');
    const registryResetFormButton = document.getElementById('aiMcpRegistryResetFormButton');
    const registryEditorMode = document.getElementById('aiMcpRegistryEditorMode');
    const registryEditorDescription = document.getElementById('aiMcpRegistryEditorDescription');
    const registryFilterRuntime = document.getElementById('aiMcpRegistryFilterRuntime');
    const registryFilterChannel = document.getElementById('aiMcpRegistryFilterChannel');
    const registryFilterStatus = document.getElementById('aiMcpRegistryFilterStatus');
    const registryFilterRollout = document.getElementById('aiMcpRegistryFilterRollout');
    const registryFilterEnvironment = document.getElementById('aiMcpRegistryFilterEnvironment');
    const registryFilterCompanyId = document.getElementById('aiMcpRegistryFilterCompanyId');

    const helpTopics = {
        overview: {
            title: 'Visão geral',
            body: 'Comece aqui quando ainda não estiver certo do que precisa. Esta área resume o console e aponta o caminho mais curto para configurar, testar ou operar.',
            steps: [
                'Leia os atalhos rápidos antes de clicar em qualquer tela técnica.',
                'Use a busca quando souber a palavra-chave do que procura.',
                'Se estiver em dúvida, siga para Onboarding e volte depois.'
            ]
        },
        profiles: {
            title: 'Perfis e permissões',
            body: 'Use esta seção para entender quem pode fazer o quê. Ela reduz risco antes de liberar acesso ou pedir alteração de perfil.',
            steps: [
                'Compare colaborador, cliente, administrador e admin técnico.',
                'Observe o risco permitido sem gate humano.',
                'Valide se a permissão cobre o domínio certo antes de avançar.'
            ]
        },
        surfaces: {
            title: 'Surfaces e domínios',
            body: 'Use esta tela para localizar onde cada assunto mora. Ela evita saltar entre sistemas e reduz dúvida operacional.',
            steps: [
                'Confira qual surface deve ser usada: user, admin, analytics ou ops.',
                'Abra o domínio e leia as tools canônicas disponíveis.',
                'Quando houver conflito, volte ao playbook da surface.'
            ]
        },
        catalog: {
            title: 'Catálogo',
            body: 'Aqui você enxerga as tools disponíveis e o nível de risco. É a tela certa para decidir se algo pode ser usado ou precisa de gate.',
            steps: [
                'Verifique o risco antes de testar uma tool.',
                'Confirme em qual domínio a tool está classificada.',
                'Se a tool for crítica, prefira validar primeiro em leitura.'
            ]
        },
        onboarding: {
            title: 'Onboarding e cadastros',
            body: 'Use este bloco para configurar o ambiente e organizar cadastros de forma guiada. Ele foi pensado para diminuir retrabalho.',
            steps: [
                'Comece pela empresa ativa e pelo perfil do usuário.',
                'Abra o fluxo guiado de configuração antes de tentar operar.',
                'Finalize lendo os requisitos de surface e evidência.'
            ]
        },
        release: {
            title: 'Release e freeze',
            body: 'Esta é a área para deixar tudo pronto para teste com menor surpresa possível. Ela cobre checklist, smokes e congelamento de tool.',
            steps: [
                'Confirme os gates antes de qualquer liberação.',
                'Revise os smokes pós-deploy obrigatórios.',
                'Se houver risco, congele a tool e siga o procedimento.'
            ]
        },
        dashboard: {
            title: 'Dashboard e readiness',
            body: 'Use a tela de observabilidade para ver prontidão, alertas e sinais de uso. Ela responde se o console já está de pé para teste.',
            steps: [
                'Olhe os painéis antes de mudar algo estrutural.',
                'Procure por bloqueios de readiness.',
                'Prefira agir só depois de entender o alerta ativo.'
            ]
        },
        governance: {
            title: 'Governança',
            body: 'Governança é onde você confirma se o canon técnico e o enforcement continuam alinhados. É a área que evita drift silencioso.',
            steps: [
                'Leia os critérios de abertura com atenção.',
                'Confira as condições de bloqueio antes de ampliar uso.',
                'Se houver drift, trate como tarefa de correção, não como dúvida.'
            ]
        },
        'instruction-registry': {
            title: 'Instruction Registry',
            body: 'Aqui você governa o bundle mínimo remoto do Sapiens. É a camada para rollout controlado, override por tenant e invalidation sem redeploy.',
            steps: [
                'Comece validando channels, runtimes e quantidade de entries ativas.',
                'Use o cadastro mínimo para publicar ou ajustar uma entry do runtime correto.',
                'Se o bundle mudou, invalide cache de forma controlada e releia a auditoria.'
            ]
        }
    };



    const wizardState = {
        currentStep: 1,
        selected: [],
        answers: [],
        pendingAction: null,
    };

    const connectionState = {
        mode: null,
        content: '',
    };
    const registryUiState = {
        editingEntry: null,
        filters: {
            runtime_profile: '',
            channel: '',
            status: '',
            rollout_status: '',
            environment: '',
            company_id: '',
        },
    };

    function formatContextLabel(value) {
        const normalized = normalize(value);
        if (normalized === 'user') return 'Usuário';
        if (normalized === 'company') return 'Empresa';
        if (normalized === 'user_and_company' || normalized === 'usercompany') return 'Usuário + Empresa';
        if (normalized === 'company_only') return 'Somente empresa';
        if (normalized === 'user_only') return 'Somente usuário';
        if (normalized === 'no_explicit_context') return 'Sem contexto explícito';
        return String(value || 'Indefinido');
    }

    function replaceChildren(node, items) {
        if (!node) return;
        node.innerHTML = '';
        items.forEach((item) => node.appendChild(item));
    }

    function renderChipCollection(node, items, emptyLabel = 'Sem contexto explícito') {
        if (!node) return;
        const values = Array.isArray(items) ? items.filter(Boolean) : [];
        const chips = (values.length ? values : [emptyLabel]).map((item) => {
            const chip = document.createElement('span');
            chip.className = 'ai-mcp-chip';
            chip.textContent = formatContextLabel(item);
            return chip;
        });
        replaceChildren(node, chips);
    }

    function renderKeyValueCollection(node, values, emptyKey = 'status', emptyValue = 'Sem dados') {
        if (!node) return;
        const entries = Object.entries(values || {}).filter(([, value]) => value !== undefined && value !== null && value !== '');
        const rows = (entries.length ? entries : [[emptyKey, emptyValue]]).map(([key, value]) => {
            const item = document.createElement('li');
            const title = document.createElement('strong');
            const content = document.createElement('span');
            title.textContent = String(key);
            content.textContent = String(value);
            item.appendChild(title);
            item.appendChild(content);
            return item;
        });
        replaceChildren(node, rows);
    }

    function renderContextSummaryCollection(node, values) {
        if (!node) return;
        const entries = Object.entries(values || {}).filter(([, value]) => Number(value) > 0);
        const rows = (entries.length ? entries : [['no_explicit_context', 0]]).map(([key, value]) => {
            const item = document.createElement('li');
            const title = document.createElement('strong');
            const content = document.createElement('span');
            title.textContent = formatContextLabel(key);
            content.textContent = `${value} feature${Number(value) === 1 ? '' : 's'}`;
            item.appendChild(title);
            item.appendChild(content);
            return item;
        });
        replaceChildren(node, rows);
    }

    function renderBootstrapContext(payload) {
        const currentContext = payload?.current_context || {};
        renderChipCollection(bootstrapContextRequired, currentContext.required, 'Sem requisito explícito');
        renderKeyValueCollection(
            bootstrapContextResolved,
            currentContext.resolved,
            'status',
            'aguardando bootstrap automático',
        );
        renderKeyValueCollection(
            bootstrapContextResolution,
            currentContext.resolution,
            'company',
            'aguardando releitura',
        );
        renderContextSummaryCollection(bootstrapContextSummary, payload?.context_summary);
    }

    function renderRuntimeContext(payload) {
        const runtimeContext = payload?.runtime_context || {};
        const resolved = runtimeContext.resolved || {};
        const resolution = runtimeContext.resolution || {};
        const contextRequirements = payload?.catalog?.context_requirements || {};
        if (runtimeContextSummary) {
            runtimeContextSummary.textContent = resolved.company_code
                || resolved.company_id
                || 'Sem empresa resolvida';
        }
        if (runtimeContextMeta) {
            runtimeContextMeta.textContent = resolved.company_name
                || 'Feature com empresa exige contexto explícito ou pinado.';
        }
        if (runtimeContextSource) {
            runtimeContextSource.textContent = `Origem: ${resolution.company || 'não resolvida'}`;
        }
        if (runtimeContextBadges) {
            renderChipCollection(runtimeContextBadges, [
                `user-only: ${contextRequirements.user_only || 0}`,
                `company-only: ${contextRequirements.company_only || 0}`,
                `user+company: ${contextRequirements.user_and_company || 0}`,
            ]);
        }
    }

    function renderBootstrapResult(payload, tone = 'success') {
        const bootstrap = payload?.bootstrap || payload || {};
        const features = Array.isArray(bootstrap.features) ? bootstrap.features : [];
        const domains = Array.isArray(bootstrap.domains) ? bootstrap.domains : [];
        const version = bootstrap.catalog_version || 'sem versão';
        const surface = bootstrap.surface || documentationBootstrap?.dataset.defaultSurface || 'user';

        if (bootstrapStatus) bootstrapStatus.textContent = String(features.length);
        if (bootstrapMeta) bootstrapMeta.textContent = `${version} · ${surface}`;
        if (bootstrapResultTitle) bootstrapResultTitle.textContent = tone === 'success'
            ? 'Bootstrap executado automaticamente'
            : 'Falha ao executar bootstrap';
        if (bootstrapResultText) bootstrapResultText.textContent = tone === 'success'
            ? `Foram carregadas ${features.length} features resumidas para a surface ${surface}.`
            : (payload?.error || 'Não foi possível carregar o catálogo MCP automaticamente.');
        if (bootstrapResultMeta) bootstrapResultMeta.textContent = tone === 'success'
            ? `Domínios disponíveis: ${domains.join(', ') || 'nenhum domínio liberado'}.`
            : 'Revise contexto, empresa ativa e permissões da surface.';
        renderBootstrapContext(bootstrap);
        if (bootstrapFeatureList) {
            bootstrapFeatureList.innerHTML = '';
            const items = tone === 'success'
                ? features.slice(0, 5).map((feature) => feature.nome || feature.id)
                : [];
            items.forEach((label) => {
                const item = document.createElement('li');
                item.textContent = label;
                bootstrapFeatureList.appendChild(item);
            });
            if (!items.length) {
                const fallback = document.createElement('li');
                fallback.textContent = tone === 'success'
                    ? 'Nenhuma feature disponível para a surface atual.'
                    : 'Bootstrap automático indisponível no momento.';
                bootstrapFeatureList.appendChild(fallback);
            }
        }
    }

    async function autoBootstrapDocumentationCatalog() {
        if (!documentationBootstrap) return;
        const endpoint = documentationBootstrap.dataset.endpoint;
        const autoLoad = documentationBootstrap.dataset.autoLoad === 'true';
        const defaultSurface = documentationBootstrap.dataset.defaultSurface || 'user';
        if (!endpoint || !autoLoad) return;

        try {
            const response = await fetch(`${endpoint}?surface=${encodeURIComponent(defaultSurface)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.error || 'Falha ao carregar bootstrap documental.');
            }
            renderBootstrapResult(payload.bootstrap, 'success');
        } catch (error) {
            renderBootstrapResult({ error: error.message || 'Falha ao carregar bootstrap documental.' }, 'error');
        }
    }



    function setStageExpanded(stage, expanded) {
        if (!stage) return;
        const toggle = stage.querySelector('[data-stage-toggle]');
        stage.classList.toggle('is-collapsed', !expanded);
        stage.classList.toggle('is-expanded', expanded);
        if (toggle) {
            toggle.setAttribute('aria-expanded', String(expanded));
        }
    }

    function updateTranscript() {
        if (!wizardTranscript || !wizardTranscriptList) return;
        const answers = wizardState.answers.filter(Boolean);
        wizardTranscript.hidden = answers.length === 0;
        wizardTranscriptList.innerHTML = '';

        answers.forEach((answer) => {
            const item = document.createElement('div');
            item.className = 'ai-mcp-wizard-transcript__item';
            item.innerHTML = `<span>${answer.question}</span><strong>${answer.answer}</strong>`;
            wizardTranscriptList.appendChild(item);
        });
    }

    function setPanelExpanded(panel, expanded) {
        if (!panel) return;
        const toggle = panel.querySelector('[data-panel-toggle]');
        panel.classList.toggle('is-collapsed', !expanded);
        panel.classList.toggle('is-expanded', expanded);
        panel.classList.toggle('is-active', expanded && panel.classList.contains('is-active'));
        if (toggle) {
            toggle.setAttribute('aria-expanded', String(expanded));
        }
    }

    function expandActivePanel(target) {
        const activePanel = root.querySelector(`[data-console-panel="${target}"]`);
        setPanelExpanded(activePanel, true);
    }

    function activateWizardStep(stepNumber) {
        wizardState.currentStep = stepNumber;
        wizardStepPills.forEach((pill) => {
            const current = Number(pill.dataset.wizardStepPill || 0);
            pill.classList.toggle('is-active', current === stepNumber);
            pill.classList.toggle('is-complete', current < stepNumber);
        });
        wizardSteps.forEach((step) => {
            const current = Number(step.dataset.wizardStep || 0);
            step.classList.toggle('is-active', current === stepNumber);
            step.classList.toggle('is-complete', current < stepNumber);
        });
    }

    function finalizeWizard(option) {
        wizardState.pendingAction = option;
        const targetTab = option.dataset.targetTab || 'overview';
        const targetSelector = option.dataset.targetSelector || '';
        const choiceLabel = option.dataset.choiceLabel || option.textContent.trim();
        if (wizardResultTitle) wizardResultTitle.textContent = `Próximo passo: ${choiceLabel}`;
        if (wizardResultText) {
            wizardResultText.textContent = `Abra ${targetTab} e use a busca sugerida (${targetSelector || 'sem filtro'}) para cair no trecho certo do console.`;
        }
        if (wizardResult) wizardResult.hidden = false;
    }

    function resetWizard() {
        wizardState.currentStep = 1;
        wizardState.selected = [];
        wizardState.answers = [];
        wizardState.pendingAction = null;
        wizardChoiceCards.forEach((card) => card.classList.remove('is-selected'));
        if (wizardResult) wizardResult.hidden = true;
        updateTranscript();
        activateWizardStep(1);
    }

    function activateTab(target) {
        tabs.forEach((tab) => tab.classList.toggle('is-active', tab.dataset.consoleTab === target));
        panels.forEach((panel) => {
            const isTarget = panel.dataset.consolePanel === target;
            panel.classList.toggle('is-active', isTarget);
            if (isTarget) {
                setPanelExpanded(panel, true);
            }
        });
        wizardButtons.forEach((button) => {
            button.classList.toggle('is-selected', button.dataset.consoleGoTab === target);
            button.setAttribute('aria-pressed', button.dataset.consoleGoTab === target ? 'true' : 'false');
        });
        updateHelp(target);
    }

    function normalize(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function applySearch(term) {
        const needle = normalize(term);
        decisionCards.forEach((card) => {
            const match = !needle || normalize(card.dataset.searchable || card.textContent || '').includes(needle);
            card.classList.toggle('ai-mcp-hidden', !match);
        });
        wizardStages.forEach((stage) => {
            const stageMatch = !needle || normalize(stage.dataset.searchable || stage.textContent || '').includes(needle);
            stage.classList.toggle('ai-mcp-hidden', !stageMatch);
            if (needle && stageMatch) {
                setStageExpanded(stage, true);
            }
        });
        panels.forEach((panel) => {
            const haystack = normalize(panel.dataset.searchable || panel.textContent || '');
            const panelMatch = !needle || haystack.includes(needle);
            panel.classList.toggle('ai-mcp-hidden', !panelMatch);
            if (needle && panelMatch) {
                setPanelExpanded(panel, true);
            }

            panel.querySelectorAll('[data-searchable]').forEach((node) => {
                const nodeMatch = !needle || normalize(node.dataset.searchable || node.textContent || '').includes(needle);
                node.classList.toggle('ai-mcp-hidden', !nodeMatch);
            });
        });

        collapsibleCards.forEach((card) => {
            const toggle = card.querySelector(':scope > header .ai-mcp-card__toggle');
            if (!toggle) return;

            if (needle) {
                const match = normalize(card.dataset.searchable || card.textContent || '').includes(needle);
                card.classList.toggle('ai-mcp-card--collapsed', !match);
                toggle.setAttribute('aria-expanded', String(match));
                return;
            }

            const siblingCards = Array.from(card.parentElement?.children || []).filter((node) => node.classList?.contains('ai-mcp-card'));
            const shouldStartCollapsed = siblingCards.indexOf(card) > 0;
            card.classList.toggle('ai-mcp-card--collapsed', shouldStartCollapsed);
            toggle.setAttribute('aria-expanded', String(!shouldStartCollapsed));
        });
    }

    function updateHelp(topicKey) {
        const topic = helpTopics[topicKey] || helpTopics.overview;
        if (helpTitle) helpTitle.textContent = topic.title;
        if (helpBody) helpBody.textContent = topic.body;
        if (helpSteps) {
            helpSteps.innerHTML = '';
            topic.steps.forEach((step) => {
                const li = document.createElement('li');
                li.textContent = step;
                helpSteps.appendChild(li);
            });
        }
    }

    function setConnectionFeedback(message, tone = 'error') {
        if (!connectionFeedback) return;
        connectionFeedback.hidden = !message;
        connectionFeedback.textContent = message || '';
        connectionFeedback.dataset.tone = message ? tone : '';
    }

    function setRegistryFeedback(message, tone = 'error') {
        if (!registryFeedback) return;
        registryFeedback.hidden = !message;
        registryFeedback.textContent = message || '';
        registryFeedback.dataset.tone = message ? tone : '';
    }

    function getRegistryEntries() {
        return Array.isArray(consoleState?.instruction_registry?.entries) ? consoleState.instruction_registry.entries : [];
    }

    function getRegistryAudit() {
        return Array.isArray(consoleState?.instruction_registry?.recent_audit) ? consoleState.instruction_registry.recent_audit : [];
    }

    function getRegistryChanges() {
        return Array.isArray(consoleState?.instruction_registry?.recent_changes) ? consoleState.instruction_registry.recent_changes : [];
    }

    function safeParseJson(value) {
        try {
            return { ok: true, value: JSON.parse(value || '{}') };
        } catch (error) {
            return { ok: false, error };
        }
    }

    function createActionButton(label, action, entryId, extra = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ai-mcp-btn ai-mcp-btn--secondary ai-mcp-btn--small';
        button.textContent = label;
        button.dataset.registryAction = action;
        button.dataset.entryId = String(entryId);
        Object.entries(extra).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                button.dataset[key] = String(value);
            }
        });
        return button;
    }

    function createRegistryEntryCard(entry) {
        const card = document.createElement('div');
        card.className = 'ai-mcp-entity-card';
        card.dataset.searchable = [
            entry.runtime_profile,
            entry.scope_type,
            entry.channel,
            entry.status,
            entry.rollout_status,
            entry.agent_key,
            entry.harness_key,
        ].filter(Boolean).join(' ');
        const title = document.createElement('div');
        title.className = 'ai-mcp-entity-card__head';
        title.innerHTML = `
            <strong>${entry.runtime_profile || 'runtime indefinido'}</strong>
            <span>${entry.scope_type || 'scope'} · ${entry.channel || 'canal'}</span>
        `;
        const body = document.createElement('p');
        body.textContent = `Status ${entry.status || 'n/a'} · rollout ${entry.rollout_status || 'n/a'} · version ${entry.entry_version || 'n/a'} · env ${entry.environment || 'n/a'}`;
        const meta = document.createElement('small');
        meta.textContent = `company_id=${entry.company_id ?? '—'} · checksum=${entry.checksum || 'n/a'} · invalidation=${entry.invalidation_token || 'n/a'}`;
        const actions = document.createElement('div');
        actions.className = 'ai-mcp-connection-generator__actions';
        actions.appendChild(createActionButton('Editar', 'edit', entry.id));
        if (entry.channel !== 'stable') {
            actions.appendChild(createActionButton('Promover p/ stable', 'promote', entry.id, { targetChannel: 'stable' }));
        }
        if (entry.channel !== 'beta') {
            actions.appendChild(createActionButton('Clonar p/ beta', 'promote', entry.id, { targetChannel: 'beta' }));
        }
        actions.appendChild(createActionButton(entry.status === 'active' ? 'Pausar' : 'Ativar', 'toggle-status', entry.id));
        actions.appendChild(createActionButton('Invalidar', 'invalidate', entry.id));
        card.appendChild(title);
        card.appendChild(body);
        card.appendChild(meta);
        card.appendChild(actions);
        return card;
    }

    function createRegistryAuditCard(audit) {
        const card = document.createElement('div');
        card.className = 'ai-mcp-entity-card';
        card.dataset.searchable = [
            audit.event_type,
            audit.result,
            audit.detail,
        ].filter(Boolean).join(' ');
        card.innerHTML = `
            <div class="ai-mcp-entity-card__head">
                <strong>${audit.event_type || 'evento'}</strong>
                <span>${audit.result || 'n/a'}</span>
            </div>
            <p>${audit.detail || 'Sem detalhe adicional.'}</p>
            <small>entry_id=${audit.entry_id ?? '—'} · actor=${audit.actor_user_id ?? '—'} · ${audit.created_at || 'sem timestamp'}</small>
        `;
        return card;
    }

    function createRegistryChangeCard(change) {
        const card = document.createElement('div');
        card.className = 'ai-mcp-entity-card';
        card.dataset.searchable = [change.event_type, change.summary].filter(Boolean).join(' ');
        card.innerHTML = `
            <div class="ai-mcp-entity-card__head">
                <strong>${change.event_type || 'mudança'}</strong>
                <span>entry ${change.entry_id ?? '—'}</span>
            </div>
            <p>${change.summary || 'sem resumo'}</p>
            <small>${change.created_at || 'sem timestamp'}</small>
        `;
        return card;
    }

    function renderRegistryCollection(node, items, emptyTitle, emptySubtitle, factory) {
        if (!node) return;
        node.innerHTML = '';
        if (!Array.isArray(items) || !items.length) {
            const card = document.createElement('div');
            card.className = 'ai-mcp-entity-card';
            card.innerHTML = `
                <div class="ai-mcp-entity-card__head">
                    <strong>${emptyTitle}</strong>
                    <span>baseline</span>
                </div>
                <p>${emptySubtitle}</p>
            `;
            node.appendChild(card);
            return;
        }
        items.forEach((item) => node.appendChild(factory(item)));
    }

    function getRegistryFilteredEntries() {
        const filters = registryUiState.filters || {};
        return getRegistryEntries().filter((entry) => {
            if (filters.runtime_profile && entry.runtime_profile !== filters.runtime_profile) return false;
            if (filters.channel && entry.channel !== filters.channel) return false;
            if (filters.status && entry.status !== filters.status) return false;
            if (filters.rollout_status && entry.rollout_status !== filters.rollout_status) return false;
            if (filters.environment && entry.environment !== filters.environment) return false;
            if (filters.company_id && String(entry.company_id ?? '') !== String(filters.company_id)) return false;
            return true;
        });
    }

    function renderInstructionRegistry(state) {
        const summary = state?.summary || {};
        const entries = getRegistryFilteredEntries();
        const audit = getRegistryAudit();
        const changes = getRegistryChanges();
        const channels = Array.isArray(summary.channels) ? summary.channels : [];
        const runtimes = Array.isArray(summary.runtimes) ? summary.runtimes : [];

        if (registryEntriesCount) registryEntriesCount.textContent = String(summary.entries || 0);
        if (registryActiveEntriesCount) registryActiveEntriesCount.textContent = String(summary.active_entries || 0);
        if (registryTenantOverridesCount) registryTenantOverridesCount.textContent = String(summary.tenant_overrides || 0);
        if (registryChannelsCount) registryChannelsCount.textContent = String(channels.length);
        if (registryChannelsList) registryChannelsList.textContent = channels.join(', ') || 'nenhum';
        if (registryRuntimesCount) registryRuntimesCount.textContent = String(runtimes.length);
        if (registryRuntimesList) registryRuntimesList.textContent = runtimes.join(', ') || 'nenhum';

        renderRegistryCollection(
            registryEntriesList,
            entries,
            'Nenhuma entry cadastrada',
            'Assim que o registry remoto for sincronizado, as entries aparecerão aqui.',
            createRegistryEntryCard,
        );
        renderRegistryCollection(
            registryAuditList,
            audit,
            'Sem auditoria recente',
            'Os eventos de criação, atualização e invalidação serão exibidos aqui.',
            createRegistryAuditCard,
        );
        renderRegistryCollection(
            registryChangesList,
            changes,
            'Sem mudanças comparativas recentes',
            'Quando houver create/update/promote com delta relevante, o resumo aparecerá aqui.',
            createRegistryChangeCard,
        );
    }

    function getRegistryAdminState() {
        return consoleState?.instruction_registry || {};
    }

    function setRegistryEditorMode(entry = null) {
        registryUiState.editingEntry = entry || null;
        if (registryEditorMode) {
            registryEditorMode.textContent = entry
                ? `editando entry #${entry.id} (${entry.runtime_profile} · ${entry.channel})`
                : 'novo cadastro';
        }
        if (registryEditorDescription) {
            registryEditorDescription.textContent = entry
                ? 'Os campos abaixo foram preenchidos a partir da entry selecionada. Você pode salvar para atualizar a própria entry ou mudar o canal para clonar/promover.'
                : 'Use o formulário para publicar uma nova entry ou clique em “Editar” em uma entry existente para carregar os dados.';
        }
    }

    function fillRegistryForm(entry) {
        document.getElementById('aiMcpRegistryScopeType').value = entry.scope_type || 'runtime';
        document.getElementById('aiMcpRegistryRuntimeProfile').value = entry.runtime_profile || 'squad_cliente';
        document.getElementById('aiMcpRegistryChannel').value = entry.channel || 'stable';
        document.getElementById('aiMcpRegistryEnvironment').value = entry.environment || 'production';
        document.getElementById('aiMcpRegistryStatus').value = entry.status || 'active';
        document.getElementById('aiMcpRegistryRolloutStatus').value = entry.rollout_status || 'active';
        document.getElementById('aiMcpRegistryCompanyId').value = entry.company_id ?? '';
        document.getElementById('aiMcpRegistryAgentKey').value = entry.agent_key || '';
        document.getElementById('aiMcpRegistryHarnessKey').value = entry.harness_key || '';
        document.getElementById('aiMcpRegistryEntryVersion').value = entry.entry_version || 'v1';
        document.getElementById('aiMcpRegistryCacheTtl').value = entry.cache_ttl_seconds || 1800;
        document.getElementById('aiMcpRegistryNotes').value = entry.notes || '';
        document.getElementById('aiMcpRegistryPayloadJson').value = JSON.stringify(entry.payload_json || {}, null, 2);
        setRegistryEditorMode(entry);
    }

    function resetRegistryForm() {
        document.getElementById('aiMcpRegistryScopeType').value = 'runtime';
        document.getElementById('aiMcpRegistryRuntimeProfile').value = 'squad_cliente';
        document.getElementById('aiMcpRegistryChannel').value = 'stable';
        document.getElementById('aiMcpRegistryEnvironment').value = 'production';
        document.getElementById('aiMcpRegistryStatus').value = 'active';
        document.getElementById('aiMcpRegistryRolloutStatus').value = 'active';
        document.getElementById('aiMcpRegistryCompanyId').value = '';
        document.getElementById('aiMcpRegistryAgentKey').value = '';
        document.getElementById('aiMcpRegistryHarnessKey').value = '';
        document.getElementById('aiMcpRegistryEntryVersion').value = 'v1';
        document.getElementById('aiMcpRegistryCacheTtl').value = '1800';
        document.getElementById('aiMcpRegistryNotes').value = '';
        document.getElementById('aiMcpRegistryPayloadJson').value = `{
  "summary": "Bundle mínimo remoto do runtime selecionado",
  "introduction_message": "Carregar bundle mínimo, manter MCP First e consultar docs completos sob demanda."
}`;
        setRegistryEditorMode(null);
    }

    function findRegistryEntryById(entryId) {
        return getRegistryEntries().find((entry) => String(entry.id) === String(entryId)) || null;
    }

    async function refreshInstructionRegistryState() {
        const endpoint = getRegistryAdminState()?.endpoints?.frontend_state;
        if (!endpoint) return;
        try {
            const response = await fetch(endpoint, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.error || 'Falha ao recarregar o instruction registry.');
            }
            consoleState.instruction_registry = payload.state || {};
            renderInstructionRegistry(consoleState.instruction_registry);
            setRegistryFeedback('Estado do instruction registry recarregado.', 'success');
        } catch (error) {
            setRegistryFeedback(error.message || 'Falha ao recarregar o instruction registry.');
        }
    }

    function collectRegistryUpsertPayload() {
        const parsedPayload = safeParseJson(document.getElementById('aiMcpRegistryPayloadJson')?.value || '{}');
        if (!parsedPayload.ok) {
            throw new Error('Payload JSON inválido. Revise a estrutura antes de salvar.');
        }
        const companyIdRaw = document.getElementById('aiMcpRegistryCompanyId')?.value?.trim();
        const cacheTtlRaw = document.getElementById('aiMcpRegistryCacheTtl')?.value?.trim();
        return {
            scope_type: document.getElementById('aiMcpRegistryScopeType')?.value || 'runtime',
            runtime_profile: document.getElementById('aiMcpRegistryRuntimeProfile')?.value || 'squad_cliente',
            channel: document.getElementById('aiMcpRegistryChannel')?.value || 'stable',
            environment: document.getElementById('aiMcpRegistryEnvironment')?.value || 'production',
            status: document.getElementById('aiMcpRegistryStatus')?.value || 'active',
            rollout_status: document.getElementById('aiMcpRegistryRolloutStatus')?.value || 'active',
            company_id: companyIdRaw ? Number(companyIdRaw) : null,
            agent_key: document.getElementById('aiMcpRegistryAgentKey')?.value?.trim() || null,
            harness_key: document.getElementById('aiMcpRegistryHarnessKey')?.value?.trim() || null,
            entry_version: document.getElementById('aiMcpRegistryEntryVersion')?.value?.trim() || 'v1',
            cache_ttl_seconds: cacheTtlRaw ? Number(cacheTtlRaw) : 1800,
            notes: document.getElementById('aiMcpRegistryNotes')?.value?.trim() || null,
            payload: parsedPayload.value,
        };
    }

    async function saveInstructionRegistryEntry() {
        const endpoint = getRegistryAdminState()?.endpoints?.upsert_entry;
        if (!endpoint) return;
        setRegistryFeedback('');
        registrySaveButton && (registrySaveButton.disabled = true);
        try {
            const payload = collectRegistryUpsertPayload();
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Falha ao salvar entry do instruction registry.');
            }
            setRegistryFeedback('Entry salva com sucesso. Recarregando estado...', 'success');
            await refreshInstructionRegistryState();
        } catch (error) {
            setRegistryFeedback(error.message || 'Falha ao salvar entry do instruction registry.');
        } finally {
            registrySaveButton && (registrySaveButton.disabled = false);
        }
    }

    function collectRegistryInvalidatePayload() {
        const entryIdRaw = document.getElementById('aiMcpRegistryInvalidateEntryId')?.value?.trim();
        const companyIdRaw = document.getElementById('aiMcpRegistryInvalidateCompanyId')?.value?.trim();
        return {
            entry_id: entryIdRaw ? Number(entryIdRaw) : null,
            runtime_profile: document.getElementById('aiMcpRegistryInvalidateRuntimeProfile')?.value || null,
            channel: document.getElementById('aiMcpRegistryInvalidateChannel')?.value || null,
            company_id: companyIdRaw ? Number(companyIdRaw) : null,
            reason: document.getElementById('aiMcpRegistryInvalidateReason')?.value?.trim() || 'Ajuste controlado do bundle remoto',
        };
    }

    async function invalidateInstructionRegistryEntries() {
        const endpoint = getRegistryAdminState()?.endpoints?.invalidate;
        if (!endpoint) return;
        setRegistryFeedback('');
        registryInvalidateButton && (registryInvalidateButton.disabled = true);
        try {
            const payload = collectRegistryInvalidatePayload();
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Falha ao invalidar cache do instruction registry.');
            }
            setRegistryFeedback(`Invalidação concluída em ${result.result?.invalidated || 0} entry(s).`, 'success');
            await refreshInstructionRegistryState();
        } catch (error) {
            setRegistryFeedback(error.message || 'Falha ao invalidar cache do instruction registry.');
        } finally {
            registryInvalidateButton && (registryInvalidateButton.disabled = false);
        }
    }

    async function quickUpsertRegistryEntry(entry, patch = {}, successLabel = 'Entry atualizada com sucesso.') {
        const endpoint = getRegistryAdminState()?.endpoints?.upsert_entry;
        if (!endpoint || !entry) return;
        const payload = {
            scope_type: entry.scope_type,
            runtime_profile: entry.runtime_profile,
            agent_key: entry.agent_key,
            harness_key: entry.harness_key,
            company_id: entry.company_id,
            channel: entry.channel,
            environment: entry.environment,
            status: entry.status,
            rollout_status: entry.rollout_status,
            entry_version: entry.entry_version,
            cache_ttl_seconds: entry.cache_ttl_seconds,
            payload: entry.payload_json || {},
            notes: entry.notes,
            ...patch,
        };
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Falha ao executar ação rápida no instruction registry.');
        }
        setRegistryFeedback(successLabel, 'success');
        await refreshInstructionRegistryState();
    }

    async function quickPromoteRegistryEntry(entry, targetChannel) {
        const endpoint = getRegistryAdminState()?.endpoints?.promote;
        if (!endpoint || !entry) return;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_entry_id: entry.id,
                target_channel: targetChannel,
                target_environment: entry.environment || 'production',
                target_status: 'active',
                target_rollout_status: 'active',
                notes: `Promoção rápida da entry #${entry.id} para ${targetChannel} via console`,
            }),
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Falha ao promover a entry selecionada.');
        }
        setRegistryFeedback(`Entry #${entry.id} promovida para ${targetChannel}.`, 'success');
        await refreshInstructionRegistryState();
    }

    async function quickInvalidateRegistryEntry(entry) {
        const endpoint = getRegistryAdminState()?.endpoints?.invalidate;
        if (!endpoint || !entry) return;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entry_id: entry.id,
                reason: `Invalidação rápida da entry ${entry.id} pelo console`,
            }),
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Falha ao invalidar a entry selecionada.');
        }
        setRegistryFeedback(`Entry #${entry.id} invalidada com sucesso.`, 'success');
        await refreshInstructionRegistryState();
    }

    async function handleRegistryListAction(event) {
        const button = event.target.closest('[data-registry-action]');
        if (!button) return;
        const entry = findRegistryEntryById(button.dataset.entryId);
        if (!entry) {
            setRegistryFeedback('Entry não encontrada para a ação solicitada.');
            return;
        }
        const action = button.dataset.registryAction;
        try {
            if (action === 'edit') {
                fillRegistryForm(entry);
                setRegistryFeedback(`Entry #${entry.id} carregada no formulário.`, 'success');
                return;
            }
            if (action === 'toggle-status') {
                const nextStatus = entry.status === 'active' ? 'paused' : 'active';
                const nextRollout = nextStatus === 'active' && entry.rollout_status === 'paused' ? 'active' : entry.rollout_status;
                await quickUpsertRegistryEntry(
                    entry,
                    { status: nextStatus, rollout_status: nextRollout, notes: `${entry.notes || ''}`.trim() || null },
                    `Entry #${entry.id} atualizada para status ${nextStatus}.`,
                );
                return;
            }
            if (action === 'promote') {
                const targetChannel = button.dataset.targetChannel || 'stable';
                await quickPromoteRegistryEntry(entry, targetChannel);
                return;
            }
            if (action === 'invalidate') {
                await quickInvalidateRegistryEntry(entry);
            }
        } catch (error) {
            setRegistryFeedback(error.message || 'Falha ao executar a ação rápida no instruction registry.');
        }
    }

    function updateRegistryFilters() {
        registryUiState.filters.runtime_profile = registryFilterRuntime?.value || '';
        registryUiState.filters.channel = registryFilterChannel?.value || '';
        registryUiState.filters.status = registryFilterStatus?.value || '';
        registryUiState.filters.rollout_status = registryFilterRollout?.value || '';
        registryUiState.filters.environment = registryFilterEnvironment?.value || '';
        registryUiState.filters.company_id = registryFilterCompanyId?.value?.trim() || '';
        renderInstructionRegistry(consoleState.instruction_registry || {});
    }

    function getConnectionPayload(mode) {
        return {
            mode,
            name: document.getElementById('aiMcpConnectionName')?.value?.trim() || '',
            default_company: document.getElementById('aiMcpConnectionCompany')?.value?.trim() || '',
            url: document.getElementById('aiMcpConnectionUrl')?.value?.trim() || '',
            auth_type: 'bearer',
            token: document.getElementById('aiMcpConnectionToken')?.value?.trim() || '',
        };
    }

    async function copyConnectionResult() {
        if (!connectionState.content) return;
        try {
            await navigator.clipboard.writeText(connectionState.content);
            setConnectionFeedback('Conteúdo copiado.', 'success');
        } catch (error) {
            setConnectionFeedback('Não foi possível copiar automaticamente. Copie manualmente abaixo.');
        }
    }

    async function generateConnectionSnippet(mode) {
        if (!connectionGenerator) return;
        const endpoint = connectionGenerator.dataset.endpoint;
        const payload = getConnectionPayload(mode);
        const label = mode === 'raw_config' ? 'Configuração técnica pronta para copiar' : 'Comando Ativar Sapiens pronto para copiar';

        setConnectionFeedback('');
        connectionModeButtons.forEach((button) => {
            button.disabled = true;
        });

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Falha ao gerar conteúdo de conexão.');
            }

            connectionState.mode = result.mode;
            connectionState.content = result.content || '';
            if (connectionResultTitle) connectionResultTitle.textContent = label;
            if (connectionResultDescription) {
                connectionResultDescription.textContent = mode === 'raw_config'
                    ? 'Copie este JSON no cliente que aceita configuração MCP manual.'
                    : 'Copie este comando no outro cliente para ele configurar, ativar o Sapiens e criar atalho quando possível.';
            }
            if (connectionSourceJson) {
                connectionSourceJson.textContent = result.source_json || '';
                connectionSourceJson.hidden = !result.source_json;
            }
            if (connectionOutput) connectionOutput.textContent = result.content || '';
            if (connectionResult) connectionResult.hidden = false;
            setConnectionFeedback('Conteúdo gerado com sucesso.', 'success');
        } catch (error) {
            if (connectionResult) connectionResult.hidden = true;
            setConnectionFeedback(error.message || 'Falha ao gerar conteúdo.');
        } finally {
            connectionModeButtons.forEach((button) => {
                button.disabled = false;
            });
        }
    }

    function setupCollapsibleCards() {
        collapsibleCards.forEach((card) => {
            const header = card.querySelector(':scope > header');
            if (!header || card.classList.contains('ai-mcp-card--wizard')) return;

            const bodyNodes = Array.from(card.children).filter((node) => node !== header);
            if (!bodyNodes.length) return;

            card.classList.add('ai-mcp-card--collapsible');

            let body = card.querySelector(':scope > .ai-mcp-card__body');
            if (!body) {
                body = document.createElement('div');
                body.className = 'ai-mcp-card__body';
                bodyNodes.forEach((node) => body.appendChild(node));
                card.appendChild(body);
            }

            let toggle = header.querySelector('.ai-mcp-card__toggle');
            if (!toggle) {
                toggle = document.createElement('button');
                toggle.type = 'button';
                toggle.className = 'ai-mcp-card__toggle';
                toggle.setAttribute('aria-expanded', 'true');
                toggle.setAttribute('title', 'Expandir ou recolher seção');
                toggle.innerHTML = '<span class="ai-mcp-card__toggle-icon">⌄</span>';
                header.appendChild(toggle);
            }

            const siblingCards = Array.from(card.parentElement?.children || []).filter((node) => node.classList?.contains('ai-mcp-card'));
            const shouldStartCollapsed = siblingCards.indexOf(card) > 0;
            card.classList.toggle('ai-mcp-card--collapsed', shouldStartCollapsed);
            toggle.setAttribute('aria-expanded', String(!shouldStartCollapsed));

            toggle.addEventListener('click', () => {
                const collapsed = card.classList.toggle('ai-mcp-card--collapsed');
                toggle.setAttribute('aria-expanded', String(!collapsed));
            });
        });
    }


    stageToggles.forEach((toggle) => {
        toggle.addEventListener('click', () => {
            const stage = toggle.closest('[data-wizard-stage]');
            const expanded = toggle.getAttribute('aria-expanded') !== 'true';
            setStageExpanded(stage, expanded);
        });
    });

    panelToggles.forEach((toggle) => {
        toggle.addEventListener('click', () => {
            const panel = toggle.closest('[data-console-panel]');
            const expanded = toggle.getAttribute('aria-expanded') !== 'true';
            setPanelExpanded(panel, expanded);
        });
    });

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => activateTab(tab.dataset.consoleTab));
    });

    wizardButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const target = button.dataset.consoleGoTab || 'overview';
            activateTab(target);
            root.querySelector(`[data-console-panel="${target}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    searchInput?.addEventListener('input', (event) => applySearch(event.target.value));


    wizardChoiceCards.forEach((card) => {
        card.addEventListener('click', () => {
            const stepNumber = Number(card.closest('[data-wizard-step]')?.dataset.wizardStep || 1);
            wizardChoiceCards.filter((item) => item.closest('[data-wizard-step]')?.dataset.wizardStep === String(stepNumber)).forEach((item) => item.classList.remove('is-selected'));
            card.classList.add('is-selected');
            const choiceLabel = card.dataset.choiceLabel || card.textContent.trim();
            wizardState.selected[stepNumber - 1] = choiceLabel;
            wizardState.answers[stepNumber - 1] = {
                question: card.dataset.stepTitle || `Pergunta ${stepNumber}`,
                answer: choiceLabel,
            };
            updateTranscript();
            const nextStep = stepNumber + 1;
            if (nextStep <= wizardSteps.length) {
                activateWizardStep(nextStep);
            } else {
                finalizeWizard(card);
            }
        });
    });

    assistantActions.forEach((button) => {
        button.addEventListener('click', () => {
            const target = button.dataset.targetTab || 'overview';
            const query = button.dataset.query || '';
            activateTab(target);
            if (searchInput) {
                searchInput.value = query;
                applySearch(query);
            }
            root.querySelector(`[data-console-panel="${target}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    wizardGo?.addEventListener('click', () => {
        const target = wizardState.pendingAction?.dataset.targetTab || 'overview';
        activateTab(target);
        root.querySelector(`[data-console-panel="${target}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    wizardSearch?.addEventListener('click', () => {
        const query = wizardState.pendingAction?.dataset.targetSelector || '';
        if (searchInput) {
            searchInput.value = query;
            applySearch(query);
        }
    });

    connectionModeButtons.forEach((button) => {
        button.addEventListener('click', () => {
            generateConnectionSnippet(button.dataset.connectionMode || 'ai_prompt');
        });
    });

    connectionCopyButton?.addEventListener('click', copyConnectionResult);
    registrySaveButton?.addEventListener('click', saveInstructionRegistryEntry);
    registryRefreshButton?.addEventListener('click', refreshInstructionRegistryState);
    registryInvalidateButton?.addEventListener('click', invalidateInstructionRegistryEntries);
    registryResetFormButton?.addEventListener('click', resetRegistryForm);
    registryEntriesList?.addEventListener('click', handleRegistryListAction);
    registryFilterRuntime?.addEventListener('change', updateRegistryFilters);
    registryFilterChannel?.addEventListener('change', updateRegistryFilters);
    registryFilterStatus?.addEventListener('change', updateRegistryFilters);
    registryFilterRollout?.addEventListener('change', updateRegistryFilters);
    registryFilterEnvironment?.addEventListener('change', updateRegistryFilters);
    registryFilterCompanyId?.addEventListener('input', updateRegistryFilters);

    setupCollapsibleCards();
    wizardReset?.addEventListener('click', resetWizard);
    renderRuntimeContext(consoleState);
    renderBootstrapContext(consoleState?.documentation_bootstrap?.summary || {});
    renderInstructionRegistry(consoleState?.instruction_registry || {});
    setRegistryEditorMode(null);
    activateTab(root.dataset.defaultTab || tabs[0]?.dataset.consoleTab || 'overview');
    resetWizard();
    autoBootstrapDocumentationCatalog();
});
