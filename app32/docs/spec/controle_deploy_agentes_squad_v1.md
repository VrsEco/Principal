# SPEC — Controle de Deploy por Agentes do Squad Engenharia v1

**Status:** implementação local concluída (não homologada em produção)  
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
MCP request/approve_agent_deployment
        │ RBAC + company_id + política + aprovação humana
        ▼
PostgreSQL deployment_ledger (fonte de verdade)
        │ dispatch autenticado por GitHub App
        ▼
GitHub Actions / deploy-app32.yml
        │ github.actor + github.triggering_actor + run_id + SHA
        ▼
callback OIDC /webhook/agent-deployments/github
        ▼
deploy_configr.sh → app.gestaoversus.com.br
```

## Identidade e autorização

- Agentes e humanos autenticam por OAuth. O servidor deriva `actor_kind`
  (`codex`, `claude`, `human`) do `client_id` autenticado, mapeado em
  `AGENT_DEPLOY_CLIENT_KINDS` (JSON `client_id → tipo`). Cliente não mapeado é
  recusado (fail-closed). `actor_kind`, `company_id`, status e URL de run **não**
  são parâmetros de nenhuma tool.
- O tenant é o de governança (`AGENT_DEPLOY_GOVERNANCE_COMPANY_ID`) e precisa
  coincidir com o contexto validado pelo wrapper MCP e com a identidade.
- Agente solicita; somente `actor_kind=human` aprova. A tool de aprovação tem
  human gate persistido do APP32 (payload exato) e RBAC `deployment.approve`.
- O workflow prova origem por **OIDC do GitHub Actions** (sem segredo): o
  callback exige assinatura RS256 do emissor GitHub, audiência
  `AGENT_DEPLOY_OIDC_AUDIENCE`, `repository`, `ref=refs/heads/main`,
  `event_name=workflow_dispatch`, `environment=production`, `workflow_ref` do
  workflow oficial e `sha` igual ao `target_sha` aprovado (40 hex).
- `github.actor`, `run_id`, `run_attempt`, `workflow_ref` e `sha` gravados no
  ledger vêm exclusivamente desses claims verificados.

## Ledger PostgreSQL e multi-tenancy

`agent_deployments` (estado corrente) e `agent_deployment_events`
(append-only, com bloqueio no ORM e trigger PostgreSQL). `company_id` é
NOT NULL em ambas; `correlation_id` (128 bits) é único e é o vínculo com o
workflow — não é exposto às tools. Toda leitura/mutação de tool filtra
`company_id`; o callback resolve o tenant pelo ledger, nunca pelo corpo.

Status: `pending_approval → approved → dispatched → running → succeeded|failed`;
`pending_approval → cancelled`; `approved|dispatched → failed`. A máquina de
estados vive em `services/agent_deployment_policy.py`. `succeeded` exige
`health_status=200` e smoke 200 de todos os assets declarados. Só há um deploy
ativo por tenant. Falha de dispatch marca `failed` sem retry automático.

## Contrato MCP (surface `admin`)

| Tool | Finalidade | Permissão | Risco / gate |
|---|---|---|---|
| `request_agent_deployment` | cria pedido `pending_approval` (SHA completo; `full` exige `migration_confirmed`) | `deployment.request` | médio |
| `approve_agent_deployment` | aprovação humana + dispatch do workflow | `deployment.approve` | crítico, human gate |
| `get_agent_deployment` | pedido + trilha de eventos | `deployment.read` | baixo |
| `list_agent_deployments` | lista do tenant | `deployment.read` | baixo |

Não existe tool para registrar sucesso, falha ou URL de run: isso é exclusivo
do callback `POST /webhook/agent-deployments/github` (rota fina: autentica o
OIDC, valida o formato e delega a `apply_workflow_callback`). As tools são
registradas somente nas surfaces da sua capability (tag `control_plane`).

## Configuração do servidor (nunca em banco, prompt ou Git)

`AGENT_DEPLOY_GOVERNANCE_COMPANY_ID`, `AGENT_DEPLOY_CLIENT_KINDS`,
`AGENT_DEPLOY_GITHUB_REPOSITORY`, `AGENT_DEPLOY_OIDC_AUDIENCE`,
`AGENT_DEPLOY_GITHUB_DISPATCH_TOKEN` (GitHub App/token de dispatch, só ambiente).
No GitHub (variables do repositório): `APP32_DEPLOY_CALLBACK_URL`,
`APP32_DEPLOY_OIDC_AUDIENCE`, `APP32_PUBLIC_BASE_URL`.

## Riscos residuais conhecidos

- Quem tiver permissão `workflow_dispatch` no GitHub ainda pode disparar o
  workflow manualmente; um `deployment_id` só avança se estiver aprovado, for do
  mesmo SHA/`main` e ainda não vinculado a run. Proteger o environment
  `production` com revisores obrigatórios e restringir permissão de dispatch.
- `main` que avançou depois da aprovação faz o callback `started` recusar o run
  (SHA divergente); é preciso novo pedido.
- Aprovação de drift (`deployment.approve_drift`) continua fora do v1.

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
snapshot do drift e registro posterior no runbook com o `deployment_id`. A gravação da contingência
no ledger (evento `manual_contingency`, autor humano) ainda não existe na v1. Não é
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
