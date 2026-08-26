(function () {
    'use strict';

    const root = document.getElementById('knowledgeExperience');
    const workspace = document.getElementById('strategicTreeWorkspace');
    if (!root || !workspace) return;

    const elements = {
        ask: root.querySelector('.kv-ask-card'),
        select: document.getElementById('strategicTreeSelect'),
        status: document.getElementById('strategicTreeStatus'),
        empty: document.getElementById('strategicTreeEmpty'),
        create: document.getElementById('strategicTreeCreate'),
        layout: document.getElementById('strategicTreeLayout'),
        name: document.getElementById('strategicTreeName'),
        nav: document.getElementById('strategicTreeNav'),
        breadcrumb: document.getElementById('strategicTreeBreadcrumb'),
        branchTitle: document.getElementById('strategicBranchTitle'),
        branchState: document.getElementById('strategicBranchState'),
        count: document.getElementById('strategicContributionCount'),
        contributions: document.getElementById('strategicTreeContributions'),
        composer: document.getElementById('strategicTreeComposer'),
        content: document.getElementById('strategicTreeContent'),
        confidential: document.getElementById('strategicTreeConfidential'),
        nextAction: document.getElementById('strategicTreeNextAction'),
    };

    let initialized = false;
    let activeTree = null;
    let activeNodeId = null;
    let treeSnapshot = null;
    const csrfToken = root.dataset.strategicTreeCsrf || '';

    function setStatus(message, error) {
        elements.status.hidden = !message;
        elements.status.textContent = message || '';
        elements.status.classList.toggle('is-error', Boolean(error));
    }

    async function api(path, options) {
        const response = await fetch(path, {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...(options?.method && options.method !== 'GET' ? { 'X-CSRF-Token': csrfToken } : {}),
                ...(options?.headers || {}),
            },
            ...options,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) throw new Error(payload.error || 'Não foi possível carregar a Árvore Estratégica.');
        return payload;
    }

    function toggleSurface(scope) {
        const active = scope === 'strategic_tree';
        root.classList.toggle('is-strategic-tree', active);
        workspace.hidden = !active;
        if (elements.ask) elements.ask.hidden = active;
        if (active && !initialized) initialize();
    }

    function flattenNode(node, depth, output) {
        if (!node) return;
        output.push({ node, depth });
        (node.children || []).forEach((child) => flattenNode(child, depth + 1, output));
    }

    function renderTree(snapshot) {
        treeSnapshot = snapshot;
        activeTree = snapshot.tree;
        elements.name.textContent = activeTree.title;
        elements.nav.textContent = '';
        const nodes = [];
        flattenNode(snapshot.root, 0, nodes);
        nodes.forEach(({ node, depth }) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `st-node st-node-depth-${Math.min(depth, 2)}`;
            button.classList.toggle('is-active', node.id === activeNodeId);
            button.dataset.nodeId = String(node.id);

            const icon = document.createElement('span');
            icon.className = 'st-node-icon';
            const iconElement = document.createElement('i');
            iconElement.className = node.node_type === 'root' ? 'fas fa-sitemap' : 'far fa-folder';
            icon.append(iconElement);
            const label = document.createElement('span');
            label.className = 'st-node-label';
            label.textContent = node.title;
            const count = document.createElement('span');
            count.className = 'st-node-count';
            count.textContent = String(snapshot.contribution_counts?.[node.id] || 0);
            button.append(icon, label, count);
            button.addEventListener('click', () => loadBranch(node.id));
            elements.nav.append(button);
        });
    }

    function renderBreadcrumb(items) {
        elements.breadcrumb.textContent = '';
        (items || []).forEach((item) => {
            const span = document.createElement('span');
            span.textContent = item.title;
            elements.breadcrumb.append(span);
        });
    }

    function visibleStatus(value) {
        return {
            collecting: 'Coletando informações', analyzing: 'Analisando',
            ready_to_discuss: 'Pronto para discutir', awaiting_decision: 'Aguardando decisão',
            in_execution: 'Em execução', completed: 'Concluído', parked: 'Estacionado',
        }[value] || 'Coletando informações';
    }

    function renderContributions(items) {
        elements.contributions.textContent = '';
        if (!items.length) {
            const empty = document.createElement('p');
            empty.className = 'st-no-content';
            empty.textContent = 'Este tema ainda está vazio. Registre a primeira percepção, fato, dúvida ou ideia para começar a discussão.';
            elements.contributions.append(empty);
            return;
        }
        items.forEach((item) => {
            const card = document.createElement('article');
            card.className = 'st-contribution';
            const text = document.createElement('p');
            text.textContent = item.content || '';
            const meta = document.createElement('div');
            meta.className = 'st-contribution-meta';
            const tag = document.createElement('span');
            tag.className = 'st-contribution-tag';
            tag.textContent = item.attribution_mode === 'confidential' ? 'Confidencial' : 'Contribuição';
            const date = document.createElement('span');
            date.textContent = item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '';
            meta.append(tag, date);
            card.append(text, meta);
            elements.contributions.append(card);
        });
    }

    async function loadBranch(nodeId) {
        if (!activeTree) return;
        activeNodeId = Number(nodeId);
        renderTree(treeSnapshot);
        setStatus('Carregando o tema…');
        try {
            const payload = await api(`/api/knowledge/strategic-trees/${activeTree.id}/nodes/${activeNodeId}`);
            elements.branchTitle.textContent = payload.node.title;
            elements.branchState.textContent = visibleStatus(payload.node.visible_status);
            elements.count.textContent = `${payload.contributions.length} ${payload.contributions.length === 1 ? 'registro' : 'registros'}`;
            elements.nextAction.textContent = payload.next_action || 'Adicionar informação';
            renderBreadcrumb(payload.breadcrumb);
            renderContributions(payload.contributions || []);
            setStatus('');
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    async function loadTree(treeId, preferredNodeId) {
        setStatus('Organizando os ramos…');
        try {
            const payload = await api(`/api/knowledge/strategic-trees/${treeId}`);
            activeNodeId = Number(preferredNodeId || payload.tree.root_node_id);
            renderTree(payload);
            elements.layout.hidden = false;
            elements.empty.hidden = true;
            await loadBranch(activeNodeId);
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    async function loadTrees() {
        setStatus('Carregando suas árvores…');
        try {
            const payload = await api('/api/knowledge/strategic-trees');
            elements.select.textContent = '';
            (payload.trees || []).forEach((tree) => {
                const option = document.createElement('option');
                option.value = String(tree.id);
                option.textContent = tree.title;
                elements.select.append(option);
            });
            const hasTrees = Boolean(payload.trees?.length);
            elements.empty.hidden = hasTrees;
            elements.layout.hidden = !hasTrees;
            elements.select.disabled = !hasTrees;
            setStatus('');
            if (hasTrees) await loadTree(payload.trees[0].id);
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    async function createTree() {
        elements.create.disabled = true;
        setStatus('Criando a estrutura inicial…');
        const companyName = root.querySelector('.kv-company')?.textContent?.trim() || 'Empresa';
        try {
            const payload = await api('/api/knowledge/strategic-trees', {
                method: 'POST',
                body: JSON.stringify({
                    title: `Reestruturação — ${companyName}`,
                    purpose: 'Organizar e amadurecer o conhecimento estratégico e operacional da empresa.',
                }),
            });
            await loadTrees();
            elements.select.value = String(payload.tree.id);
            await loadTree(payload.tree.id);
        } catch (error) {
            setStatus(error.message, true);
        } finally {
            elements.create.disabled = false;
        }
    }

    async function addContribution(event) {
        event.preventDefault();
        const content = elements.content.value.trim();
        if (content.length < 3 || !activeTree || !activeNodeId) {
            setStatus('Escreva ao menos três caracteres antes de registrar.', true);
            return;
        }
        const submit = elements.composer.querySelector('button[type="submit"]');
        submit.disabled = true;
        setStatus('Registrando e classificando a informação…');
        const idempotencyKey = window.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        try {
            const payload = await api(`/api/knowledge/strategic-trees/${activeTree.id}/contributions`, {
                method: 'POST',
                headers: { 'Idempotency-Key': idempotencyKey },
                body: JSON.stringify({
                    node_id: activeNodeId,
                    content,
                    attribution_mode: elements.confidential.checked ? 'confidential' : 'identified',
                }),
            });
            elements.content.value = '';
            elements.confidential.checked = false;
            const targetNodeId = payload.classified_branch?.id || activeNodeId;
            await loadTree(activeTree.id, targetNodeId);
            setStatus(`Informação registrada em “${payload.classified_branch?.title || 'tema atual'}”.`);
            window.setTimeout(() => setStatus(''), 2800);
        } catch (error) {
            setStatus(error.message, true);
        } finally {
            submit.disabled = false;
        }
    }

    function initialize() {
        initialized = true;
        elements.create.addEventListener('click', createTree);
        elements.select.addEventListener('change', () => loadTree(Number(elements.select.value)));
        elements.composer.addEventListener('submit', addContribution);
        loadTrees();
    }

    root.addEventListener('sapiens:scope-change', (event) => toggleSurface(event.detail?.scope));
    const activeButton = root.querySelector('[data-scope].is-active');
    toggleSurface(activeButton?.dataset.scope || new URLSearchParams(window.location.search).get('scope') || 'all');
})();
