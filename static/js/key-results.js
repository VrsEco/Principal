/**
 * Dynamic Key Results Management Component
 * Reusable component for managing Key Results in OKRs
 */

class KeyResultsManager {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`KeyResultsManager: container '${containerId}' not found`);
            return;
        }

        this.listContainer = this.container.querySelector(".key-results-list");
        if (!this.listContainer) {
            console.error(`KeyResultsManager: .key-results-list not found inside '${containerId}'`);
            return;
        }

        this.counter = 0;
        this.options = {
            minResults: options.minResults || 0,
            maxResults: options.maxResults || 50,
            required: options.required || false,
            onChange: typeof options.onChange === "function" ? options.onChange : null,
        };

        this.participants = this._loadData("participants", options.participants);
        this.indicators = this._loadData("indicators", options.indicators);

        this._setupAddButton();

        if (this.options.minResults > 0) {
            for (let i = 0; i < this.options.minResults; i += 1) {
                this.addKeyResult();
            }
        } else {
            this.addKeyResult();
        }
    }

    _loadData(attribute, fallback) {
        if (Array.isArray(fallback) && fallback.length) {
            return fallback;
        }
        const raw = this.container.dataset[attribute];
        if (raw) {
            try {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    return parsed;
                }
            } catch (error) {
                console.warn(`KeyResultsManager: failed to parse dataset for ${attribute}`, error);
            }
        }
        if (window.okrContext && Array.isArray(window.okrContext[attribute])) {
            return window.okrContext[attribute];
        }
        return [];
    }

    _setupAddButton() {
        const addButton = this.container.querySelector("[data-add-key-result]");
        const legacyButton = this.container.querySelector("[onclick*='addKeyResult']");
        const handler = (event) => {
            event.preventDefault();
            this.addKeyResult();
        };
        if (addButton) {
            addButton.addEventListener("click", handler);
        }
        if (legacyButton) {
            legacyButton.removeAttribute("onclick");
            legacyButton.addEventListener("click", handler);
        }
    }

    addKeyResult(data = {}) {
        if (this.getKeyResultsCount() >= this.options.maxResults) {
            alert(`Máximo de ${this.options.maxResults} Key Results permitidos.`);
            return null;
        }

        const krIndex = this.counter++;
        const row = document.createElement("div");
        row.className = "okr-kpi-row";
        row.id = `kr-row-${krIndex}`;
        row.innerHTML = this._renderRow(krIndex, data);
        this.listContainer.appendChild(row);
        this._animateIn(row);
        this._bindRowEvents(row, krIndex);
        return krIndex;
    }

    _renderRow(krIndex, data) {
        const requiredAttr = this.options.required ? " required" : "";
        const ownerValue = this._escapeAttr(data.owner || "");
        const indicatorLabel = this._escapeAttr(data.indicator_label || data.indicator_display || "");
        return `
            <div class="form-field">
                <span>Key Result</span>
                <input type="text" name="okr_kr_${krIndex}" placeholder="Descrição do Key Result..." value="${this._escapeAttr(data.label || "")}"${requiredAttr} />
            </div>
            <div class="form-field">
                <span>Meta do Indicador</span>
                <input type="text" name="okr_kr_${krIndex}_target" placeholder="Meta a ser atingida..." value="${this._escapeAttr(data.target || "")}" />
            </div>
            <div class="form-field">
                <span>Prazo do Indicador</span>
                <input type="date" name="okr_kr_${krIndex}_deadline" value="${this._escapeAttr(data.deadline || "")}" />
            </div>
            <div class="form-field">
                <span>Responsável pelo Indicador</span>
                <select name="okr_kr_${krIndex}_owner_id" class="kr-owner-select" data-owner-input="okr_kr_${krIndex}_owner">
                    ${this._buildParticipantOptions(data.owner_id)}
                </select>
                <input type="hidden" name="okr_kr_${krIndex}_owner" id="okr_kr_${krIndex}_owner" value="${ownerValue}" />
            </div>
            <div class="form-field">
                <span>Indicador associado</span>
                <select name="okr_kr_${krIndex}_indicator_id" class="kr-indicator-select" data-indicator-input="okr_kr_${krIndex}_indicator_label">
                    ${this._buildIndicatorOptions(data.indicator_id)}
                </select>
                <input type="hidden" name="okr_kr_${krIndex}_indicator_label" value="${indicatorLabel}" />
            </div>
            <div class="form-field kr-actions">
                <button type="button" class="button button-small button-danger" data-remove-kr="${krIndex}">
                    <span>🗑️</span>
                </button>
            </div>
        `;
    }

    _buildParticipantOptions(selectedId) {
        const selected = selectedId !== undefined && selectedId !== null ? String(selectedId) : "";
        const options = ['<option value="">Selecione o responsável</option>'];
        this.participants.forEach((participant) => {
            const value = participant && participant.id !== undefined && participant.id !== null ? String(participant.id) : "";
            const labelText = participant && (participant.label || participant.name) ? participant.label || participant.name : "Participante";
            const label = this._escapeHtml(labelText);
            const nameAttr = this._escapeAttr(participant && participant.name ? participant.name : labelText);
            const isSelected = value && selected && value === selected ? " selected" : "";
            options.push(`<option value="${this._escapeAttr(value)}" data-name="${nameAttr}"${isSelected}>${label}</option>`);
        });
        return options.join("\n");
    }

    _buildIndicatorOptions(selectedId) {
        const selected = selectedId !== undefined && selectedId !== null ? String(selectedId) : "";
        const options = ['<option value="">Selecione o indicador</option>'];
        this.indicators.forEach((indicator) => {
            const value = indicator && indicator.id !== undefined && indicator.id !== null ? String(indicator.id) : "";
            const labelText = indicator && (indicator.label || indicator.name) ? indicator.label || indicator.name : "Indicador";
            const label = this._escapeHtml(labelText);
            const labelAttr = this._escapeAttr(labelText);
            const isSelected = value && selected && value === selected ? " selected" : "";
            options.push(`<option value="${this._escapeAttr(value)}" data-label="${labelAttr}"${isSelected}>${label}</option>`);
        });
        return options.join("\n");
    }

    _bindRowEvents(row, krIndex) {
        row.querySelectorAll('input[type="text"], input[type="date"]').forEach((input) => {
            input.addEventListener("input", () => this.onKeyResultChange(krIndex, input.name, input.value));
        });

        const ownerSelect = row.querySelector(`select[name="okr_kr_${krIndex}_owner_id"]`);
        if (ownerSelect) {
            ownerSelect.addEventListener("change", () => {
                const targetId = ownerSelect.dataset.ownerInput;
                if (targetId) {
                    const hiddenInput = row.querySelector(`#${targetId}`);
                    if (hiddenInput) {
                        const option = ownerSelect.options[ownerSelect.selectedIndex];
                        const ownerName = option ? (option.dataset.name || option.textContent || "") : "";
                        hiddenInput.value = ownerName.trim();
                    }
                }
                this.onKeyResultChange(krIndex, ownerSelect.name, ownerSelect.value);
            });
            ownerSelect.dispatchEvent(new Event("change"));
        }

        const indicatorSelect = row.querySelector(`select[name="okr_kr_${krIndex}_indicator_id"]`);
        if (indicatorSelect) {
            indicatorSelect.addEventListener("change", () => {
                const targetName = indicatorSelect.dataset.indicatorInput;
                if (targetName) {
                    const hiddenInput = row.querySelector(`input[name="${targetName}"]`);
                    if (hiddenInput) {
                        const option = indicatorSelect.options[indicatorSelect.selectedIndex];
                        const indicatorValue = option ? (option.dataset.label || option.textContent || "") : "";
                        hiddenInput.value = indicatorValue.trim();
                    }
                }
                this.onKeyResultChange(krIndex, indicatorSelect.name, indicatorSelect.value);
            });
            indicatorSelect.dispatchEvent(new Event("change"));
        }

        const removeButton = row.querySelector("[data-remove-kr]");
        if (removeButton) {
            removeButton.addEventListener("click", (event) => {
                event.preventDefault();
                this.removeKeyResult(krIndex);
            });
        }
    }

    onKeyResultChange(krIndex, fieldName, value) {
        if (this.options.onChange) {
            this.options.onChange(krIndex, fieldName, value);
        }
    }

    removeKeyResult(krIndex) {
        const row = document.getElementById(`kr-row-${krIndex}`);
        if (!row) {
            return;
        }
        if (this.getKeyResultsCount() <= this.options.minResults && this.options.minResults > 0) {
            alert(`Mínimo de ${this.options.minResults} Key Results é obrigatório.`);
            return;
        }
        this._animateOut(row, () => row.remove());
    }

    _animateIn(element) {
        element.style.opacity = "0";
        element.style.transform = "translateY(-10px)";
        requestAnimationFrame(() => {
            element.style.transition = "all 0.3s ease";
            element.style.opacity = "1";
            element.style.transform = "translateY(0)";
        });
    }

    _animateOut(element, callback) {
        element.style.transition = "all 0.3s ease";
        element.style.opacity = "0";
        element.style.transform = "translateY(-10px)";
        setTimeout(() => {
            if (typeof callback === "function") {
                callback();
            }
        }, 300);
    }

    getKeyResultsCount() {
        return this.listContainer.querySelectorAll(".okr-kpi-row").length;
    }

    getKeyResults() {
        const results = [];
        const rows = this.listContainer.querySelectorAll(".okr-kpi-row");
        rows.forEach((row, position) => {
            const krIndex = row.id.split("-")[2];
            const labelInput = row.querySelector(`input[name="okr_kr_${krIndex}"]`);
            const targetInput = row.querySelector(`input[name="okr_kr_${krIndex}_target"]`);
            const deadlineInput = row.querySelector(`input[name="okr_kr_${krIndex}_deadline"]`);
            const ownerInput = row.querySelector(`input[name="okr_kr_${krIndex}_owner"]`);
            const ownerSelect = row.querySelector(`select[name="okr_kr_${krIndex}_owner_id"]`);
            const indicatorSelect = row.querySelector(`select[name="okr_kr_${krIndex}_indicator_id"]`);
            const indicatorLabelInput = row.querySelector(`input[name="okr_kr_${krIndex}_indicator_label"]`);

            const label = labelInput ? labelInput.value.trim() : "";
            if (!label) {
                return;
            }

            results.push({
                id: position,
                label,
                target: targetInput ? targetInput.value.trim() : "",
                deadline: deadlineInput ? deadlineInput.value.trim() : "",
                owner: ownerInput ? ownerInput.value.trim() : "",
                owner_id: ownerSelect ? ownerSelect.value || "" : "",
                indicator_id: indicatorSelect ? indicatorSelect.value || "" : "",
                indicator_label: indicatorLabelInput ? indicatorLabelInput.value.trim() : "",
            });
        });
        return results;
    }

    setKeyResults(results) {
        this.listContainer.innerHTML = "";
        this.counter = 0;
        if (Array.isArray(results) && results.length) {
            results.forEach((result) => this.addKeyResult(result));
        } else if (this.options.minResults === 0) {
            this.addKeyResult();
        }
    }

    validate() {
        const results = this.getKeyResults();
        if (this.options.required && results.length === 0) {
            alert("Pelo menos um Key Result é obrigatório.");
            return false;
        }
        if (results.length < this.options.minResults) {
            alert(`Mínimo de ${this.options.minResults} Key Results é obrigatório.`);
            return false;
        }
        if (results.length > this.options.maxResults) {
            alert(`Máximo de ${this.options.maxResults} Key Results permitidos.`);
            return false;
        }
        return true;
    }

    _escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    _escapeAttr(value) {
        return this._escapeHtml(value);
    }
}

