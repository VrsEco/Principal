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
    processes: boot.processes || []
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

  function load() {
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
  function blocksMobile(d) {
    var B = S.blocks;
    if (!B.on) return '';
    if (B.loading && !B.days[d]) return '<p class="ag-note">Carregando blocos…</p>';
    if (B.error) return '<p class="ag-note">' + h(B.error) + '</p>';
    var bd = B.days[d];
    if (!bd) return '<p class="ag-note">Escolha um colaborador para ver os blocos.</p>';
    var out = '<section class="ag-bk" aria-label="Blocos do dia">' + dayBar(bd);
    bd.blocks.forEach(function (b) {
      out += '<div class="ag-bk-row"><span class="ag-bk-row__time">' + h(b.start) + '–' + h(b.end) + '</span><span class="ag-bk-row__name">' + h(b.name) + '</span>' +
        sigChip(b.signal) + (b.without_estimate ? '<span class="ag-bk-row__warn">' + b.without_estimate + ' sem estimativa</span>' : '') + '</div>';
    });
    return out + '</section>';
  }
  function blockBands(x, H0, H1) {
    var bd = bday(x), out = '';
    if (!bd) return '';
    bd.blocks.forEach(function (b) {
      var s0 = Math.max(b.start_minutes, H0), e0 = Math.min(b.end_minutes, H1);
      if (e0 <= s0) return;
      out += '<div class="ag-bk-band ag-bk-band--' + (b.signal.state || 'none') + '" style="top:' + ((s0 - H0) / 60 * HP) + 'px;height:' + ((e0 - s0) / 60 * HP) + 'px" aria-hidden="true"><span>' + h(b.name) + ' ' + sigChip(b.signal, true) + '</span></div>';
    });
    return out;
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
    return strip + blocksMobile(d) + '<div class="ag-cards--day">' + body + '</div>';
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
    var n = days.length, cols = 'grid-template-columns:52px repeat(' + n + ',minmax(0,1fr))';
    var hr = hourRange(days), H0 = hr[0], H1 = hr[1], height = (H1 - H0) / 60 * HP;
    var head = '<div class="ag-tg__head" style="' + cols + '"><div class="ag-tg__hd is-gut"></div>';
    days.forEach(function (x) {
      head += '<div class="ag-tg__hd' + (x === cfg.today ? ' is-today' : '') + '"><small>' + DOW[dow(x)] + '</small><b>' + dnum(x) + '</b>' + (bday(x) ? sigChip(bday(x).day, true) : '') + '</div>';
    });
    head += '</div>';
    var allday = '<div class="ag-tg__allday" style="' + cols + '"><div class="ag-tg__al is-gut">dia todo</div>';
    days.forEach(function (x) {
      var l = onDay(x).filter(function (e) { return e.start == null; }), shown = l.slice(0, 3);
      allday += '<div class="ag-tg__al">' + shown.map(function (e) {
        return '<button type="button" class="ag-ap t-' + e.type + (e.closed ? ' is-closed' : '') + '" data-key="' + h(e.key) + '" aria-label="' + h(ariaEv(e)) + '"><span class="ag-tl">' + TYPES[e.type] + '</span><span>' + h(e.title) + '</span></button>';
      }).join('') + (l.length > 3 ? '<button type="button" class="ag-more" data-go="' + x + '">+' + (l.length - 3) + ' mais</button>' : '') + '</div>';
    });
    allday += '</div>';
    var lab = ''; for (var m = H0; m <= H1; m += 60) lab += '<span style="top:' + ((m - H0) / 60 * HP) + 'px">' + hm(m) + '</span>';
    var body = '<div class="ag-tg__body" style="' + cols + '"><div class="ag-tg__gut" style="height:' + height + 'px">' + lab + '</div>';
    var now = new Date(), nowMin = now.getHours() * 60 + now.getMinutes();
    days.forEach(function (x) {
      var timed = onDay(x).filter(function (e) { return e.start != null; }), inner = blockBands(x, H0, H1);
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
    if (v === 'day') html = dayMobile() + grid([S.sel]);
    else if (v === 'week') { var ws = weekStart(S.sel), days = []; for (var i = 0; i < 7; i++) days.push(add(ws, i)); html = weekMobile() + grid(days); }
    else html = monthMobile() + monthDesktop();
    var note = S.googleNote ? '<p class="ag-note">' + h(S.googleNote) + '</p>' : '';
    main.innerHTML = '<div class="ag-view">' + note + html + '</div>';
  }

  /* ---------- cabeçalho, filtros, atrasadas ---------- */
  function rangeLabel() {
    var d = pd(S.sel);
    if (S.view === 'day') return isMobile() ? DOW[d.getDay()] + ', ' + d.getDate() + ' de ' + MON3[d.getMonth()] : cap1(longDay(S.sel));
    if (S.view === 'month') return cap1(MONTHS[d.getMonth()]) + ' de ' + d.getFullYear();
    var r = range(), a = pd(r.start), b = pd(r.end);
    if (a.getMonth() === b.getMonth()) return a.getDate() + ' – ' + b.getDate() + ' de ' + MONTHS[b.getMonth()] + ' de ' + b.getFullYear();
    return a.getDate() + ' de ' + MON3[a.getMonth()] + ' – ' + b.getDate() + ' de ' + MON3[b.getMonth()] + ' de ' + b.getFullYear();
  }
  function renderChrome() {
    $('agRange').textContent = rangeLabel();
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
      out += '<a class="ag-btn ag-btn--primary" href="' + h(e.url) + '" data-track-item="' + e.type + '" data-autofocus>Abrir página de gestão</a></div>';
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
  function menuHtml() {
    var out = '<h3 id="agDlg">Mais opções</h3><div class="ag-menu">' +
      '<a href="' + h(cfg.legacyUrl) + '" data-track-legacy>Calendário operacional (versão anterior)<small>Planejamento por capacidade</small></a>' +
      '<a href="/companies/' + cfg.companyId + '/work-journey/report">Relatório gerencial<small>PDF da jornada</small></a>';
    if (S.google.configured) out += '<a href="/agenda/google">Conexão com o Google<small>Gerenciar</small></a>';
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
    else inner = googleHtml();
    host.innerHTML = sheetWrap(inner, panel, 'agDlg');
    var f = host.querySelector('[data-autofocus]') || host.querySelector('input,select,textarea,a,button');
    if (f) f.focus();
    if (L.kind === 'est') estCounter();
  }
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
    S.view = v; store('agenda.view', v); track('view_change', v);
    renderChrome(); ensureLoaded();
  }
  function go(date, view) { S.sel = date; if (view && view !== S.view) setView(view); else { renderChrome(); ensureLoaded(); } }
  function shift(dir) {
    var d = pd(S.sel);
    if (S.view === 'month') { d.setDate(1); d.setMonth(d.getMonth() + dir); S.sel = iso(d); }
    else S.sel = add(S.sel, (S.view === 'day' ? 1 : 7) * dir);
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
    if (t.matches('[data-lsort]')) { S.late.sort = t.value; track('late_sort', t.value); renderLate(); loadLate(); }
  });
  root.addEventListener('submit', function (ev) {
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
})();
