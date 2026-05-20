(function () {
  class CompanyRolePermissionMatrix {
    constructor(options = {}) {
      this.mount = options.mount;
      this.summaryMount = options.summaryMount;
      this.searchInput = options.searchInput;
      this.presetSelect = options.presetSelect;
      this.presetNameInput = options.presetNameInput;
      this.presetDescriptionInput = options.presetDescriptionInput;
      this.presetDeleteButton = options.presetDeleteButton;
      this.catalog = null;
      this.companyId = null;
      this.selected = {};
      this.expanded = new Set(["companies", "projects", "financial", "operations", "mcp"]);
      this.actionOrder = [];

      if (this.searchInput) {
        this.searchInput.addEventListener("input", () => this.render());
      }
      if (this.presetSelect) {
        this.presetSelect.addEventListener("change", () => this.syncPresetEditor());
      }
    }

    async ensureCatalog(companyId, options = {}) {
      if (!this.mount || !companyId) return;
      this.companyId = companyId;
      if (this.catalog && !options.force) return;

      const response = await fetch(`/api/companies/${companyId}/permission-catalog`);
      if (!response.ok) {
        throw new Error("Falha ao carregar catálogo de permissões.");
      }

      this.catalog = await response.json();
      this.actionOrder = (this.catalog.actions || []).map((item) => item.key);
      this.populatePresetSelect();
      this.syncPresetEditor();
      this.render();
    }

    presetsBySource(source) {
      if (this.catalog?.preset_groups?.[source]) return this.catalog.preset_groups[source];
      return (this.catalog?.presets || []).filter((item) => item.source === source);
    }

    populatePresetSelect() {
      if (!this.presetSelect) return;
      const renderOptions = (presets) => presets
        .map((preset) => `<option value="${preset.key}">${preset.label}</option>`)
        .join("");

      const systemPresets = renderOptions(this.presetsBySource("system"));
      const companyPresets = renderOptions(this.presetsBySource("company"));

      this.presetSelect.innerHTML = `
        <option value="">Preset de perfil</option>
        ${systemPresets ? `<optgroup label="Presets do sistema">${systemPresets}</optgroup>` : ""}
        ${companyPresets ? `<optgroup label="Presets da empresa">${companyPresets}</optgroup>` : ""}
      `;
    }

    findPreset(presetKey) {
      return (this.catalog?.presets || []).find((item) => item.key === presetKey) || null;
    }

    selectedPreset() {
      return this.findPreset(this.presetSelect?.value);
    }

    syncPresetEditor() {
      const preset = this.selectedPreset();
      if (this.presetNameInput) this.presetNameInput.value = preset?.label || "";
      if (this.presetDescriptionInput) this.presetDescriptionInput.value = preset?.description || "";
      if (this.presetDeleteButton) {
        this.presetDeleteButton.disabled = !(preset && preset.source === "company" && preset.id);
      }
    }

    reset() {
      this.selected = {};
      this.expanded = new Set(["companies", "projects", "financial", "operations", "mcp"]);
      if (this.searchInput) this.searchInput.value = "";
      if (this.presetSelect) this.presetSelect.value = "";
      this.syncPresetEditor();
      this.render();
    }

    setValue(flatPermissions) {
      this.selected = {};
      Object.entries(flatPermissions || {}).forEach(([resourceKey, actions]) => {
        if (!Array.isArray(actions)) return;
        const normalized = [...new Set(actions.map((item) => String(item || "").trim()).filter(Boolean))];
        if (normalized.length) this.selected[resourceKey] = normalized;
      });
      if (this.presetSelect) this.presetSelect.value = "";
      this.syncPresetEditor();
      this.render();
    }

    getValue() {
      return JSON.parse(JSON.stringify(this.selected));
    }

    applyPreset(presetKey) {
      const preset = this.findPreset(presetKey);
      if (!preset) return;
      this.setValue(preset.grants || {});
      if (this.presetSelect) this.presetSelect.value = preset.key;
      this.syncPresetEditor();
      this.expandTouchedDomains();
    }

    async saveCompanyPreset() {
      if (!this.companyId) {
        throw new Error("Empresa não identificada para salvar o preset.");
      }
      const preset = this.selectedPreset();
      const payload = {
        name: this.presetNameInput?.value || "",
        description: this.presetDescriptionInput?.value || "",
        permissions: this.getValue(),
      };
      const isUpdate = preset && preset.source === "company" && preset.id;
      const url = isUpdate
        ? `/api/companies/${this.companyId}/role-permission-presets/${preset.id}`
        : `/api/companies/${this.companyId}/role-permission-presets`;
      const response = await fetch(url, {
        method: isUpdate ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || "Falha ao salvar preset.");
      }
      await this.ensureCatalog(this.companyId, { force: true });
      if (this.presetSelect) this.presetSelect.value = result.key;
      this.syncPresetEditor();
      return result;
    }

    async deleteSelectedCompanyPreset() {
      const preset = this.selectedPreset();
      if (!preset || preset.source !== "company" || !preset.id) {
        throw new Error("Selecione um preset da empresa para excluir.");
      }
      const response = await fetch(
        `/api/companies/${this.companyId}/role-permission-presets/${preset.id}`,
        { method: "DELETE" }
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || "Falha ao excluir preset.");
      }
      if (this.presetSelect) this.presetSelect.value = "";
      await this.ensureCatalog(this.companyId, { force: true });
      this.syncPresetEditor();
      return result;
    }

    expandTouchedDomains() {
      Object.keys(this.selected).forEach((key) => {
        const parts = key.split(".");
        let current = "";
        parts.forEach((part, index) => {
          current = index === 0 ? part : `${current}.${part}`;
          this.expanded.add(current);
        });
      });
      this.render();
    }

    toggleNode(resourceKey) {
      if (this.expanded.has(resourceKey)) this.expanded.delete(resourceKey);
      else this.expanded.add(resourceKey);
      this.render();
    }

    setAction(resourceKey, actionKey, checked) {
      const node = this.findNode(resourceKey);
      if (!node) return;
      this.applyActionCascade(node, actionKey, checked);
      this.render();
    }

    applyActionCascade(node, actionKey, checked) {
      if ((node.actions || []).includes(actionKey)) {
        const current = new Set(this.selected[node.key] || []);
        if (checked) current.add(actionKey);
        else current.delete(actionKey);
        if (current.size) this.selected[node.key] = [...current];
        else delete this.selected[node.key];
      }
      (node.children || []).forEach((child) => this.applyActionCascade(child, actionKey, checked));
    }

    findNode(resourceKey) {
      const walk = (nodes) => {
        for (const node of nodes || []) {
          if (node.key === resourceKey) return node;
          const found = walk(node.children || []);
          if (found) return found;
        }
        return null;
      };
      return walk(this.catalog?.roots || []);
    }

    visibleRows() {
      const term = (this.searchInput?.value || "").trim().toLowerCase();
      const matches = (node) => {
        const own = `${node.label || ""} ${node.description || ""}`.toLowerCase().includes(term);
        const childMatch = (node.children || []).some((child) => matches(child));
        if (term && childMatch) this.expanded.add(node.key);
        return own || childMatch;
      };

      const rows = [];
      const walk = (nodes, depth = 0) => {
        (nodes || []).forEach((node) => {
          if (term && !matches(node)) return;
          rows.push({ node, depth });
          if ((node.children || []).length && this.expanded.has(node.key)) walk(node.children, depth + 1);
        });
      };

      walk(this.catalog?.roots || []);
      return rows;
    }

    selectedActionCount() {
      return Object.values(this.selected).reduce((acc, actions) => acc + actions.length, 0);
    }

    configuredNodeCount() {
      return Object.values(this.selected).filter((actions) => actions.length).length;
    }

    projectNodeCount() {
      return Object.keys(this.selected).filter((key) => key.startsWith("projects")).length;
    }

    rootDomainCount() {
      const rootKeys = new Set((this.catalog?.roots || []).map((item) => item.key));
      const touched = new Set();
      Object.keys(this.selected).forEach((key) => {
        const root = key.split(".")[0];
        if (rootKeys.has(root)) touched.add(root);
      });
      return touched.size;
    }

    resourceSelection(node) {
      return new Set(this.selected[node.key] || []);
    }

    descendantActionCount(node, actionKey) {
      let count = 0;
      const walk = (children) => {
        (children || []).forEach((child) => {
          if (this.resourceSelection(child).has(actionKey)) count += 1;
          walk(child.children || []);
        });
      };
      walk(node.children || []);
      return count;
    }

    nodeInheritanceMeta(node) {
      const selected = this.resourceSelection(node);
      const actionStates = {};
      let inheritedCount = 0;
      let partialCount = 0;

      this.actionOrder.forEach((actionKey) => {
        if (!(node.actions || []).includes(actionKey)) return;
        const own = selected.has(actionKey);
        const descendants = this.descendantActionCount(node, actionKey);
        const inherited = !own && descendants > 0;
        const partial = own && descendants > 0;
        if (inherited) inheritedCount += 1;
        if (partial) partialCount += 1;
        actionStates[actionKey] = { own, descendants, inherited, partial };
      });

      return { actionStates, inheritedCount, partialCount };
    }

    renderSummary() {
      if (!this.summaryMount) return;
      this.summaryMount.innerHTML = `
        <div class="role-permissions-summary__card">
          <strong>${this.selectedActionCount()}</strong>
          <span>Ações concedidas</span>
        </div>
        <div class="role-permissions-summary__card">
          <strong>${this.configuredNodeCount()}</strong>
          <span>Recursos configurados</span>
        </div>
        <div class="role-permissions-summary__card">
          <strong>${this.projectNodeCount()}</strong>
          <span>Nós ativos em Projetos</span>
        </div>
        <div class="role-permissions-summary__card">
          <strong>${this.rootDomainCount()}</strong>
          <span>Domínios sistêmicos tocados</span>
        </div>
      `;
    }

    applyIndeterminateStates() {
      this.mount.querySelectorAll('input[data-indeterminate="true"]').forEach((input) => {
        input.indeterminate = true;
      });
    }

    render() {
      if (!this.mount || !this.catalog) return;
      this.renderSummary();

      const rows = this.visibleRows();
      if (!rows.length) {
        this.mount.innerHTML = `<div class="role-permission-empty">Nenhum recurso encontrado para o filtro informado.</div>`;
        return;
      }

      const header = (this.catalog.actions || [])
        .map((action) => `<th title="${action.label}">${action.short_label || action.label}</th>`)
        .join("");

      const body = rows.map(({ node, depth }) => {
        const selected = this.resourceSelection(node);
        const indent = depth * 20;
        const hasChildren = !!(node.children || []).length;
        const expanded = this.expanded.has(node.key);
        const badge = `${selected.size}/${(node.actions || []).length}`;
        const inheritance = this.nodeInheritanceMeta(node);

        const cells = this.actionOrder.map((actionKey) => {
          if (!(node.actions || []).includes(actionKey)) {
            return `<td class="role-permission-cell--disabled">—</td>`;
          }

          const state = inheritance.actionStates[actionKey] || {};
          const checked = state.own ? "checked" : "";
          const indeterminate = state.inherited ? "true" : "false";
          const classes = [
            "role-permission-checkbox",
            state.inherited ? "role-permission-checkbox--inherited" : "",
            state.partial ? "role-permission-checkbox--partial" : "",
          ].filter(Boolean).join(" ");
          const title = state.inherited
            ? `Herdado visualmente de ${state.descendants} filho(s) com esta ação`
            : state.partial
              ? `Este nó e ${state.descendants} filho(s) possuem esta ação`
              : "";

          return `
            <td class="${state.inherited ? "role-permission-cell--inherited" : ""}">
              <input
                class="${classes}"
                type="checkbox"
                ${checked}
                data-indeterminate="${indeterminate}"
                title="${title}"
                onchange="window.rolePermissionMatrix.setAction('${node.key}', '${actionKey}', this.checked)"
              >
            </td>
          `;
        }).join("");

        const extraBadges = [
          inheritance.inheritedCount ? `<span class="role-permission-badge role-permission-badge--inherit">${inheritance.inheritedCount} ação(ões) herdadas visualmente</span>` : "",
          inheritance.partialCount ? `<span class="role-permission-badge role-permission-badge--partial">${inheritance.partialCount} ação(ões) com filhos ativos</span>` : "",
        ].join("");

        return `
          <tr>
            <td>
              <div class="role-permission-row__name" style="padding-left:${indent}px;">
                <button
                  type="button"
                  class="role-permission-toggle"
                  ${hasChildren ? "" : "disabled"}
                  onclick="window.rolePermissionMatrix.toggleNode('${node.key}')"
                  aria-label="${expanded ? "Recolher" : "Expandir"} ${node.label}"
                >${hasChildren ? (expanded ? "▾" : "▸") : "•"}</button>
                <div class="role-permission-node__copy">
                  <strong>${node.label}</strong>
                  <small>${node.description || ""}</small>
                  <div class="role-permission-node__meta">
                    <span class="role-permission-badge">${badge} ações neste nó</span>
                    ${extraBadges}
                    <span class="role-permission-badge">${node.key}</span>
                  </div>
                </div>
              </div>
            </td>
            ${cells}
          </tr>
        `;
      }).join("");

      this.mount.innerHTML = `
        <div class="role-permissions-table-shell">
          <table class="role-permissions-table">
            <thead>
              <tr>
                <th>Recurso / Feature</th>
                ${header}
              </tr>
            </thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      `;

      this.applyIndeterminateStates();
    }
  }

  window.CompanyRolePermissionMatrix = CompanyRolePermissionMatrix;
})();
