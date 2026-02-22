// ============================================================================
// CÓDIGO PARA ADICIONAR EM my-work.js (linha ~3204)
// Substituir o bloco dentro do if (currentActivity.type === 'project'...)
// ============================================================================

// SUBSTITUIR ESTE BLOCO (linhas 3204-3220):
/*
    if (currentActivity.type === 'project' && currentActivity.company_id && currentActivity.project_id) {
      // Fetch current activity data
      const fetchResponse = await fetch(
        `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities`
      );
      // ... resto do código antigo
*/

// POR ESTE NOVO BLOCO:
if (currentActivity.type === 'project' && currentActivity.company_id && currentActivity.project_id) {
    // Registrar horas via nova API de colaboradores
    const response = await fetch(
        `/api/companies/${currentActivity.company_id}/projects/${currentActivity.project_id}/activities/${currentActivity.id}/collaborators`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                employee_id: {{ current_user.employee_id if current_user.employee_id else 'null' }},
        role: 'executor',
        hours: hoursToAdd,
        notes: description || `Adicionado ${hoursToAdd}h em ${new Date(date).toLocaleDateString('pt-BR')}`
          })
        }
      );

const data = await response.json();

if (!response.ok || !data.success) {
    throw new Error(data.error || 'Erro ao registrar horas');
}

window.showMessage(`✅ ${hoursToAdd}h registradas com sucesso!`, 'success');
closeModal('modalAddHours');
loadActivitiesData();
return; // IMPORTANTE: return aqui para não executar o código antigo
    }

// O resto do código (para processos) continua igual...
