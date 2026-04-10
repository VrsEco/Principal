document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('aiMcpConsolePage');
    if (!root) return;

    const tabs = Array.from(root.querySelectorAll('[data-console-tab]'));
    const panels = Array.from(root.querySelectorAll('[data-console-panel]'));
    const searchInput = document.getElementById('aiMcpConsoleSearch');

    function activateTab(target) {
        tabs.forEach((tab) => tab.classList.toggle('is-active', tab.dataset.consoleTab === target));
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.consolePanel === target));
    }

    function normalize(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function applySearch(term) {
        const needle = normalize(term);
        panels.forEach((panel) => {
            const haystack = normalize(panel.dataset.searchable || panel.textContent || '');
            const panelMatch = !needle || haystack.includes(needle);
            panel.classList.toggle('ai-mcp-hidden', !panelMatch);

            panel.querySelectorAll('[data-searchable]').forEach((node) => {
                const nodeMatch = !needle || normalize(node.dataset.searchable || node.textContent || '').includes(needle);
                node.classList.toggle('ai-mcp-hidden', !nodeMatch);
            });
        });
    }

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => activateTab(tab.dataset.consoleTab));
    });

    searchInput?.addEventListener('input', (event) => applySearch(event.target.value));
    activateTab(root.dataset.defaultTab || tabs[0]?.dataset.consoleTab || 'overview');
});
