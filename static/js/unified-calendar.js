(function () {
  'use strict';

  var root = document.getElementById('ucRoot');
  if (!root) return;

  var companyId = root.dataset.companyId;
  var canViewAll = root.dataset.canViewAll === 'true';
  var myEmployeeId = root.dataset.employeeId || '';
  var TYPE_LABEL = { meeting: 'Reunião', project_task: 'Atividade', process_instance: 'Instância', google_event: 'Google' };
  var MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  var WEEKDAYS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];

  var el = {
    grid: document.getElementById('ucGrid'),
    month: document.getElementById('ucMonthLabel'),
    status: document.getElementById('ucStatus'),
    dayTitle: document.getElementById('ucDayTitle'),
    dayList: document.getElementById('ucDayList'),
    create: document.getElementById('ucCreate'),
    modal: document.getElementById('ucModal'),
    form: document.getElementById('ucForm'),
    mTitle: document.getElementById('ucModalTitle'),
    fTitle: document.getElementById('ucFTitle'),
    fDate: document.getElementById('ucFDate'),
    fProject: document.getElementById('ucFProject'),
    fProcess: document.getElementById('ucFProcess'),
    fError: document.getElementById('ucFError'),
    fSubmit: document.getElementById('ucFSubmit'),
    scope: document.getElementById('ucScope'),
    employee: document.getElementById('ucEmployee')
  };

  var state = {
    view: firstOfMonth(parseISO(root.dataset.today)),
    selected: root.dataset.today,
    events: [],
    byDate: {},
    createType: null,
    requestSeq: 0,
    flash: ''
  };

  function parseISO(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function toISO(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function firstOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function gridRange() {
    var start = new Date(state.view);
    start.setDate(1 - start.getDay());
    var end = new Date(start);
    end.setDate(start.getDate() + 41);
    return { start: start, end: end };
  }
  function h(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function formatDay(iso) {
    var d = parseISO(iso);
    return WEEKDAYS[d.getDay()] + ', ' + d.getDate() + ' de ' + MONTHS[d.getMonth()];
  }

  function activeTypes() {
    return Array.prototype.slice.call(document.querySelectorAll('.uc-filters input[data-type]:checked:not(:disabled)'))
      .map(function (i) { return i.dataset.type; });
  }

  function load() {
    var range = gridRange();
    var types = activeTypes();
    var seq = ++state.requestSeq;
    if (!types.length) { state.events = []; index(); render(); return; }
    var qs = new URLSearchParams({ start: toISO(range.start), end: toISO(range.end), types: types.join(',') });
    var scope = el.scope ? el.scope.value : 'mine';
    qs.set('scope', scope);
    if (scope === 'all' && el.employee && el.employee.value) qs.set('employee_id', el.employee.value);
    el.status.textContent = 'Carregando…';
    fetch('/api/companies/' + companyId + '/agenda/events?' + qs.toString(), { credentials: 'same-origin' })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (seq !== state.requestSeq) return;
        if (!res.ok || !res.body.success) throw new Error(res.body.message || 'Falha ao carregar.');
        state.events = res.body.events || [];
        if (res.body.google_error) state.flash = state.flash || res.body.google_error;
        el.status.textContent = state.flash || res.body.note || (state.events.length ? '' : 'Nenhum registro neste período.');
        state.flash = '';
        index();
        render();
      })
      .catch(function (err) {
        if (seq !== state.requestSeq) return;
        state.events = [];
        index();
        render();
        el.status.textContent = err.message || 'Falha ao carregar.';
      });
  }

  function index() {
    state.byDate = {};
    state.events.forEach(function (e) { (state.byDate[e.date] = state.byDate[e.date] || []).push(e); });
  }

  function render() {
    el.month.textContent = MONTHS[state.view.getMonth()] + ' ' + state.view.getFullYear();
    var range = gridRange();
    var today = root.dataset.today;
    el.grid.textContent = '';
    for (var i = 0; i < 42; i++) {
      var d = new Date(range.start);
      d.setDate(range.start.getDate() + i);
      var iso = toISO(d);
      var items = state.byDate[iso] || [];
      var cell = h('button', 'uc-cell');
      cell.type = 'button';
      cell.setAttribute('role', 'gridcell');
      cell.dataset.date = iso;
      if (d.getMonth() !== state.view.getMonth()) cell.classList.add('uc-cell--out');
      if (iso === today) cell.classList.add('uc-cell--today');
      if (iso === state.selected) cell.classList.add('uc-cell--selected');
      cell.setAttribute('aria-label', formatDay(iso) + (items.length ? ', ' + items.length + ' registro(s)' : ''));
      cell.appendChild(h('span', 'uc-cell__num', String(d.getDate())));

      var list = h('div', 'uc-cell__events');
      items.slice(0, 3).forEach(function (e) {
        list.appendChild(h('span', 'uc-pill uc-pill--' + e.type + (e.closed ? ' is-closed' : ''), (e.time ? e.time + ' ' : '') + e.title));
      });
      if (items.length > 3) list.appendChild(h('span', 'uc-more', '+' + (items.length - 3) + ' mais'));
      cell.appendChild(list);

      var dots = h('div', 'uc-dots');
      var seen = {};
      items.forEach(function (e) {
        if (seen[e.type]) return;
        seen[e.type] = true;
        dots.appendChild(h('span', 'uc-dot uc-dot--' + e.type));
      });
      cell.appendChild(dots);
      el.grid.appendChild(cell);
    }
    renderDay();
  }

  function renderDay() {
    el.dayTitle.textContent = formatDay(state.selected);
    el.create.hidden = false;
    var taskBtn = el.create.querySelector('[data-create="project_task"]');
    if (taskBtn) taskBtn.hidden = !canViewAll;
    el.dayList.textContent = '';
    var items = state.byDate[state.selected] || [];
    if (!items.length) {
      el.dayList.appendChild(h('li', 'uc-list__empty', 'Nenhum registro neste dia.'));
      return;
    }
    items.forEach(function (e) {
      var li = h('li', 'uc-item uc-item--' + e.type + (e.closed ? ' is-closed' : ''));
      var a = h('a');
      if (e.url) a.href = e.url;
      if (e.external) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
      a.appendChild(h('span', 'uc-item__kind', TYPE_LABEL[e.type] + (e.time ? ' · ' + e.time : '')));
      a.appendChild(h('span', 'uc-item__title', e.title));
      var meta = [e.subtitle, e.status].filter(Boolean).join(' · ');
      if (meta) a.appendChild(h('span', 'uc-item__meta', meta));
      li.appendChild(a);
      el.dayList.appendChild(li);
    });
  }

  function select(iso) {
    state.selected = iso;
    var d = parseISO(iso);
    if (d.getMonth() !== state.view.getMonth() || d.getFullYear() !== state.view.getFullYear()) {
      state.view = firstOfMonth(d);
      load();
      return;
    }
    render();
    if (window.matchMedia('(max-width: 1024px)').matches) {
      document.getElementById('ucDayPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function moveMonth(delta) {
    state.view = new Date(state.view.getFullYear(), state.view.getMonth() + delta, 1);
    state.selected = toISO(state.view);
    load();
  }

  /* ---------- criação ---------- */
  function openCreate(type) {
    if (type === 'meeting') {
      window.location.href = '/meetings/company/' + companyId + '?new=1&date=' + encodeURIComponent(state.selected);
      return;
    }
    state.createType = type;
    el.mTitle.textContent = type === 'project_task' ? 'Nova atividade de projeto' : 'Nova instância de processo';
    el.fTitle.value = '';
    el.fDate.value = state.selected;
    el.fError.hidden = true;
    Array.prototype.forEach.call(el.form.querySelectorAll('[data-for]'), function (f) { f.hidden = f.dataset.for !== type; });
    var picker = type === 'project_task' ? el.fProject : el.fProcess;
    if (!picker.options.length) {
      el.fError.textContent = type === 'project_task' ? 'Não há projetos cadastrados.' : 'Não há processos cadastrados.';
      el.fError.hidden = false;
    }
    el.modal.hidden = false;
    el.fTitle.focus();
  }

  function closeModal() { el.modal.hidden = true; el.fSubmit.disabled = false; }

  function submitCreate(ev) {
    ev.preventDefault();
    var type = state.createType;
    var title = el.fTitle.value.trim();
    if (!title || !el.fDate.value) return;
    var url, body;
    if (type === 'project_task') {
      if (!el.fProject.value) return;
      url = '/api/projects/' + el.fProject.value + '/tasks?company_id=' + companyId;
      body = { what: title, due_date: el.fDate.value };
      if (myEmployeeId) body.employee_id = +myEmployeeId;
    } else {
      if (!el.fProcess.value) return;
      url = '/api/companies/' + companyId + '/process-instances';
      body = { process_id: +el.fProcess.value, title: title, due_date: el.fDate.value, status: 'pending' };
    }
    el.fSubmit.disabled = true;
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.body.id) {
          var msg = res.body.message || res.body.error || (res.body.errors && JSON.stringify(res.body.errors)) || 'Não foi possível criar o registro.';
          throw new Error(msg);
        }
        window.location.href = type === 'project_task'
          ? '/my-work/project-task/' + res.body.id + '?from=agenda'
          : '/my-work/process-instance/' + res.body.id + '?company_id=' + companyId + '&from=agenda';
      })
      .catch(function (err) {
        el.fError.textContent = err.message;
        el.fError.hidden = false;
        el.fSubmit.disabled = false;
      });
  }

  /* ---------- eventos ---------- */
  el.grid.addEventListener('click', function (ev) {
    var cell = ev.target.closest('.uc-cell');
    if (cell) select(cell.dataset.date);
  });
  document.getElementById('ucPrev').addEventListener('click', function () { moveMonth(-1); });
  document.getElementById('ucNext').addEventListener('click', function () { moveMonth(1); });
  document.getElementById('ucToday').addEventListener('click', function () {
    state.view = firstOfMonth(parseISO(root.dataset.today));
    state.selected = root.dataset.today;
    load();
  });
  Array.prototype.forEach.call(document.querySelectorAll('.uc-filters input[data-type]'), function (i) {
    i.addEventListener('change', load);
  });
  if (el.scope) {
    el.scope.addEventListener('change', function () { el.employee.hidden = el.scope.value !== 'all'; load(); });
    el.employee.addEventListener('change', load);
  }
  el.create.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-create]');
    if (btn) openCreate(btn.dataset.create);
  });
  el.form.addEventListener('submit', submitCreate);
  el.modal.addEventListener('click', function (ev) { if (ev.target.hasAttribute('data-close')) closeModal(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !el.modal.hidden) closeModal(); });

  /* ---------- Google Calendar ---------- */
  var g = {
    box: document.getElementById('ucGoogle'),
    label: document.getElementById('ucGoogleLabel'),
    connect: document.getElementById('ucGConnect'),
    sync: document.getElementById('ucGSync'),
    syncAll: document.getElementById('ucGSyncAll'),
    disconnect: document.getElementById('ucGDisconnect')
  };
  var GOOGLE_MSG = {
    connected: 'Conta Google conectada.',
    denied: 'Autorização negada no Google.',
    invalid: 'Autorização inválida. Tente conectar novamente.',
    error: 'Não foi possível concluir a conexão com o Google.',
    not_configured: 'Integração com o Google não configurada neste ambiente.'
  };

  function googleApi(path, options) {
    return fetch('/api/companies/' + companyId + '/agenda/google/' + path, Object.assign({ credentials: 'same-origin' }, options || {}))
      .then(function (r) { return r.json().catch(function () { return {}; }); });
  }

  function refreshGoogle() {
    if (!myEmployeeId) return;
    googleApi('status').then(function (s) {
      var banner = document.getElementById('ucGBanner');
      var chip = document.getElementById('ucChipGoogle');
      if (banner) banner.hidden = !(s.success && s.configured && s.needs_reconnect);
      var wasEnabled = chip && !chip.querySelector('input').disabled;
      if (chip) {
        chip.hidden = !(s.success && s.connected);
        chip.querySelector('input').disabled = !(s.success && s.connected);
        if (!!(s.success && s.connected) !== !!wasEnabled) load();
      }
      if (!s.success || !s.configured) { g.box.hidden = true; return; }
      g.box.hidden = false;
      var ok = s.connected;
      g.connect.hidden = ok;
      g.sync.hidden = !ok;
      g.syncAll.hidden = !ok;
      g.disconnect.hidden = !s.status;
      g.connect.textContent = s.status === 'revoked' ? 'Reconectar Google' : 'Conectar Google';
      g.connect.href = s.status === 'revoked' ? '/agenda/google' : '/agenda/google/connect';
      var text = ok ? 'Google Calendar: ' + (s.email || 'conectado') : 'Google Calendar: não conectado';
      if (ok && s.last_synced_at) text += ' · última sincronização ' + new Date(s.last_synced_at + 'Z').toLocaleString('pt-BR');
      if (s.last_error) text += ' · ' + s.last_error;
      g.label.textContent = text;
    });
  }

  function runSync(url, label) {
    var range = gridRange();
    g.sync.disabled = true;
    g.syncAll.disabled = true;
    el.status.textContent = 'Sincronizando ' + label + '…';
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start: toISO(range.start), end: toISO(range.end) })
    }).then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (res) {
        if (!res.success) throw new Error(res.message || 'Falha na sincronização.');
        var st = res.stats;
        el.status.textContent = 'Google sincronizado (' + label + '): ' + st.created + ' criados, ' + st.updated + ' atualizados, ' +
          st.deleted + ' removidos' + (st.failed ? ', ' + st.failed + ' com falha' : '') + '.';
      }).catch(function (err) {
        el.status.textContent = err.message;
      }).then(function () { g.sync.disabled = false; g.syncAll.disabled = false; refreshGoogle(); });
  }

  g.sync.addEventListener('click', function () {
    runSync('/api/companies/' + companyId + '/agenda/google/sync', 'esta empresa');
  });
  g.syncAll.addEventListener('click', function () {
    runSync('/api/agenda/google/sync-all', 'todas as empresas');
  });

  g.disconnect.addEventListener('click', function () {
    if (!window.confirm('Desconectar o Google Calendar? Os eventos já criados no Google permanecem lá.')) return;
    googleApi('disconnect', { method: 'POST' }).then(refreshGoogle);
  });

  var googleFlag = new URLSearchParams(window.location.search).get('google');
  if (googleFlag && GOOGLE_MSG[googleFlag]) {
    state.flash = GOOGLE_MSG[googleFlag];
    window.history.replaceState(null, '', window.location.pathname);
  }

  load();
  refreshGoogle();
})();
