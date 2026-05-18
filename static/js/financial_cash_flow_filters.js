document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.report-filter-grid[data-view-action]');
    if (!form) {
        return;
    }

    const formId = form.getAttribute('id');
    const resolveAssociatedControl = (selector) => {
        if (!formId) {
            return form.querySelector(selector) || document.querySelector(selector);
        }
        return form.querySelector(selector) || document.querySelector(`${selector}[form="${formId}"]`);
    };

    const resolveOutputMode = () => {
        const radio = resolveAssociatedControl('input[name="output_mode"]:checked');
        if (radio) {
            return radio.value;
        }
        const select = resolveAssociatedControl('select[name="output_mode"]');
        return select ? select.value : '';
    };

    const serializeControlValue = (params, control) => {
        if (!control || control.disabled || !control.name) {
            return;
        }

        const tagName = String(control.tagName || '').toUpperCase();
        const type = String(control.type || '').toLowerCase();

        if ((type === 'checkbox' || type === 'radio') && !control.checked) {
            return;
        }

        if (tagName === 'SELECT' && control.multiple) {
            Array.from(control.selectedOptions || [])
                .map((option) => option.value)
                .filter((value) => String(value ?? '').trim() !== '')
                .forEach((value) => params.append(control.name, value));
            return;
        }

        const value = control.value;
        if (value == null) {
            return;
        }
        params.append(control.name, value);
    };

    const buildSubmissionQuery = () => {
        const params = new URLSearchParams();
        const seen = new Set();
        const controls = Array.from(form.elements || []);
        const associatedControls = formId
            ? Array.from(document.querySelectorAll(`[form="${formId}"]`))
            : [];

        [...controls, ...associatedControls].forEach((control) => {
            if (!control || seen.has(control)) {
                return;
            }
            seen.add(control);
            serializeControlValue(params, control);
        });

        params.set('ui_refresh', '1');
        return params;
    };

    form.addEventListener('submit', (event) => {
        let targetAction = form.dataset.viewAction;
        if (form.dataset.applyFiltersOnly !== 'true') {
            const outputMode = resolveOutputMode();
            targetAction = outputMode === 'pdf' ? form.dataset.pdfAction : form.dataset.viewAction;
        }

        if (!targetAction) {
            return;
        }

        event.preventDefault();
        const query = buildSubmissionQuery().toString();
        window.location.href = query ? `${targetAction}?${query}` : targetAction;
    });

    const scopedSelector = (selector) => {
        if (!formId) {
            return form.querySelector(selector) || document.querySelector(selector);
        }
        return resolveAssociatedControl(selector);
    };

    const preview = form.querySelector('[data-cash-flow-preview]');
    if (!preview) {
        return;
    }

    const previewEndpoint = preview.dataset.previewEndpoint;
    const previewBody = form.querySelector('[data-cash-flow-preview-body]');
    const previewSummary = form.querySelector('[data-cash-flow-preview-summary]');
    const selectionPanel = document.querySelector('[data-cash-flow-selection-panel]');
    const selectedCount = form.querySelector('[data-cash-flow-selected-count]');
    const toggle = form.querySelector('[data-cash-flow-exclusion-toggle]');
    const flagInput = form.querySelector('[data-cash-flow-exclusion-flag]');
    const selectedInputsContainer = form.querySelector('[data-cash-flow-selected-inputs]');
    const periodStartInput = scopedSelector('input[name="period_start"]');
    const periodEndInput = scopedSelector('input[name="period_end"]');

    const selectedIds = new Set(
        Array.from(selectedInputsContainer.querySelectorAll('input[name="excluded_entry_ids"]'))
            .map((input) => String(input.value || '').trim())
            .filter(Boolean)
    );

    const escapeHtml = (value) => String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');

    const renderEmpty = (message, summaryMessage) => {
        previewBody.innerHTML = `<div class="cash-flow-preview__empty">${escapeHtml(message)}</div>`;
        if (previewSummary) {
            previewSummary.textContent = summaryMessage || message;
        }
    };

    const syncSelectedInputs = () => {
        selectedInputsContainer.innerHTML = '';
        Array.from(selectedIds)
            .sort((left, right) => Number(left) - Number(right))
            .forEach((entryId) => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'excluded_entry_ids';
                input.value = entryId;
                selectedInputsContainer.appendChild(input);
            });
        if (selectedCount) {
            selectedCount.textContent = String(selectedIds.size);
        }
    };

    const updateEnabledState = (enabled) => {
        flagInput.value = enabled ? 'true' : 'false';
        preview.dataset.enabled = enabled ? 'true' : 'false';
        selectionPanel?.classList.toggle('is-hidden', !enabled);
        if (!enabled) {
            selectedIds.clear();
            syncSelectedInputs();
            renderEmpty(
                'A retirada manual está desativada. Marque a opção acima para selecionar títulos.',
                'A retirada manual está desativada.'
            );
            return;
        }
        renderEmpty(
            'Clique em Aplicar Filtros para atualizar a página e listar os títulos em aberto do período informado.',
            'Filtros prontos para atualizar os títulos do período.'
        );
    };

    const buildPreviewQuery = () => {
        const params = new URLSearchParams();
        const formData = new FormData(form);
        for (const [key, rawValue] of formData.entries()) {
            if (key === 'excluded_entry_ids' || key === 'enable_title_exclusions') {
                continue;
            }
            const value = String(rawValue ?? '').trim();
            if (!value) {
                continue;
            }
            params.append(key, value);
        }
        params.set('enable_title_exclusions', flagInput.value || 'false');
        Array.from(selectedIds).forEach((entryId) => params.append('excluded_entry_ids', entryId));
        return params;
    };

    const toggleRowSelection = (entryId, checked, row) => {
        if (checked) {
            selectedIds.add(entryId);
            row.classList.add('is-selected');
        } else {
            selectedIds.delete(entryId);
            row.classList.remove('is-selected');
        }
        syncSelectedInputs();
    };

    const renderTitles = (titles, summary) => {
        if (!Array.isArray(titles) || !titles.length) {
            renderEmpty(
                'Nenhum título em aberto foi localizado para os filtros informados.',
                summary?.period_label
                    ? `Nenhum título localizado em ${summary.period_label}.`
                    : 'Nenhum título localizado.'
            );
            syncSelectedInputs();
            return;
        }

        previewBody.innerHTML = '';
        titles.forEach((item) => {
            const entryId = String(item.id);
            if (item.selected) {
                selectedIds.add(entryId);
            }

            const row = document.createElement('div');
            row.className = `cash-flow-preview__row${selectedIds.has(entryId) ? ' is-selected' : ''}`;
            row.innerHTML = `
                <div class="cash-flow-preview__cell cash-flow-preview__cell--check">
                    <label class="check-field">
                        <input type="checkbox" ${selectedIds.has(entryId) ? 'checked' : ''}>
                    </label>
                </div>
                <span class="cash-flow-preview__cell--strong">${escapeHtml(item.history || '-')}</span>
                <span>${escapeHtml(item.type || '-')}</span>
                <span>${escapeHtml(item.title_amount || '-')}</span>
                <span>${escapeHtml(item.open_amount || '-')}</span>
                <span>${escapeHtml(item.counterparty || '-')}</span>
                <span>${escapeHtml(item.number_installment || '-')}</span>
                <span>${escapeHtml(item.competence_date || '-')}</span>
                <span>${escapeHtml(item.due_date || '-')}</span>
            `;

            const checkbox = row.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (event) => {
                toggleRowSelection(entryId, event.target.checked, row);
            });

            previewBody.appendChild(row);
        });

        if (previewSummary) {
            const count = Number(summary?.count || titles.length);
            const totalLabel = summary?.total_open_amount_label || '-';
            previewSummary.textContent = `${count} título(s) localizado(s) · ${totalLabel} em aberto.`;
        }
        syncSelectedInputs();
    };

    const processFilters = async () => {
        if (flagInput.value !== 'true') {
            return;
        }
        if (!periodStartInput?.value || !periodEndInput?.value) {
            renderEmpty(
                'Informe a Data Inicial e a Data Final para listar os títulos do fluxo.',
                'Período obrigatório para buscar os títulos.'
            );
            return;
        }

        renderEmpty('Carregando títulos em aberto do período...', 'Atualizando filtros...');
        try {
            const response = await fetch(`${previewEndpoint}?${buildPreviewQuery().toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                throw new Error('Não foi possível buscar os títulos do fluxo de caixa.');
            }
            const payload = await response.json();
            renderTitles(payload.titles || [], payload.summary || {});
        } catch (error) {
            renderEmpty(
                error?.message || 'Falha ao buscar os títulos do fluxo de caixa.',
                'Erro ao atualizar os filtros.'
            );
        }
    };

    toggle?.addEventListener('change', (event) => {
        updateEnabledState(Boolean(event.target.checked));
    });

    syncSelectedInputs();
    if (flagInput.value === 'true') {
        if (toggle) {
            toggle.checked = true;
        }
        processFilters();
    } else {
        updateEnabledState(false);
    }
});
