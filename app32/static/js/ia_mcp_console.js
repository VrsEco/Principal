(() => {
    const normalize = (value) => String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();

    const boot = () => {
        const root = document.querySelector('[data-mcp-console]');
        if (!root) return;

        const searchInput = root.querySelector('[data-console-search]');
        const filterButtons = Array.from(root.querySelectorAll('[data-console-filter]'));
        const navButtons = Array.from(root.querySelectorAll('[data-console-nav]'));
        const sections = Array.from(root.querySelectorAll('[data-console-section]'));
        const cards = Array.from(root.querySelectorAll('[data-console-card]'));
        const emptyState = root.querySelector('[data-console-empty]');

        let activeFilter = 'all';

        const setActiveNav = (targetId) => {
            navButtons.forEach((button) => {
                const isActive = button.dataset.consoleNav === targetId;
                button.classList.toggle('is-active', isActive);
                button.setAttribute('aria-current', isActive ? 'page' : 'false');
            });
        };

        const applyFilters = () => {
            const term = normalize(searchInput?.value);
            let visibleCards = 0;

            cards.forEach((card) => {
                const tags = normalize(card.dataset.consoleTags);
                const searchable = normalize(card.dataset.searchable);
                const matchesFilter = activeFilter === 'all' || tags.includes(activeFilter);
                const matchesSearch = !term || searchable.includes(term);
                const show = matchesFilter && matchesSearch;
                card.hidden = !show;
                if (show) visibleCards += 1;
            });

            sections.forEach((section) => {
                const hasVisibleCard = section.querySelector('[data-console-card]:not([hidden])');
                section.hidden = !hasVisibleCard;
            });

            if (emptyState) {
                emptyState.hidden = visibleCards > 0;
            }
        };

        filterButtons.forEach((button) => {
            button.addEventListener('click', () => {
                activeFilter = button.dataset.consoleFilter || 'all';
                filterButtons.forEach((item) => {
                    const isActive = item === button;
                    item.classList.toggle('is-active', isActive);
                    item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
                });
                applyFilters();
            });
        });

        navButtons.forEach((button) => {
            button.addEventListener('click', () => {
                const section = document.getElementById(button.dataset.consoleNav || '');
                if (!section || section.hidden) return;
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                setActiveNav(section.id);
            });
        });

        searchInput?.addEventListener('input', applyFilters);

        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting && !entry.target.hidden) {
                        setActiveNav(entry.target.id);
                    }
                });
            }, {
                threshold: 0.22,
                rootMargin: '-20% 0px -55% 0px',
            });

            sections.forEach((section) => observer.observe(section));
        }

        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && searchInput && document.activeElement === searchInput) {
                searchInput.value = '';
                applyFilters();
            }
        });

        applyFilters();
        setActiveNav(sections.find((section) => !section.hidden)?.id || 'visao-geral');
    };

    document.addEventListener('DOMContentLoaded', boot);
})();

