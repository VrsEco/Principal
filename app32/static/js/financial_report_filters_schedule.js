document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('[data-schedule-report-root]');
  const form = document.getElementById('schedule-report-filter-form');

  if (!root || !form) {
    return;
  }

  const badge = document.getElementById('schedule-report-filter-count');
  const inlineCounter = document.getElementById('schedule-report-active-filters-inline');
  const clearButton = document.getElementById('schedule-report-clear-filters');
  const trackedInputs = Array.from(form.querySelectorAll('[data-filter-input]'));

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

    if (badge) {
      badge.textContent = String(total);
    }
    if (inlineCounter) {
      inlineCounter.textContent = String(total);
    }
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
