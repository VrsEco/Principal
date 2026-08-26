(function () {
    'use strict';

    const root = document.getElementById('sapiensTraining');
    if (!root || root.dataset.accessDenied === '1') return;

    const elements = {
        status: document.getElementById('trainingStatus'),
        build: document.getElementById('buildTrainingProposals'),
        metrics: {
            negative: document.getElementById('metricNegative'),
            gaps: document.getElementById('metricGaps'),
            pending: document.getElementById('metricPending'),
            approved: document.getElementById('metricApproved'),
        },
        lists: {
            feedback: document.getElementById('feedbackList'),
            gaps: document.getElementById('gapList'),
            proposals: document.getElementById('proposalList'),
            playbooks: document.getElementById('playbookList'),
        },
    };

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    function setStatus(message, kind) {
        elements.status.hidden = !message;
        elements.status.className = `st-status${kind ? ` is-${kind}` : ''}`;
        elements.status.textContent = message || '';
    }

    async function requestJson(url, options) {
        const response = await fetch(url, options || {});
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) {
            throw new Error(payload.error || 'Não foi possível carregar o treinamento.');
        }
        return payload;
    }

    function meta(items) {
        return items.filter(Boolean).map((item) => `<span class="st-pill">${escapeHtml(item)}</span>`).join('');
    }

    function empty(message) {
        return `<div class="st-empty">${escapeHtml(message)}</div>`;
    }

    function renderFeedback(items) {
        if (!items.length) return empty('Ainda não há feedback negativo para revisar.');
        return items.map((item) => `
            <article class="st-card">
                <h3>${escapeHtml(item.question || 'Pergunta sem título')}</h3>
                <div class="st-card-meta">${meta([item.rating, item.reason, item.understanding?.domain])}</div>
                <p><strong>Resposta entregue:</strong> ${escapeHtml(item.answer_preview || 'Sem prévia registrada.')}</p>
                ${item.comment ? `<p><strong>Comentário:</strong> ${escapeHtml(item.comment)}</p>` : ''}
                ${item.expected_answer ? `<p><strong>Resposta esperada:</strong> ${escapeHtml(item.expected_answer)}</p>` : ''}
            </article>
        `).join('');
    }

    function renderGaps(items) {
        if (!items.length) return empty('Nenhuma lacuna de conhecimento encontrada.');
        return items.map((item) => `
            <article class="st-card">
                <h3>${escapeHtml(item.question || 'Pergunta sem título')}</h3>
                <div class="st-card-meta">${meta([item.rating_status, item.understanding?.domain, 'knowledge_gap'])}</div>
                <p>${escapeHtml(item.answer_preview || 'O Sapiens não encontrou evidência suficiente.')}</p>
            </article>
        `).join('');
    }

    function renderProposals(items) {
        if (!items.length) return empty('Rode o robô treinador ou aguarde mais feedbacks.');
        return items.map((item) => {
            const disabled = item.status !== 'pending_review' ? ' disabled' : '';
            return `
                <article class="st-card" data-proposal-id="${escapeHtml(item.proposal_id)}">
                    <h3>${escapeHtml(item.pattern || 'Padrão detectado')}</h3>
                    <div class="st-card-meta">${meta([item.status, item.suggestion_type, item.suggested_domain, `${item.evidence_count || 0} evidência(s)`])}</div>
                    <p><strong>Recomendação:</strong> ${escapeHtml(item.recommendation?.action || item.suggestion_type || 'Revisar curadoria')}</p>
                    <p>Aplicação automática: <strong>não</strong>. A proposta só vira melhoria após revisão humana.</p>
                    <div class="st-card-actions">
                        <button type="button" class="st-mini approve" data-decision="approved"${disabled}>Aprovar</button>
                        <button type="button" class="st-mini reject" data-decision="rejected"${disabled}>Rejeitar</button>
                    </div>
                </article>
            `;
        }).join('');
    }

    function renderPlaybooks(items) {
        if (!items.length) return empty('Nenhum playbook sugerido neste momento.');
        return items.map((item) => `
            <article class="st-card">
                <h3>${escapeHtml(item.title)}</h3>
                <p>${escapeHtml(item.reason)}</p>
                <p><strong>Próximo passo:</strong> ${escapeHtml(item.next_step)}</p>
            </article>
        `).join('');
    }

    function render(payload) {
        const summary = payload.summary || {};
        elements.metrics.negative.textContent = summary.negative_feedback || 0;
        elements.metrics.gaps.textContent = summary.knowledge_gaps || 0;
        elements.metrics.pending.textContent = summary.pending_proposals || 0;
        elements.metrics.approved.textContent = summary.approved_proposals || 0;
        elements.lists.feedback.innerHTML = renderFeedback(payload.feedback || []);
        elements.lists.gaps.innerHTML = renderGaps(payload.gaps || []);
        elements.lists.proposals.innerHTML = renderProposals(payload.proposals || []);
        elements.lists.playbooks.innerHTML = renderPlaybooks(payload.playbooks || []);
    }

    async function refreshTraining() {
        setStatus('Carregando curadoria do Sapiens…');
        try {
            const payload = await requestJson('/api/agents/knowledge/training/overview?limit=50');
            render(payload);
            setStatus('');
        } catch (error) {
            setStatus(error.message, 'error');
        }
    }

    async function buildProposals() {
        elements.build.disabled = true;
        setStatus('Robô treinador analisando feedbacks…');
        try {
            const payload = await requestJson('/api/agents/knowledge/training/proposals/build', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ min_evidence: 1, limit: 100 }),
            });
            setStatus(`${payload.created_count || 0} proposta(s) criada(s) para revisão.`, 'success');
            await refreshTraining();
        } catch (error) {
            setStatus(error.message, 'error');
        } finally {
            elements.build.disabled = false;
        }
    }

    async function decideProposal(card, decision) {
        const proposalId = card.dataset.proposalId;
        if (!proposalId) return;
        setStatus('Registrando decisão humana…');
        try {
            await requestJson(`/api/agents/knowledge/training/proposals/${encodeURIComponent(proposalId)}/decision`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ decision }),
            });
            setStatus('Proposta revisada com segurança.', 'success');
            await refreshTraining();
        } catch (error) {
            setStatus(error.message, 'error');
        }
    }

    document.querySelectorAll('[data-tab]').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('[data-tab]').forEach((item) => item.classList.remove('is-active'));
            document.querySelectorAll('.st-panel').forEach((item) => item.classList.remove('is-active'));
            button.classList.add('is-active');
            document.getElementById(`tab-${button.dataset.tab}`)?.classList.add('is-active');
        });
    });

    elements.build.addEventListener('click', buildProposals);
    elements.lists.proposals.addEventListener('click', (event) => {
        const button = event.target.closest('[data-decision]');
        const card = event.target.closest('[data-proposal-id]');
        if (button && card) decideProposal(card, button.dataset.decision);
    });

    refreshTraining();
})();
