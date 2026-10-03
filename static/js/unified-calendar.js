(function () {
  'use strict';

  var root = document.getElementById('agRoot');
  if (!root) return;

  var $ = function (id) { return document.getElementById(id); };
  var boot = {};
  try { boot = JSON.parse($('agBoot').textContent) || {}; } catch (e) { boot = {}; }

  var cfg = {
    companyId: root.dataset.companyId,
    companyName: root.dataset.companyName || '',
    today: root.dataset.today,
    canViewAll: root.dataset.canViewAll === 'true',
    employeeId: root.dataset.employeeId || '',
    legacyUrl: root.dataset.legacyUrl || '/calendar',
    employees: boot.employees || [],
    projects: boot.projects || [],
    processes: boot.processes || [],
    personBlocks: !!boot.person_blocks
  };

  var TYPE_ORDER = ['meeting', 'project_task', 'process_instance', 'manual', 'google_event'];
  var TYPES = {
    meeting: 'Reunião', project_task: 'Atividade', process_instance: 'Instância', manual: 'Evento avulso', google_event: 'Google'
  };
  var DOW = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  var DOWL = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
  var MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  var MON3 = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  var STATUS = {
    planned: 'Planejada', in_progress: 'Em andamento', completed: 'Concluída', cancelled: 'Cancelada', pending: 'Pendente',
    paused: 'Pausada', waiting_external: 'Aguardando', failed: 'Falhou', overdue: 'Atrasada', draft: 'Rascunho', scheduled: 'Agendada',
    finished: 'Concluída', done: 'Concluída', confirmed: 'Confirmado', tentative: 'Provisório'
  };
  var HP = 44;
  var LATE_SORTS = [['old', 'Mais antigas primeiro'], ['new', 'Mais recentes primeiro'], ['type', 'Tipo'], ['source', 'Projeto ou processo']];

  /* ---------- utilidades ---------- */
  function h(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pd(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function add(s, n) { var d = pd(s); d.setDate(d.getDate() + n); return iso(d); }
  function dow(s) { return pd(s).getDay(); }
  function dnum(s) { return pd(s).getDate(); }
  function ddmm(s) { return String(dnum(s)).padStart(2, '0') + '/' + String(pd(s).getMonth() + 1).padStart(2, '0'); }
  function pad(n) { return String(n).padStart(2, '0'); }
  function hm(m) { return pad(Math.floor(m / 60)) + ':' + pad(m % 60); }
  function toMin(t) { if (!t) return null; var p = String(t).split(':'); return (+p[0]) * 60 + (+p[1] || 0); }
  function longDay(s) { var d = pd(s); return DOWL[d.getDay()] + ', ' + d.getDate() + ' de ' + MONTHS[d.getMonth()]; }
  function cap1(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function isMobile() { return window.matchMedia('(max-width: 760px)').matches; }
  function weekStart(s) { return add(s, -dow(s)); }

  function store(key, val) { try { if (val === undefined) return window.localStorage.getItem(key); window.localStorage.setItem(key, val); } catch (e) { /* sem armazenamento */ } return null; }

  /* ---------- estado ---------- */
  var S = {
    view: null,
    sel: cfg.today,
    events: [],
    loading: true,
    error: null,
    reqSeq: 0,
    rangeKey: '',
    filters: { types: { meeting: true, project_task: true, process_instance: true, manual: true, google_event: true }, scope: 'mine', employee: '' },
    late: { open: false, sort: 'old', types: { project_task: true, process_instance: true }, items: [], total: 0, loading: false, error: null },
    google: { configured: false, connected: false, needsReconnect: false, email: null, status: null },
    googleNote: null,
    blocks: { on: false, days: {}, loading: false, error: null },
    req: { tab: 'abs', loading: false, error: null, data: null, form: false, saving: false, pending: 0 },
    rules: { loading: false, error: null, items: [], form: null, saving: false, confirmDelete: null },
    team: { loading: false, error: null, data: null, key: '', filter: 'all' },
    pb: { loading: false, error: null, blocks: [], warnings: [], has: false, mode: 'list', editing: null, proposal: null, decisions: {}, saving: false, confirmRevert: false, form: null },
    move: { key: null, loading: false, error: null, options: [], item: null, applyNow: false, sel: null, reason: '', saving: false },
    sug: { date: null, loading: false, error: null, proposals: [], unplaced: [], saving: false },
    est: { total: 0, items: [], loaded: false, types: { project_task: true, process_instance: true }, picks: {}, loading: false, saving: false, error: null, skipped: {} },
    layer: null,
    filtersOpen: false,
    lastFocus: null,
    toastTimer: null
  };

  S.blocks.on = store('agenda.blocks') === '1';
  var saved = store('agenda.view');
  S.view = (saved === 'day' || saved === 'week' || saved === 'month') ? saved : (isMobile() ? 'day' : 'week');

  /* ---------- API ---------- */
  function api(path, opts) {
    opts = opts || {};
    var init = { credentials: 'same-origin', method: opts.method || 'GET', headers: {} };
    if (opts.json !== undefined) { init.method = opts.method || 'POST'; init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opts.json); }
    return fetch(path, init).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, status: r.status, body: j || {} }; });
    }).catch(function () {
      return { ok: false, status: 0, body: { message: 'Sem conexão. Verifique a internet e tente de novo.' } };
    });
  }
  function base() { return '/api/companies/' + cfg.companyId; }
  function errText(res, fallback) {
    var b = res.body || {};
    if (b.message) return b.message;
    if (typeof b.error === 'string') return b.error;
    if (b.errors) { try { return JSON.stringify(b.errors); } catch (e) { /* ignora */ } }
    if (res.status === 403) return 'Você não tem permissão para fazer isso.';
    return fallback;
  }

  /* ---------- telemetria (só o nome da ação) ---------- */
  var tq = [], tTimer = null;
  function track(event, detail) {
    tq.push({ event: event, detail: detail || null });
    if (tq.length >= 10) flush(); else if (!tTimer) tTimer = setTimeout(flush, 1500);
  }
  function flush() {
    if (tTimer) { clearTimeout(tTimer); tTimer = null; }
    if (!tq.length) return;
    var payload = { device: isMobile() ? 'mobile' : 'desktop', events: tq.splice(0, 20) };
    try {
      fetch(base() + '/agenda/telemetry', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), keepalive: true }).catch(function () { /* ignora */ });
    } catch (e) { /* ignora */ }
  }
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') flush(); });

  /* ---------- dados ---------- */
  function norm(e) {
    e.start = toMin(e.time);
    var d = e.duration_minutes || (e.start != null && e.end_time ? (toMin(e.end_time) - e.start) : null);
    e.dur = d && d > 0 ? d : null;
    e.label = e.status_label || STATUS[e.status] || cap1(String(e.status || '').replace(/_/g, ' '));
    return e;
  }
  function range() {
    var s = S.sel;
    if (S.view === 'month') {
      var first = s.slice(0, 8) + '01';
      var start = add(first, -dow(first));
      return { start: start, end: add(start, 41) };
    }
    var ws = weekStart(s);
    return { start: ws, end: add(ws, 6) };
  }
  function typesParam() {
    var t = [];
    TYPE_ORDER.forEach(function (k) {
      if (!S.filters.types[k]) return;
      if (k === 'google_event' && !S.google.connected) return;
      t.push(k);
    });
    return t.join(',');
  }
  function scopeParams() {
    var p = 'scope=' + S.filters.scope;
    if (S.filters.scope === 'all' && S.filters.employee) p += '&employee_id=' + encodeURIComponent(S.filters.employee);
    return p;
  }
  function onDay(d) {
    return S.events.filter(function (e) { return e.date === d; }).sort(function (a, b) {
      return (a.start == null ? -1 : a.start) - (b.start == null ? -1 : b.start);
    });
  }
  function lookup(key) {
    var i, list = S.events.concat(S.late.items);
    for (i = 0; i < list.length; i++) if (list[i].key === key) return list[i];
    return null;
  }

  function loadTeam() {
    var T = S.team, key = S.sel;
    T.key = key; T.loading = true; T.error = null; renderMain();
    api(base() + '/agenda/team?start=' + S.sel + '&end=' + S.sel).then(function (res) {
      if (T.key !== key) return;
      T.loading = false;
      if (!res.ok || !res.body.success) { T.error = errText(res, 'Não foi possível carregar a equipe.'); T.data = null; }
      else T.data = res.body;
      renderMain();
    });
  }
  function load() {
    if (S.view === 'team') { loadTeam(); return; }
    var r = range(), seq = ++S.reqSeq, types = typesParam();
    S.rangeKey = r.start + '|' + r.end + '|' + types + '|' + scopeParams();
    S.error = null;
    if (!types) { S.events = []; S.loading = false; renderMain(); return; }
    S.loading = true;
    renderMain();
    api(base() + '/agenda/events?start=' + r.start + '&end=' + r.end + '&types=' + types + '&' + scopeParams()).then(function (res) {
      if (seq !== S.reqSeq) return;
      S.loading = false;
      if (!res.ok || !res.body.success) { S.error = errText(res, 'Não foi possível carregar a agenda.'); S.events = []; }
      else { S.events = (res.body.events || []).map(norm); S.googleNote = res.body.google_error || null; }
      renderMain();
      renderChrome();
    });
    loadBlocks();
  }
  function loadBlocks() {
    var B = S.blocks;
    if (!B.on || S.view === 'month') { B.days = {}; B.loading = false; B.error = null; return; }
    var r = range(), key = r.start + '|' + r.end + '|' + scopeParams();
    B.loading = true; B.error = null; B.key = key;
    api(base() + '/agenda/blocks?start=' + r.start + '&end=' + r.end + '&' + scopeParams()).then(function (res) {
      if (B.key !== key) return;
      B.loading = false;
      B.days = {};
      if (!res.ok || !res.body.success) B.error = errText(res, 'Não foi possível carregar os blocos.');
      else (res.body.days || []).forEach(function (d) { B.days[d.date] = d; });
      renderMain();
    });
  }
  function ensureLoaded() {
    if (S.view === 'team') { if (S.team.key !== S.sel || !S.team.data) loadTeam(); else renderMain(); return; }
    var r = range(), key = r.start + '|' + r.end + '|' + typesParam() + '|' + scopeParams();
    if (key !== S.rangeKey) load(); else { renderMain(); }
  }
  function loadLate() {
    S.late.loading = true; S.late.error = null;
    var types = Object.keys(S.late.types).filter(function (k) { return S.late.types[k]; }).join(',');
    if (!types) { S.late.items = []; S.late.total = 0; S.late.loading = false; renderLate(); return; }
    api(base() + '/agenda/late?sort=' + S.late.sort + '&types=' + types + '&' + scopeParams()).then(function (res) {
      S.late.loading = false;
      if (!res.ok || !res.body.success) { S.late.error = errText(res, 'Não foi possível carregar as atrasadas.'); }
      else { S.late.items = (res.body.items || []).map(norm); S.late.total = res.body.total || 0; }
      renderLate();
    });
  }
  function loadGoogle() {
    api(base() + '/agenda/google/status').then(function (res) {
      var g = S.google, was = g.connected;
      if (res.ok && res.body.success) {
        g.configured = !!res.body.configured; g.connected = !!res.body.connected; g.needsReconnect = !!res.body.needs_reconnect;
        g.email = res.body.email || null; g.status = res.body.status || null;
      }
      renderChrome();
      if (g.connected !== was) load();
    });
  }

  /* ---------- feedback ---------- */
  function toast(msg, isError) {
    var el = $('agToast');
    el.textContent = msg; el.classList.toggle('is-error', !!isError); el.hidden = false;
    if (S.toastTimer) clearTimeout(S.toastTimer);
    S.toastTimer = setTimeout(function () { el.hidden = true; }, isError ? 6000 : 3500);
  }
  function keepFocus(fn) {
    var a = document.activeElement, fk = a && a.dataset ? a.dataset.fk : null;
    fn();
    if (fk) { var n = root.querySelector('[data-fk="' + fk + '"]'); if (n) n.focus(); }
  }

  /* ---------- peças de HTML ---------- */
  function dots(d) {
    var seen = {}, out = '';
    onDay(d).forEach(function (e) { if (!seen[e.type]) { seen[e.type] = 1; out += '<i class="d-' + e.type + '"></i>'; } });
    return '<span class="ag-dots" aria-hidden="true">' + out + '</span>';
  }
  function whenTxt(e) {
    if (e.start != null) return hm(e.start) + (e.dur ? '–' + hm(e.start + e.dur) : '');
    if (e.days_late != null) return 'venceu ' + ddmm(e.date);
    return 'Dia todo';
  }
  function pills(e) {
    var out = '<span class="ag-pill' + (e.status === 'overdue' ? ' ag-pill--late' : '') + '">' + h(e.label) + '</span>';
    if (e.days_late != null) out += '<span class="ag-pill ag-pill--late">' + e.days_late + (e.days_late === 1 ? ' dia' : ' dias') + ' de atraso</span>';
    return out;
  }
  function card(e) {
    return '<button type="button" class="ag-card t-' + e.type + (e.closed ? ' is-closed' : '') + '" data-key="' + h(e.key) + '">' +
      '<span class="ag-card__row"><span class="ag-tl">' + TYPES[e.type] + '</span><span class="ag-card__when">' + h(whenTxt(e)) + '</span></span>' +
      '<span class="ag-card__title">' + h(e.title) + '</span>' +
      (e.subtitle ? '<span class="ag-card__sub">' + h(e.subtitle) + '</span>' : '') +
      '<span class="ag-card__row">' + pills(e) + '</span></button>';
  }
  function ariaEv(e) { return TYPES[e.type] + ', ' + e.title + ', ' + whenTxt(e); }

  /* ---------- estimativas (Estimar em lote) ---------- */
  var EST_SHORTCUTS = [30, 60, 120, 240];
  function estTypes() { return Object.keys(S.est.types).filter(function (k) { return S.est.types[k]; }).join(','); }
  function loadEstCount() {
    api(base() + '/agenda/estimates?limit=1&' + scopeParams()).then(function (res) {
      if (!res.ok || !res.body.success) return;
      S.est.total = res.body.total || 0;
      renderEst();
    });
  }
  function renderEst() {
    var el = $('agEst'), n = S.est.total;
    if (!n) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    el.innerHTML = '<span><b>' + n + (n === 1 ? ' item sem estimativa.' : ' itens sem estimativa.') + '</b> Eles ficam fora da conta dos blocos.</span>' +
      '<button type="button" class="ag-btn ag-btn--sm" data-act="est-open" data-fk="est-open">Estimar agora</button>';
  }
  function loadEstList() {
    var E = S.est, types = estTypes();
    E.loading = true; E.error = null;
    if (!types) { E.items = []; E.loading = false; renderLayer(); return; }
    api(base() + '/agenda/estimates?types=' + types + '&' + scopeParams()).then(function (res) {
      E.loading = false; E.loaded = true;
      if (!res.ok || !res.body.success) E.error = errText(res, 'Não foi possível carregar os itens.');
      else { E.items = res.body.items || []; E.listTotal = res.body.total || 0; }
      if (S.layer && S.layer.kind === 'est') renderLayer();
    });
  }
  function estPicks() { return Object.keys(S.est.picks).filter(function (k) { return S.est.picks[k]; }); }
  function estCounter() {
    var n = estPicks().length, btn = document.querySelector('[data-act="est-save"]'), c = document.getElementById('agEstCount');
    if (c) c.textContent = n ? n + (n === 1 ? ' selecionado' : ' selecionados') : 'Escolha um tempo para cada item';
    if (btn) { btn.disabled = !n || S.est.saving; btn.textContent = S.est.saving ? 'Salvando…' : (n ? 'Salvar ' + n : 'Salvar'); }
  }
  function dueTxt(d) { return d ? 'prazo ' + ddmm(d) : 'sem prazo'; }
  function estHtml() {
    var E = S.est, out = '<h3 id="agDlg">Estimar em lote</h3><p class="ag-meta">Itens abertos sem tempo estimado, do prazo mais próximo ao mais distante. Só os itens que você escolher serão alterados.</p>';
    out += '<div class="ag-est-types">' + ['project_task', 'process_instance'].map(function (k) {
      return '<button type="button" class="ag-fchip t-' + k + '" data-act="est-type" data-k="' + k + '" aria-pressed="' + (E.types[k] !== false) + '"><span>' + (k === 'project_task' ? 'Atividades' : 'Instâncias') + '</span></button>';
    }).join('') + '</div>';
    if (E.error) out += '<p class="ag-error" role="alert">' + h(E.error) + '</p>';
    if (E.loading) out += '<p class="ag-meta">Carregando…</p>';
    else if (!E.items.length) out += '<p class="ag-state">Nenhum item sem estimativa com este filtro.</p>';
    else {
      out += '<div class="ag-est-list">' + E.items.map(function (it) {
        var picked = E.picks[it.key] || 0, why = E.skipped[it.key];
        return '<div class="ag-est-row t-' + it.type + '"><div class="ag-est-row__txt"><span class="ag-tl">' + TYPES[it.type] + '</span><b>' + h(it.title) + '</b><small>' + h(it.subtitle || '') + (it.subtitle ? ' · ' : '') + dueTxt(it.due_date) + '</small>' +
          (why ? '<small class="ag-est-row__err" role="alert">' + h(why) + '</small>' : '') + '</div><div class="ag-est-row__btns" role="group" aria-label="Tempo para ' + h(it.title) + '">' +
          EST_SHORTCUTS.map(function (m) { return '<button type="button" data-act="est-pick" data-key="' + h(it.key) + '" data-min="' + m + '" aria-pressed="' + (picked === m) + '">' + (m >= 60 ? (m / 60) + ' h' : m + ' min') + '</button>'; }).join('') + '</div></div>';
      }).join('') + '</div>' + (E.listTotal > E.items.length ? '<p class="ag-meta">Mostrando ' + E.items.length + ' de ' + E.listTotal + '.</p>' : '');
    }
    return out + '<div class="ag-btns ag-btns--sticky"><span class="ag-est-count" id="agEstCount" aria-live="polite"></span><button type="button" class="ag-btn" data-act="close">Fechar</button><button type="button" class="ag-btn ag-btn--primary" data-act="est-save" disabled>Salvar</button></div>';
  }
  function saveEstimates() {
    var E = S.est, keys = estPicks();
    if (!keys.length || E.saving) return;
    E.saving = true; E.skipped = {}; estCounter();
    var entries = keys.map(function (k) { var p = k.split(':'); return { type: p[0], id: +p[1], minutes: E.picks[k] }; });
    track('estimate_save');
    api(base() + '/agenda/estimates', { json: { entries: entries } }).then(function (res) {
      E.saving = false;
      if (!res.ok || !res.body.success) { E.error = errText(res, 'Não foi possível salvar as estimativas.'); renderLayer(); estCounter(); return; }
      var saved = res.body.saved || [], skipped = res.body.skipped || [];
      E.items = E.items.filter(function (it) { return saved.indexOf(it.key) < 0; });
      E.listTotal = Math.max(0, (E.listTotal || 0) - saved.length);
      saved.forEach(function (k) { delete E.picks[k]; });
      skipped.forEach(function (x) { E.skipped[x.key] = x.reason; });
      E.error = null;
      toast(saved.length + (saved.length === 1 ? ' estimativa salva.' : ' estimativas salvas.') + (skipped.length ? ' ' + skipped.length + ' não puderam ser salvas.' : ''), skipped.length > 0 && !saved.length);
      renderLayer(); estCounter(); loadEstCount(); loadBlocks();
    });
  }

  /* ---------- ausências, transferências e regras de recorrência (Configurar) ---------- */
  var ABS_TYPES = { vacation: 'Férias', absence: 'Ausência', medical_leave: 'Atestado médico' };
  function planEmployee() { return (S.filters.scope === 'all' && S.filters.employee) ? S.filters.employee : cfg.employeeId; }
  function empName(id) { var e = cfg.employees.filter(function (x) { return String(x.id) === String(id); })[0]; return e ? e.name : ''; }
  function dmy(iso) { return iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) + '/' + iso.slice(0, 4) : ''; }
  function statusChip(st, label) { return '<span class="ag-st ag-st--' + h(st) + '">' + h(label || st) + '</span>'; }
  function loadReq(thenRender) {
    var R = S.req; R.loading = true; R.error = null;
    api(base() + '/agenda/requests').then(function (res) {
      R.loading = false;
      if (!res.ok || !res.body.success) R.error = errText(res, 'Não foi possível carregar os pedidos.');
      else { R.data = res.body; R.pending = res.body.pending_total || 0; }
      if (S.layer && S.layer.kind === 'req') renderLayer();
    });
  }
  function reqHtml() {
    var R = S.req, d = R.data, out = '<h3 id="agDlg">Ausências e transferências</h3>';
    out += '<div class="ag-seg" role="group" aria-label="Seção"><button type="button" data-act="req-tab" data-tab="abs" aria-pressed="' + (R.tab === 'abs') + '">Ausências</button><button type="button" data-act="req-tab" data-tab="trf" aria-pressed="' + (R.tab === 'trf') + '">Transferências</button></div>';
    if (R.error) out += '<p class="ag-error" role="alert">' + h(R.error) + '</p>';
    if (R.loading && !d) return out + '<p class="ag-meta">Carregando…</p>' + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
    if (!d) return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
    if (R.tab === 'abs') {
      if (R.form) return out + absFormHtml();
      out += '<div class="ag-btns ag-btns--start"><button type="button" class="ag-btn ag-btn--primary" data-act="abs-new">+ Pedir ausência</button></div>';
      if (!d.absences.length) out += '<p class="ag-state">Nenhuma ausência registrada.</p>';
      else out += '<div class="ag-req-list">' + d.absences.map(function (a) {
        return '<div class="ag-req"><div class="ag-req__top"><b>' + h(a.type_label) + '</b>' + statusChip(a.status, a.status_label) + '</div>' +
          '<small>' + (d.is_manager && a.employee_name ? h(a.employee_name) + ' · ' : '') + dmy(a.start_date) + ' a ' + dmy(a.end_date) + '</small>' +
          (a.reason ? '<small>' + h(a.reason) + '</small>' : '') +
          (a.can_approve ? '<div class="ag-req__btns"><button type="button" class="ag-btn ag-btn--primary ag-btn--sm" data-act="abs-approve" data-id="' + a.id + '">Aprovar</button></div>' : '') + '</div>';
      }).join('') + '</div>';
    } else {
      if (!d.transfers.length) out += '<p class="ag-state">Nenhuma transferência pendente ou registrada.</p>';
      else out += '<div class="ag-req-list">' + d.transfers.map(function (t) {
        return '<div class="ag-req"><div class="ag-req__top"><b>' + h(t.item_title || 'Item') + '</b>' + statusChip(t.status, t.status_label) + '</div>' +
          '<small>' + h(t.from_name || '?') + ' → ' + h(t.to_name || '?') + '</small>' + (t.reason ? '<small>' + h(t.reason) + '</small>' : '') +
          (t.can_approve ? '<div class="ag-req__btns"><button type="button" class="ag-btn ag-btn--primary ag-btn--sm" data-act="trf-approve" data-id="' + t.id + '">Aprovar</button></div>' : '') + '</div>';
      }).join('') + '</div>' + '<p class="ag-note">Para pedir a transferência de um item, use a tela do item. Aqui você acompanha e, sendo gestor, aprova.</p>';
    }
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
  }
  function absFormHtml() {
    var emp = '';
    if (cfg.canViewAll && cfg.employees.length) {
      emp = field('Colaborador', '<select name="employee_id">' + cfg.employees.map(function (e) { return '<option value="' + e.id + '"' + (String(e.id) === String(cfg.employeeId) ? ' selected' : '') + '>' + h(e.name) + '</option>'; }).join('') + '</select>', 'absEmp');
    }
    return '<form class="ag-form" data-absform novalidate>' + emp +
      field('Tipo', '<select name="absence_type">' + Object.keys(ABS_TYPES).map(function (k) { return '<option value="' + k + '">' + ABS_TYPES[k] + '</option>'; }).join('') + '</select>', 'absType') +
      '<div class="ag-row2">' + field('De', '<input type="date" name="start_date" required>', 'absFrom') + field('Até', '<input type="date" name="end_date" required>', 'absTo') + '</div>' +
      field('Motivo (opcional)', '<textarea name="reason" rows="2" maxlength="500"></textarea>', 'absReason') +
      '<p class="ag-note">O pedido fica pendente até um gestor aprovar. O motivo só é visto por você e pelos gestores.</p>' +
      '<p class="ag-error" data-error role="alert" hidden></p><div class="ag-btns"><button type="button" class="ag-btn" data-act="abs-cancel">Cancelar</button><button type="submit" class="ag-btn ag-btn--primary" data-submit>Enviar pedido</button></div></form>';
  }
  function absSubmit(form) {
    var fd = new FormData(form), payload = { employee_id: +(fd.get('employee_id') || cfg.employeeId), absence_type: fd.get('absence_type'), start_date: fd.get('start_date'), end_date: fd.get('end_date'), reason: (fd.get('reason') || '').trim() || null };
    if (!payload.employee_id) { showError(form, 'Seu usuário não tem colaborador vinculado nesta empresa.'); return; }
    if (!payload.start_date || !payload.end_date) { showError(form, 'Informe as datas.'); return; }
    var btn = form.querySelector('[data-submit]'); btn.disabled = true;
    api(base() + '/work-journey/absences', { json: payload }).then(function (res) {
      btn.disabled = false;
      if (!res.ok || res.body.success === false) { showError(form, errText(res, 'Não foi possível enviar o pedido.')); return; }
      S.req.form = false; toast('Pedido de ausência enviado.'); loadReq();
    });
  }
  function approve(kind, id, node) {
    var url = base() + '/work-journey/' + (kind === 'abs' ? 'absences' : 'transfers') + '/' + id + '/approve';
    node.disabled = true; track('request_approve', kind === 'abs' ? 'absence' : 'transfer');
    api(url, { json: {} }).then(function (res) {
      if (!res.ok || res.body.success === false) { node.disabled = false; toast(errText(res, 'Não foi possível aprovar.'), true); return; }
      toast('Aprovado.'); loadReq();
    });
  }
  function recurTxt(r) {
    var c = r.recurrence_config || {};
    if (r.recurrence_type === 'daily') return 'Todo dia';
    if (r.recurrence_type === 'weekly') return (c.weekdays && c.weekdays.length ? c.weekdays.map(function (d) { return WD[d]; }).join(', ') : 'Segunda') + ' (toda semana)';
    if (r.recurrence_type === 'monthly') return 'Dias ' + ((c.days && c.days.length) ? c.days.join(', ') : '1') + ' do mês';
    if (r.recurrence_type === 'annual') return c.mmdd ? 'Todo ano em ' + c.mmdd.slice(3) + '/' + c.mmdd.slice(0, 2) : 'Anual';
    if (r.recurrence_type === 'sporadic') return c.date ? 'Em ' + dmy(c.date) : 'Pontual';
    return r.recurrence_type;
  }
  function loadRules() {
    var K = S.rules, emp = planEmployee(); K.loading = true; K.error = null;
    if (!emp) { K.loading = false; K.error = 'Seu usuário não tem colaborador vinculado nesta empresa.'; renderLayer(); return; }
    api(base() + '/work-journey/rules?employee_id=' + encodeURIComponent(emp)).then(function (res) {
      K.loading = false;
      if (!res.ok || !res.body.success) K.error = errText(res, 'Não foi possível carregar as regras.');
      else K.items = res.body.rules || [];
      if (S.layer && S.layer.kind === 'rules') renderLayer();
    });
  }
  function rulesHtml() {
    var K = S.rules;
    if (K.form) return ruleFormHtml();
    var out = '<h3 id="agDlg">Regras de recorrência</h3><p class="ag-meta">Obrigações que se repetem e entram sozinhas na sua agenda' + (S.filters.scope === 'all' && S.filters.employee ? ' (de ' + h(empName(S.filters.employee)) + ')' : '') + '.</p>';
    if (K.error) out += '<p class="ag-error" role="alert">' + h(K.error) + '</p>';
    if (K.loading) return out + '<p class="ag-meta">Carregando…</p>';
    out += '<div class="ag-btns ag-btns--start"><button type="button" class="ag-btn ag-btn--primary" data-act="rule-new">+ Nova regra</button></div>';
    if (!K.items.length && !K.error) out += '<p class="ag-state">Nenhuma regra ainda. Crie a primeira, por exemplo "Conferir o caixa" todo dia.</p>';
    else out += '<div class="ag-req-list">' + K.items.map(function (r) {
      return '<div class="ag-req' + (r.is_active ? '' : ' is-off') + '"><div class="ag-req__top"><b>' + h(r.title) + '</b>' + (r.is_active ? '' : statusChip('cancelled', 'Pausada')) + '</div>' +
        '<small>' + h(recurTxt(r)) + ' · ' + dur(r.estimated_minutes) + '</small>' +
        '<div class="ag-req__btns"><button type="button" class="ag-btn ag-btn--sm" data-act="rule-edit" data-id="' + r.id + '">Editar</button><button type="button" class="ag-btn ag-btn--sm ag-btn--danger" data-act="rule-del" data-id="' + r.id + '">Excluir</button></div></div>';
    }).join('') + '</div>';
    if (K.confirmDelete) out += '<div class="ag-confirm" role="alert"><span>Excluir “' + h(K.confirmDelete.title) + '”?</span><button type="button" class="ag-btn ag-btn--danger ag-btn--sm" data-act="rule-del-yes">Excluir</button><button type="button" class="ag-btn ag-btn--sm" data-act="rule-del-no">Cancelar</button></div>';
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
  }
  function ruleNew() { return { id: null, title: '', description: '', recurrence_type: 'weekly', weekdays: [0], days: '1', date: '', minutes: 60, priority: 'normal', active: true, start_date: '', end_date: '', preferred_block_id: null }; }
  function ruleFormHtml() {
    var f = S.rules.form, t = f.recurrence_type;
    var out = '<h3 id="agDlg">' + (f.id ? 'Editar regra' : 'Nova regra') + '</h3><form class="ag-form" data-ruleform novalidate>' +
      field('O que precisa ser feito', '<input type="text" name="title" maxlength="180" value="' + h(f.title) + '" required>', 'ruTitle') +
      field('Repete', '<select name="recurrence_type" data-rtype>' + [['daily', 'Todo dia'], ['weekly', 'Toda semana'], ['monthly', 'Todo mês'], ['annual', 'Todo ano'], ['sporadic', 'Uma data só']].map(function (o) { return '<option value="' + o[0] + '"' + (t === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select>', 'ruType');
    if (t === 'weekly') out += '<div class="ag-field"><span>Dias da semana</span><div class="ag-wdays" role="group" aria-label="Dias da semana">' + WD.map(function (n, i) { return '<button type="button" data-act="rule-day" data-d="' + i + '" aria-pressed="' + (f.weekdays.indexOf(i) >= 0) + '">' + n + '</button>'; }).join('') + '</div></div>';
    if (t === 'monthly') out += field('Dias do mês (separe por vírgula)', '<input type="text" name="days" inputmode="numeric" value="' + h(f.days) + '" placeholder="1, 15">', 'ruDays');
    if (t === 'annual' || t === 'sporadic') out += field(t === 'annual' ? 'Dia e mês' : 'Data', '<input type="date" name="date" value="' + h(f.date) + '" required>', 'ruDate');
    out += '<div class="ag-row2">' + field('Tempo estimado', '<select name="minutes">' + [15, 30, 45, 60, 90, 120, 180, 240].map(function (m) { return '<option value="' + m + '"' + (+f.minutes === m ? ' selected' : '') + '>' + dur(m) + '</option>'; }).join('') + '</select>', 'ruMin') +
      field('Prioridade', '<select name="priority">' + [['low', 'Baixa'], ['normal', 'Normal'], ['high', 'Alta'], ['urgent', 'Urgente']].map(function (o) { return '<option value="' + o[0] + '"' + (f.priority === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select>', 'ruPri') + '</div>' +
      '<label class="ag-check"><input type="checkbox" name="active"' + (f.active ? ' checked' : '') + '><span>Regra ativa</span></label>' +
      '<p class="ag-error" data-error role="alert" hidden></p><div class="ag-btns"><button type="button" class="ag-btn" data-act="rule-back">Cancelar</button><button type="submit" class="ag-btn ag-btn--primary" data-submit>Salvar</button></div></form>';
    return out;
  }
  function ruleSubmit(form) {
    var f = S.rules.form, fd = new FormData(form), type = fd.get('recurrence_type'), cfgR = {};
    f.title = (fd.get('title') || '').trim();
    if (!f.title) { showError(form, 'Informe o que precisa ser feito.'); return; }
    if (type === 'weekly') { if (!f.weekdays.length) { showError(form, 'Escolha ao menos um dia da semana.'); return; } cfgR = { weekdays: f.weekdays.slice().sort() }; }
    if (type === 'monthly') {
      var days = String(fd.get('days') || '').split(/[,\s]+/).map(function (x) { return parseInt(x, 10); }).filter(function (n) { return n >= 1 && n <= 31; });
      if (!days.length) { showError(form, 'Informe ao menos um dia do mês (1 a 31).'); return; }
      cfgR = { days: days };
    }
    if (type === 'annual' || type === 'sporadic') {
      var dt = fd.get('date'); if (!dt) { showError(form, 'Informe a data.'); return; }
      cfgR = type === 'annual' ? { mmdd: dt.slice(5) } : { date: dt };
    }
    var payload = { employee_id: +planEmployee(), preferred_block_id: f.preferred_block_id, title: f.title, description: f.description || null, item_type: 'manual', recurrence_type: type, recurrence_config: cfgR, estimated_minutes: +fd.get('minutes'), priority: fd.get('priority'), start_date: f.start_date || null, end_date: f.end_date || null, is_active: !!fd.get('active') };
    var btn = form.querySelector('[data-submit]'); btn.disabled = true;
    api(base() + '/work-journey/rules' + (f.id ? '/' + f.id : ''), { method: f.id ? 'PUT' : 'POST', json: payload }).then(function (res) {
      btn.disabled = false;
      if (!res.ok || res.body.success === false) { showError(form, errText(res, 'Não foi possível salvar a regra.')); return; }
      S.rules.form = null; toast('Regra salva.'); loadRules(); load();
    });
  }

  /* ---------- meus blocos (blocos da pessoa) e assistente de migração ---------- */
  var WD = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];   /* 0 = segunda, igual ao servidor */
  var PB_TYPES = [['project_task', 'Atividade'], ['process_instance', 'Instância'], ['meeting', 'Reunião'], ['manual', 'Evento avulso']];
  var PB_MODES = { operational: 'Operacional (recebe tarefas)', reserved_full: 'Capacidade ocupada', buffer: 'Vazio / Buffer (urgências)' };
  function wdTxt(list) {
    if (!list || !list.length) return '';
    if (list.length === 7) return 'Todos os dias';
    if (list.join() === '0,1,2,3,4') return 'Seg a Sex';
    return list.map(function (d) { return WD[d]; }).join(', ');
  }
  function pbApi(path, opts) { return api('/api/agenda/person-blocks' + path, opts); }
  function loadPb() {
    var P = S.pb; P.loading = true; P.error = null;
    pbApi('').then(function (res) {
      P.loading = false;
      if (!res.ok || !res.body.success) P.error = errText(res, 'Não foi possível carregar seus blocos.');
      else { P.blocks = res.body.blocks || []; P.warnings = res.body.warnings || []; P.has = !!res.body.has_blocks; cfg.personBlocks = P.has; P.mode = P.has ? 'list' : 'intro'; }
      if (S.layer && S.layer.kind === 'pblocks') renderLayer();
    });
  }
  function pbAfterChange() { loadPb(); loadBlocks(); renderChrome(); }
  function pbWarnHtml(list) {
    return list && list.length ? '<div class="ag-warnbox" role="status"><b>Atenção:</b> ' + list.map(function (w) { return h(w.message); }).join(' ') + ' Isso não impede o uso.</div>' : '';
  }
  function pbFormHtml() {
    var f = S.pb.form, out = '<h3 id="agDlg">' + (f.id ? 'Editar bloco' : 'Novo bloco') + '</h3><form class="ag-form" data-pbform novalidate>';
    out += field('Nome', '<input type="text" name="name" maxlength="160" value="' + h(f.name) + '" required>', 'pbName');
    out += '<div class="ag-row2">' + field('Início', '<input type="time" name="start" value="' + h(f.start) + '" required>', 'pbStart') + field('Fim', '<input type="time" name="end" value="' + h(f.end) + '" required>', 'pbEnd') + '</div>';
    out += field('Modo', '<select name="mode">' + Object.keys(PB_MODES).map(function (k) { return '<option value="' + k + '"' + (f.mode === k ? ' selected' : '') + '>' + h(PB_MODES[k]) + '</option>'; }).join('') + '</select>', 'pbMode');
    out += '<div class="ag-field"><span>Dias da semana</span><div class="ag-wdays" role="group" aria-label="Dias da semana">' + WD.map(function (n, i) {
      return '<button type="button" data-act="pb-day" data-d="' + i + '" aria-pressed="' + (f.weekdays.indexOf(i) >= 0) + '">' + n + '</button>';
    }).join('') + '</div></div>';
    out += '<div class="ag-field"><span>Tipos preferidos <small>(só sugestão; o bloco aceita qualquer item)</small></span><div class="ag-est-types">' + PB_TYPES.map(function (t) {
      return '<button type="button" class="ag-fchip" data-act="pb-type" data-t="' + t[0] + '" aria-pressed="' + (f.types.indexOf(t[0]) >= 0) + '"><span>' + t[1] + '</span></button>';
    }).join('') + '</div></div>';
    out += '<p class="ag-error" data-error role="alert" hidden></p><div class="ag-btns"><button type="button" class="ag-btn" data-act="pb-back">Cancelar</button><button type="submit" class="ag-btn ag-btn--primary" data-submit>Salvar</button></div></form>';
    return out;
  }
  function pbListHtml() {
    var P = S.pb, out = '<h3 id="agDlg">Meus blocos</h3><p class="ag-meta">Valem para todas as empresas em que você atua. Eles organizam o seu dia; nada é bloqueado.</p>' + pbWarnHtml(P.warnings);
    if (!P.blocks.length) out += '<p class="ag-state">Você ainda não tem blocos. Crie o primeiro.</p>';
    else out += '<div class="ag-pb-list">' + P.blocks.map(function (b) {
      return '<div class="ag-pb' + (b.is_active ? '' : ' is-off') + '"><div class="ag-pb__txt"><b>' + h(b.name) + '</b><small>' + h(b.start) + '–' + h(b.end) + ' · ' + h(wdTxt(b.weekdays)) + ' · ' + h((PB_MODES[b.mode] || '').split(' (')[0]) + '</small></div>' +
        '<div class="ag-pb__btns"><button type="button" class="ag-btn ag-btn--sm" data-act="pb-edit" data-id="' + b.id + '">Editar</button><button type="button" class="ag-btn ag-btn--sm ag-btn--danger" data-act="pb-del" data-id="' + b.id + '">Excluir</button></div></div>';
    }).join('') + '</div>';
    out += '<div data-confirm>' + (P.confirmDelete ? '<div class="ag-confirm" role="alert"><span>Excluir “' + h(P.confirmDelete.name) + '”?</span><button type="button" class="ag-btn ag-btn--danger ag-btn--sm" data-act="pb-del-yes">Excluir</button><button type="button" class="ag-btn ag-btn--sm" data-act="pb-del-no">Cancelar</button></div>' : '') + '</div>';
    out += '<div class="ag-btns"><button type="button" class="ag-btn ag-btn--primary" data-act="pb-new" data-autofocus>+ Novo bloco</button></div>';
    out += '<details class="ag-revert"><summary>Voltar aos blocos por empresa</summary><p class="ag-meta">Seus blocos por empresa continuam guardados. Os itens que você colocou nos blocos da pessoa voltam a ser sugeridos pelo sistema.</p>' +
      (P.confirmRevert ? '<div class="ag-confirm" role="alert"><span>Voltar agora?</span><button type="button" class="ag-btn ag-btn--danger ag-btn--sm" data-act="pb-revert-yes">Voltar</button><button type="button" class="ag-btn ag-btn--sm" data-act="pb-revert-no">Cancelar</button></div>' : '<button type="button" class="ag-btn ag-btn--sm" data-act="pb-revert">Voltar aos blocos por empresa</button>') + '</details>';
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
  }
  function pbIntroHtml() {
    return '<h3 id="agDlg">Meus blocos</h3><p class="ag-meta">Hoje seus blocos são cadastrados <b>por empresa</b>, e a mesma hora pode aparecer duas vezes. Com <b>blocos da pessoa</b> você tem um dia só, válido para todas as empresas.</p>' +
      '<ul class="ag-bullets"><li>O assistente monta uma proposta a partir dos seus blocos atuais e agrupa os repetidos (como “Almoço”).</li><li>Nada é criado sem a sua confirmação, bloco a bloco.</li><li>Você pode voltar aos blocos por empresa quando quiser.</li></ul>' +
      (S.pb.error ? '<p class="ag-error" role="alert">' + h(S.pb.error) + '</p>' : '') +
      '<div class="ag-btns"><button type="button" class="ag-btn" data-act="pb-new">Criar do zero</button><button type="button" class="ag-btn ag-btn--primary" data-act="pb-proposal" data-autofocus>Ver proposta</button></div>';
  }
  function pbProposalHtml() {
    var P = S.pb, pr = P.proposal || { proposals: [] }, out = '<h3 id="agDlg">Proposta de blocos</h3>';
    if (P.loading) return out + '<p class="ag-meta">Montando a proposta…</p>';
    if (P.error) out += '<p class="ag-error" role="alert">' + h(P.error) + '</p>';
    if (!pr.proposals.length) return out + '<p class="ag-state">Não encontramos blocos por empresa para propor. Você pode criar do zero.</p><div class="ag-btns"><button type="button" class="ag-btn" data-act="pb-back">Voltar</button><button type="button" class="ag-btn ag-btn--primary" data-act="pb-new">Criar do zero</button></div>';
    out += '<p class="ag-meta">Encontramos ' + pr.legacy_count + ' blocos em ' + pr.companies + (pr.companies === 1 ? ' empresa' : ' empresas') + '. Confirme os que quer manter; você pode ajustar nome e horário.</p><div class="ag-pb-list">';
    pr.proposals.forEach(function (x) {
      var d = P.decisions[x.id] || (P.decisions[x.id] = { accept: true, name: x.name, start: x.start, end: x.end });
      out += '<div class="ag-pb ag-pb--prop' + (d.accept ? '' : ' is-off') + '"><label class="ag-check"><input type="checkbox" data-pdec="accept" data-pid="' + x.id + '"' + (d.accept ? ' checked' : '') + '><span>Criar este bloco</span></label>' +
        '<div class="ag-row3"><input type="text" aria-label="Nome" data-pdec="name" data-pid="' + x.id + '" value="' + h(d.name) + '" maxlength="160"><input type="time" aria-label="Início" data-pdec="start" data-pid="' + x.id + '" value="' + h(d.start) + '"><input type="time" aria-label="Fim" data-pdec="end" data-pid="' + x.id + '" value="' + h(d.end) + '"></div>' +
        '<small>' + h(wdTxt(x.weekdays)) + ' · ' + h((PB_MODES[x.mode] || '').split(' (')[0]) + '</small>' +
        '<small class="ag-pb__src">' + (x.merged ? 'Junta: ' : 'Vem de: ') + x.sources.map(function (sr) { return h((sr.company || '') + ' ' + sr.start + '–' + sr.end); }).join('; ') + '</small>' +
        (x.note ? '<small class="ag-pb__note">' + h(x.note) + '</small>' : '') + '</div>';
    });
    out += '</div><p class="ag-error" data-error role="alert" hidden></p><div class="ag-btns"><button type="button" class="ag-btn" data-act="pb-back">Voltar</button><button type="button" class="ag-btn ag-btn--primary" data-act="pb-apply"' + (P.saving ? ' disabled' : '') + '>' + (P.saving ? 'Criando…' : 'Criar meus blocos') + '</button></div>';
    return out;
  }
  function pbHtml() {
    var P = S.pb;
    if (P.loading && !P.blocks.length && P.mode !== 'proposal') return '<h3 id="agDlg">Meus blocos</h3><p class="ag-meta">Carregando…</p>';
    if (P.mode === 'form') return pbFormHtml();
    if (P.mode === 'proposal') return pbProposalHtml();
    if (P.error && !P.blocks.length && !P.has) return '<h3 id="agDlg">Meus blocos</h3><p class="ag-error" role="alert">' + h(P.error) + '</p><div class="ag-btns"><button type="button" class="ag-btn" data-act="close" data-autofocus>Fechar</button></div>';
    return P.has ? pbListHtml() : pbIntroHtml();
  }
  function pbNewForm() { return { id: null, name: '', start: '08:00', end: '12:00', mode: 'operational', weekdays: [0, 1, 2, 3, 4], types: [] }; }
  function pbSubmit(form) {
    var f = S.pb.form, fd = new FormData(form), payload = { name: fd.get('name'), start: fd.get('start'), end: fd.get('end'), mode: fd.get('mode'), weekdays: f.weekdays, preferred_item_types: f.types };
    var btn = form.querySelector('[data-submit]'); btn.disabled = true;
    var req = f.id ? pbApi('/' + f.id, { method: 'PATCH', json: payload }) : pbApi('', { json: payload });
    req.then(function (res) {
      btn.disabled = false;
      if (!res.ok || !res.body.success) { showError(form, errText(res, 'Não foi possível salvar o bloco.')); return; }
      track('blocks_edit_save', f.id ? 'update' : 'create');
      S.pb.mode = 'list'; S.pb.form = null;
      toast('Bloco salvo.' + (res.body.warnings && res.body.warnings.length ? ' Há blocos que se sobrepõem.' : ''));
      S.blocks.on = true; store('agenda.blocks', '1');
      pbAfterChange();
    });
  }
  function pbApply() {
    var P = S.pb, decisions = Object.keys(P.decisions).map(function (id) { var d = P.decisions[id]; return { id: +id, accept: d.accept, name: d.name, start: d.start, end: d.end }; });
    if (!decisions.some(function (d) { return d.accept; })) { var eb = $('agLayer').querySelector('[data-error]'); eb.textContent = 'Confirme ao menos um bloco.'; eb.hidden = false; return; }
    P.saving = true; renderLayer(); track('migration_apply');
    pbApi('/migration/apply', { json: { decisions: decisions } }).then(function (res) {
      P.saving = false;
      if (!res.ok || !res.body.success) { P.error = errText(res, 'Não foi possível criar os blocos.'); renderLayer(); return; }
      P.error = null; P.mode = 'list';
      toast((res.body.created || []).length + ' blocos criados' + (res.body.routines_rebound ? ' e ' + res.body.routines_rebound + ' rotinas reapontadas' : '') + '.');
      S.blocks.on = true; store('agenda.blocks', '1');
      pbAfterChange();
    });
  }

  /* ---------- mover para um bloco e sugestão de distribuição ---------- */
  function planQs() { return scopeParams(); }
  function loadMove() {
    var M = S.move, e = lookup(M.key);
    if (!e) return;
    M.loading = true; M.error = null; M.options = []; M.sel = null; M.reason = '';
    api(base() + '/agenda/move-options?type=' + e.type + '&id=' + e.id + '&' + planQs()).then(function (res) {
      M.loading = false;
      if (!res.ok || !res.body.success) M.error = errText(res, 'Não foi possível carregar os destinos.');
      else { M.options = res.body.options || []; M.item = res.body.item || null; M.applyNow = !!res.body.due_change_applies_now; }
      if (S.layer && S.layer.kind === 'move') renderLayer();
    });
  }
  function optLabel(o) { return cap1(DOW[dow(o.date)].toLowerCase()) + ' ' + ddmm(o.date) + ' · ' + o.block_name + ' ' + o.start + '–' + o.end; }
  function moveHtml() {
    var M = S.move, e = lookup(M.key), out = '<h3 id="agDlg">Mover para um bloco</h3>';
    if (e) out += '<p class="ag-meta"><b>' + h(e.title) + '</b>' + (M.item && M.item.without_estimate ? ' · sem estimativa (não altera a conta)' : (M.item ? ' · ' + dur(M.item.estimated_minutes) : '')) + '</p>';
    if (M.error) out += '<p class="ag-error" role="alert">' + h(M.error) + '</p>';
    if (M.loading) out += '<p class="ag-meta">Buscando os melhores blocos…</p>';
    else if (!M.options.length && !M.error) out += '<p class="ag-state">Nenhum bloco disponível nos próximos 14 dias para este tipo de item.' + (e && e.type === 'process_instance' ? ' Instâncias só se movem entre blocos do mesmo dia.' : '') + '</p>';
    else {
      out += '<div class="ag-opts" role="list">' + M.options.map(function (o, i) {
        var sel = M.sel === i;
        var card = '<div class="ag-opt' + (sel ? ' is-sel' : '') + '" role="listitem"><button type="button" class="ag-opt__main" data-act="move-pick" data-i="' + i + '" aria-pressed="' + sel + '">' +
          '<span class="ag-opt__title">' + h(optLabel(o)) + '</span><span class="ag-opt__states">' + sigChip(o.before, true) + '<span aria-hidden="true">→</span><span class="sr-only"> ficaria </span>' + sigChip(o.after, true) +
          (o.changes_due_date ? '<span class="ag-tag">Muda o prazo</span>' : '') + (!o.fits ? '<span class="ag-tag ag-tag--warn">Passa da capacidade</span>' : '') + '</span></button>';
        if (sel) {
          if (o.needs_reason) {
            card += '<div class="ag-opt__form"><p class="ag-note">' + (M.applyNow ? 'Você pode alterar este prazo: a mudança vale na hora.' : 'Você não pode alterar este prazo sozinho: o pedido segue para aprovação e o item fica onde está até a decisão.') + '</p>' +
              '<label class="ag-field" for="agMoveReason">Motivo da mudança de prazo<textarea id="agMoveReason" rows="2" data-move-reason maxlength="500" placeholder="Por que mudar o prazo?">' + h(M.reason) + '</textarea></label>';
          } else card += '<div class="ag-opt__form">';
          card += '<p class="ag-error" data-move-error role="alert" hidden></p><button type="button" class="ag-btn ag-btn--primary" data-act="move-confirm"' + (M.saving ? ' disabled' : '') + '>' + (M.saving ? 'Movendo…' : (o.needs_reason ? (M.applyNow ? 'Mudar prazo e mover' : 'Pedir mudança de prazo') : 'Mover para cá')) + '</button></div>';
        }
        return card + '</div>';
      }).join('') + '</div>';
    }
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close" data-autofocus>Fechar</button></div>';
  }
  function moveConfirm() {
    var M = S.move, o = M.options[M.sel], e = lookup(M.key);
    if (!o || !e || M.saving) return;
    var box = $('agLayer').querySelector('[data-move-error]'), rs = $('agLayer').querySelector('[data-move-reason]');
    M.reason = rs ? rs.value.trim() : '';
    if (o.needs_reason && !M.reason) { box.textContent = 'Informe o motivo da mudança de prazo.'; box.hidden = false; rs.focus(); return; }
    M.saving = true; renderLayer();
    track('move_confirm', o.needs_reason ? 'other_day' : 'same_day');
    api(base() + '/agenda/assign?' + planQs(), { json: { type: e.type, id: e.id, date: o.date, block_id: o.block_id, reason: M.reason || null } }).then(function (res) {
      M.saving = false;
      if (!res.ok || !res.body.success) { M.error = errText(res, 'Não foi possível mover o item.'); renderLayer(); return; }
      S.layer = null; renderLayer();
      toast(res.body.message || 'Item movido.');
      load(); loadLate(); loadEstCount();
    });
  }
  function loadSug() {
    var G = S.sug;
    G.loading = true; G.error = null;
    api(base() + '/agenda/suggestions?date=' + G.date + '&' + planQs()).then(function (res) {
      G.loading = false;
      if (!res.ok || !res.body.success) G.error = errText(res, 'Não foi possível calcular a sugestão.');
      else { G.proposals = res.body.proposals || []; G.unplaced = res.body.unplaced || []; }
      if (S.layer && S.layer.kind === 'sug') renderLayer();
    });
  }
  function sugHtml() {
    var G = S.sug, out = '<h3 id="agDlg">Sugerir distribuição</h3><p class="ag-meta">' + h(cap1(longDay(G.date))) + '. O sistema só sugere; nada é bloqueado. Você pode aceitar ou desfazer depois.</p>';
    if (G.error) out += '<p class="ag-error" role="alert">' + h(G.error) + '</p>';
    if (G.loading) out += '<p class="ag-meta">Calculando…</p>';
    else if (!G.proposals.length && !G.unplaced.length && !G.error) out += '<p class="ag-state">Não há itens deste dia esperando um bloco.</p>';
    else {
      if (G.proposals.length) out += '<div class="ag-sug-list">' + G.proposals.map(function (p) { return '<div class="ag-sug-row"><b>' + h(p.title) + '</b><small>' + dur(p.minutes) + ' → ' + h(p.block_name) + '</small></div>'; }).join('') + '</div>';
      if (G.unplaced.length) out += '<p class="ag-sec">Não cabem (ficam sem bloco)</p><div class="ag-sug-list">' + G.unplaced.map(function (p) { return '<div class="ag-sug-row"><b>' + h(p.title) + '</b><small>' + dur(p.minutes) + '</small></div>'; }).join('') + '</div>';
    }
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close" data-autofocus>Cancelar</button>' +
      '<button type="button" class="ag-btn ag-btn--primary" data-act="sug-apply"' + (!G.proposals.length || G.saving ? ' disabled' : '') + '>' + (G.saving ? 'Aplicando…' : 'Aplicar sugestão') + '</button></div>';
  }
  function sugAction(action, doneMsg) {
    var d = S.sel;
    api(base() + '/agenda/suggestions?' + planQs(), { json: { action: action, date: d } }).then(function (res) {
      S.sug.saving = false;
      if (!res.ok || !res.body.success) { toast(errText(res, 'Não foi possível concluir.'), true); return; }
      var b = res.body;
      S.layer = null; renderLayer();
      toast(doneMsg(b));
      loadBlocks();
    });
  }

  /* ---------- blocos e sinais (somente leitura; nunca bloqueiam) ---------- */
  function bday(d) { return S.blocks.on ? (S.blocks.days[d] || null) : null; }
  function dur(m) { m = Math.max(0, Math.round(m)); var hh = Math.floor(m / 60), mm = m % 60; return hh && mm ? hh + 'h' + pad(mm) : (hh ? hh + 'h' : mm + 'min'); }
  function sigChip(sig, small) {
    if (!sig || sig.state === 'none' || !sig.label) return '';
    return '<span class="ag-sig ag-sig--' + sig.state + (small ? ' ag-sig--sm' : '') + '">' + h(sig.label) + '</span>';
  }
  function dayBar(bd) {
    var d = bd.day;
    if (!d || d.state === 'none') return '<p class="ag-bk-day"><b>Sem expediente</b></p>';
    var pct = d.capacity_minutes ? Math.min(100, Math.round(d.consumed_minutes / d.capacity_minutes * 100)) : 0;
    return '<div class="ag-bk-day"><div class="ag-bk-day__txt"><b>Dia</b> ' + dur(d.consumed_minutes) + ' de ' + dur(d.capacity_minutes) + ' ' + sigChip(d, true) +
      '</div><div class="ag-bar" role="img" aria-label="Ocupação do dia: ' + dur(d.consumed_minutes) + ' de ' + dur(d.capacity_minutes) + '"><i class="ag-bar--' + d.state + '" style="width:' + pct + '%"></i></div></div>';
  }
  var ITEM_TAG = { project_task: ['Atividade', 'act'], process_instance: ['Instância', 'inst'], manual: ['Avulso', 'man'], meeting: ['Reunião', 'meet'] };
  var EVENT_TAG = { google_event: ['Google', 'goog'], meeting: ['Reunião', 'meet'], manual: ['Evento avulso', 'man'] };
  function blockState(d) {
    var B = S.blocks;
    if (!B.on) return { html: '' };
    if (B.loading && !B.days[d]) return { html: '<p class="ag-note">Carregando blocos…</p>' };
    if (B.error) return { html: '<p class="ag-note">' + h(B.error) + '</p>' };
    var bd = B.days[d];
    if (!bd) return { html: '<p class="ag-note">Escolha um colaborador para ver os blocos.</p>' };
    return { bd: bd };
  }
  function blocksSummary(d) {
    var st = blockState(d);
    if (!st.bd) return st.html;
    var bd = st.bd, out = '<section class="ag-bk ag-bk--sum" aria-label="Resumo do dia">' + dayBar(bd), sc = bd.day.suggested_count || 0;
    if (sc) out += '<div class="ag-sugbar" role="status"><span><b>' + sc + (sc === 1 ? ' item sugerido' : ' itens sugeridos') + '</b> pelo sistema.</span><span class="ag-sugbar__btns"><button type="button" class="ag-btn ag-btn--sm" data-act="sug-accept">Aceitar</button><button type="button" class="ag-btn ag-btn--sm" data-act="sug-undo">Desfazer sugestão</button></span></div>';
    else if (bd.day.state !== 'none') out += '<div class="ag-sugbar"><span>Itens do dia sem bloco?</span><button type="button" class="ag-btn ag-btn--sm" data-act="sug-open">Sugerir distribuição</button></div>';
    return out + '</section>';
  }
  function legendHtml() {
    return '<p class="ag-legend" aria-label="Legenda"><span><i class="k-act"></i>Atividade</span><span><i class="k-inst"></i>Instância</span><span><i class="k-goog"></i>Google</span><span><i class="k-meet"></i>Reunião</span></p>';
  }
  function blockRow(b) {
    var out = '<div class="ag-bk-row"><span class="ag-bk-row__time">' + h(b.start) + '–' + h(b.end) + '</span><span class="ag-bk-row__name">' + h(b.name) + '</span>' +
      sigChip(b.signal) + (b.without_estimate ? '<span class="ag-bk-row__warn">' + b.without_estimate + ' sem estimativa</span>' : '');
    var li = '';
    (b.events || []).forEach(function (e) {
      var t = EVENT_TAG[e.type] || ['Evento', 'man'], part = e.total_minutes && e.minutes < e.total_minutes ? dur(e.minutes) + ' de ' + dur(e.total_minutes) + ' neste bloco' : dur(e.minutes);
      li += '<li class="ev ' + t[1] + '"><span class="ag-ttag">' + t[0] + '</span><span class="t">' + h(e.title || 'Compromisso') + '</span><small>' + h(e.start) + (e.end ? '–' + h(e.end) : '') + ' · ' + part + '</small></li>';
    });
    (b.items || []).forEach(function (it) {
      var t = ITEM_TAG[it.type] || ['Item', 'act'];
      li += '<li class="it ' + t[1] + '"><span class="ag-ttag">' + t[0] + '</span><span class="t">' + h(it.title) + '</span><small>' + (it.minutes ? dur(it.minutes) : 'sem estimativa') + (it.company ? ' · ' + h(it.company) : '') + (it.suggested ? ' · sugerido' : '') + '</small></li>';
    });
    if (li) out += '<ul class="ag-bk-items">' + li + '</ul>';
    return out + '</div>';
  }
  function blocksList(d) {
    var st = blockState(d);
    if (!st.bd) return '';
    return '<div class="ag-bk-list">' + st.bd.blocks.map(blockRow).join('') + '</div>' + legendHtml();
  }
  function blocksMobile(d) {   /* celular: resumo + lista aberta */
    var st = blockState(d);
    if (!st.bd) return st.html;
    return blocksSummary(d) + '<section class="ag-bk" aria-label="Blocos do dia">' + blocksList(d) + '</section>';
  }
  function blocksPanel(d) {    /* computador: lista recolhida abaixo da grade */
    var st = blockState(d);
    if (!st.bd) return '';
    var n = st.bd.blocks.length;
    return '<details class="ag-panel"><summary>Blocos do dia <span class="ag-panel__n">' + n + '</span>' + sigChip(st.bd.day, true) + '</summary>' + blocksList(d) + '</details>' +
      '<p class="ag-note">Passe o mouse numa faixa da trilha para ver o nome e o sinal do bloco. A lista traz os itens e os eventos de cada um.</p>';
  }
  /* trilha lateral (Dia): uma faixa por bloco, lado a lado quando se sobrepõem */
  function railLanes(blocks) {
    var ends = [], items = [];
    blocks.forEach(function (b) {
      var l = 0; while (ends[l] !== undefined && ends[l] > b.start_minutes) l++;
      ends[l] = b.end_minutes; items.push({ b: b, lane: l });
    });
    return { items: items, n: ends.length };
  }
  function overlapIds(blocks) {
    var ids = {};
    blocks.forEach(function (a, i) { blocks.forEach(function (c, j) {
      if (i < j && a.mode === 'operational' && c.mode === 'operational' && a.start_minutes < c.end_minutes && c.start_minutes < a.end_minutes) { ids[a.id] = 1; ids[c.id] = 1; }
    }); });
    return ids;
  }
  function railInfo(x, H0, H1) {
    var bd = bday(x);
    if (!bd || !bd.blocks.length) return null;
    var ln = railLanes(bd.blocks), warn = overlapIds(bd.blocks), out = '';
    ln.items.forEach(function (it) {
      var b = it.b, s0 = Math.max(b.start_minutes, H0), e0 = Math.min(b.end_minutes, H1);
      if (e0 <= s0) return;
      var state = (b.signal && b.signal.state) || 'none', tip = b.name + ' · ' + b.start + '–' + b.end + (b.signal && b.signal.label ? ' · ' + b.signal.label : ' · Capacidade ocupada');
      out += '<div class="ag-lane ag-lane--' + state + (warn[b.id] ? ' has-warn' : '') + '" style="top:' + ((s0 - H0) / 60 * HP + 1) + 'px;height:' + ((e0 - s0) / 60 * HP - 2) + 'px;left:' + (3 + it.lane * 17) + 'px" title="' + h(tip) + (warn[b.id] ? ' · sobreposto a outro bloco' : '') + '" role="img" aria-label="' + h(tip) + '"><span>' + h(b.name) + '</span></div>';
    });
    return { html: out, w: Math.max(26, 6 + ln.n * 17) };
  }
  /* Semana: marcas finas na borda da coluna, sem rótulos */
  function weekEdges(x, H0, H1) {
    var bd = bday(x), out = '';
    if (!bd) return '';
    bd.blocks.forEach(function (b) {
      var s0 = Math.max(b.start_minutes, H0), e0 = Math.min(b.end_minutes, H1);
      if (e0 <= s0) return;
      out += '<div class="ag-wedge ag-wedge--' + ((b.signal && b.signal.state) || 'none') + '" style="top:' + ((s0 - H0) / 60 * HP + 1) + 'px;height:' + ((e0 - s0) / 60 * HP - 2) + 'px" title="' + h(b.name + (b.signal && b.signal.label ? ' · ' + b.signal.label : '')) + '" aria-hidden="true"></div>';
    });
    return out;
  }
  function miniBar(day) {
    if (!day || day.state === 'none' || !day.capacity_minutes) return '';
    var pct = Math.min(100, Math.round(day.consumed_minutes / day.capacity_minutes * 100));
    return '<div class="ag-bar ag-bar--mini" role="img" aria-label="Ocupação: ' + dur(day.consumed_minutes) + ' de ' + dur(day.capacity_minutes) + '"><i class="ag-bar--' + day.state + '" style="width:' + pct + '%"></i></div>';
  }

  /* ---------- equipe (gestor) ---------- */
  function teamCard(e) {
    var d = e.days[0], day = d.day, cap = day.capacity_minutes || 0;
    var mine = cap ? Math.min(100, Math.round(day.this_company_minutes / cap * 100)) : 0;
    var others = cap ? Math.min(100 - mine, Math.round(day.other_companies_minutes / cap * 100)) : 0;
    var head = '<div class="ag-tm__head"><b>' + h(e.name) + '</b><span class="ag-tag">' + (e.source === 'person' ? 'Blocos da pessoa' : 'Por empresa') + '</span>' + sigChip(day, true) + '</div>';
    var bar = cap ? '<div class="ag-tbar" role="img" aria-label="Ocupação: ' + dur(day.consumed_minutes) + ' de ' + dur(cap) + ', ' + dur(day.this_company_minutes) + ' desta empresa e ' + dur(day.other_companies_minutes) + ' de outras"><i class="is-mine" style="width:' + mine + '%"></i><i class="is-other" style="width:' + others + '%"></i></div>' +
      '<p class="ag-tm__sum">' + dur(day.consumed_minutes) + ' de ' + dur(cap) + ' · <span class="k-mine">desta empresa ' + dur(day.this_company_minutes) + '</span>' + (e.source === 'person' ? ' · <span class="k-other">outras empresas ' + dur(day.other_companies_minutes) + '</span>' : '') + '</p>' : '<p class="ag-tm__sum">Sem expediente neste dia.</p>';
    var rows = d.blocks.map(function (b) {
      var items = b.items.length ? '<ul class="ag-bk-items">' + b.items.map(function (it) { return '<li>' + h(it.title) + ' <small>' + (it.minutes ? dur(it.minutes) : 'sem estimativa') + '</small></li>'; }).join('') + '</ul>' : '';
      var split = b.mode === 'operational' ? '<small>desta empresa ' + dur(b.this_company_minutes) + (e.source === 'person' ? ' · outras empresas ' + dur(b.other_companies_minutes) : '') + (b.without_estimate ? ' · ' + b.without_estimate + ' sem estimativa' : '') + '</small>' : '';
      return '<div class="ag-bk-row"><span class="ag-bk-row__time">' + h(b.start) + '–' + h(b.end) + '</span><span class="ag-bk-row__name">' + h(b.name) + '</span>' + sigChip(b.signal) + split + items + '</div>';
    }).join('');
    var more = d.blocks.length ? '<details class="ag-tm__more"><summary>Ver blocos (' + d.blocks.length + ')</summary>' + rows + '</details>' : '';
    return '<article class="ag-tm">' + head + bar + more + '</article>';
  }
  function teamHtml() {
    var T = S.team;
    if (T.loading && !T.data) return '<p class="ag-state">Carregando a equipe…</p>';
    if (T.error) return '<div class="ag-state ag-state--error" role="alert"><p>' + h(T.error) + '</p><button type="button" class="ag-btn" data-act="retry">Tentar de novo</button></div>';
    var list = (T.data && T.data.employees) || [], over = 0, free = 0;
    list.forEach(function (e) { var st = e.days[0].day.state; if (st === 'over') over++; else if (st === 'free') free++; });
    var shown = list.filter(function (e) { var st = e.days[0].day.state; return T.filter === 'all' || st === T.filter; });
    var chips = [['all', 'Todos (' + list.length + ')'], ['over', 'Acima (' + over + ')'], ['free', 'Com folga (' + free + ')']].map(function (c) {
      return '<button type="button" class="ag-fchip" data-act="team-filter" data-f="' + c[0] + '" aria-pressed="' + (T.filter === c[0]) + '"><span>' + c[1] + '</span></button>';
    }).join('');
    var note = '<p class="ag-note">Você vê o total de cada pessoa em todas as empresas. Itens de outras empresas aparecem só como tempo, sem título.</p>';
    return '<div class="ag-view ag-team"><div class="ag-est-types" role="group" aria-label="Filtrar equipe">' + chips + '</div>' + note +
      (shown.length ? '<div class="ag-tm-grid">' + shown.map(teamCard).join('') + '</div>' : '<p class="ag-state">Nenhum colaborador neste filtro.</p>') + '</div>';
  }

  /* ---------- visões ---------- */
  function dayMobile() {
    var d = S.sel, strip = '<div class="ag-strip" role="group" aria-label="Dias da semana">';
    for (var i = 0; i < 7; i++) {
      var x = add(weekStart(d), i);
      strip += '<button type="button" data-sel="' + x + '" aria-pressed="' + (x === d) + '"' + (x === cfg.today ? ' class="is-today" aria-current="date"' : '') +
        ' aria-label="' + h(longDay(x)) + '"><small>' + DOW[i] + '</small><b>' + dnum(x) + '</b>' + dots(x) + '</button>';
    }
    strip += '</div>';
    var list = onDay(d), all = list.filter(function (e) { return e.start == null; }), tm = list.filter(function (e) { return e.start != null; });
    var body = '';
    if (!list.length) body = '<p class="ag-state">Nada marcado para este dia. Toque em Criar.</p>';
    if (all.length) body += '<p class="ag-sec">Dia todo</p><div class="ag-cards">' + all.map(card).join('') + '</div>';
    if (tm.length) body += '<p class="ag-sec">Horários</p><div class="ag-cards">' + tm.map(card).join('') + '</div>';
    return strip + '<div class="ag-bk-m">' + blocksMobile(d) + '</div><div class="ag-cards--day">' + body + '</div>';
  }
  function weekMobile() {
    var out = '<div class="ag-weeklist">', ws = weekStart(S.sel);
    for (var i = 0; i < 7; i++) {
      var x = add(ws, i), l = onDay(x);
      out += '<button type="button" class="ag-wrow' + (x === cfg.today ? ' is-today' : '') + '" data-go="' + x + '"><span class="ag-wrow__head">' + DOW[i] + ' ' + dnum(x) + dots(x) +
        (bday(x) ? sigChip(bday(x).day, true) : '') + '<small>' + l.length + (l.length === 1 ? ' item' : ' itens') + '</small></span>' +
        '<span class="ag-wrow__txt">' + (l.length ? h(l.slice(0, 2).map(function (e) { return e.title; }).join(' · ')) : 'Livre') + '</span></button>';
    }
    return out + '</div>';
  }
  function monthMobile() {
    var d = S.sel, r = range(), out = '<div class="ag-mgrid">';
    DOW.forEach(function (n) { out += '<div class="ag-wd" aria-hidden="true">' + n.charAt(0) + '</div>'; });
    for (var k = 0; k < 42; k++) {
      var x = add(r.start, k), outm = pd(x).getMonth() !== pd(d).getMonth();
      out += '<button type="button" class="ag-mcell-m' + (outm ? ' is-out' : '') + (x === cfg.today ? ' is-today' : '') + '" data-sel="' + x + '" aria-pressed="' + (x === d) + '" aria-label="' + h(longDay(x)) + '"><span>' + dnum(x) + '</span>' + dots(x) + '</button>';
    }
    out += '</div><p class="ag-sec">' + h(longDay(d)) + '</p>';
    var list = onDay(d);
    return out + '<div class="ag-cards ag-cards--day">' + (list.length ? list.map(card).join('') : '<p class="ag-state">Nada marcado.</p>') + '</div>';
  }

  function hourRange(days) {
    var min = 7 * 60, max = 19 * 60;
    days.forEach(function (x) { onDay(x).forEach(function (e) {
      if (e.start == null) return;
      min = Math.min(min, Math.floor(e.start / 60) * 60);
      max = Math.max(max, Math.ceil((e.start + (e.dur || 60)) / 60) * 60);
    }); var bd = bday(x); if (bd) bd.blocks.forEach(function (b) { min = Math.min(min, Math.floor(b.start_minutes / 60) * 60); max = Math.max(max, Math.ceil(b.end_minutes / 60) * 60); }); });
    return [Math.max(0, min), Math.min(24 * 60, max)];
  }
  function layout(events) {
    var items = events.map(function (e) { return { e: e, s: e.start, f: e.start + (e.dur || 60) }; }).sort(function (a, b) { return a.s - b.s || b.f - a.f; });
    var cluster = [], clusterEnd = -1, out = [];
    function close() {
      var lanes = 0; cluster.forEach(function (c) { lanes = Math.max(lanes, c.lane + 1); });
      cluster.forEach(function (c) { c.lanes = lanes; out.push(c); }); cluster = []; clusterEnd = -1;
    }
    items.forEach(function (it) {
      if (cluster.length && it.s >= clusterEnd) close();
      var lanesEnd = [];
      cluster.forEach(function (c) { lanesEnd[c.lane] = Math.max(lanesEnd[c.lane] || 0, c.f); });
      var lane = 0; while (lanesEnd[lane] != null && lanesEnd[lane] > it.s) lane++;
      it.lane = lane; cluster.push(it); clusterEnd = Math.max(clusterEnd, it.f);
    });
    if (cluster.length) close();
    return out;
  }
  function grid(days) {
    var n = days.length, hr = hourRange(days), H0 = hr[0], H1 = hr[1], height = (H1 - H0) / 60 * HP;
    var rail = n === 1 ? railInfo(days[0], H0, H1) : null;
    var cols = 'grid-template-columns:' + (rail ? rail.w + 'px ' : '') + '52px repeat(' + n + ',minmax(0,1fr))';
    var head = '<div class="ag-tg__head" style="' + cols + '">' + (rail ? '<div class="ag-tg__hd is-gut"></div>' : '') + '<div class="ag-tg__hd is-gut"></div>';
    days.forEach(function (x) {
      head += '<div class="ag-tg__hd' + (x === cfg.today ? ' is-today' : '') + '"><small>' + DOW[dow(x)] + '</small><b>' + dnum(x) + '</b>' + (bday(x) ? sigChip(bday(x).day, true) + (n > 1 ? miniBar(bday(x).day) : '') : '') + '</div>';
    });
    head += '</div>';
    var allday = '<div class="ag-tg__allday" style="' + cols + '">' + (rail ? '<div class="ag-tg__al is-gut"></div>' : '') + '<div class="ag-tg__al is-gut">dia todo</div>';
    days.forEach(function (x) {
      var l = onDay(x).filter(function (e) { return e.start == null; }), shown = l.slice(0, 3);
      allday += '<div class="ag-tg__al">' + shown.map(function (e) {
        return '<button type="button" class="ag-ap t-' + e.type + (e.closed ? ' is-closed' : '') + '" data-key="' + h(e.key) + '" aria-label="' + h(ariaEv(e)) + '"><span class="ag-tl">' + TYPES[e.type] + '</span><span>' + h(e.title) + '</span></button>';
      }).join('') + (l.length > 3 ? '<button type="button" class="ag-more" data-go="' + x + '">+' + (l.length - 3) + ' mais</button>' : '') + '</div>';
    });
    allday += '</div>';
    var lab = ''; for (var m = H0; m <= H1; m += 60) lab += '<span style="top:' + ((m - H0) / 60 * HP) + 'px">' + hm(m) + '</span>';
    var body = '<div class="ag-tg__body" style="' + cols + '">' + (rail ? '<div class="ag-rail" style="height:' + height + 'px">' + rail.html + '</div>' : '') + '<div class="ag-tg__gut" style="height:' + height + 'px">' + lab + '</div>';
    var now = new Date(), nowMin = now.getHours() * 60 + now.getMinutes();
    days.forEach(function (x) {
      var timed = onDay(x).filter(function (e) { return e.start != null; }), inner = (n > 1 ? weekEdges(x, H0, H1) : '');
      layout(timed).forEach(function (it) {
        var e = it.e, top = (it.s - H0) / 60 * HP, hh = Math.max((it.f - it.s) / 60 * HP - 2, 22), w = 100 / it.lanes, left = it.lane * w;
        inner += '<button type="button" class="ag-ev t-' + e.type + (e.closed ? ' is-closed' : '') + '" data-key="' + h(e.key) + '" aria-label="' + h(ariaEv(e)) + '" style="top:' + top + 'px;height:' + hh + 'px;left:calc(' + left + '% + 2px);width:calc(' + w + '% - 4px)"><b>' + h(e.title) + '</b>' + hm(it.s) + (e.dur ? '–' + hm(it.f) : '') + '</button>';
      });
      if (x === cfg.today && nowMin >= H0 && nowMin <= H1) inner += '<div class="ag-now" style="top:' + ((nowMin - H0) / 60 * HP) + 'px"></div>';
      body += '<div class="ag-tg__col' + (x === cfg.today ? ' is-today' : '') + '" data-col="' + x + '" data-h0="' + H0 + '" role="group" aria-label="' + h(longDay(x)) + '" style="height:' + height + 'px;background-size:100% ' + HP + 'px">' + inner + '</div>';
    });
    return '<div class="ag-grid"><div class="ag-tg">' + head + allday + body + '</div></div>';
  }
  function monthDesktop() {
    var r = range(), out = '<div class="ag-dmonth">';
    DOW.forEach(function (n) { out += '<div class="ag-wd">' + n + '</div>'; });
    for (var k = 0; k < 42; k++) {
      var x = add(r.start, k), outm = pd(x).getMonth() !== pd(S.sel).getMonth(), l = onDay(x);
      out += '<div class="ag-dcell' + (outm ? ' is-out' : '') + (x === cfg.today ? ' is-today' : '') + '" data-cell="' + x + '"><span class="ag-dcell__n">' + dnum(x) + '</span>' +
        l.slice(0, 3).map(function (e) { return '<button type="button" class="ag-mchip t-' + e.type + '" data-key="' + h(e.key) + '" aria-label="' + h(ariaEv(e)) + '">' + (e.start != null ? hm(e.start) + ' ' : '') + h(e.title) + '</button>'; }).join('') +
        (l.length > 3 ? '<button type="button" class="ag-more" data-go="' + x + '">+' + (l.length - 3) + ' mais</button>' : '') + '</div>';
    }
    return out + '</div>';
  }

  function renderMain() {
    var main = $('agMain');
    if (S.view === 'team') { main.setAttribute('aria-busy', S.team.loading ? 'true' : 'false'); main.innerHTML = teamHtml(); return; }
    main.setAttribute('aria-busy', S.loading ? 'true' : 'false');
    if (S.error) {
      main.innerHTML = '<div class="ag-state ag-state--error" role="alert"><p>' + h(S.error) + '</p><button type="button" class="ag-btn" data-act="retry">Tentar de novo</button></div>';
      return;
    }
    if (S.loading && !S.events.length && !main.querySelector('.ag-view')) {
      main.innerHTML = '<p class="ag-state">Carregando a agenda…</p>';
      return;
    }
    var v = S.view, html;
    if (v === 'day') html = dayMobile() + '<div class="ag-bk-d">' + blocksSummary(S.sel) + '</div>' + grid([S.sel]) + '<div class="ag-bk-d">' + blocksPanel(S.sel) + '</div>';
    else if (v === 'week') { var ws = weekStart(S.sel), days = []; for (var i = 0; i < 7; i++) days.push(add(ws, i)); html = weekMobile() + grid(days); }
    else html = monthMobile() + monthDesktop();
    var note = S.googleNote ? '<p class="ag-note">' + h(S.googleNote) + '</p>' : '';
    main.innerHTML = '<div class="ag-view">' + note + html + '</div>';
  }

  /* ---------- cabeçalho, filtros, atrasadas ---------- */
  function rangeLabel() {
    var d = pd(S.sel);
    if (S.view === 'day' || S.view === 'team') return isMobile() ? DOW[d.getDay()] + ', ' + d.getDate() + ' de ' + MON3[d.getMonth()] : cap1(longDay(S.sel));
    if (S.view === 'month') return cap1(MONTHS[d.getMonth()]) + ' de ' + d.getFullYear();
    var r = range(), a = pd(r.start), b = pd(r.end);
    if (a.getMonth() === b.getMonth()) return a.getDate() + ' – ' + b.getDate() + ' de ' + MONTHS[b.getMonth()] + ' de ' + b.getFullYear();
    return a.getDate() + ' de ' + MON3[a.getMonth()] + ' – ' + b.getDate() + ' de ' + MON3[b.getMonth()] + ' de ' + b.getFullYear();
  }
  function renderChrome() {
    $('agRange').textContent = rangeLabel();
    var tb = $('agTeamBtn'); if (tb) tb.hidden = !cfg.canViewAll;
    root.classList.toggle('is-team', S.view === 'team');
    var bt = $('agBlocksToggle');
    if (bt) { bt.setAttribute('aria-pressed', String(S.blocks.on)); bt.disabled = S.view === 'month'; bt.title = S.view === 'month' ? 'Os blocos aparecem nas visões Dia e Semana.' : ''; }
    Array.prototype.forEach.call($('agViews').querySelectorAll('button'), function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === S.view)); });
    var g = S.google, chip = $('agGoogleChip');
    if (!g.configured) chip.hidden = true;
    else {
      chip.hidden = false;
      chip.className = 'ag-chip' + (g.connected ? ' ag-chip--ok' : (g.needsReconnect ? ' ag-chip--warn' : ''));
      chip.innerHTML = '<span class="ag-dot"></span>' + (g.connected ? 'Google' : (g.needsReconnect ? 'Reconectar' : 'Conectar Google'));
    }
    var banner = $('agBanner');
    if (g.configured && g.needsReconnect) {
      banner.hidden = false;
      banner.innerHTML = '<span><b>Google pausado.</b> Sua conexão expirou e a sincronização está parada.</span><a class="ag-btn ag-btn--primary ag-btn--sm" href="/agenda/google">Reconectar agora</a>';
    } else banner.hidden = true;
    keepFocus(renderFilters);
  }
  function activeFilterCount() {
    var n = 0;
    TYPE_ORDER.forEach(function (k) { if (S.filters.types[k] === false) n++; });
    if (S.filters.scope === 'all') n++;
    return n;
  }
  function renderFilters() {
    var tg = $('agFilterToggle'), n = activeFilterCount();
    tg.setAttribute('aria-expanded', String(S.filtersOpen));
    tg.innerHTML = 'Filtros' + (n ? ' <span class="ag-badge">' + n + '</span>' : '') + ' <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
    $('agFilters').classList.toggle('is-collapsed', !S.filtersOpen);
    var out = '';
    TYPE_ORDER.forEach(function (k) {
      if (k === 'google_event' && !S.google.connected) return;
      out += '<button type="button" class="ag-fchip t-' + k + '" data-ftype="' + k + '" data-fk="f-' + k + '" aria-pressed="' + (S.filters.types[k] !== false) + '"><span>' + TYPES[k] + '</span></button>';
    });
    if (cfg.canViewAll) {
      out += '<select class="ag-select" data-fscope data-fk="f-scope" aria-label="Escopo"><option value="mine"' + (S.filters.scope === 'mine' ? ' selected' : '') + '>Somente meus</option><option value="all"' + (S.filters.scope === 'all' ? ' selected' : '') + '>Toda a empresa</option></select>';
      if (S.filters.scope === 'all') {
        out += '<select class="ag-select" data-femp data-fk="f-emp" aria-label="Colaborador"><option value="">Todos os colaboradores</option>' +
          cfg.employees.map(function (e) { return '<option value="' + e.id + '"' + (String(e.id) === String(S.filters.employee) ? ' selected' : '') + '>' + h(e.name) + '</option>'; }).join('') + '</select>';
      }
    }
    $('agFilters').innerHTML = out;
  }
  function lateCard(e) { return card(e); }
  function renderLate() {
    var el = $('agLate'), L = S.late, label = (LATE_SORTS.filter(function (s) { return s[0] === L.sort; })[0] || LATE_SORTS[0])[1];
    var any = L.total > 0 || L.error || !Object.keys(L.types).every(function (k) { return L.types[k]; });
    if (!any && !L.loading) { el.hidden = true; return; }
    el.hidden = false;
    var open = L.open;
    var html = '<button type="button" class="ag-late__head" data-act="late-toggle" data-fk="late-head" aria-expanded="' + open + '"><span>Atrasadas</span><span class="ag-late__count">' + L.total + '</span><span class="ag-late__hint">' + h(label) + '</span>' +
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>';
    if (open) {
      html += '<div class="ag-late__body"><div class="ag-late__ctrl"><label>Ordenar<select class="ag-select" data-lsort data-fk="late-sort" aria-label="Ordenar atrasadas">' +
        LATE_SORTS.map(function (s) { return '<option value="' + s[0] + '"' + (L.sort === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') + '</select></label>' +
        ['project_task', 'process_instance'].map(function (k) { return '<button type="button" class="ag-fchip t-' + k + '" data-ltype="' + k + '" data-fk="late-' + k + '" aria-pressed="' + (L.types[k] !== false) + '"><span>' + (k === 'project_task' ? 'Atividades' : 'Instâncias') + '</span></button>'; }).join('') + '</div>';
      if (L.error) html += '<p class="ag-error" role="alert">' + h(L.error) + '</p>';
      else if (L.loading) html += '<p class="ag-meta">Carregando…</p>';
      else if (!L.items.length) html += '<p class="ag-meta">Nenhuma atrasada com este filtro.</p>';
      else html += '<div class="ag-late__list">' + L.items.map(lateCard).join('') + '</div>' + (L.total > L.items.length ? '<p class="ag-meta">Mostrando ' + L.items.length + ' de ' + L.total + '.</p>' : '');
      html += '</div>';
    }
    el.innerHTML = html;
  }

  /* ---------- camadas ---------- */
  function sheetWrap(inner, panel, labelId) {
    return '<div class="ag-scrim' + (panel ? ' ag-scrim--panel' : '') + '" data-scrim><div class="ag-sheet" role="dialog" aria-modal="true" aria-labelledby="' + labelId + '"><div class="ag-grab"></div>' + inner + '</div></div>';
  }
  function detailHtml(e) {
    var out = '<span class="ag-tl t-' + e.type + '">' + TYPES[e.type] + '</span><h3 id="agDlg">' + h(e.title) + '</h3>';
    if (e.subtitle) out += '<p class="ag-meta">' + h(e.subtitle) + '</p>';
    out += '<p class="ag-meta">' + h(cap1(longDay(e.date))) + ' · ' + h(whenTxt(e)) + '</p><div>' + pills(e) + '</div>';
    if (e.description) out += '<p class="ag-meta">' + h(e.description) + '</p>';
    out += '<div class="ag-btns">';
    if (e.type === 'google_event') {
      out += (e.url ? '<a class="ag-btn ag-btn--primary" href="' + h(e.url) + '" target="_blank" rel="noopener noreferrer" data-autofocus>Abrir no Google</a>' : '') + '</div><p class="ag-note">Evento do Google: somente consulta. Edite-o no Google.</p>';
    } else if (e.type === 'manual') {
      out += '<button type="button" class="ag-btn ag-btn--primary" data-act="edit-manual" data-key="' + h(e.key) + '" data-autofocus>Editar</button>' +
        (e.closed ? '' : '<button type="button" class="ag-btn" data-act="complete-manual" data-key="' + h(e.key) + '">Marcar como concluído</button>') +
        '<button type="button" class="ag-btn ag-btn--danger" data-act="ask-delete" data-key="' + h(e.key) + '">Excluir</button></div><div data-confirm></div>';
    } else {
      out += '<a class="ag-btn ag-btn--primary" href="' + h(e.url) + '" data-track-item="' + e.type + '" data-autofocus>Abrir página de gestão</a>' +
        ((e.type === 'project_task' || e.type === 'process_instance') && !e.closed ? '<button type="button" class="ag-btn" data-act="move-open" data-key="' + h(e.key) + '">Mover para um bloco</button>' : '') + '</div>';
    }
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
  }
  function createHtml(L) {
    var d = L.date, opts = [
      ['meeting', 'Reunião', 'Agendar com pauta e participantes', true],
      ['project_task', 'Atividade', cfg.canViewAll ? 'Tarefa de um projeto' : 'Só quem administra a empresa cria atividades', cfg.canViewAll],
      ['process_instance', 'Instância', 'Execução de um processo', true],
      ['manual', 'Evento avulso', 'Compromisso pessoal ou rápido', !!cfg.employeeId]
    ];
    return '<h3 id="agDlg">Criar em ' + h(longDay(d)) + (L.time != null ? ' às ' + hm(L.time) : '') + '</h3><div class="ag-opts">' +
      opts.map(function (o, i) {
        return '<button type="button" class="ag-opt" data-act="create" data-kind="' + o[0] + '"' + (o[3] ? '' : ' disabled') + (i === 0 ? ' data-autofocus' : '') + '><span class="ag-tl t-' + o[0] + '">' + TYPES[o[0]] + '</span><b>' + o[1] + '</b><span>' + h(o[2]) + '</span></button>';
      }).join('') + '</div><div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Cancelar</button></div>';
  }
  function field(label, inner, id) { return '<label class="ag-field" for="' + id + '">' + label + inner + '</label>'; }
  function formHtml(L) {
    var k = L.formKind, ev = L.event || null, title = ev ? ev.title : '', date = ev ? ev.date : L.date, out = '';
    var heading = ev ? 'Editar evento avulso' : ({ project_task: 'Nova atividade', process_instance: 'Nova instância', manual: 'Novo evento avulso' }[k]);
    out += '<h3 id="agDlg">' + heading + '</h3><form class="ag-form" data-form="' + k + '" novalidate>';
    out += field('Título', '<input id="agfTitle" name="title" type="text" maxlength="200" required value="' + h(title) + '" autocomplete="off" data-autofocus>', 'agfTitle');
    if (k === 'project_task') {
      out += field('Projeto', '<select id="agfProject" name="project">' + cfg.projects.map(function (p) { return '<option value="' + p.id + '">' + h(p.name) + '</option>'; }).join('') + '</select>', 'agfProject');
    }
    if (k === 'process_instance') {
      out += field('Processo', '<select id="agfProcess" name="process">' + cfg.processes.map(function (p) { return '<option value="' + p.id + '">' + h(p.name) + '</option>'; }).join('') + '</select>', 'agfProcess');
    }
    out += field(k === 'manual' ? 'Data' : 'Prazo', '<input id="agfDate" name="date" type="date" required value="' + h(date) + '">', 'agfDate');
    if (k === 'manual') {
      out += '<div class="ag-row">' + field('Início (opcional)', '<input id="agfStart" name="start" type="time" value="' + h(ev && ev.time ? ev.time : (L.time != null ? hm(L.time) : '')) + '">', 'agfStart') +
        field('Fim (opcional)', '<input id="agfEnd" name="end" type="time" value="' + h(ev && ev.end_time ? ev.end_time : '') + '">', 'agfEnd') + '</div>' +
        field('Observações (opcional)', '<textarea id="agfNotes" name="notes" maxlength="2000">' + h(ev && ev.description ? ev.description : '') + '</textarea>', 'agfNotes');
    }
    out += '<p class="ag-error" data-error role="alert" hidden></p><div class="ag-btns"><button type="submit" class="ag-btn ag-btn--primary" data-submit>' + (ev ? 'Salvar' : 'Criar') + '</button><button type="button" class="ag-btn" data-act="close">Cancelar</button></div></form>';
    return out;
  }
  function menuItem(act, title, sub, badge) {
    return '<button type="button" class="ag-menu__btn" data-act="' + act + '">' + title + (badge ? ' <span class="ag-badge">' + badge + '</span>' : '') + '<small>' + sub + '</small></button>';
  }
  function menuHtml() {
    var pend = cfg.canViewAll ? S.req.pending : 0;
    var out = '<h3 id="agDlg">Mais opções</h3><div class="ag-menu">' +
      '<p class="ag-menu__sec">Planejamento</p>' +
      menuItem('pb-open', 'Blocos de horário', cfg.personBlocks ? 'Seu dia, valendo para todas as empresas' : 'Organize seu dia em um só lugar') +
      menuItem('rules-open', 'Regras de recorrência', 'Obrigações que se repetem todo dia, semana ou mês') +
      menuItem('req-open-abs', 'Ausências', 'Férias, ausências e atestados', pend ? '' : '') +
      menuItem('req-open-trf', 'Transferências', 'Pedidos de troca de responsável');
    if (cfg.canViewAll) {
      out += '<p class="ag-menu__sec">Gestão</p>' +
        (pend ? '<button type="button" class="ag-menu__btn ag-menu__btn--alert" data-act="req-open-pending">Aprovações pendentes <span class="ag-badge">' + pend + '</span><small>Ausências e transferências aguardando decisão</small></button>' : '') +
        '<a href="/companies/' + cfg.companyId + '/work-journey/report">Relatório gerencial<small>PDF da jornada</small></a>';
    }
    out += '<p class="ag-menu__sec">Integração</p>';
    if (S.google.configured) out += '<a href="/agenda/google">Conexão com o Google<small>Gerenciar</small></a>';
    out += '<p class="ag-menu__sec">Versão anterior</p>' +
      '<a href="' + h(cfg.legacyUrl) + '" data-track-legacy>Calendário operacional<small>Tela antiga de planejamento por capacidade</small></a>';
    return out + '</div><div class="ag-btns"><button type="button" class="ag-btn" data-act="close" data-autofocus>Fechar</button></div>';
  }
  function googleHtml() {
    var g = S.google, out = '<h3 id="agDlg">Google Calendar</h3>';
    if (g.connected) {
      out += '<p class="ag-meta">Conectado' + (g.email ? ' como ' + h(g.email) : '') + '.</p>' +
        '<div class="ag-btns"><button type="button" class="ag-btn ag-btn--primary" data-act="sync" data-autofocus>Sincronizar esta empresa</button><button type="button" class="ag-btn" data-act="sync-all">Sincronizar todas as empresas</button></div>' +
        '<p class="ag-note">A conexão é sua e vale em todas as empresas. A sincronização cobre o período exibido.</p>';
    } else if (g.needsReconnect) {
      out += '<p class="ag-meta">Sua conexão com o Google expirou e a sincronização está pausada. Reconectar leva cerca de 20 segundos.</p><div class="ag-btns"><a class="ag-btn ag-btn--primary" href="/agenda/google" data-autofocus>Reconectar com o Google</a></div>';
    } else {
      out += '<p class="ag-meta">Conecte sua conta para enviar seus compromissos ao Google e vê-los aqui.</p><div class="ag-btns"><a class="ag-btn ag-btn--primary" href="/agenda/google" data-autofocus>Conectar com o Google</a></div>';
    }
    return out + '<div class="ag-btns"><button type="button" class="ag-btn" data-act="close">Fechar</button></div>';
  }
  function renderLayer() {
    var host = $('agLayer'), L = S.layer;
    if (!L) { host.innerHTML = ''; return; }
    var inner, panel = false;
    if (L.kind === 'detail') { var e = lookup(L.key); if (!e) { S.layer = null; host.innerHTML = ''; return; } inner = detailHtml(e); panel = true; }
    else if (L.kind === 'create') inner = createHtml(L);
    else if (L.kind === 'form') inner = formHtml(L);
    else if (L.kind === 'menu') inner = menuHtml();
    else if (L.kind === 'est') inner = estHtml();
    else if (L.kind === 'move') inner = moveHtml();
    else if (L.kind === 'pblocks') inner = pbHtml();
    else if (L.kind === 'req') inner = reqHtml();
    else if (L.kind === 'rules') inner = rulesHtml();
    else if (L.kind === 'sug') inner = sugHtml();
    else inner = googleHtml();
    host.innerHTML = sheetWrap(inner, panel, 'agDlg');
    var f = host.querySelector('[data-autofocus]') || host.querySelector('input,select,textarea,a,button');
    if (f) f.focus();
    if (L.kind === 'est') estCounter();
  }
  function renderLayer0() { openLayer({ kind: 'pblocks' }, $('agMenuBtn')); loadPb(); }
  function openLayer(layer, trigger) {
    S.lastFocus = trigger || document.activeElement;
    S.layer = layer; renderLayer();
  }
  function closeLayer() {
    S.layer = null; renderLayer();
    if (S.lastFocus && document.body.contains(S.lastFocus) && S.lastFocus.focus) S.lastFocus.focus();
  }
  function trapTab(ev) {
    var dlg = $('agLayer').querySelector('.ag-sheet');
    if (!dlg) return;
    var f = dlg.querySelectorAll('a[href],button:not([disabled]),input,select,textarea'); if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
    else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
  }

  /* ---------- formulários ---------- */
  function showError(form, msg) { var p = form.querySelector('[data-error]'); p.textContent = msg; p.hidden = !msg; }
  function busy(form, on) { var b = form.querySelector('[data-submit]'); b.disabled = on; b.textContent = on ? 'Salvando…' : (S.layer && S.layer.event ? 'Salvar' : 'Criar'); }
  function submitForm(form) {
    var k = form.dataset.form, f = form.elements, title = (f.title.value || '').trim(), date = f.date.value;
    showError(form, '');
    if (!title) return showError(form, 'Informe o título.');
    if (!date) return showError(form, 'Informe a data.');
    if (k === 'manual') {
      if (!cfg.employeeId) return showError(form, 'Seu usuário não está vinculado a um colaborador ativo desta empresa.');
      var s = f.start.value, e = f.end.value;
      if (e && !s) return showError(form, 'Informe também o horário de início.');
      if (s && e && toMin(e) <= toMin(s)) return showError(form, 'O fim deve ser depois do início.');
      var body = { title: title, event_date: date, start_time: s || null, end_time: e || null, description: (f.notes.value || '').trim() || null };
      var editing = S.layer && S.layer.event;
      busy(form, true);
      var req = editing
        ? api(base() + '/work-journey/calendar/events/' + editing.id, { method: 'PATCH', json: body })
        : api(base() + '/work-journey/calendar/events', { json: Object.assign({ employee_id: +cfg.employeeId, source_type: 'manual' }, body) });
      return req.then(function (res) {
        busy(form, false);
        if (!res.ok || res.body.success === false) return showError(form, errText(res, 'Não foi possível salvar o evento.'));
        S.layer = null; renderLayer(); toast(editing ? 'Evento atualizado.' : 'Evento avulso criado para ' + ddmm(date) + '.'); load(); S.late.loading = false;
      });
    }
    busy(form, true);
    var req2;
    if (k === 'project_task') {
      if (!f.project.value) { busy(form, false); return showError(form, 'Não há projetos cadastrados.'); }
      req2 = api('/api/projects/' + f.project.value + '/tasks?company_id=' + cfg.companyId, { json: Object.assign({ what: title, due_date: date }, cfg.employeeId ? { employee_id: +cfg.employeeId } : {}) });
    } else {
      if (!f.process.value) { busy(form, false); return showError(form, 'Não há processos cadastrados.'); }
      req2 = api(base() + '/process-instances', { json: { process_id: +f.process.value, title: title, due_date: date, status: 'pending' } });
    }
    req2.then(function (res) {
      busy(form, false);
      if (!res.ok || !res.body.id) return showError(form, errText(res, 'Não foi possível criar o registro.'));
      S.layer = null; renderLayer(); toast((k === 'project_task' ? 'Atividade criada para ' : 'Instância criada para ') + ddmm(date) + '.'); load(); loadLate();
    });
  }

  /* ---------- ações ---------- */
  function setView(v) {
    S.view = v; if (v !== 'team') store('agenda.view', v); track('view_change', v);
    renderChrome(); ensureLoaded();
  }
  function go(date, view) { S.sel = date; if (view && view !== S.view) setView(view); else { renderChrome(); ensureLoaded(); } }
  function shift(dir) {
    var d = pd(S.sel);
    if (S.view === 'month') { d.setDate(1); d.setMonth(d.getMonth() + dir); S.sel = iso(d); }
    else S.sel = add(S.sel, (S.view === 'day' || S.view === 'team' ? 1 : 7) * dir);
    renderChrome(); ensureLoaded();
  }
  function openCreate(date, time, trigger) { track('create_open'); openLayer({ kind: 'create', date: date, time: time }, trigger); }
  function colMinutes(col, y) { var r = col.getBoundingClientRect(), h0 = +col.dataset.h0; return h0 + Math.floor((y - r.top) / HP) * 60; }

  root.addEventListener('click', function (ev) {
    var t = ev.target, n;
    if (t.matches && t.matches('[data-scrim]') && t === t.closest('[data-scrim]')) { closeLayer(); return; }
    if ((n = t.closest('[data-track-item]'))) track('item_open', n.dataset.trackItem);
    if (t.closest('[data-track-legacy]')) { track('legacy_open'); flush(); }
    if ((n = t.closest('[data-view]')) && n.closest('#agViews')) { setView(n.dataset.view); return; }
    if ((n = t.closest('[data-sel]'))) { S.sel = n.dataset.sel; renderChrome(); ensureLoaded(); return; }
    if ((n = t.closest('[data-go]'))) { go(n.dataset.go, 'day'); return; }
    if ((n = t.closest('[data-ftype]'))) {
      var k = n.dataset.ftype; S.filters.types[k] = !(S.filters.types[k] !== false);
      keepFocus(function () { renderFilters(); }); load(); return;
    }
    if ((n = t.closest('[data-ltype]'))) {
      var lk = n.dataset.ltype; S.late.types[lk] = !(S.late.types[lk] !== false); track('late_filter', lk);
      keepFocus(function () { renderLate(); }); loadLate(); return;
    }
    if ((n = t.closest('[data-key]')) && !t.closest('[data-act]')) {
      var e = lookup(n.dataset.key);
      if (e) { track('item_open', e.type); openLayer({ kind: 'detail', key: e.key }, n); }
      return;
    }
    if ((n = t.closest('[data-act]'))) { act(n.dataset.act, n, ev); return; }
    var col = t.closest('[data-col]');
    if (col && !t.closest('.ag-ev')) { openCreate(col.dataset.col, colMinutes(col, ev.clientY), col); return; }
    var cell = t.closest('[data-cell]');
    if (cell && !t.closest('button')) { openCreate(cell.dataset.cell, null, cell); return; }
  });
  root.addEventListener('change', function (ev) {
    var t = ev.target;
    if (t.matches('[data-fscope]')) { S.filters.scope = t.value; S.filters.employee = ''; renderFilters(); load(); loadLate(); loadEstCount(); return; }
    if (t.matches('[data-femp]')) { S.filters.employee = t.value; load(); loadLate(); loadEstCount(); return; }
    if (t.matches('[data-rtype]')) { var rf = S.rules.form, fd2 = new FormData(t.form); rf.title = (fd2.get('title') || ''); rf.minutes = +fd2.get('minutes'); rf.priority = fd2.get('priority'); rf.active = !!fd2.get('active'); rf.recurrence_type = t.value; renderLayer(); return; }
    if (t.matches('[data-pdec]')) { var dd = S.pb.decisions[t.dataset.pid]; if (dd) { var k2 = t.dataset.pdec; dd[k2] = k2 === 'accept' ? t.checked : t.value; if (k2 === 'accept') renderLayer(); } return; }
    if (t.matches('[data-lsort]')) { S.late.sort = t.value; track('late_sort', t.value); renderLate(); loadLate(); }
  });
  root.addEventListener('submit', function (ev) {
    var aform = ev.target.closest('[data-absform]');
    if (aform) { ev.preventDefault(); absSubmit(aform); return; }
    var rform = ev.target.closest('[data-ruleform]');
    if (rform) { ev.preventDefault(); ruleSubmit(rform); return; }
    var pform = ev.target.closest('[data-pbform]');
    if (pform) { ev.preventDefault(); pbSubmit(pform); return; }
    var form = ev.target.closest('[data-form]');
    if (form) { ev.preventDefault(); submitForm(form); }
  });
  document.addEventListener('keydown', function (ev) {
    if (!S.layer) return;
    if (ev.key === 'Escape') { ev.preventDefault(); closeLayer(); }
    else if (ev.key === 'Tab') trapTab(ev);
  });

  function act(name, node) {
    if (name === 'close') return closeLayer();
    if (name === 'retry') return load();
    if (name === 'team-filter') { S.team.filter = node.dataset.f; track('team_filter', S.team.filter); renderMain(); return; }
    if (name === 'req-open-abs' || name === 'req-open-trf' || name === 'req-open-pending') {
      S.req.tab = name === 'req-open-trf' ? 'trf' : 'abs'; S.req.form = false; track('config_open', S.req.tab === 'abs' ? 'absences' : 'transfers');
      if (name === 'req-open-pending' && S.req.data && !S.req.data.absences.some(function (a) { return a.status === 'pending'; }) && S.req.data.transfers.some(function (t) { return t.status === 'pending'; })) S.req.tab = 'trf';
      openLayer({ kind: 'req' }, node); loadReq(); return;
    }
    if (name === 'req-tab') { S.req.tab = node.dataset.tab; S.req.form = false; renderLayer(); return; }
    if (name === 'abs-new') { S.req.form = true; renderLayer(); return; }
    if (name === 'abs-cancel') { S.req.form = false; renderLayer(); return; }
    if (name === 'abs-approve') return approve('abs', node.dataset.id, node);
    if (name === 'trf-approve') return approve('trf', node.dataset.id, node);
    if (name === 'rules-open') { track('config_open', 'rules'); S.rules.form = null; S.rules.confirmDelete = null; openLayer({ kind: 'rules' }, node); loadRules(); return; }
    if (name === 'rule-new') { S.rules.form = ruleNew(); renderLayer(); return; }
    if (name === 'rule-back') { S.rules.form = null; renderLayer(); return; }
    if (name === 'rule-edit') {
      var rr = S.rules.items.filter(function (x) { return String(x.id) === node.dataset.id; })[0]; if (!rr) return;
      var cc = rr.recurrence_config || {};
      S.rules.form = { id: rr.id, title: rr.title, description: rr.description || '', recurrence_type: rr.recurrence_type, weekdays: (cc.weekdays || [0]).map(Number), days: (cc.days || [1]).join(', '), date: rr.recurrence_type === 'annual' ? '2026-' + (cc.mmdd || '01-01') : (cc.date || ''), minutes: rr.estimated_minutes, priority: rr.priority, active: rr.is_active, start_date: rr.start_date || '', end_date: rr.end_date || '', preferred_block_id: rr.preferred_block_id };
      renderLayer(); return;
    }
    if (name === 'rule-day') { var rd = +node.dataset.d, wl = S.rules.form.weekdays, wi = wl.indexOf(rd); if (wi >= 0) wl.splice(wi, 1); else wl.push(rd); node.setAttribute('aria-pressed', String(wl.indexOf(rd) >= 0)); return; }
    if (name === 'rule-del') { S.rules.confirmDelete = S.rules.items.filter(function (x) { return String(x.id) === node.dataset.id; })[0] || null; renderLayer(); return; }
    if (name === 'rule-del-no') { S.rules.confirmDelete = null; renderLayer(); return; }
    if (name === 'rule-del-yes') {
      var del = S.rules.confirmDelete; if (!del) return; node.disabled = true;
      api(base() + '/work-journey/rules/' + del.id, { method: 'DELETE' }).then(function (res) {
        S.rules.confirmDelete = null;
        if (!res.ok || res.body.success === false) { toast(errText(res, 'Não foi possível excluir a regra.'), true); renderLayer(); return; }
        toast('Regra excluída.'); loadRules(); load();
      });
      return;
    }
    if (name === 'pb-open') { track('blocks_edit_open'); S.pb.mode = 'list'; S.pb.form = null; S.pb.confirmRevert = false; S.pb.confirmDelete = null; renderLayer0(); return; }
    if (name === 'pb-new') { S.pb.form = pbNewForm(); S.pb.mode = 'form'; renderLayer(); return; }
    if (name === 'pb-edit') { var eb0 = S.pb.blocks.filter(function (b) { return String(b.id) === node.dataset.id; })[0]; if (eb0) { S.pb.form = { id: eb0.id, name: eb0.name, start: eb0.start, end: eb0.end, mode: eb0.mode, weekdays: eb0.weekdays.slice(), types: eb0.preferred_item_types.slice() }; S.pb.mode = 'form'; renderLayer(); } return; }
    if (name === 'pb-back') { S.pb.mode = S.pb.has ? 'list' : 'intro'; S.pb.form = null; renderLayer(); return; }
    if (name === 'pb-day') { var di = +node.dataset.d, wl = S.pb.form.weekdays, wi = wl.indexOf(di); if (wi >= 0) wl.splice(wi, 1); else wl.push(di); wl.sort(); node.setAttribute('aria-pressed', String(wl.indexOf(di) >= 0)); return; }
    if (name === 'pb-type') { var tl = S.pb.form.types, tk = node.dataset.t, ti = tl.indexOf(tk); if (ti >= 0) tl.splice(ti, 1); else tl.push(tk); node.setAttribute('aria-pressed', String(tl.indexOf(tk) >= 0)); return; }
    if (name === 'pb-del') { S.pb.confirmDelete = S.pb.blocks.filter(function (b) { return String(b.id) === node.dataset.id; })[0] || null; renderLayer(); return; }
    if (name === 'pb-del-no') { S.pb.confirmDelete = null; renderLayer(); return; }
    if (name === 'pb-del-yes') {
      var dbk = S.pb.confirmDelete; if (!dbk) return; node.disabled = true;
      pbApi('/' + dbk.id, { method: 'DELETE' }).then(function (res) {
        S.pb.confirmDelete = null;
        if (!res.ok || !res.body.success) { toast(errText(res, 'Não foi possível excluir o bloco.'), true); renderLayer(); return; }
        track('blocks_edit_save', 'delete'); toast('Bloco excluído.'); pbAfterChange();
      });
      return;
    }
    if (name === 'pb-revert') { S.pb.confirmRevert = true; renderLayer(); var dt = $('agLayer').querySelector('details'); if (dt) dt.open = true; return; }
    if (name === 'pb-revert-no') { S.pb.confirmRevert = false; renderLayer(); return; }
    if (name === 'pb-revert-yes') {
      node.disabled = true; track('migration_revert');
      pbApi('/migration/revert', { json: {} }).then(function (res) {
        S.pb.confirmRevert = false;
        if (!res.ok || !res.body.success) { toast(errText(res, 'Não foi possível voltar.'), true); renderLayer(); return; }
        cfg.personBlocks = false; S.pb.has = false; S.pb.blocks = []; S.pb.mode = 'intro';
        toast('Você voltou aos blocos por empresa.'); pbAfterChange();
      });
      return;
    }
    if (name === 'pb-proposal') {
      track('migration_open'); S.pb.mode = 'proposal'; S.pb.proposal = null; S.pb.decisions = {}; S.pb.loading = true; S.pb.error = null; renderLayer();
      pbApi('/migration').then(function (res) {
        S.pb.loading = false;
        if (!res.ok || !res.body.success) S.pb.error = errText(res, 'Não foi possível montar a proposta.');
        else if (res.body.already_migrated) { S.pb.mode = 'list'; loadPb(); return; }
        else S.pb.proposal = res.body;
        renderLayer();
      });
      return;
    }
    if (name === 'pb-apply') return pbApply();
    if (name === 'move-open') { track('move_open'); S.move.key = node.dataset.key; S.move.saving = false; openLayer({ kind: 'move' }, node); loadMove(); return; }
    if (name === 'move-pick') { S.move.sel = +node.dataset.i; S.move.error = null; renderLayer(); var rf = $('agLayer').querySelector('[data-move-reason], [data-act="move-confirm"]'); if (rf) rf.focus(); return; }
    if (name === 'move-confirm') return moveConfirm();
    if (name === 'sug-open') { track('suggest_open'); S.sug.date = S.sel; S.sug.saving = false; S.sug.proposals = []; S.sug.unplaced = []; openLayer({ kind: 'sug' }, node); loadSug(); return; }
    if (name === 'sug-apply') { S.sug.saving = true; track('suggest_apply'); renderLayer(); sugAction('apply', function (b) { return b.applied + (b.applied === 1 ? ' item sugerido.' : ' itens sugeridos.') + (b.unplaced && b.unplaced.length ? ' ' + b.unplaced.length + ' sem bloco.' : ''); }); return; }
    if (name === 'sug-accept') { track('suggest_accept'); sugAction('accept', function (b) { return b.accepted + (b.accepted === 1 ? ' sugestão aceita.' : ' sugestões aceitas.'); }); return; }
    if (name === 'sug-undo') { track('suggest_undo'); sugAction('undo', function (b) { return b.removed + (b.removed === 1 ? ' sugestão desfeita.' : ' sugestões desfeitas.'); }); return; }
    if (name === 'est-open') { track('estimate_open'); S.est.picks = {}; S.est.skipped = {}; openLayer({ kind: 'est' }, node); loadEstList(); return; }
    if (name === 'est-type') { var ek = node.dataset.k; S.est.types[ek] = !(S.est.types[ek] !== false); S.est.picks = {}; renderLayer(); loadEstList(); return; }
    if (name === 'est-pick') {
      var pk = node.dataset.key, pm = +node.dataset.min;
      S.est.picks[pk] = S.est.picks[pk] === pm ? 0 : pm;
      Array.prototype.forEach.call(node.parentNode.querySelectorAll('button'), function (b) { b.setAttribute('aria-pressed', String(S.est.picks[pk] === +b.dataset.min)); });
      estCounter(); return;
    }
    if (name === 'est-save') return saveEstimates();
    if (name === 'late-toggle') { S.late.open = !S.late.open; if (S.late.open) track('late_open'); keepFocus(function () { renderLate(); }); return; }
    if (name === 'create') {
      var kind = node.dataset.kind, L = S.layer || {}, date = L.date || S.sel;
      track('create_choose', kind);
      if (kind === 'meeting') { flush(); window.location.href = '/meetings/company/' + cfg.companyId + '?new=1&date=' + encodeURIComponent(date); return; }
      S.layer = { kind: 'form', formKind: kind, date: date, time: L.time, event: null };
      renderLayer();
      return;
    }
    if (name === 'edit-manual') { var ev0 = lookup(node.dataset.key); if (ev0) { S.layer = { kind: 'form', formKind: 'manual', date: ev0.date, time: null, event: ev0 }; renderLayer(); } return; }
    if (name === 'complete-manual') {
      var e1 = lookup(node.dataset.key); if (!e1) return;
      node.disabled = true;
      api(base() + '/work-journey/calendar/events/' + e1.id, { method: 'PATCH', json: { status: 'done' } }).then(function (res) {
        if (!res.ok || res.body.success === false) { node.disabled = false; return toast(errText(res, 'Não foi possível concluir o evento.'), true); }
        S.layer = null; renderLayer(); toast('Evento concluído.'); load();
      });
      return;
    }
    if (name === 'ask-delete') {
      var box = $('agLayer').querySelector('[data-confirm]');
      box.innerHTML = '<div class="ag-confirm" role="alert"><span>Excluir este evento?</span><button type="button" class="ag-btn ag-btn--danger ag-btn--sm" data-act="do-delete" data-key="' + h(node.dataset.key) + '" data-autofocus>Sim, excluir</button><button type="button" class="ag-btn ag-btn--sm" data-act="cancel-delete">Não</button></div>';
      box.querySelector('[data-autofocus]').focus(); return;
    }
    if (name === 'cancel-delete') { $('agLayer').querySelector('[data-confirm]').innerHTML = ''; return; }
    if (name === 'do-delete') {
      var e2 = lookup(node.dataset.key); if (!e2) return;
      node.disabled = true;
      api(base() + '/work-journey/calendar/events/' + e2.id, { method: 'DELETE' }).then(function (res) {
        if (!res.ok || res.body.success === false) { node.disabled = false; return toast(errText(res, 'Não foi possível excluir o evento.'), true); }
        S.layer = null; renderLayer(); toast('Evento excluído.'); load();
      });
      return;
    }
    if (name === 'sync' || name === 'sync-all') {
      var r = range(), url = name === 'sync' ? base() + '/agenda/google/sync' : '/api/agenda/google/sync-all';
      node.disabled = true; node.textContent = 'Sincronizando…';
      api(url, { json: { start: r.start, end: r.end } }).then(function (res) {
        if (!res.ok || !res.body.success) { closeLayer(); toast(errText(res, 'A sincronização falhou.'), true); loadGoogle(); return; }
        var st = res.body.stats || {};
        closeLayer(); toast('Google sincronizado: ' + (st.created || 0) + ' criados, ' + (st.updated || 0) + ' atualizados, ' + (st.deleted || 0) + ' removidos' + (st.failed ? ', ' + st.failed + ' com falha' : '') + '.'); load(); loadGoogle();
      });
    }
  }
  /* ---------- eventos fixos da barra ---------- */
  $('agToday').addEventListener('click', function () { S.sel = cfg.today; renderChrome(); ensureLoaded(); });
  $('agPrev').addEventListener('click', function () { shift(-1); });
  $('agNext').addEventListener('click', function () { shift(1); });
  $('agBlocksToggle').addEventListener('click', function () {
    S.blocks.on = !S.blocks.on; store('agenda.blocks', S.blocks.on ? '1' : '0'); track('blocks_toggle', S.blocks.on ? 'on' : 'off');
    renderChrome(); if (S.blocks.on) loadBlocks(); else S.blocks.days = {}; renderMain();
  });
  $('agCreateBtn').addEventListener('click', function () { openCreate(S.sel, null, $('agCreateBtn')); });
  $('agFilterToggle').addEventListener('click', function () { S.filtersOpen = !S.filtersOpen; renderFilters(); });
  $('agFab').addEventListener('click', function () { openCreate(S.sel, null, $('agFab')); });
  $('agMenuBtn').addEventListener('click', function () { openLayer({ kind: 'menu' }, $('agMenuBtn')); });
  $('agGoogleChip').addEventListener('click', function () { track('google_open'); openLayer({ kind: 'google' }, $('agGoogleChip')); });

  /* ---------- início ---------- */
  track('agenda_open', S.view);
  renderChrome();
  renderLate();
  load();
  loadLate();
  loadGoogle();
  loadEstCount();
  if (cfg.canViewAll) loadReq();
})();
