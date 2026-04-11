document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('aiMcpConsolePage');
    if (!root) return;

    const tabs = Array.from(root.querySelectorAll('[data-console-tab]'));
    const panels = Array.from(root.querySelectorAll('[data-console-panel]'));
    const searchInput = document.getElementById('aiMcpConsoleSearch');
    const wizardButtons = Array.from(root.querySelectorAll('[data-console-go-tab]'));
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
    const assistantActions = Array.from(root.querySelectorAll('[data-assistant-action]'));
    const collapsibleCards = Array.from(root.querySelectorAll('.ai-mcp-panels .ai-mcp-card'));

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
        }
    };



    const wizardState = {
        currentStep: 1,
        selected: [],
        pendingAction: null,
    };

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
        wizardState.pendingAction = null;
        wizardChoiceCards.forEach((card) => card.classList.remove('is-selected'));
        if (wizardResult) wizardResult.hidden = true;
        activateWizardStep(1);
    }

    function activateTab(target) {
        tabs.forEach((tab) => tab.classList.toggle('is-active', tab.dataset.consoleTab === target));
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.consolePanel === target));
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
        panels.forEach((panel) => {
            const haystack = normalize(panel.dataset.searchable || panel.textContent || '');
            const panelMatch = !needle || haystack.includes(needle);
            panel.classList.toggle('ai-mcp-hidden', !panelMatch);

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
            wizardState.selected[stepNumber - 1] = card.dataset.choiceLabel || card.textContent.trim();
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

    setupCollapsibleCards();
    wizardReset?.addEventListener('click', resetWizard);
    activateTab(root.dataset.defaultTab || tabs[0]?.dataset.consoleTab || 'overview');
    resetWizard();
});
