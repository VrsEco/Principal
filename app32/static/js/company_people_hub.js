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
})();
