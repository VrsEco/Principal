function populateEmployeeSelect() {
    const sel = document.getElementById('occCollaborators');
    if (!sel) return;
    sel.innerHTML = state.employees.map(e => `<option value="${e.id}">${e.name}</option>`).join('');
}

async function fetchOccurrences() {
    try {
        const companyId = state.process?.company_id || window.companyId;
        const query = new URLSearchParams({ process_id: processId });

        if (companyId) {
            query.set('company_id', companyId);
        }

        const res = await fetch(`/api/occurrences?${query.toString()}`);
        if (!res.ok) throw new Error('Falha ao carregar ocorrências');
        state.occurrences = await res.json();
    } catch (e) {
        console.warn('Erro ao buscar ocorrências:', e);
        state.occurrences = [];
    }
}

function renderOccurrences() {
    const container = document.getElementById('occurrencesList');
    if (!state.occurrences || state.occurrences.length === 0) {
        container.innerHTML = `
                <div class="empty-state p-5">
                    <div class="empty-icon">🔔</div>
                    <p>Nenhuma ocorrência registrada para este processo.</p>
                    <button class="btn btn-outline-primary btn-sm mt-2" onclick="openOccurrenceModal()">Registrar Primeira</button>
                </div>
            `;
        return;
    }

    container.innerHTML = state.occurrences.map(o => {
        const labels = {
            'positive': 'Positiva',
            'negative': 'Negativa',
            'improvement': 'Melhoria',
            'incident': 'Incidente',
            'compliment': 'Elogio',
            'complaint': 'Reclamação',
            'idea': 'Ideia',
            'other': 'Outro'
        };
        const label = labels[o.type] || o.type;
        const color = (['negative', 'incident', 'complaint'].includes(o.type) || o.score < 0) ? 'var(--danger)' : 'var(--success)';
        const dateStr = new Date(o.created_at).toLocaleDateString('pt-BR');
        let empDisplay = 'Ninguém';
        if (o.collaborators_ids && o.collaborators_ids.length > 0) {
            const names = o.collaborators_ids.map(id => {
                const e = state.employees.find(emp => emp.id === id);
                return e ? e.name : '';
            }).filter(n => n);
            if (names.length === 1) empDisplay = names[0];
            else if (names.length === 2) empDisplay = `${names[0]} e ${names[1]}`;
            else empDisplay = `${names[0]} e +${names.length - 1}`;
        } else if (o.employee_name) {
            empDisplay = o.employee_name;
        }

        return `
            <div class="occurrence-card" style="border-left: 4px solid ${color};">
                <div class="occ-header">
                    <div class="occ-title-group">
                        <span class="badge" style="background: ${color}20; color: ${color}; border: 1px solid ${color}40;">${label}</span>
                        <h3>${o.title}</h3>
                    </div>
                    <div class="occ-actions">
                        <span class="occ-score" style="color: ${o.score >= 0 ? 'var(--success)' : 'var(--danger)'}">
                            ${o.score > 0 ? '+' : ''}${o.score} pts
                        </span>
                        <button class="btn btn-icon btn-sm" onclick="editOccurrence(${o.id})">✏️</button>
                        <button class="btn btn-icon btn-sm" onclick="deleteOccurrence(${o.id})">🗑️</button>
                    </div>
                </div>
                <p class="occ-desc">${o.description || 'Sem descrição.'}</p>
                <div class="occ-footer">
                    <span>👥 ${empDisplay}</span>
                    <span>📅 ${dateStr}</span>
                </div>
            </div>
            `;
    }).join('');
}

function getSelectedValues(select) {
    return Array.from(select.selectedOptions).map(option => parseInt(option.value));
}

function setMultiSelect(select, values) {
    if (!values) values = [];
    Array.from(select.options).forEach(option => {
        option.selected = values.includes(parseInt(option.value));
    });
}

function openOccurrenceModal(id = null) {
    document.getElementById('occurrenceModal').style.display = 'block';
    const form = document.getElementById('occurrenceForm');

    if (id) {
        const occ = state.occurrences.find(o => o.id === id);
        document.getElementById('occurrenceModalTitle').textContent = 'Editar Ocorrência';
        document.getElementById('occId').value = occ.id;
        document.getElementById('occTitle').value = occ.title;
        document.getElementById('occType').value = occ.type;
        document.getElementById('occScore').value = occ.score;
        document.getElementById('occDescription').value = occ.description;

        let ids = occ.collaborators_ids || [];
        if (ids.length === 0 && occ.employee_id) ids = [occ.employee_id];
        setMultiSelect(document.getElementById('occCollaborators'), ids);
    } else {
        document.getElementById('occurrenceModalTitle').textContent = 'Nova Ocorrência';
        form.reset();
        document.getElementById('occId').value = '';
        setMultiSelect(document.getElementById('occCollaborators'), []);
        form.querySelector('[name="process_id"]').value = processId;
    }
}

window.editOccurrence = function (id) {
    openOccurrenceModal(id);
}

window.deleteOccurrence = async function (id) {
    if (!confirm('Deseja realmente excluir esta ocorrência?')) return;
    try {
        const res = await fetch(`/api/occurrences/${id}`, { method: 'DELETE' });
        if (res.ok) {
            state.occurrences = state.occurrences.filter(o => o.id !== id);
            renderOccurrences();
        } else {
            alert('Erro ao excluir ocorrência.');
        }
    } catch (e) { console.error(e); alert('Erro de conexão.'); }
}

async function handleOccurrenceSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    data.collaborators_ids = getSelectedValues(document.getElementById('occCollaborators'));
    data.score = parseInt(data.score) || 0;
    data.process_id = parseInt(data.process_id);
    if (!data.id) delete data.id;

    const url = data.id ? `/api/occurrences/${data.id}` : '/api/occurrences';
    const method = data.id ? 'PUT' : 'POST';

    if (!data.id && state.process && state.process.company_id) {
        data.company_id = state.process.company_id;
    }

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            closeModal('occurrenceModal');
            await fetchOccurrences();
            renderOccurrences();
        } else {
            const err = await res.json();
            alert('Erro ao salvar: ' + (JSON.stringify(err.errors || err.error || err.message)));
        }
    } catch (e) {
        console.error(e);
        alert('Erro de conexão.');
    }
}
