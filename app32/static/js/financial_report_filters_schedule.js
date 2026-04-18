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

  const resolveOutputAction = () => {
    const selectedOutput = form.querySelector('input[name="output_mode"]:checked');
    form.action = selectedOutput && selectedOutput.value === 'pdf'
      ? form.dataset.pdfAction
      : form.dataset.viewAction;
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

  form.addEventListener('submit', resolveOutputAction);

  trackedInputs.forEach((input) => {
    const eventName = input.tagName === 'SELECT' || input.type === 'radio' || input.type === 'checkbox'
      ? 'change'
      : 'input';
    input.addEventListener(eventName, () => {
      resolveOutputAction();
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

  resolveOutputAction();
  countActiveFilters();
});
