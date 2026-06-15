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

## Matriz transacional v1

| Domínio | Cobertura DEV_FULL atual | Ações esperadas | Cleanup esperado | Status |
|---|---|---|---|---|
| Meetings | Criar, atualizar preliminares, iniciar, salvar execução, finalizar, excluir | POST/PUT/POST/PUT/POST/DELETE | DELETE da reunião | Implementado |
| Work Journey | Criar tarefa manual, listar, atualizar/concluir, excluir | POST/GET/PATCH/DELETE | DELETE do item | Implementado |
| Admin | Leitura e save seguro de parametrização | GET/PUT controlado | Reverter valor anterior quando aplicável | Parcial |
| Processes | Renderização e rascunho seguro em DEV_FULL | GET/PUT rascunho | Reverter rascunho quando aplicável | Parcial |
| Financial | Renderização, catálogos, relatórios e exportações | GET/exportações | Sem mutação financeira no v1 | Pendente transacional |
| Contracts/Fiscal | Renderização, filtros e ações de painel | GET/POST controlado futuro | Cancelar/excluir massa criada | Pendente transacional |
| Integrations/MCP/Sapiens | Catálogos, health e contratos | GET/POST health/tool controlada | Remover integração fake quando aplicável | Pendente transacional |
| Cadastros mestres | Não há ciclo universal hoje | criar/editar/inativar/excluir | exclusão/soft-delete por marcador | Pendente transacional |

## Critério de aceite v1
- Runner `devfull_transactional_validation` executa as suítes destrutivas existentes.
- O relatório mostra ações executadas, status e artefatos.
- Auditoria genérica procura resíduos com o marcador em colunas textuais tenant-safe.
- `residue_total == 0` é obrigatório para aprovação.

## Evolução necessária para “tudo”
Para cobrir literalmente todas as telas/campos/botões/processamentos, cada módulo precisa registrar seu contrato transacional: massa mínima, rotas de criação, processamento, reversão e limpeza. A suíte v1 cria a fundação e impede falsa impressão de cobertura total.
