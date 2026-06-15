# Harness — Robô DEV_FULL Transacional

## Classe documental
Harness.

## Objetivo
Validar jornadas destrutivas em ambiente `DEV_FULL`, com massa isolada por `company_id`, marcador único de execução e cleanup obrigatório.

## Guardrails
- Proibido rodar em `PROD_SAFE`.
- Exige `E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true`.
- Exige `E2E_COMPANY_ID`.
- Toda criação precisa ter marcador `AUTOE2E::`.
- Toda jornada destrutiva precisa ter etapa de reversão/cancelamento/exclusão.
- O fechamento só é aprovado com auditoria de resíduo zero para o marcador da execução.

## Matriz transacional v2 — full-app

Inventário base de expansão:
- `run_20260614_225925`
- 716 rotas Flask registradas
- 46 itens no inventário E2E oficial atual
- 678 rotas candidatas a classificação/cobertura
- módulos detectados: `cross`, `financial`, `integrations`, `meetings`, `processes`, `qa`, `work_journey`, `workspace`

| Domínio | Cobertura funcional atual | Cobertura transacional DEV_FULL | Ações esperadas | Cleanup esperado | Status |
|---|---|---|---|---|
| Meetings | Probe de tela/gestão | Criar, atualizar preliminares, iniciar, salvar execução, finalizar, excluir reunião e excluir projeto gerado | POST/PUT/POST/PUT/POST/DELETE | DELETE reunião + DELETE projeto derivado | Implementado |
| Work Journey | Board/tarefas manuais | Criar tarefa manual, listar, atualizar/concluir, excluir | POST/GET/PATCH/DELETE | DELETE do item | Implementado |
| Workspace/My Work | Render, filtros, atividades, PDF | Mutação operacional ainda indireta via Work Journey | abrir, filtrar, exportar, validar atividades | Cleanup por itens criados nos domínios-fonte | Parcial |
| Processes/BPMN | Lista, detalhe, modeler, diagrama, save de rascunho | Diagrama BPMN: ler diagrama salvo, salvar rascunho marcado, validar persistência e restaurar payload original. Falta ciclo criar processo -> instanciar -> executar -> cancelar/excluir | criar, versionar, publicar/rascunhar, instanciar, executar | restaurar BPMN original; remover instâncias/rascunhos/processo teste quando houver CRUD completo | Parcial implementado |
| Projects/Planos/OKR | Cobertura indireta via Meetings | Falta CRUD direto de projeto/plano/atividade | criar/editar/mover/concluir/excluir | excluir projeto, tarefas e vínculos | Pendente transacional |
| Financial | Páginas, catálogos, títulos, relatórios/exportações | Falta ciclo seguro de conta/categoria/título/borderô/transferência cancelada | criar/editar/processar/cancelar/excluir | estorno/cancelamento + exclusão/inativação | Pendente transacional |
| Contracts/Fiscal | Fila fiscal, filtros, painel de ações | Falta massa de contrato/NF/ação em lote controlada | criar/importar, filtrar, acionar lote, cancelar | remover NF/contrato teste e arquivos | Pendente transacional |
| Admin/Cadastros | Save seguro de parametrização | Parametrização de performance: ler, alterar boolean controlado, validar persistência, restaurar valor original. Falta CRUD de usuários, colaboradores, empresas auxiliares e permissões | criar/editar/permissões/inativar/excluir | reverter permissões/parâmetros, excluir cadastros | Parcial implementado |
| Integrations/MCP/Sapiens/IA | Catálogo, requests, MCP health, concorrência | Falta integração fake/request/tool controlada com teardown | criar request fake, executar health/tool, cancelar/excluir | remover request/config fake | Pendente transacional |
| Reports/Downloads | Relatórios e exports principais | Não destrutivo por definição; depende de massa dos domínios | emitir PDF/XLSX/prints | remover massa fonte por marcador | Funcional implementado |
| QA/Governança | Inventário, drift, diff, central QA | Runner full-app e drift | auditar cobertura e execuções | sem resíduo | Implementado base |

## Critério de aceite v1
- Runner `devfull_transactional_validation` executa as suítes destrutivas existentes.
- O relatório mostra ações executadas, status e artefatos.
- Auditoria genérica procura resíduos com o marcador em colunas textuais tenant-safe.
- `residue_total == 0` é obrigatório para aprovação.

## Critério de aceite full-app
- `devfull_full_app_validation` deve rodar todos os probes funcionais aplicáveis em `DEV_FULL`.
- `devfull_transactional_validation` deve rodar todos os journeys destrutivos já implementados.
- O relatório full-app deve listar domínio a domínio: funcional, transacional, pendente e motivo.
- Nenhum journey destrutivo pode aprovar com `residue_total > 0`.
- Toda expansão nova deve atualizar esta matriz antes do deploy.

## Evolução necessária para “tudo”
Para cobrir literalmente todas as telas/campos/botões/processamentos, cada módulo precisa registrar seu contrato transacional: massa mínima, rotas de criação, processamento, reversão e limpeza. A suíte v1 cria a fundação e impede falsa impressão de cobertura total.
