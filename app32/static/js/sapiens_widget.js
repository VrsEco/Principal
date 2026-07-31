(function () {
    'use strict';

    const root = document.getElementById('sapiens-widget-container');
    if (!root) return;

    const panel = document.getElementById('sapiens-widget-panel');
    const launcher = document.getElementById('sapiens-launcher');
    const closeButton = root.querySelector('[data-sapiens-close]');
    const scopeButtons = Array.from(root.querySelectorAll('[data-sapiens-scope]'));
    const messages = document.getElementById('sapiens-widget-messages');
    const status = document.getElementById('sapiens-widget-status');
    const form = document.getElementById('sapiens-widget-form');
    const input = document.getElementById('sapiens-widget-input');
    const submit = form.querySelector('button[type="submit"]');
    let activeScope = 'all';

    function setOpen(open) {
        panel.hidden = !open;
        launcher.setAttribute('aria-expanded', String(open));
        launcher.setAttribute('aria-label', open ? 'Fechar Sapiens' : 'Abrir Sapiens');
        if (open) window.setTimeout(() => input.focus(), 0);
    }

    function setScope(scope) {
        activeScope = ['all', 'company', 'product'].includes(scope) ? scope : 'all';
        scopeButtons.forEach((button) => {
            const active = button.dataset.sapiensScope === activeScope;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });
        input.placeholder = activeScope === 'product'
            ? 'Como uso o APP Versus?'
            : 'Faça uma pergunta...';
    }

    function showStatus(text, kind) {
        status.hidden = !text;
        status.textContent = text || '';
        status.classList.toggle('is-error', kind === 'error');
    }

    function safeTarget(value) {
        const target = String(value || '').trim();
        return target.startsWith('/') && !target.startsWith('//') && !target.includes('\\')
            ? target
            : '';
    }

    function appendInline(container, value) {
        const text = String(value || '');
        const pattern = /\*\*([^*]+)\*\*/g;
        let cursor = 0;
        let match;
        while ((match = pattern.exec(text)) !== null) {
            if (match.index > cursor) container.append(document.createTextNode(text.slice(cursor, match.index)));
            const strong = document.createElement('strong');
            strong.textContent = match[1];
            container.append(strong);
            cursor = match.index + match[0].length;
        }
        if (cursor < text.length) container.append(document.createTextNode(text.slice(cursor)));
    }

    function appendStructured(container, value) {
        const lines = String(value || '').split(/\r?\n/);
        let list = null;
        let listType = null;
        lines.forEach((rawLine) => {
            const line = rawLine.trim();
            if (!line) { list = null; listType = null; return; }
            const heading = line.match(/^#{1,4}\s+(.+)$/);
            const ordered = line.match(/^\d+[.)]\s+(.+)$/);
            const bullet = line.match(/^[-*]\s+(.+)$/);
            if (heading) {
                list = null; listType = null;
                const title = document.createElement('h4');
                appendInline(title, heading[1]);
                container.append(title);
                return;
            }
            if (ordered || bullet) {
                const nextType = ordered ? 'ol' : 'ul';
                if (!list || listType !== nextType) {
                    list = document.createElement(nextType);
                    listType = nextType;
                    container.append(list);
                }
                const item = document.createElement('li');
                appendInline(item, (ordered || bullet)[1]);
                list.append(item);
                return;
            }
            list = null; listType = null;
            const paragraph = document.createElement('p');
            appendInline(paragraph, line);
            container.append(paragraph);
        });
    }

    function appendMessage(text, role) {
        const welcome = messages.querySelector('.sapiens-widget-welcome');
        if (welcome) welcome.remove();
        const card = document.createElement('article');
        card.className = `sapiens-widget-message${role === 'user' ? ' is-user' : ''}`;
        if (role === 'user') card.textContent = text;
        else appendStructured(card, text);
        messages.append(card);
        messages.scrollTop = messages.scrollHeight;
        return card;
    }

    function renderPayload(payload) {
        const claims = Array.isArray(payload.claims) ? payload.claims : [];
        const answer = claims.length
            ? claims.map((claim) => claim.text || '').filter(Boolean).join('\n\n')
            : payload.answer;
        const card = appendMessage(answer || 'Não encontrei uma resposta segura.', 'assistant');
        const actions = (payload.actions || []).filter((action) => safeTarget(action.target));
        if (actions.length) {
            const row = document.createElement('div');
            row.className = 'sapiens-widget-actions';
            actions.forEach((action) => {
                const link = document.createElement('a');
                link.href = safeTarget(action.target);
                link.textContent = action.label || 'Abrir no APP Versus';
                row.append(link);
            });
            card.append(row);
        }
        const citations = Array.isArray(payload.citations) ? payload.citations : [];
        if (citations.length) {
            const note = document.createElement('div');
            note.className = 'sapiens-widget-source-note';
            note.textContent = `${citations.length} ${citations.length === 1 ? 'fonte oficial consultada' : 'fontes autorizadas consultadas'}`;
            card.append(note);
        }
    }

    function looksLikeGuidanceQuestion(question) {
        const normalized = String(question || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
        return /^(como|onde|por onde)\b/.test(normalized)
            || /\b(me ensine|me oriente|preciso de ajuda|ajuda para)\b/.test(normalized);
    }

    async function fetchJson(url, options, timeoutMs) {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
        try {
            const response = await fetch(url, { ...options, signal: controller.signal });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || !payload.success) throw new Error(payload.error || 'Não foi possível consultar o Sapiens.');
            return payload;
        } finally {
            window.clearTimeout(timeout);
        }
    }

    async function askKnowledge(question) {
        const payload = await fetchJson('/api/agents/knowledge/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, scope: activeScope, source_types: [] }),
        }, 12000);
        if (!(payload.warnings || []).includes('knowledge_gap')
            || activeScope === 'product'
            || looksLikeGuidanceQuestion(question)) return payload;
        const fallback = await fetchJson('/api/agents/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: question, contact: 'sapiens' }),
        }, 15000);
        return {
            ...payload,
            answer: fallback.response,
            claims: [], citations: [], actions: [], warnings: [],
        };
    }

    async function submitQuestion() {
        const question = input.value.trim();
        if (question.length < 3) {
            showStatus('Digite uma pergunta com pelo menos 3 caracteres.', 'error');
            return;
        }
        appendMessage(question, 'user');
        input.value = '';
        input.style.height = 'auto';
        submit.disabled = true;
        showStatus('Consultando fontes autorizadas...');
        try {
            const payload = await askKnowledge(question);
            renderPayload(payload);
            showStatus('');
        } catch (error) {
            showStatus(error.name === 'AbortError'
                ? 'A consulta demorou além do esperado. Tente novamente.'
                : (error.message || 'Não foi possível responder agora.'), 'error');
        } finally {
            submit.disabled = false;
        }
    }

    launcher.addEventListener('click', () => setOpen(panel.hidden));
    closeButton.addEventListener('click', () => setOpen(false));
    scopeButtons.forEach((button) => button.addEventListener('click', () => setScope(button.dataset.sapiensScope)));
    form.addEventListener('submit', (event) => { event.preventDefault(); submitQuestion(); });
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = `${Math.min(input.scrollHeight, 108)}px`;
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !panel.hidden) setOpen(false);
    });
    setScope('all');
})();
