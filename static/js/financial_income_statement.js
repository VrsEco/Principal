document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('.dre-report-page');
  const rows = Array.from(document.querySelectorAll('.dre-row[data-row-id]'));

  if (rows.length) {
    const rowMap = new Map(rows.map((row) => [row.dataset.rowId, row]));

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
  }

  const dialog = document.getElementById('dre-detail-dialog');
  const dialogTitle = document.getElementById('dre-detail-dialog-title');
  const dialogSubtitle = document.getElementById('dre-detail-dialog-subtitle');
  const dialogTotal = document.getElementById('dre-detail-dialog-total');
  const dialogCount = document.getElementById('dre-detail-dialog-count');
  const dialogFeedback = document.getElementById('dre-detail-dialog-feedback');
  const dialogTableWrap = document.getElementById('dre-detail-dialog-table-wrap');
  const dialogTableBody = document.getElementById('dre-detail-dialog-table-body');
  const drilldownUrl = root?.dataset?.dreDrilldownUrl;

  if (!dialog || !dialogTitle || !dialogSubtitle || !dialogTotal || !dialogCount || !dialogFeedback || !dialogTableWrap || !dialogTableBody || !drilldownUrl) {
    return;
  }

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const setFeedback = (message, tone = 'neutral') => {
    dialogFeedback.hidden = false;
    dialogFeedback.dataset.tone = tone;
    dialogFeedback.textContent = message;
    dialogTableWrap.hidden = true;
    dialogTableBody.innerHTML = '';
  };

  const closeDialog = () => {
    if (typeof dialog.close === 'function' && dialog.open) {
      dialog.close();
      return;
    }
    dialog.removeAttribute('open');
  };

  const openDialog = () => {
    if (typeof dialog.showModal === 'function') {
      if (!dialog.open) {
        dialog.showModal();
      }
      return;
    }
    dialog.setAttribute('open', 'open');
  };

  const renderRows = (items) => {
    dialogTableBody.innerHTML = items.map((item) => {
      const referenceMeta = [
        item.component_label ? `<span class="dre-detail-table__meta">${escapeHtml(item.component_label)}</span>` : '',
        item.description ? `<div class="dre-detail-table__desc">${escapeHtml(item.description)}</div>` : '',
      ].join('');
      return `
        <tr>
          <td>${escapeHtml(item.source_kind_label || '-')}</td>
          <td>
            <strong>${escapeHtml(item.source_code || '-')}</strong>
            ${referenceMeta}
          </td>
          <td>
            <strong>${escapeHtml(item.account_label || '-')}</strong>
            <div class="dre-detail-table__desc">${escapeHtml(item.cost_center_label || 'Todos')}</div>
          </td>
          <td>${escapeHtml(item.counterparty || 'Não informado')}</td>
          <td>${escapeHtml(item.competence_date || '-')}</td>
          <td>${escapeHtml(item.due_date || '-')}</td>
          <td>${escapeHtml(item.settlement_date || '-')}</td>
          <td class="dre-detail-table__amount">${escapeHtml(item.amount_label || '-')}</td>
        </tr>
      `;
    }).join('');
    dialogFeedback.hidden = true;
    dialogTableWrap.hidden = false;
  };

  const buildDrilldownUrl = (trigger) => {
    const url = new URL(drilldownUrl, window.location.origin);
    const params = new URLSearchParams(window.location.search);
    params.set('bucket', trigger.dataset.bucket || '');
    if (trigger.dataset.chartAccountId) {
      params.set('chart_account_id', trigger.dataset.chartAccountId);
    } else {
      params.delete('chart_account_id');
    }
    url.search = params.toString();
    return url.toString();
  };

  const loadDrilldown = async (trigger) => {
    dialogTitle.textContent = `${trigger.dataset.bucketLabel || 'Detalhamento'} · ${trigger.dataset.accountLabel || 'Total consolidado'}`;
    dialogSubtitle.textContent = 'Carregando composição...';
    dialogTotal.textContent = '...';
    dialogCount.textContent = '...';
    setFeedback('Carregando composição da DRE...');
    openDialog();

    try {
      const response = await fetch(buildDrilldownUrl(trigger), {
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        throw new Error(`Falha ao carregar detalhamento (${response.status}).`);
      }

      const payload = await response.json();
      dialogTitle.textContent = `${payload.bucket_label || trigger.dataset.bucketLabel || 'Detalhamento'} · ${payload.account_label || trigger.dataset.accountLabel || 'Total consolidado'}`;
      dialogSubtitle.textContent = payload.source_label
        ? `${payload.source_label} que compõem o valor selecionado.`
        : 'Confira os lançamentos que compõem o valor selecionado.';
      dialogTotal.textContent = payload.total_label || 'R$ 0,00';
      dialogCount.textContent = String(payload.item_count || 0);

      if (!Array.isArray(payload.items) || !payload.items.length) {
        setFeedback('Nenhum título ou baixa encontrado para os filtros e a célula selecionada.');
        return;
      }

      renderRows(payload.items);
    } catch (error) {
      dialogTotal.textContent = 'R$ 0,00';
      dialogCount.textContent = '0';
      setFeedback(error?.message || 'Não foi possível carregar o detalhamento da DRE.', 'danger');
    }
  };

  document.querySelectorAll('[data-dre-detail-trigger]').forEach((button) => {
    button.addEventListener('click', () => loadDrilldown(button));
  });

  dialog.querySelectorAll('[data-dre-detail-close]').forEach((button) => {
    button.addEventListener('click', closeDialog);
  });

  dialog.addEventListener('click', (event) => {
    const bounds = dialog.getBoundingClientRect();
    const clickedOutside = event.clientX < bounds.left
      || event.clientX > bounds.right
      || event.clientY < bounds.top
      || event.clientY > bounds.bottom;
    if (clickedOutside) {
      closeDialog();
    }
  });
});
