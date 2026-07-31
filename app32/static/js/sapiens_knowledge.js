(function () {
    'use strict';

    const params = new URLSearchParams(window.location.search);
    const legacyRequested = params.get('legacy') === '1'
        || ['engineering', 'factory'].includes(params.get('contact'))
        || ['approvals', 'catalog', 'logs'].includes(params.get('view'));
    if (legacyRequested) {
        document.body.classList.add('sapiens-legacy');
        return;
    }

    const root = document.getElementById('knowledgeExperience');
    if (!root) return;

    const elements = {
        form: document.getElementById('knowledgeQuestionForm'),
        question: document.getElementById('knowledgeQuestion'),
        submit: document.getElementById('knowledgeSubmit'),
        scopeButtons: Array.from(root.querySelectorAll('[data-scope]')),
        suggestions: document.getElementById('knowledgeSuggestions'),
        mode: document.getElementById('knowledgeModeLabel'),
        refineToggle: document.getElementById('knowledgeRefineToggle'),
        refinePanel: document.getElementById('knowledgeRefinePanel'),
        sourceType: document.getElementById('knowledgeSourceType'),
        status: document.getElementById('knowledgeStatus'),
        empty: document.getElementById('knowledgeEmpty'),
        answer: document.getElementById('knowledgeAnswer'),
        answerEyebrow: document.getElementById('knowledgeAnswerEyebrow'),
        answerTitle: document.getElementById('knowledgeAnswerTitle'),
        answerBadge: document.getElementById('knowledgeAnswerBadge'),
        answerBody: document.getElementById('knowledgeAnswerBody'),
        trust: document.getElementById('knowledgeTrust'),
        trustText: document.getElementById('knowledgeTrustText'),
        warning: document.getElementById('knowledgeWarning'),
        actions: document.getElementById('knowledgeActions'),
        sources: document.getElementById('knowledgeSources'),
        sourcesList: document.getElementById('knowledgeSourcesList'),
        sourcesClose: document.getElementById('knowledgeSourcesClose'),
        recent: document.getElementById('knowledgeRecent'),
        recentList: document.getElementById('knowledgeRecentList'),
        recentClear: document.getElementById('knowledgeRecentClear'),
    };

    let activeScope = params.get('scope') || 'all';
    let lastPayload = null;
    let loadingMessageTimer = null;
    const storageKey = `gv-sapiens-recent-v2:${root.dataset.companyId || 'product'}`;
    const scopeLabels = {
        all: 'Todos',
        company: 'Minha empresa',
        product: 'Como usar o APP Versus',
    };
    const trustLabels = {
        official: 'Conteúdo oficial',
        internal: 'Fonte interna autorizada',
        published: 'Publicado e vigente',
        active: 'Fonte ativa',
        draft: 'Conteúdo em rascunho',
    };

    function setScope(scope) {
        activeScope = ['all', 'company', 'product'].includes(scope) ? scope : 'all';
        elements.scopeButtons.forEach((button) => {
            const active = button.dataset.scope === activeScope;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });
        if (activeScope === 'product') {
            elements.question.placeholder = 'Ex.: Como publico um processo no Portal de Processos?';
            elements.sourceType.value = '';
            elements.sourceType.disabled = true;
        } else {
            elements.question.placeholder = 'Ex.: O que foi decidido na última reunião?';
            elements.sourceType.disabled = false;
        }
    }

    function resizeQuestion() {
        elements.question.style.height = 'auto';
        elements.question.style.height = `${Math.min(elements.question.scrollHeight, 126)}px`;
    }

    function setStatus(message, kind) {
        clearInterval(loadingMessageTimer);
        loadingMessageTimer = null;
        if (!message) {
            elements.status.hidden = true;
            elements.status.className = 'kv-status';
            elements.status.textContent = '';
            return;
        }
        elements.status.hidden = false;
        elements.status.className = `kv-status${kind ? ` is-${kind}` : ''}`;
        elements.status.textContent = message;
    }

    function beginLoading() {
        const messages = [
            'Entendendo sua pergunta…',
            'Consultando somente as fontes que você pode acessar…',
            'Organizando a resposta e as evidências…',
        ];
        let index = 0;
        setStatus(messages[index], 'loading');
        loadingMessageTimer = window.setInterval(() => {
            index = Math.min(index + 1, messages.length - 1);
            elements.status.textContent = messages[index];
        }, 1700);
    }

    function humanize(value) {
        if (!value) return '';
        return trustLabels[value] || String(value).replace(/[_-]+/g, ' ').replace(/^./, (char) => char.toUpperCase());
    }

    function safeAppTarget(value) {
        if (!value || typeof value !== 'string') return null;
        try {
            const target = new URL(value, window.location.origin);
            if (target.origin !== window.location.origin || !target.pathname.startsWith('/')) return null;
            return `${target.pathname}${target.search}${target.hash}`;
        } catch (_) {
            return null;
        }
    }

    function createIcon(className) {
        const icon = document.createElement('i');
        icon.className = className;
        icon.setAttribute('aria-hidden', 'true');
        return icon;
    }

    function createAction(label, iconClass, options) {
        const config = options || {};
        const target = safeAppTarget(config.target);
        const control = target ? document.createElement('a') : document.createElement('button');
        control.className = `kv-action${config.primary ? ' is-primary' : ''}`;
        if (target) control.href = target;
        else control.type = 'button';
        control.append(createIcon(iconClass), document.createTextNode(label));
        if (config.onClick) control.addEventListener('click', config.onClick);
        return control;
    }

    function renderTrust(payload) {
        const signals = Array.from(new Set((payload.trust_signals || []).filter(Boolean))).map(humanize);
        elements.trust.hidden = signals.length === 0;
        elements.trustText.textContent = '';
        if (!signals.length) return;
        const strong = document.createElement('strong');
        strong.textContent = signals[0];
        elements.trustText.append(strong);
        if (signals.length > 1) elements.trustText.append(document.createTextNode(` · ${signals.slice(1).join(' · ')}`));
    }

    function citationNumber(citationId, citations) {
        const index = citations.findIndex((item) => item.id === citationId);
        return index >= 0 ? index + 1 : null;
    }

    function openSources(citationId) {
        elements.sources.hidden = false;
        const target = citationId ? elements.sourcesList.querySelector(`[data-citation-id="${CSS.escape(citationId)}"]`) : null;
        (target || elements.sources).scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        if (target) {
            target.animate([{ backgroundColor: '#eaf4ff' }, { backgroundColor: '#fbfcfe' }], { duration: 900 });
        }
    }

    function renderAnswerBody(payload) {
        const claims = Array.isArray(payload.claims) ? payload.claims : [];
        const citations = Array.isArray(payload.citations) ? payload.citations : [];
        elements.answerBody.textContent = '';
        if (claims.length) {
            claims.forEach((claim) => {
                const paragraph = document.createElement('p');
                paragraph.className = 'kv-claim';
                paragraph.append(document.createTextNode(claim.text || ''));
                (claim.citations || []).forEach((citationId) => {
                    const number = citationNumber(citationId, citations);
                    if (!number) return;
                    paragraph.append(document.createTextNode(' '));
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'kv-citation';
                    button.textContent = String(number);
                    button.title = 'Ver fonte desta afirmação';
                    button.addEventListener('click', () => openSources(citationId));
                    paragraph.append(button);
                });
                elements.answerBody.append(paragraph);
            });
            return;
        }
        const text = document.createElement('p');
        text.className = 'kv-claim';
        text.textContent = payload.answer || 'Não encontrei uma resposta.';
        elements.answerBody.append(text);
    }

    function renderSources(payload) {
        const citations = Array.isArray(payload.citations) ? payload.citations : [];
        elements.sourcesList.textContent = '';
        elements.sources.hidden = true;
        citations.forEach((citation, index) => {
            const card = document.createElement('article');
            card.className = 'kv-source-card';
            card.dataset.citationId = citation.id || '';

            const title = document.createElement('div');
            title.className = 'kv-source-title';
            const titleText = document.createElement('span');
            titleText.textContent = `${index + 1}. ${citation.title || citation.source_ref || 'Fonte autorizada'}`;
            const sourceType = document.createElement('span');
            sourceType.className = 'kv-source-meta';
            sourceType.textContent = humanize(citation.source_type);
            title.append(titleText, sourceType);
            card.append(title);

            const metaParts = [
                citation.version ? `Versão ${citation.version}` : '',
                citation.valid_from ? `Vigente desde ${new Date(citation.valid_from).toLocaleDateString('pt-BR')}` : '',
                citation.source_ref || '',
            ].filter(Boolean);
            if (metaParts.length) {
                const meta = document.createElement('div');
                meta.className = 'kv-source-meta';
                meta.textContent = metaParts.join(' · ');
                card.append(meta);
            }
            if (citation.source_span) {
                const span = document.createElement('div');
                span.className = 'kv-source-span';
                span.textContent = citation.source_span;
                card.append(span);
            }
            const sourceTarget = safeAppTarget(citation.canonical_uri);
            if (sourceTarget) {
                const link = document.createElement('a');
                link.href = sourceTarget;
                link.textContent = 'Abrir fonte original';
                card.append(link);
            }
            elements.sourcesList.append(card);
        });
    }

    function renderActions(payload) {
        elements.actions.textContent = '';
        const actions = Array.isArray(payload.actions) ? payload.actions : [];
        actions.forEach((action, index) => {
            const target = safeAppTarget(action.target);
            if (!target) return;
            elements.actions.append(createAction(
                action.label || 'Abrir no APP Versus',
                action.label && action.label.toLowerCase().includes('processo') ? 'fas fa-diagram-project' : 'fas fa-location-arrow',
                { target, primary: index === 0 }
            ));
        });
        const sourceCount = (payload.citations || []).length;
        if (sourceCount) {
            elements.actions.append(createAction(
                `Ver ${sourceCount} ${sourceCount === 1 ? 'fonte' : 'fontes'}`,
                'far fa-copy',
                { onClick: () => openSources() }
            ));
        }
        elements.actions.append(createAction('Nova pergunta', 'fas fa-rotate', {
            onClick: () => {
                elements.question.value = '';
                resizeQuestion();
                elements.question.focus();
            },
        }));
    }

    function renderWarnings(payload) {
        const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
        const hasGap = warnings.includes('knowledge_gap');
        elements.warning.hidden = !warnings.length;
        elements.warning.textContent = hasGap
            ? 'Não encontrei evidência autorizada suficiente. A resposta abaixo não deve ser tratada como procedimento ou decisão oficial.'
            : warnings.map(humanize).join(' · ');
    }

    function renderPayload(payload, question) {
        lastPayload = payload;
        elements.empty.hidden = true;
        elements.answer.hidden = false;
        elements.answerEyebrow.textContent = payload.presentation?.eyebrow || 'Resposta do Sapiens';
        elements.answerTitle.textContent = question;
        elements.answerBadge.textContent = payload.presentation?.source_label || (payload.mode === 'operational' ? 'Resposta operacional' : 'Fontes autorizadas');
        elements.mode.innerHTML = '';
        elements.mode.append(createIcon(payload.presentation?.strategy_label === 'Busca aprofundada' ? 'fas fa-magnifying-glass' : 'fas fa-bolt'));
        elements.mode.append(document.createTextNode(` ${payload.presentation?.strategy_label || 'Busca rápida'} selecionada automaticamente`));
        renderTrust(payload);
        renderAnswerBody(payload);
        renderWarnings(payload);
        renderActions(payload);
        renderSources(payload);
        elements.answer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async function requestKnowledge(question) {
        const sourceType = elements.sourceType.value;
        const response = await fetch('/api/agents/knowledge/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                scope: activeScope,
                source_types: sourceType ? [sourceType] : [],
            }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) throw new Error(payload.error || 'Não foi possível consultar as fontes agora.');
        return payload;
    }

    async function requestOperationalFallback(question, knowledgePayload) {
        if (!(knowledgePayload.warnings || []).includes('knowledge_gap')) return knowledgePayload;
        setStatus('Não encontrei uma fonte indexada. Consultando o Sapiens operacional…', 'loading');
        const response = await fetch('/api/agents/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: question, contact: 'sapiens' }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success || !payload.response) return knowledgePayload;
        return {
            ...knowledgePayload,
            mode: 'operational',
            answer: payload.response,
            claims: [],
            trust_signals: [],
            presentation: {
                eyebrow: activeScope === 'product' ? 'Ajuda do APP Versus' : 'Resposta operacional',
                source_label: 'Sapiens',
                strategy_label: 'Consulta operacional',
            },
        };
    }

    async function submitQuestion(question) {
        const normalized = String(question || '').trim();
        if (normalized.length < 3) {
            setStatus('Digite uma pergunta com pelo menos 3 caracteres.', 'error');
            elements.question.focus();
            return;
        }
        elements.question.value = normalized;
        elements.submit.disabled = true;
        elements.answer.hidden = true;
        elements.empty.hidden = true;
        beginLoading();
        try {
            let payload;
            try {
                payload = await requestKnowledge(normalized);
                payload = await requestOperationalFallback(normalized, payload);
            } catch (knowledgeError) {
                const response = await fetch('/api/agents/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: normalized, contact: 'sapiens' }),
                });
                const fallback = await response.json().catch(() => ({}));
                if (!response.ok || !fallback.success) throw knowledgeError;
                payload = {
                    answer: fallback.response,
                    claims: [], citations: [], actions: [], warnings: [], trust_signals: [],
                    mode: 'operational',
                    presentation: { eyebrow: 'Resposta do Sapiens', source_label: 'Consulta operacional', strategy_label: 'Consulta operacional' },
                };
            }
            setStatus('');
            renderPayload(payload, normalized);
            saveRecent(normalized, activeScope);
        } catch (error) {
            elements.empty.hidden = false;
            setStatus(error.message || 'Não foi possível responder agora. Tente novamente.', 'error');
        } finally {
            elements.submit.disabled = false;
        }
    }

    function readRecent() {
        try {
            const data = JSON.parse(localStorage.getItem(storageKey) || '[]');
            return Array.isArray(data) ? data.slice(0, 6) : [];
        } catch (_) {
            return [];
        }
    }

    function saveRecent(question, scope) {
        const recent = readRecent().filter((item) => item.question !== question);
        recent.unshift({ question, scope, at: new Date().toISOString() });
        localStorage.setItem(storageKey, JSON.stringify(recent.slice(0, 6)));
        renderRecent();
    }

    function renderRecent() {
        const recent = readRecent();
        elements.recent.hidden = recent.length === 0;
        elements.recentList.textContent = '';
        recent.forEach((item) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = item.question;
            button.title = scopeLabels[item.scope] || scopeLabels.all;
            button.addEventListener('click', () => {
                setScope(item.scope);
                elements.question.value = item.question;
                resizeQuestion();
                submitQuestion(item.question);
            });
            elements.recentList.append(button);
        });
    }

    elements.scopeButtons.forEach((button) => button.addEventListener('click', () => setScope(button.dataset.scope)));
    elements.form.addEventListener('submit', (event) => { event.preventDefault(); submitQuestion(elements.question.value); });
    elements.question.addEventListener('input', resizeQuestion);
    elements.question.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            elements.form.requestSubmit();
        }
    });
    elements.suggestions.addEventListener('click', (event) => {
        const button = event.target.closest('[data-question]');
        if (!button) return;
        elements.question.value = button.dataset.question;
        resizeQuestion();
        submitQuestion(button.dataset.question);
    });
    elements.refineToggle.addEventListener('click', () => {
        const willOpen = elements.refinePanel.hidden;
        elements.refinePanel.hidden = !willOpen;
        elements.refineToggle.setAttribute('aria-expanded', String(willOpen));
    });
    elements.sourcesClose.addEventListener('click', () => { elements.sources.hidden = true; });
    elements.recentClear.addEventListener('click', () => { localStorage.removeItem(storageKey); renderRecent(); });
    root.querySelectorAll('[data-feedback]').forEach((button) => {
        button.addEventListener('click', () => {
            root.querySelectorAll('[data-feedback]').forEach((item) => item.classList.remove('is-selected'));
            button.classList.add('is-selected');
            button.title = 'Obrigado pelo feedback';
        });
    });

    setScope(activeScope);
    renderRecent();
    const preset = params.get('preset');
    if (preset) {
        elements.question.value = preset;
        resizeQuestion();
    }
})();
