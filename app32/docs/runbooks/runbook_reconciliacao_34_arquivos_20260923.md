# Runbook — Reconciliação dos 34 arquivos de produção

Classe documental: Runbook

## Evidência de dependências

O backup completo www.tar.gz confirma que models/financial.py NÃO contém
FinancialReconciliationPlaybook e schemas/financial.py NÃO contém os dois schemas
exigidos pelo serviço financeiro não versionado. Logo, esse serviço está incompleto
no snapshot; preservá-lo não equivale a homologar sua execução. Não importar
automaticamente todo o módulo financeiro da branch ampla para suprir isso.

app.py não referencia slow_request_probe/db_connection_policy; financial_service.py
não referencia financial_transaction. Isso é evidência limitada aos arquivos
inspecionados, não prova ausência de outras referências ou execução dinâmica.

## Destinação por arquivo

| Arquivo | Destinação |
|---|---|
| `app32/api/routes/auth.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/api/routes/users.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/config.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/database/postgres_helper.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/docs/runbooks/runbook_operacao_mcp_oauth_rbac_v1.md` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/docs/spec/identidade_oauth_keycloak_app32_mcp_v1.md` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/models/__init__.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/auth_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/identity/user_employee_orchestrator_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/keycloak_identity_provisioning_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/scheduler_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/user_employee_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/templates/auth/profile.html` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `static/css/sapiens_knowledge.css` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `static/js/companies.js` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `static/js/financial_automation_center.js` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `static/js/financial_borderos_list.js` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `static/js/my-work.js` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `static/js/process_architecture.js` | Bloco UI separado; static/ é a origem canônica versionada antes de promover |
| `app32/RELEASE_MANIFEST.txt` | Artefato operacional; preservar e verificar referências antes de remover |
| `app32/codex_remote_mcp_surface_smoke_worker.py` | Artefato operacional; preservar e verificar referências antes de remover |
| `app32/migrations/versions/20260919_0001_create_financial_reconciliation_playbooks.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/migrations/versions/20260922_1000_identity_provisioning_outbox.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/migrations/versions/20260922_1100_oauth_connection_recovery_audit.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/models/identity_provisioning_outbox.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/scripts/process_identity_provisioning_outbox.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/financial_reconciliation_playbook_service.py` | Bloco financeiro separado; não homologado nesta release |
| `app32/services/financial_transaction.py` | Bloco financeiro separado; não homologado nesta release |
| `app32/services/identity_provisioning_outbox_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/services/oauth_connection_recovery_service.py` | Coberto pela candidata OAuth/histórico de migrations; revisar diff antes da publicação |
| `app32/utils/db_connection_policy.py` | Bloco utilitários separado; validar consumidores antes de integrar |
| `app32/utils/slow_request_probe.py` | Bloco utilitários separado; validar consumidores antes de integrar |
| `uploads/pop/34ad79d3663144ef906f5640b0dc772d_image.png` | Preservar no host; nunca tratar como código descartável |
| `uploads/pop/f771d172143a480185d030263c61e106_image.png` | Preservar no host; nunca tratar como código descartável |

## Gate de execução

Nenhuma remoção, stash, reset ou alteração de arquivos de produção foi executada.
A candidata OAuth não autoriza descartar os outros blocos. Preparar commits
independentes e testes antes de transformar o checkout remoto em revisão limpa.
Os 35 testes OAuth não cobrem os blocos UI/financeiro/utilitários.

## Validação incremental dos blocos preservados
- Os assets públicos usam static/ como origem canônica versionada.
  Cópias da raiz reconciliadas localmente; cinco JS passaram em node --check.
- Playbooks: persistência/edição/listagem e isolamento testados com empresas
  sintéticas em PostgreSQL restaurado. Evidência local: backups/playbook-validation-48aa93bdc3d7467a913c7aaa2cf6a01f.
- Utilitários e financial_transaction preservados do snapshot, sem ativação de
  wrappers no app.py. Rodada combinada: 63 passed, 1 failed. Falha identificada:
  test_guard_is_inside_probe_and_before_dispatch exige instalação dos wrappers
  no runtime. Não foi removido/suprimido o teste para aparentar aprovação.
- Gate aberto: decidir composição do bloco observabilidade/pools e validar
  inicialização runtime isolada antes de habilitar os wrappers. Não publicar
  esta composição como integralmente homologada.

### Resolução do gate de wrappers
A configuração de produção já importava production_connection_options, mas
faltava instalar os wrappers no app.py. Integração adicionada na ordem pool/probe.
Diagnóstico de pilha permanece opt-in, desativado por padrão; não foi alterada
configuração do host. Teste de integração com Flask mínimo, sem banco/scheduler,
confirma dispatch HTTP, probe desligado e descarte do pool após troca de PID.
Nova rodada: 65 testes passaram, incluindo o teste anteriormente falho.
Ainda não equivale à inicialização integral do APP32 em produção.

### Startup controlado e inicialização diferida
IA/e-mail/WhatsApp agora usam construção diferida com exclusão mútua; dois testes
verificam concorrência e retry. Rodada com templates de e-mail/webhook WhatsApp:
23 testes passaram. Startup production terminou com 806 rotas, bootstrap de
schema/runtime desligado e scheduler_service.is_running=False. Rede Python e
psycopg2.connect foram bloqueados; 40 tentativas de conexão foram interceptadas
por resolução de configurações de integrações. Portanto o startup não é livre de
I/O e isso não é teste de integrações reais. Cópias de assets foram desativadas
somente no harness para evitar efeitos no workspace. Log local:
backups/oauth-release-startup-v2.log. A mensagem de construção do SchedulerService
não indica início dos jobs; o diagnóstico anterior foi corrigido.
