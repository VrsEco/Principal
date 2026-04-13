(function () {
  const page = document.getElementById('aiCapabilitiesPage');
  if (!page) return;

  const tabTriggers = Array.from(document.querySelectorAll('[data-tab-trigger]'));
  const tabPanels = Array.from(document.querySelectorAll('[data-tab-panel]'));
  const tabJumpers = Array.from(document.querySelectorAll('[data-tab-jump]'));
  const searchInput = document.getElementById('aiCapabilitiesSearch');
  const assistantButtons = Array.from(document.querySelectorAll('[data-assistant-option]'));
  const assistantResult = document.getElementById('aiCapabilitiesAssistantResult');
  const assistantTitle = document.getElementById('aiCapabilitiesAssistantTitle');
  const assistantBody = document.getElementById('aiCapabilitiesAssistantBody');
  const assistantGo = document.getElementById('aiCapabilitiesAssistantGo');

  let assistantTargetTab = page.dataset.defaultTab || 'catalog';

  function activateTab(tabKey) {
    tabTriggers.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.tabTrigger === tabKey);
    });

    tabPanels.forEach((panel) => {
      panel.classList.toggle('is-active', panel.dataset.tabPanel === tabKey);
    });

    document.querySelectorAll('[data-tab-jump]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.tabJump === tabKey);
    });
  }

  function normalize(text) {
    return (text || '')
      .toString()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  }

  function applySearch(value) {
    const query = normalize(value);
    const searchableNodes = Array.from(document.querySelectorAll('[data-searchable]'));

    searchableNodes.forEach((node) => {
      const matches = !query || normalize(node.dataset.searchable).includes(query);
      node.style.display = matches ? '' : 'none';
    });
  }

  tabTriggers.forEach((button) => {
    button.addEventListener('click', () => activateTab(button.dataset.tabTrigger));
  });

  tabJumpers.forEach((button) => {
    button.addEventListener('click', () => activateTab(button.dataset.tabJump));
  });

  assistantButtons.forEach((button) => {
    button.addEventListener('click', () => {
      assistantTargetTab = button.dataset.targetTab || 'catalog';
      assistantTitle.textContent = button.dataset.resultTitle || 'Próximo passo';
      assistantBody.textContent = button.dataset.resultBody || '';
      assistantResult.hidden = false;
    });
  });

  if (assistantGo) {
    assistantGo.addEventListener('click', () => activateTab(assistantTargetTab));
  }

  if (searchInput) {
    searchInput.addEventListener('input', (event) => applySearch(event.target.value));
  }

  activateTab(page.dataset.defaultTab || 'catalog');
})();