function addKeyResult(containerId) {
    const manager = window[`keyResultsManager_${containerId}`];
    if (manager) {
        manager.addKeyResult();
        return;
    }
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container '${containerId}' não encontrado.`);
        return;
    }
    window[`keyResultsManager_${containerId}`] = new KeyResultsManager(containerId);
}

function removeKeyResult(krIndex) {
    const row = document.getElementById(`kr-row-${krIndex}`);
    if (!row) {
        return;
    }
    const container = row.closest(".okr-kpi-grid");
    if (!container) {
        return;
    }
    const manager = window[`keyResultsManager_${container.id}`];
    if (manager) {
        manager.removeKeyResult(krIndex);
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".okr-kpi-grid").forEach((container) => {
            const containerId = container.id;
            if (!containerId) {
                return;
            }
            if (!window[`keyResultsManager_${containerId}`]) {
                window[`keyResultsManager_${containerId}`] = new KeyResultsManager(containerId);
            }
        });

        document.querySelectorAll("[data-owner-target]").forEach((select) => {
            const targetId = select.getAttribute("data-owner-target");
            if (!targetId) {
                return;
            }
            const updateHidden = () => {
                const hiddenInput = document.getElementById(targetId);
                if (!hiddenInput) {
                    return;
                }
                const option = select.options[select.selectedIndex];
                const value = option ? (option.dataset.name || option.textContent || "") : "";
                hiddenInput.value = value.trim();
            };
            select.addEventListener("change", updateHidden);
            updateHidden();
        });
    });
}
