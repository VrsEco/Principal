(function () {
  'use strict';

  var root = document.getElementById('gcRoot');
  if (!root) return;
  var companyId = root.dataset.companyId;
  var hasEmployee = root.dataset.hasEmployee === 'true';
  var el = {
    alert: document.getElementById('gcAlert'),
    title: document.getElementById('gcTitle'),
    text: document.getElementById('gcText'),
    connect: document.getElementById('gcConnect'),
    sync: document.getElementById('gcSync'),
    syncAll: document.getElementById('gcSyncAll'),
    disconnect: document.getElementById('gcDisconnect'),
    result: document.getElementById('gcResult')
  };
  var FLAGS = {
    connected: ['ok', 'Conta Google reconectada com sucesso.'],
    denied: ['warn', 'A autorização foi negada no Google. Tente novamente e conceda o acesso ao calendário.'],
    invalid: ['warn', 'A autorização expirou ou é inválida. Tente conectar novamente.'],
    error: ['warn', 'Não foi possível concluir a conexão com o Google. Tente novamente.'],
    not_configured: ['warn', 'A integração com o Google não está configurada neste ambiente.']
  };

  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function api(path, options) {
    return fetch('/api/companies/' + companyId + '/agenda/' + path, Object.assign({ credentials: 'same-origin' }, options || {}))
      .then(function (r) { return r.json().catch(function () { return {}; }); });
  }
  function showAlert(kind, text) {
    el.alert.hidden = !text;
    el.alert.className = 'uc-alert uc-alert--' + kind;
    el.alert.textContent = text || '';
  }
  function addResult(text) {
    var li = document.createElement('li');
    li.textContent = text;
    el.result.appendChild(li);
  }

  function render(s) {
    el.connect.hidden = true;
    el.sync.hidden = true;
    el.syncAll.hidden = true;
    el.disconnect.hidden = true;
    if (!s.success || !s.configured) {
      el.title.textContent = 'Integração indisponível';
      el.text.textContent = 'O Google Calendar ainda não foi configurado neste ambiente. Fale com o administrador.';
      return;
    }
    if (!hasEmployee) {
      el.title.textContent = 'Colaborador não vinculado';
      el.text.textContent = 'Seu usuário não está vinculado a um colaborador ativo em nenhuma empresa, então não há compromissos para sincronizar.';
      return;
    }
    if (s.needs_reconnect) {
      el.title.textContent = 'Sua conexão com o Google expirou';
      el.text.textContent = 'O acesso ao seu Google Calendar foi revogado ou venceu. Reconecte para voltar a sincronizar; seus compromissos serão atualizados nos dois sentidos assim que você reconectar.';
      el.connect.textContent = 'Reconectar com o Google';
      el.connect.hidden = false;
      el.disconnect.hidden = false;
      showAlert('warn', 'Conexão vencida: a sincronização está pausada.');
    } else if (s.connected) {
      el.title.textContent = 'Conectado' + (s.email ? ' como ' + s.email : '');
      el.text.textContent = s.last_synced_at
        ? 'Última sincronização em ' + new Date(s.last_synced_at + 'Z').toLocaleString('pt-BR') + '.'
        : 'Ainda não houve sincronização.';
      el.sync.hidden = false;
      el.syncAll.hidden = false;
      el.disconnect.hidden = false;
    } else {
      el.title.textContent = 'Google Calendar não conectado';
      el.text.textContent = 'Conecte sua conta Google para enviar seus compromissos ao Google e vê-los na Agenda do Versus.';
      el.connect.textContent = 'Conectar com o Google';
      el.connect.hidden = false;
    }
    if (s.last_error && !s.needs_reconnect) showAlert('warn', s.last_error);
  }

  function refresh() {
    return api('google/status').then(function (s) { render(s); return s; });
  }

  function sync(allCompanies) {
    var from = new Date();
    from.setDate(from.getDate() - 30);
    var to = new Date();
    to.setDate(to.getDate() + 60);
    el.sync.disabled = true;
    el.syncAll.disabled = true;
    el.result.textContent = '';
    addResult('Sincronizando…');
    var url = allCompanies ? '/api/agenda/google/sync-all' : '/api/companies/' + companyId + '/agenda/google/sync';
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start: iso(from), end: iso(to) })
    }).then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (res) {
        el.result.textContent = '';
        if (!res.success) throw new Error(res.message || 'Falha ao enviar ao Google.');
        var st = res.stats;
        addResult('Versus → Google (' + (allCompanies ? 'todas as empresas' : 'esta empresa') + '): ' + st.created + ' criados, ' +
          st.updated + ' atualizados, ' + st.deleted + ' removidos' + (st.failed ? ', ' + st.failed + ' com falha' : '') + '.');
        var qs = new URLSearchParams({ start: iso(from), end: iso(to), types: 'google_event', scope: 'mine' });
        return api('events?' + qs.toString());
      }).then(function (res) {
        if (res.google_error) throw new Error(res.google_error);
        addResult('Google → Versus: ' + (res.events || []).length + ' compromisso(s) do Google disponíveis na Agenda.');
        showAlert('ok', 'Sincronização concluída.');
        return true;
      }).catch(function (err) {
        el.result.textContent = '';
        showAlert('warn', err.message);
        return false;
      }).then(function (ok) {
        el.sync.disabled = false;
        el.syncAll.disabled = false;
        return refresh().then(function () { return ok; });
      });
  }

  el.sync.addEventListener('click', function () { sync(false); });
  el.syncAll.addEventListener('click', function () { sync(true); });
  el.disconnect.addEventListener('click', function () {
    if (!window.confirm('Desconectar o Google Calendar? Os eventos já criados no Google permanecem lá.')) return;
    api('google/disconnect', { method: 'POST' }).then(function () { showAlert('ok', ''); refresh(); });
  });

  var flag = new URLSearchParams(window.location.search).get('google');
  if (flag) window.history.replaceState(null, '', window.location.pathname);
  refresh().then(function (s) {
    if (flag && FLAGS[flag]) showAlert(FLAGS[flag][0], FLAGS[flag][1]);
    if (flag === 'connected' && s.connected && hasEmployee) {
      sync(true).then(function (ok) {
        if (ok) showAlert('ok', FLAGS.connected[1] + ' Compromissos de todas as empresas sincronizados nos dois sentidos.');
      });
    }
  });
})();
