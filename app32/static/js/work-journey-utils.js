(() => {
  const itemTypes = [
    { value: 'manual', label: 'Tarefa Avulsa' },
    { value: 'process_instance', label: 'Instância de Processo' },
    { value: 'project_task', label: 'Atividade de Projeto' },
    { value: 'meeting', label: 'Reunião' },
  ];

  const weekdays = [
    { value: 0, label: 'Seg' },
    { value: 1, label: 'Ter' },
    { value: 2, label: 'Qua' },
    { value: 3, label: 'Qui' },
    { value: 4, label: 'Sex' },
    { value: 5, label: 'Sáb' },
    { value: 6, label: 'Dom' },
  ];

  function normalizeErrorMessage(value) {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      const messages = value
        .map((item) => {
          if (typeof item === 'string') return item;
          if (!item || typeof item !== 'object') return '';
          const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== '__root__').join(' → ') : '';
          const message = item.msg || item.message || '';
          return location ? `${location}: ${message}` : message;
        })
        .filter(Boolean);
      return messages.join('; ');
    }
    if (value && typeof value === 'object') {
      if (typeof value.message === 'string') return value.message;
      try {
        return JSON.stringify(value);
      } catch (_error) {
        return 'Falha na operação.';
      }
    }
    return value ? String(value) : '';
  }

  function api(path, options = {}) {
    return fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    }).then(async (res) => {
      const json = await res.json().catch(() => ({}));
      if (!res.ok || json.success === false) {
        throw new Error(
          normalizeErrorMessage(json.message)
          || normalizeErrorMessage(json.error)
          || 'Falha na operação.'
        );
      }
      return json;
    });
  }

  function toast(message) {
    window.alert(message);
  }

  function formatMinutes(minutes) {
    const total = Number(minutes || 0);
    const hours = Math.floor(total / 60);
    const remainder = total % 60;
    if (!hours) return `${remainder} min`;
    if (!remainder) return `${hours}h`;
    return `${hours}h${String(remainder).padStart(2, '0')}`;
  }


  function renderTabs() {
    document.querySelectorAll('.journey-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.journey-tab').forEach((item) => item.classList.toggle('is-active', item === btn));
        document.querySelectorAll('.journey-tabpanel').forEach((panel) => panel.classList.toggle('is-active', panel.dataset.panel === btn.dataset.tab));
      });
    });
  }

  function renderCheckboxGrid(targetId, items, defaultValues = []) {
    const target = document.getElementById(targetId);
    target.innerHTML = items.map((item) => `
      <label class="journey-checkbox">
        <input type="checkbox" value="${item.value}" ${defaultValues.includes(item.value) ? 'checked' : ''}>
        <span>${item.label}</span>
      </label>
    `).join('');
  }

  function collectCheckedValues(targetId, castNumber = false) {
    return Array.from(document.querySelectorAll(`#${targetId} input[type="checkbox"]:checked`)).map((input) => castNumber ? Number(input.value) : input.value);
  }

  window.WorkJourneyUtils = {
    api,
    toast,
    formatMinutes,
    renderTabs,
    renderCheckboxGrid,
    collectCheckedValues,
    itemTypes,
    weekdays,
  };
})();
