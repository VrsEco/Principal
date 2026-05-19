document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('[data-report-workspace-root]');
  const form = document.querySelector('[data-report-filter-form]');

  if (!root || !form) {
    return;
  }

  const clearButton = form.querySelector('[data-report-clear-filters]');
  const trackedInputs = Array.from(form.querySelectorAll('[data-filter-input]'));
  const countTargets = [
    root.dataset.filterCountTarget,
    root.dataset.filterCountSecondaryTarget,
  ]
    .filter(Boolean)
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  const normalizeSearchTerm = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

  const filterSelectOptions = (selectId, searchValue) => {
    const select = document.getElementById(selectId);
    if (!select) return;
    const search = normalizeSearchTerm(searchValue);
    Array.from(select.options || []).forEach((option) => {
      const keepVisible = !search || normalizeSearchTerm(option.textContent || option.label || '').includes(search);
      option.hidden = !keepVisible;
    });
  };

  const resolveFormAction = () => {
    form.action = form.dataset.viewAction || form.getAttribute('action') || window.location.pathname;
  };

  const countActiveFilters = () => {
    const radioGroups = new Set();
    let total = 0;

    trackedInputs.forEach((input) => {
      if (input.type === 'radio') {
        if (radioGroups.has(input.name)) {
          return;
        }
        radioGroups.add(input.name);
        const checked = form.querySelector(`input[name="${input.name}"]:checked`);
        const defaultValue = input.dataset.defaultValue || '';
        if (checked && checked.value !== defaultValue) {
          total += 1;
        }
        return;
      }

      if (input.type === 'checkbox') {
        const defaultValue = input.dataset.defaultValue === 'true';
        if (input.checked !== defaultValue) {
          total += 1;
        }
        return;
      }

      if (input.tagName === 'SELECT' && input.multiple) {
        const selectedValues = Array.from(input.selectedOptions)
          .map((option) => option.value)
          .filter((value) => value !== '');
        if (selectedValues.length > 0) {
          total += 1;
        }
        return;
      }

      const defaultValue = input.dataset.defaultValue || '';
      if ((input.value || '') !== defaultValue) {
        total += 1;
      }
    });

    countTargets.forEach((target) => {
      target.textContent = String(total);
    });
  };

  form.addEventListener('submit', resolveFormAction);

  trackedInputs.forEach((input) => {
    const eventName = input.tagName === 'SELECT' || input.type === 'radio' || input.type === 'checkbox'
      ? 'change'
      : 'input';
    input.addEventListener(eventName, () => {
      resolveFormAction();
      countActiveFilters();
    });
  });

  form.querySelectorAll('[data-select-filter-target]').forEach((input) => {
    input.addEventListener('input', () => {
      filterSelectOptions(input.dataset.selectFilterTarget, input.value || '');
    });
  });

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      const clearUrl = form.dataset.clearUrl;
      if (clearUrl) {
        window.location.href = clearUrl;
      }
    });
  }

  resolveFormAction();
  countActiveFilters();
});
