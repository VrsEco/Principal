(function () {
  const STORAGE_PREFIX = 'gv-company-onboarding-draft';
  const stepOrder = ['dados', 'economico', 'cargos', 'colaboradores', 'usuarios', 'pontuacao', 'config'];
  const stepMeta = {
    dados: {
      title: '1. Quem é a empresa',
      description: 'Defina nome, código, propósito e a base institucional.',
      next: 'Depois vá para o contexto operacional e econômico.',
      hint: 'Comece por aqui se estiver criando do zero.'
    },
    economico: {
      title: '2. Contexto operacional',
      description: 'Preencha porte, segmento, cidade e CNPJ para ajudar relatórios e filtros.',
      next: 'Em seguida, ajuste a estrutura interna.',
      hint: 'Essa parte ajuda Rotina, Estratégia e Finanças a encontrarem a empresa certa.'
    },
    cargos: {
      title: '3. Estrutura e rotinas',
      description: 'Organize cargos, funções e volume planejado de pessoas.',
      next: 'Depois conecte colaboradores e acessos.',
      hint: 'Isso dá base para processos, projetos e reuniões.'
    },
    colaboradores: {
      title: '4. Time e execução',
      description: 'Cadastre pessoas que participam da operação e do dia a dia.',
      next: 'Agora transforme pessoas em usuários com acesso.',
      hint: 'Use este bloco para rotinas, execução e acompanhamento.'
    },
    usuarios: {
      title: '5. Acessos e permissões',
      description: 'Vincule usuários do sistema ao time da empresa.',
      next: 'Em seguida revise critérios e libere o sistema.',
      hint: 'Aqui você controla quem pode ver e fazer o quê.'
    },
    pontuacao: {
      title: '6. Regras de avaliação',
      description: 'Defina como o sistema mede prazo, atraso e comportamento operacional.',
      next: 'Por fim, ajuste estado, logo e preparação para API / MCP.',
      hint: 'Bom para governança e leitura executiva.'
    },
    config: {
      title: '7. API / MCP e sistema',
      description: 'Ative a unidade, carregue a identidade visual e deixe o ambiente pronto para Sapiens e agentes.',
      next: 'Revise tudo e salve.',
      hint: 'Use esta etapa para abrir a empresa para o ecossistema com segurança.'
    }
  };

  const actionMeta = {
    dados: { primaryLabel: 'Salvar e continuar', primaryKind: 'save', secondaryLabel: 'Próxima etapa: Contexto', secondaryTarget: 'economico' },
    economico: { primaryLabel: 'Salvar contexto', primaryKind: 'save', secondaryLabel: 'Próxima etapa: Estrutura', secondaryTarget: 'cargos' },
    cargos: { primaryLabel: 'Adicionar cargo', primaryKind: 'custom', primaryTarget: 'showAddRoleModal', secondaryLabel: 'Próxima etapa: Time', secondaryTarget: 'colaboradores' },
    colaboradores: { primaryLabel: 'Novo colaborador', primaryKind: 'custom', primaryTarget: 'showEmployeeModal', secondaryLabel: 'Próxima etapa: Acessos', secondaryTarget: 'usuarios' },
    usuarios: { primaryLabel: 'Vincular acesso', primaryKind: 'custom', primaryTarget: 'showAddUserModal', secondaryLabel: 'Próxima etapa: Regras', secondaryTarget: 'pontuacao' },
    pontuacao: { primaryLabel: 'Salvar regras', primaryKind: 'custom', primaryTarget: 'submitPerformanceForm', secondaryLabel: 'Próxima etapa: API / MCP', secondaryTarget: 'config' },
    config: { primaryLabel: 'Salvar sistema', primaryKind: 'save', secondaryLabel: 'Abrir API / MCP', secondaryHref: '/api-mcp' }
  };

  function getCompanyId() {
    return String(window.companyId || '').trim();
  }

  function getDraftKey() {
    return `${STORAGE_PREFIX}:${getCompanyId() || 'new'}`;
  }

  function getCurrentTabId() {
    const activeTab = document.querySelector('.tab-btn.active');
    return activeTab?.dataset.tab || 'dados';
  }

  function setHelpPanel(tabId) {
    const panel = document.getElementById('onboarding-context-panel');
    if (!panel) return;

    const meta = stepMeta[tabId] || stepMeta.dados;
    const modeLabel = getCompanyId() ? 'alterar empresa existente' : 'criar empresa nova';
    panel.innerHTML = `
      <h3>${meta.title}</h3>
      <p>${meta.description}</p>
      <ul class="onboarding-help-list">
        <li><strong>Modo atual:</strong> ${modeLabel}</li>
        <li><strong>Próximo passo:</strong> ${meta.next}</li>
        <li><strong>Dica:</strong> ${meta.hint}</li>
      </ul>
    `;
  }


  function updateFocusCard(tabId) {
    const question = document.getElementById('onboarding-focus-question');
    const confirm = document.getElementById('onboardingFocusConfirm');
    const focusMeta = {
      dados: { question: 'Você já preencheu quem é a empresa e o código dela?', label: 'Sim, ir para Contexto', target: 'economico' },
      economico: { question: 'O contexto econômico já está claro o suficiente para continuar?', label: 'Sim, ir para Estrutura', target: 'cargos' },
      cargos: { question: 'Você já definiu os cargos principais da empresa?', label: 'Sim, ir para Time', target: 'colaboradores' },
      colaboradores: { question: 'O time principal já está cadastrado?', label: 'Sim, ir para Acessos', target: 'usuarios' },
      usuarios: { question: 'Quem precisa entrar no sistema já foi vinculado?', label: 'Sim, ir para Regras', target: 'pontuacao' },
      pontuacao: { question: 'As regras mínimas já estão definidas?', label: 'Sim, ir para API / MCP', target: 'config' },
      config: { question: 'A empresa já está pronta para entrar em teste controlado?', label: 'Abrir API / MCP', href: '/api-mcp' }
    };
    const meta = focusMeta[tabId] || focusMeta.dados;
    if (question) question.textContent = meta.question;
    if (confirm) {
      confirm.textContent = meta.label;
      if (confirm.tagName === 'A') {
        if (meta.href) confirm.setAttribute('href', meta.href);
      } else if (meta.target) {
        confirm.dataset.wizardGoto = meta.target;
      }
    }
  }

  function setAdvancedVisibility(visible) {
    const advancedActions = document.getElementById('companyAdvancedActions');
    const advancedSide = document.getElementById('companyAdvancedSide');
    const toggle = document.getElementById('onboardingToggleAdvanced');
    if (advancedActions) advancedActions.style.display = visible ? 'flex' : 'none';
    if (advancedSide) advancedSide.style.display = visible ? 'grid' : 'none';
    if (toggle) {
      toggle.dataset.advancedVisible = visible ? 'true' : 'false';
      toggle.textContent = visible ? 'Esconder opções avançadas' : 'Mostrar opções avançadas';
    }
  }

  function updateNowCard(tabId) {
    const title = document.getElementById('onboarding-now-title');
    const body = document.getElementById('onboarding-now-body');
    const primary = document.getElementById('onboardingPrimaryAction');
    const secondary = document.getElementById('onboardingSecondaryAction');
    const meta = stepMeta[tabId] || stepMeta.dados;
    const action = actionMeta[tabId] || actionMeta.dados;

    if (title) title.textContent = 'Faça isso agora';
    if (body) body.textContent = `${meta.description} ${meta.next}`;
    if (primary) {
      primary.textContent = action.primaryLabel;
      primary.dataset.actionKind = action.primaryKind || 'save';
      primary.dataset.actionTarget = action.primaryTarget || '';
    }
    if (secondary) {
      if (secondary.tagName === 'A') {
        secondary.textContent = action.secondaryLabel;
        if (action.secondaryHref) secondary.setAttribute('href', action.secondaryHref);
      } else {
        secondary.textContent = action.secondaryLabel;
        if (action.secondaryTarget) secondary.dataset.wizardGoto = action.secondaryTarget;
      }
    }
  }

  function runPrimaryAction() {
    const primary = document.getElementById('onboardingPrimaryAction');
    if (!primary) return;
    const kind = primary.dataset.actionKind || 'save';
    const target = primary.dataset.actionTarget || '';
    if (kind === 'save') {
      if (typeof window.handleSubmit === 'function') window.handleSubmit();
      return;
    }
    if (kind === 'custom') {
      if (target === 'submitPerformanceForm') {
        document.querySelector('#content-pontuacao form')?.requestSubmit();
        return;
      }
      const fn = window[target];
      if (typeof fn === 'function') fn();
    }
  }

  function setActiveStep(tabId) {
    const steps = document.querySelectorAll('[data-onboarding-step]');
    const progress = document.querySelector('.onboarding-progress-bar');
    const activeIndex = Math.max(stepOrder.indexOf(tabId), 0);

    steps.forEach((step) => {
      const isActive = step.dataset.onboardingStep === tabId;
      step.classList.toggle('is-active', isActive);
      step.setAttribute('aria-current', isActive ? 'step' : 'false');
    });

    if (progress) {
      const width = stepOrder.length > 1 ? ((activeIndex + 1) / stepOrder.length) * 100 : 100;
      progress.style.width = `${Math.min(width, 100)}%`;
    }

    setHelpPanel(tabId);
    updateNowCard(tabId);
    updateFocusCard(tabId);
  }

  function bindWizardStepper() {
    const steps = document.querySelectorAll('[data-onboarding-step]');
    steps.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.onboardingStep;
        if (typeof window.switchTab === 'function') {
          window.switchTab(target);
        }
        setActiveStep(target);
        window.requestAnimationFrame(() => {
          document.getElementById('tab-content')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    });
  }

  function bindQuickActions() {
    document.querySelectorAll('[data-wizard-goto]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.wizardGoto;
        if (typeof window.switchTab === 'function') {
          window.switchTab(target);
        }
        setActiveStep(target);
      });
    });
  }

  function bindDraftPersistence() {
    const form = document.getElementById('company-form');
    if (!form) return;

    const isCreateMode = !getCompanyId();
    const inputs = form.querySelectorAll('input, textarea, select');

    const restoreDraft = () => {
      if (!isCreateMode) return;
      const raw = localStorage.getItem(getDraftKey());
      if (!raw) return;

      try {
        const draft = JSON.parse(raw);
        inputs.forEach((input) => {
          if (!input.id || !(input.id in draft)) return;
          if (input.type === 'checkbox') {
            input.checked = Boolean(draft[input.id]);
          } else {
            input.value = draft[input.id];
          }
        });
      } catch (err) {
        console.warn('Falha ao restaurar rascunho de onboarding.', err);
      }
    };

    const saveDraft = () => {
      if (!isCreateMode) return;
      const draft = {};
      inputs.forEach((input) => {
        if (!input.id) return;
        draft[input.id] = input.type === 'checkbox' ? input.checked : input.value;
      });
      localStorage.setItem(getDraftKey(), JSON.stringify(draft));
    };

    const clearDraft = () => {
      localStorage.removeItem(getDraftKey());
    };

    restoreDraft();
    inputs.forEach((input) => {
      input.addEventListener('input', saveDraft);
      input.addEventListener('change', saveDraft);
    });

    document.querySelectorAll('[data-wizard-clear-draft]').forEach((btn) => {
      btn.addEventListener('click', () => {
        clearDraft();
        if (isCreateMode) {
          form.reset();
        }
      });
    });
  }

  function updateModeCopy() {
    const modeBadge = document.getElementById('onboarding-mode-badge');
    const modeText = document.getElementById('onboarding-mode-text');
    const saveButtons = document.querySelectorAll('.onboarding-hero-actions [data-wizard-save], .wizard-status-card [data-wizard-save]');
    const isEditMode = Boolean(getCompanyId());

    if (modeBadge) {
      modeBadge.textContent = isEditMode ? 'Alteração assistida' : 'Criação guiada';
    }

    if (modeText) {
      modeText.textContent = isEditMode
      ? 'A empresa já existe; use o wizard para ajustar identidade, operação, acessos e API / MCP sem se perder.'
        : 'Você vai criar a empresa e sair com a base pronta para rotina, estratégia, finanças e Sapiens.';
    }

    saveButtons.forEach((btn) => {
      btn.textContent = isEditMode ? 'Salvar alterações' : 'Criar empresa e continuar';
    });
  }

  function enhanceTabTitles() {
    const labels = {
      dados: 'Quem é a empresa?',
      economico: 'Contexto',
      cargos: 'Estrutura',
      colaboradores: 'Time',
      usuarios: 'Acessos',
      pontuacao: 'Regras',
    config: 'API / MCP & Sistema'
    };

    document.querySelectorAll('.tab-btn[data-tab]').forEach((btn) => {
      const label = labels[btn.dataset.tab];
      if (label) btn.dataset.originalLabel = btn.textContent.trim();
      if (label) btn.textContent = label;
    });
  }

  function syncFromActiveTab() {
    setActiveStep(getCurrentTabId());
  }

  document.addEventListener('DOMContentLoaded', () => {
    enhanceTabTitles();
    bindWizardStepper();
    bindQuickActions();
    bindDraftPersistence();
    updateModeCopy();
    syncFromActiveTab();
    setAdvancedVisibility(false);

    document.getElementById('onboardingPrimaryAction')?.addEventListener('click', runPrimaryAction);
    document.getElementById('onboardingToggleAdvanced')?.addEventListener('click', () => {
      const visible = document.getElementById('onboardingToggleAdvanced')?.dataset.advancedVisible === 'true';
      setAdvancedVisibility(!visible);
    });
    document.getElementById('onboardingFocusStay')?.addEventListener('click', () => {
      document.getElementById('tab-content')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    document.querySelectorAll('[data-wizard-skip]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.wizardSkip;
        if (target && typeof window.switchTab === 'function') {
          window.switchTab(target);
          setActiveStep(target);
        }
      });
    });
  });

  window.GVCompanyOnboardingWizard = {
    stepMeta,
    setActiveStep,
    syncFromActiveTab,
    updateModeCopy
  };
})();
