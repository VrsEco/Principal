(function () {
  class CompanyRolePermissionMatrix {
    constructor(options = {}) {
      this.mount = options.mount;
      this.summaryMount = options.summaryMount;
      this.searchInput = options.searchInput;
      this.catalog = null;
      this.companyId = null;
      this.selected = {};
      this.expanded = new Set(["projects", "projects.tasks"]);
      this.actionOrder = [];

      if (this.searchInput) {
        this.searchInput.addEventListener("input", () => this.render());
      }
    }

    async ensureCatalog(companyId) {
      if (!this.mount || !companyId) return;
      this.companyId = companyId;
      if (this.catalog) return;

      const response = await fetch(`/api/companies/${companyId}/permission-catalog`);
      if (!response.ok) {
        throw new Error("Falha ao carregar catálogo de permissões.");
      }

      this.catalog = await response.json();
      this.actionOrder = (this.catalog.actions || []).map((item) => item.key);
      this.render();
    }

    reset() {
      this.selected = {};
      this.expanded = new Set(["projects", "projects.tasks"]);
      if (this.searchInput) {
        this.searchInput.value = "";
      }
      this.render();
    }

    setValue(flatPermissions) {
      this.selected = {};
      Object.entries(flatPermissions || {}).forEach(([resourceKey, actions]) => {
        if (!Array.isArray(actions)) return;
        const normalized = [...new Set(actions.map((item) => String(item || "").trim()).filter(Boolean))];
        if (normalized.length) {
          this.selected[resourceKey] = normalized;
        }
      });
      this.render();
    }

    getValue() {
      return JSON.parse(JSON.stringify(this.selected));
    }

    toggleNode(resourceKey) {
      if (this.expanded.has(resourceKey)) {
        this.expanded.delete(resourceKey);
      } else {
        this.expanded.add(resourceKey);
      }
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
        if (term && childMatch) {
          this.expanded.add(node.key);
        }
        return own || childMatch;
      };

      const rows = [];
      const walk = (nodes, depth = 0) => {
        (nodes || []).forEach((node) => {
          if (term && !matches(node)) return;
          rows.push({ node, depth });
          if ((node.children || []).length && this.expanded.has(node.key)) {
            walk(node.children, depth + 1);
          }
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

    resourceSelection(node) {
      return new Set(this.selected[node.key] || []);
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
          <span>Nós do módulo Projetos ativos</span>
        </div>
      `;
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

        const cells = this.actionOrder.map((actionKey) => {
          if (!(node.actions || []).includes(actionKey)) {
            return `<td class="role-permission-cell--disabled">—</td>`;
          }

          const checked = selected.has(actionKey) ? "checked" : "";
          return `
            <td>
              <input
                class="role-permission-checkbox"
                type="checkbox"
                ${checked}
                onchange="window.rolePermissionMatrix.setAction('${node.key}', '${actionKey}', this.checked)"
              >
            </td>
          `;
        }).join("");

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
    }
  }

  window.CompanyRolePermissionMatrix = CompanyRolePermissionMatrix;
})();
