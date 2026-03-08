# Workflow collaborator.occupancy

## Objetivo
Retornar a ocupacao operacional de um colaborador no periodo informado, com foco em:

- horas disponiveis
- horas tomadas com processos
- horas registradas em projetos
- horas comprometidas com projetos
- saldo do periodo

## Entradas esperadas
- `empresa` quando houver mais de uma empresa acessivel
- `colaborador`
- `periodo`

## Base de calculo atual
- capacidade disponivel: `weekly_hours` proporcional aos dias uteis do periodo
- processos: soma de `activity_work_logs` do colaborador para `process` e `process_instance`
- projetos registrados: soma de `activity_work_logs` do colaborador para `project`
- projetos comprometidos: soma de `estimated_hours` de atividades abertas atribuidas ao colaborador no periodo

## Observacoes
- o fluxo e somente leitura
- segue o mesmo contrato omnichannel para web, WhatsApp, Instagram e Telegram
- a heuristica de compromisso em projetos pode evoluir futuramente para alocacao mais precisa por agenda/capacidade
