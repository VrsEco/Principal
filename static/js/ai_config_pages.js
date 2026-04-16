document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('aiConfigPage');
    if (!root) return;

    const steps = Array.from(root.querySelectorAll('[data-config-step]'));
    const choices = Array.from(root.querySelectorAll('[data-config-choice]'));
    const result = document.getElementById('aiConfigResult');
    const resultTitle = document.getElementById('aiConfigResultTitle');
    const resultBody = document.getElementById('aiConfigResultBody');
    const goButton = document.getElementById('aiConfigGo');
    const resetButton = document.getElementById('aiConfigWizardReset');
    const transcript = document.getElementById('aiConfigTranscript');
    const toggles = Array.from(root.querySelectorAll('[data-config-toggle]'));
    const chatCard = root.querySelector('[data-config-chat-card]');
    const chatToggle = root.querySelector('[data-config-chat-toggle]');

    let answers = [];
    let currentTarget = null;

    function renderTranscript() {
        if (!transcript) return;
        if (!answers.length) {
            transcript.hidden = true;
            transcript.innerHTML = '';
            return;
        }

        transcript.hidden = false;
        transcript.innerHTML = answers.map((answer) => `
            <div class="ai-config-chat__transcript-item">
                <span>${answer.question}</span>
                <strong>${answer.answer}</strong>
            </div>
        `).join('');
    }

    function resetWizard() {
        answers = [];
        currentTarget = null;
        if (result) result.hidden = true;
        steps.forEach((step, index) => step.classList.toggle('is-active', index === 0));
        renderTranscript();
    }

    function openSection(sectionId) {
        if (!sectionId) return;
        const section = root.querySelector(`[data-config-section="${sectionId}"]`);
        if (!section) return;
        section.classList.remove('is-collapsed');
        section.classList.add('is-expanded');
        const toggle = section.querySelector('[data-config-toggle]');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    choices.forEach((choice) => {
        choice.addEventListener('click', () => {
            const stepNode = choice.closest('[data-config-step]');
            const stepIndex = steps.indexOf(stepNode);
            const question = stepNode?.querySelector('.ai-config-chat__bubble--agent p')?.textContent?.trim() || 'Pergunta';
            const answer = choice.dataset.choiceLabel || choice.textContent.trim();

            answers = answers.slice(0, stepIndex);
            answers.push({ question, answer });
            renderTranscript();

            currentTarget = choice.dataset.targetSection || null;
            if (resultTitle) resultTitle.textContent = choice.dataset.resultTitle || answer;
            if (resultBody) resultBody.textContent = choice.dataset.resultBody || '';
            if (result) result.hidden = false;

            const nextStep = steps[stepIndex + 1];
            if (nextStep) {
                steps.forEach((step) => step.classList.remove('is-active'));
                nextStep.classList.add('is-active');
            }
        });
    });

    goButton?.addEventListener('click', () => openSection(currentTarget));
    resetButton?.addEventListener('click', resetWizard);

    toggles.forEach((toggle) => {
        toggle.addEventListener('click', () => {
            const section = toggle.closest('[data-config-section]');
            const expanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
            section?.classList.toggle('is-collapsed', expanded);
            section?.classList.toggle('is-expanded', !expanded);
        });
    });

    chatToggle?.addEventListener('click', () => {
        if (!chatCard) return;
        const expanded = chatToggle.getAttribute('aria-expanded') === 'true';
        chatToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        chatCard.classList.toggle('is-collapsed', expanded);
        chatCard.classList.toggle('is-expanded', !expanded);
    });

    resetWizard();
});
