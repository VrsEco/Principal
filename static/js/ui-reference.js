/**
 * UI Reference System
 * Visualização de códigos completos e cópia rápida (Ctrl+Click)
 */

(function () {
    const CONFIG = {
        toggleKey: 'Y', // Pressione Ctrl + Shift + Y
        storageKey: 'ui_ref_debug_mode'
    };

    let isDebugMode = localStorage.getItem(CONFIG.storageKey) === 'true';
    let pageCode = document.body.dataset.pageRef || '??';
    let refBadges = [];
    let resizeScheduled = false;
    let rebuildScheduled = false;
    let mutationObserver = null;

    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'ui-ref-toggle';
    toggleBtn.innerHTML = '<span>&#128065;</span> Refs';
    document.body.appendChild(toggleBtn);

    if (isDebugMode) {
        enableDebug();
    }

    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.key.toUpperCase() === CONFIG.toggleKey) {
            e.preventDefault();
            toggleDebug();
        }
    });

    toggleBtn.addEventListener('click', toggleDebug);

    document.addEventListener('click', (e) => {
        const refElement = e.target.closest('[data-ref]');
        if (e.ctrlKey && refElement) {
            e.preventDefault();
            e.stopPropagation();
            const elementCode = refElement.dataset.ref;
            const fullCode = `${pageCode}-${elementCode}`;
            copyToClipboard(fullCode, refElement);
        }
    });

    function toggleDebug() {
        isDebugMode = !isDebugMode;
        localStorage.setItem(CONFIG.storageKey, isDebugMode);
        if (isDebugMode) {
            enableDebug();
        } else {
            disableDebug();
        }
    }

    function enableDebug() {
        document.body.classList.add('show-ref-codes');
        toggleBtn.style.display = 'flex';
        toggleBtn.classList.add('active');
        toggleBtn.innerHTML = '<span>&#128065;</span> Refs ON';
        console.log(`[UI Ref] Debug ativado. Página: ${pageCode}`);
        buildBadges();
        observeDomChanges();
    }

    function disableDebug() {
        document.body.classList.remove('show-ref-codes');
        toggleBtn.classList.remove('active');
        toggleBtn.innerHTML = '<span>&#128065;</span> Refs';
        clearBadges();
        disconnectObserver();
    }

    function copyToClipboard(text, element) {
        navigator.clipboard.writeText(text).then(() => {
            element.classList.add('ref-copied');
            setTimeout(() => element.classList.remove('ref-copied'), 500);
            showToast(`Código copiado: ${text}`);
        }).catch((err) => console.error('[UI Ref] Erro ao copiar:', err));
    }

    function showToast(message) {
        let toast = document.getElementById('ui-ref-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'ui-ref-toast';
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(248, 250, 252, 0.95);
                color: #111827;
                padding: 8px 18px;
                border-radius: 999px;
                font-weight: 700;
                letter-spacing: 0.06em;
                font-size: 12px;
                border: 1px solid rgba(15, 23, 42, 0.15);
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2);
                z-index: 100000;
                transition: opacity 0.3s;
            `;
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = '1';
        setTimeout(() => (toast.style.opacity = '0'), 2000);
    }

    function buildBadges() {
        clearBadges();
        document.querySelectorAll('[data-ref]').forEach((element) => {
            const elementCode = element.dataset.ref;
            if (!elementCode) return;

            const badge = document.createElement('span');
            badge.className = 'ui-ref-badge';
            badge.textContent = `${pageCode}-${elementCode}`;
            badge.dataset.refCode = elementCode;
            document.body.appendChild(badge);
            refBadges.push({ element, badge });
        });
        updateBadgePositions();
    }

    function clearBadges() {
        refBadges.forEach(({ badge }) => badge.remove());
        refBadges = [];
    }

    function updateBadgePositions() {
        if (!isDebugMode || !refBadges.length) return;

        refBadges = refBadges.filter(({ element, badge }) => {
            if (!document.body.contains(element)) {
                badge.remove();
                return false;
            }

            const rect = element.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) {
                badge.style.display = 'none';
                return true;
            }

            badge.style.display = 'block';
            const preferTop = rect.top > 30;
            const top = preferTop
                ? window.scrollY + rect.top - 12
                : window.scrollY + rect.bottom + 6;
            const left = window.scrollX + rect.left;
            badge.style.top = `${top}px`;
            badge.style.left = `${left}px`;
            badge.dataset.position = preferTop ? 'top' : 'bottom';
            return true;
        });
    }

    function scheduleBadgePositionUpdate() {
        if (resizeScheduled) return;
        resizeScheduled = true;
        requestAnimationFrame(() => {
            resizeScheduled = false;
            updateBadgePositions();
        });
    }

    function scheduleBadgeRebuild() {
        if (!isDebugMode || rebuildScheduled) return;
        rebuildScheduled = true;
        requestAnimationFrame(() => {
            rebuildScheduled = false;
            buildBadges();
        });
    }

    function observeDomChanges() {
        if (mutationObserver) return;
        mutationObserver = new MutationObserver(() => scheduleBadgeRebuild());
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-ref']
        });
    }

    function disconnectObserver() {
        if (mutationObserver) {
            mutationObserver.disconnect();
            mutationObserver = null;
        }
    }

    window.addEventListener('resize', scheduleBadgePositionUpdate);
    window.addEventListener('scroll', scheduleBadgePositionUpdate, true);

    document.querySelectorAll('[data-ref]').forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.top < 40) {
            el.classList.add('ref-bottom');
        }
    });
})();
