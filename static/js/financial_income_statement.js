document.addEventListener('DOMContentLoaded', () => {
  const rows = Array.from(document.querySelectorAll('.dre-row[data-row-id]'));
  if (!rows.length) {
    return;
  }

  const rowMap = new Map(rows.map((row) => [row.dataset.rowId, row]));

  const getChildren = (rowId) => rows.filter((row) => row.dataset.parentId === rowId);

  const applyVisibility = () => {
    rows.forEach((row) => {
      let parentId = row.dataset.parentId;
      let hidden = false;
      while (parentId) {
        const parent = rowMap.get(parentId);
        if (!parent) {
          break;
        }
        if (parent.dataset.collapsed === 'true') {
          hidden = true;
          break;
        }
        parentId = parent.dataset.parentId;
      }
      row.classList.toggle('is-hidden', hidden);
    });
  };

  const setCollapsedState = (row, collapsed) => {
    if (row && row.dataset.hasChildren === 'true') {
      row.dataset.collapsed = collapsed ? 'true' : 'false';
    }
  };

  document.querySelectorAll('[data-dre-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const row = rowMap.get(button.dataset.dreToggle);
      if (!row) {
        return;
      }
      setCollapsedState(row, row.dataset.collapsed !== 'true');
      applyVisibility();
    });
  });

  const collapseAll = () => {
    rows.forEach((row) => {
      if (row.dataset.hasChildren === 'true' && Number(row.dataset.level || 0) >= 0) {
        row.dataset.collapsed = Number(row.dataset.level || 0) > 0 ? 'true' : 'false';
      }
    });
    applyVisibility();
  };

  const expandAll = () => {
    rows.forEach((row) => setCollapsedState(row, false));
    applyVisibility();
  };

  document.querySelector('[data-dre-action="collapse-all"]')?.addEventListener('click', collapseAll);
  document.querySelector('[data-dre-action="expand-all"]')?.addEventListener('click', expandAll);

  applyVisibility();
});
