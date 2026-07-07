document.addEventListener('DOMContentLoaded', function () {
  var root = document.querySelector('.dre-report-page');
  var rows = Array.prototype.slice.call(document.querySelectorAll('.dre-row[data-row-id]'));

  if (rows.length) {
    var rowMap = new Map(rows.map(function (row) {
      return [row.dataset.rowId, row];
    }));

    var applyVisibility = function () {
      rows.forEach(function (row) {
        var parentId = row.dataset.parentId;
        var hidden = false;
        while (parentId) {
          var parent = rowMap.get(parentId);
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

    var collapsedRowIds = function () {
      return rows
        .filter(function (row) {
          return row.dataset.hasChildren === 'true' && row.dataset.collapsed === 'true';
        })
        .map(function (row) {
          return row.dataset.rowId;
        })
        .filter(Boolean);
    };

    var syncExportPdfLinks = function () {
      document.querySelectorAll('[data-dre-export-pdf]').forEach(function (link) {
        var url = new URL(link.getAttribute('href') || window.location.href, window.location.origin);
        url.searchParams.delete('collapsed_row_ids');
        collapsedRowIds().forEach(function (rowId) {
          url.searchParams.append('collapsed_row_ids', rowId);
        });
        link.setAttribute('href', url.pathname + url.search + url.hash);
      });
    };

    var setCollapsedState = function (row, collapsed) {
      if (row && row.dataset.hasChildren === 'true') {
        row.dataset.collapsed = collapsed ? 'true' : 'false';
      }
    };

    document.querySelectorAll('[data-dre-toggle]').forEach(function (button) {
      button.addEventListener('click', function () {
        var row = rowMap.get(button.dataset.dreToggle);
        if (!row) {
          return;
        }
        setCollapsedState(row, row.dataset.collapsed !== 'true');
        applyVisibility();
        syncExportPdfLinks();
      });
    });

    var collapseAllButton = document.querySelector('[data-dre-action="collapse-all"]');
    var expandAllButton = document.querySelector('[data-dre-action="expand-all"]');

    var collapseAll = function () {
      rows.forEach(function (row) {
        if (row.dataset.hasChildren === 'true' && Number(row.dataset.level || 0) >= 0) {
          row.dataset.collapsed = Number(row.dataset.level || 0) > 0 ? 'true' : 'false';
        }
      });
      applyVisibility();
      syncExportPdfLinks();
    };

    var expandAll = function () {
      rows.forEach(function (row) {
        setCollapsedState(row, false);
      });
      applyVisibility();
      syncExportPdfLinks();
    };

    if (collapseAllButton) {
      collapseAllButton.addEventListener('click', collapseAll);
    }
    if (expandAllButton) {
      expandAllButton.addEventListener('click', expandAll);
    }

    applyVisibility();
    syncExportPdfLinks();

    document.addEventListener('click', function (event) {
      if (event.target.closest('[data-dre-export-pdf]')) {
        syncExportPdfLinks();
      }
    });
  }

  var drilldownUrl = root && root.dataset ? root.dataset.dreDrilldownUrl : '';
  var modal = document.getElementById('dre-detail-modal');
  var modalTitle = document.getElementById('dre-detail-modal-title');
  var modalSubtitle = document.getElementById('dre-detail-modal-subtitle');
  var modalTotal = document.getElementById('dre-detail-modal-total');
  var modalCount = document.getElementById('dre-detail-modal-count');
  var modalFeedback = document.getElementById('dre-detail-modal-feedback');
  var modalTableWrap = document.getElementById('dre-detail-modal-table-wrap');
  var modalTableBody = document.getElementById('dre-detail-modal-table-body');

  if (!drilldownUrl || !modal || !modalTitle || !modalSubtitle || !modalTotal || !modalCount || !modalFeedback || !modalTableWrap || !modalTableBody) {
    return;
  }

  var escapeHtml = function (value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[char];
    });
  };

  var setFeedback = function (message, tone) {
    modalFeedback.hidden = false;
    modalFeedback.setAttribute('data-tone', tone || 'neutral');
    modalFeedback.textContent = message;
    modalTableWrap.hidden = true;
    modalTableBody.innerHTML = '';
  };

  var openModal = function () {
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
  };

  var closeModal = function () {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
  };

  var renderRows = function (items) {
    modalTableBody.innerHTML = items.map(function (item) {
      var referenceMeta = '';
      if (item.component_label) {
        referenceMeta += '<span class="dre-detail-table__meta">' + escapeHtml(item.component_label) + '</span>';
      }
      if (item.description) {
        referenceMeta += '<div class="dre-detail-table__desc">' + escapeHtml(item.description) + '</div>';
      }
      return '' +
        '<tr>' +
          '<td>' + escapeHtml(item.source_kind_label || '-') + '</td>' +
          '<td><strong>' + escapeHtml(item.source_code || '-') + '</strong>' + referenceMeta + '</td>' +
          '<td><strong>' + escapeHtml(item.account_label || '-') + '</strong><div class="dre-detail-table__desc">' + escapeHtml(item.cost_center_label || 'Todos') + '</div></td>' +
          '<td>' + escapeHtml(item.counterparty || 'Não informado') + '</td>' +
          '<td>' + escapeHtml(item.competence_date || '-') + '</td>' +
          '<td>' + escapeHtml(item.due_date || '-') + '</td>' +
          '<td>' + escapeHtml(item.settlement_date || '-') + '</td>' +
          '<td class="dre-detail-table__amount">' + escapeHtml(item.amount_label || '-') + '</td>' +
        '</tr>';
    }).join('');
    modalFeedback.hidden = true;
    modalTableWrap.hidden = false;
  };

  var buildDrilldownUrl = function (trigger) {
    var url = new URL(drilldownUrl, window.location.origin);
    var params = new URLSearchParams(window.location.search);
    params.set('bucket', trigger.getAttribute('data-bucket') || '');
    var chartAccountId = trigger.getAttribute('data-chart-account-id') || '';
    if (chartAccountId) {
      params.set('detail_chart_account_id', chartAccountId);
    } else {
      params.delete('detail_chart_account_id');
    }
    url.search = params.toString();
    return url.toString();
  };

  var loadDrilldown = function (trigger) {
    modalTitle.textContent = (trigger.getAttribute('data-bucket-label') || 'Detalhamento') + ' · ' + (trigger.getAttribute('data-account-label') || 'Total consolidado');
    modalSubtitle.textContent = 'Carregando composição...';
    modalTotal.textContent = '...';
    modalCount.textContent = '...';
    setFeedback('Carregando composição da DRE...');
    openModal();

    fetch(buildDrilldownUrl(trigger), {
      headers: {
        Accept: 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'same-origin'
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Falha ao carregar detalhamento (' + response.status + ').');
        }
        return response.json();
      })
      .then(function (payload) {
        modalTitle.textContent = (payload.bucket_label || trigger.getAttribute('data-bucket-label') || 'Detalhamento') + ' · ' + (payload.account_label || trigger.getAttribute('data-account-label') || 'Total consolidado');
        modalSubtitle.textContent = payload.source_label
          ? payload.source_label + ' que compõem o valor selecionado.'
          : 'Confira os lançamentos que compõem o valor selecionado.';
        modalTotal.textContent = payload.total_label || 'R$ 0,00';
        modalCount.textContent = String(payload.item_count || 0);

        if (!Array.isArray(payload.items) || !payload.items.length) {
          setFeedback('Nenhum título ou baixa encontrado para os filtros e a célula selecionada.');
          return;
        }

        renderRows(payload.items);
      })
      .catch(function (error) {
        modalTotal.textContent = 'R$ 0,00';
        modalCount.textContent = '0';
        setFeedback((error && error.message) || 'Não foi possível carregar o detalhamento da DRE.', 'danger');
      });
  };

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-dre-detail-trigger]');
    if (trigger) {
      event.preventDefault();
      loadDrilldown(trigger);
      return;
    }

    var closeTrigger = event.target.closest('[data-dre-detail-close]');
    if (closeTrigger) {
      event.preventDefault();
      closeModal();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
      closeModal();
    }
  });
});
