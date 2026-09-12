(() => {
  'use strict';
  const hub = document.querySelector('.people-hub');
  const count = document.getElementById('peopleAccessCount');
  const companyId = Number(hub?.dataset.companyId || 0);
  if (!count || !companyId) return;
  fetch(`/api/companies/${companyId}/users`, {headers: {Accept: 'application/json'}})
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(users => { count.textContent = `${Array.isArray(users) ? users.length : 0} contas vinculadas`; })
    .catch(() => { count.textContent = 'Contas vinculadas indisponíveis'; });
  const telemetryStatus = document.getElementById('peopleTelemetryStatus');
  async function loadTelemetry(days) {
    if (!telemetryStatus) return;
    telemetryStatus.textContent = 'Carregando uso agregado…';
    const end = new Date(), start = new Date(end); start.setDate(end.getDate() - Number(days) + 1);
    const iso = value => value.toISOString().slice(0, 10);
    try {
      const response = await fetch(`/api/companies/${companyId}/usage-telemetry?start=${iso(start)}&end=${iso(end)}`, {headers: {Accept: 'application/json'}});
      const data = await response.json(); if (!response.ok) throw new Error();
      document.getElementById('peopleTelemetrySessions').textContent = data.sessions_started;
      document.getElementById('peopleTelemetryTime').textContent = `${Math.floor(Number(data.active_seconds || 0) / 3600)}h`;
      document.getElementById('peopleTelemetryRequests').textContent = data.request_count;
      telemetryStatus.textContent = `Período: ${data.start} a ${data.end}.`;
    } catch (_) { telemetryStatus.textContent = 'Uso agregado indisponível.'; }
  }
  document.querySelectorAll('[data-people-period]').forEach(button => button.addEventListener('click', () => loadTelemetry(button.dataset.peoplePeriod)));
  loadTelemetry(7);
})();
