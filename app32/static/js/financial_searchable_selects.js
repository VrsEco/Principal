(function () {
  const DEFAULT_MAX_OPEN = 8;

  function normalizeSearchTerm(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function resolveSelect(targetOrId, root = document) {
    if (!targetOrId) return null;
    if (typeof targetOrId !== 'string') return targetOrId;
    return root.getElementById?.(targetOrId) || root.querySelector?.(`#${CSS.escape(targetOrId)}`) || null;
  }

  function ensureDefaults(select) {
    if (!select) return;
    if (!select.dataset.gvSearchableDefaultSize) {
      const sizeAttr = select.getAttribute('size');
      select.dataset.gvSearchableDefaultSize = sizeAttr || '';
    }
    if (!select.dataset.gvSearchableWasMultiple) {
      select.dataset.gvSearchableWasMultiple = select.multiple ? '1' : '0';
    }
  }

  function restoreSelectSize(select) {
    if (!select) return;
    ensureDefaults(select);
    const defaultSize = select.dataset.gvSearchableDefaultSize || '';
    if (defaultSize) {
      select.setAttribute('size', defaultSize);
      return;
    }
    select.removeAttribute('size');
  }

  function visibleOptions(select) {
    return Array.from(select?.options || []).filter((option) => !option.hidden);
  }

  function openSelect(select, searchValue = '') {
    if (!select) return;
    ensureDefaults(select);
    const search = normalizeSearchTerm(searchValue);
    if (!search) {
      restoreSelectSize(select);
      return;
    }
    const shown = visibleOptions(select).length;
    if (shown <= 1) {
      restoreSelectSize(select);
      return;
    }
    select.setAttribute('size', String(Math.min(Math.max(shown, 2), DEFAULT_MAX_OPEN)));
  }

  function filterSelectOptions(targetOrId, searchValue = '', root = document) {
    const select = resolveSelect(targetOrId, root);
    if (!select) return null;
    ensureDefaults(select);
    const search = normalizeSearchTerm(searchValue);
    Array.from(select.options || []).forEach((option, index) => {
      if (index === 0 && !select.multiple) {
        option.hidden = false;
        return;
      }
      const keepVisible = !search || normalizeSearchTerm(option.textContent || option.label || '').includes(search);
      option.hidden = !keepVisible;
    });
    openSelect(select, searchValue);
    return select;
  }

  function bindSearchInput(input, root = document) {
    if (!input || input.dataset.gvSearchableBound === '1') return;
    input.dataset.gvSearchableBound = '1';

    const getTarget = () => resolveSelect(input.dataset.selectFilterTarget, root);
    const apply = () => filterSelectOptions(getTarget(), input.value || '', root);

    input.addEventListener('input', apply);
    input.addEventListener('focus', apply);
    input.addEventListener('blur', () => {
      window.setTimeout(() => {
        const select = getTarget();
        if (!select) return;
        restoreSelectSize(select);
      }, 180);
    });

    apply();
  }

  function bindWithin(root = document) {
    root.querySelectorAll?.('[data-select-filter-target]').forEach((input) => bindSearchInput(input, root));
  }

  document.addEventListener('DOMContentLoaded', () => bindWithin(document));

  window.GVFinancialSearchableSelects = {
    normalizeSearchTerm,
    filterSelectOptions,
    openSelect,
    restoreSelectSize,
    bindWithin,
    bindSearchInput,
  };
})();
