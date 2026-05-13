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
        answers: [],
        pendingAction: null,
    };

    const connectionState = {
        mode: null,
        content: '',
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

    setupCollapsibleCards();
    wizardReset?.addEventListener('click', resetWizard);
    renderRuntimeContext(consoleState);
    renderBootstrapContext(consoleState?.documentation_bootstrap?.summary || {});
    activateTab(root.dataset.defaultTab || tabs[0]?.dataset.consoleTab || 'overview');
    resetWizard();
    autoBootstrapDocumentationCatalog();
});
