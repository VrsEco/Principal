# SPEC — Controle de Deploy por Agentes do Squad Engenharia v1

**Status:** proposto para implementação controlada
**Classe:** SPEC
**Dono:** Squad Engenharia
**Escopo:** toda publicação em `app.gestaoversus.com.br`, por humano, Codex ou Claude.

## Decisão

O deploy de produção terá um único plano de controle: **MCP de Deploy → GitHub
Actions → script oficial de deploy**. Nenhum agente recebe chave SSH de
produção. Codex e Claude solicitam a mesma operação MCP, enquanto somente o
workflow oficial tem o segredo de transporte para o host.

## Objetivos de aceite

1. Todo deploy possui um registro imutável, tenant-safe, com `company_id`, SHA,
   ambiente, modo, solicitante autenticado, agente-origem, aprovação, run do
   GitHub e resultado.
2. É possível identificar, sem confiar em texto fornecido pelo agente, se o
   deploy foi solicitado por humano, Codex ou Claude.
3. Um deploy em `production` só alcança o host pelo workflow
   `.github/workflows/deploy-app32.yml` e pelo script versionado
   `app32/scripts/deploy_configr.sh`.
4. A conclusão só é `success` após health e smoke dos assets declarados no
   release. Falha mantém evidências e não dispara retry automático.

## Arquitetura

```text
Codex / Claude / operador humano
        │ OAuth/JWT com subject verificável
        ▼
MCP deployment.request
        │ RBAC + company_id + política + aprovação
        ▼
PostgreSQL deployment_ledger (fonte de verdade)
        │ dispatch autenticado por GitHub App
        ▼
GitHub Actions / deploy-app32.yml
        │ github.actor + github.triggering_actor + run_id + SHA
        ▼
MCP deployment.record_stage / deployment.complete
        ▼
deploy_configr.sh → app.gestaoversus.com.br
```

## Identidade e autorização

- Cada agente usa uma instalação/identidade separada de GitHub App: por
  exemplo, `gv-codex-deploy[bot]` e `gv-claude-deploy[bot]`. Tokens são de
  curta duração e ficam no runtime do respectivo agente; são proibidos tokens
  compartilhados e chaves SSH distribuídas a agentes.
- O MCP deriva `requested_by_subject` do JWT/OAuth e `agent_kind` da identidade
  autenticada. Campos informados pelo chamador servem somente como contexto e
  não substituem a identidade verificada.
- O workflow grava `github.actor`, `github.triggering_actor`,
  `github.run_id`, `github.run_attempt`, `github.sha` e `github.workflow_ref`.
  Esses valores são evidências imutáveis da execução.
- `production` exige RBAC `deployment:request`, aprovação de ambiente GitHub e
  uma aprovação MCP vinculada à solicitação. Apenas `main` protegida é aceita.

## Ledger PostgreSQL e multi-tenancy

A tabela `deployment_ledger` deve conter, no mínimo:

- `id` UUID, `company_id` **NOT NULL**, `environment`, `mode`, `target_sha`,
  `target_ref`, `status`, `requested_at`, `started_at`, `finished_at`;
- `requested_by_subject`, `agent_kind`, `approval_id`, `github_actor`,
  `github_triggering_actor`, `github_run_id`, `github_run_attempt`;
- `preflight_evidence`, `validation_evidence`, `failure_reason` e `created_by`.

Toda consulta e mutação filtra `company_id`. O tenant de governança do Gestão
Versus é resolvido no servidor por configuração, nunca aceito livremente de
um agente. Eventos de estágio são append-only; transição de status é validada
por service, não por rota HTTP.

## Contrato MCP

| Tool | Finalidade | Permissão mínima |
|---|---|---|
| `deployment.request` | cria pedido e inicia aprovação/dispatch | `deployment:request` |
| `deployment.get` | consulta um pedido do mesmo `company_id` | `deployment:read` |
| `deployment.record_stage` | uso exclusivo do workflow autenticado | service identity |
| `deployment.complete` | fecha com sucesso/falha e evidências | service identity |
| `deployment.approve_drift` | autoriza snapshot controlado | `deployment:approve_drift` |

Rotas HTTP, quando necessárias para callback do GitHub, só autenticam,
validam schema e delegam ao service. A regra de política não vive na rota.

## Política do workflow

1. `concurrency` única para produção, sem cancelamento de release em curso.
2. `quick`, `standard` e `full` são escolhidos por política de impacto; `full`
   exige confirmação adicional de migration.
3. Drift bloqueia o deploy. A exceção requer snapshot externo, `approval_id` e
   registro no ledger; não há `DEPLOY_ALLOW_DIRTY` livre em input.
4. Antes do restart: confirmar SHA em `origin/main`, arquivos do release e
   permissões públicas de `static/vendor`.
5. Depois do restart: `healthz` 200 e smoke HTTP 200 dos assets críticos,
   incluindo tipo JavaScript para Chart.js. Falha encerra o run como vermelho.

## Operação e contingência

SSH manual é contingência de incidente: precisa de ticket/`deployment_id`,
snapshot do drift e registro posterior via `deployment.record_stage`. Não é
um caminho alternativo de publicação. O runbook deve registrar o executor,
o motivo, o SHA e as evidências de validação.

## Rollout em três entregas

1. Criar ledger, migration, service e tools MCP com testes de isolamento por
   `company_id`.
2. Configurar GitHub Apps separadas e adaptar o workflow para registrar todos
   os estágios, gates e correlação por `deployment_id`.
3. Adicionar preflight de permissões públicas, smoke de assets, runbook e
   harness de contrato antes de tornar o fluxo obrigatório.

## Não objetivos v1

- Não automatizar deploy por `push` em `main`.
- Não armazenar segredos de GitHub ou SSH no PostgreSQL.
- Não executar migration fora do modo `full` aprovado.
