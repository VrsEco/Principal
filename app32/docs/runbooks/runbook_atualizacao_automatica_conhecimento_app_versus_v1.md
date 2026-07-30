# Runbook — Atualização Automática do Conhecimento do APP Versus v1

**Classe documental:** Runbook
**Status:** canônico
**Data:** 2026-07-30
**Jobs:** `knowledge_product_help_sync`, `knowledge_tenant_sources_sync`

## Operação normal

- runtime: scheduler dedicado;
- frequência padrão: 15 minutos;
- primeira execução: imediata ao iniciar o scheduler;
- concorrência: `max_instances=1`;
- algoritmo: descoberta, validação, checksum, upsert, chunks e deativação;
- evidência: `knowledge_index_runs`.

## Configuração

`KNOWLEDGE_PRODUCT_HELP_SYNC_MINUTES` define o intervalo, com mínimo de um minuto.

`KNOWLEDGE_TENANT_SYNC_MINUTES` define o intervalo das fontes corporativas, com
mínimo de um minuto. O job percorre empresas ativas e executa isoladamente os
adapters `process_publication` e `meeting`.

## Verificação

1. confirmar o job no heartbeat do scheduler;
2. consultar a execução mais recente em `knowledge_index_runs`;
3. validar `status=completed`;
4. comparar contadores discovered/created/updated/unchanged/deactivated;
5. confirmar que fonte removida ficou `inactive` e com `deleted_at`;
6. executar pergunta dourada quando retrieval estiver habilitado.

## Falha

1. localizar `error_message` do run;
2. validar o JSON apontado;
3. corrigir campos obrigatórios, status, datas ou duplicidade;
4. aguardar próxima janela ou reiniciar o scheduler de forma controlada;
5. confirmar nova execução concluída.

## Regras de segurança

- catálogo inválido falha fechado;
- falha não remove projeções anteriores;
- `product_help` nunca recebe `company_id`;
- não editar banco para forçar checksum;
- não reexecutar migration destrutivamente;
- não usar o job como bypass de publicação.

## Rollback

1. desabilitar o job na configuração do scheduler;
2. preservar tabelas e ledger;
3. reverter código do adapter;
4. reativar após validação;
5. downgrade de migration somente com janela e backup aprovados.

## Diagnóstico da busca citada

1. confirmar que a migration `20260730_1700` foi aplicada;
2. confirmar a última sincronização concluída;
3. executar `answer_product_help` com uma pergunta dourada;
4. verificar `query_plan`, `claims` e `citations`;
5. se não houver resultado, validar status, vigência, checksum e termos indexados;
6. se faltar empresa ativa em consulta corporativa, corrigir a sessão em vez de
   aceitar `company_id` informado pelo usuário;
7. qualquer resultado de outro tenant bloqueia o rollout.

## Diagnóstico das fontes tenant-owned

1. confirmar as migrations `20260730_1700` e `20260730_1800`;
2. localizar runs por `company_id` e `source_type`;
3. validar se o Processo/POP possui publicação vigente;
4. validar se a reunião está `completed` ou `done`;
5. inspecionar `knowledge_source_grants`;
6. fonte sem grant suportado deve permanecer sem resultado;
7. grant de usuário ou colaborador precisa coincidir com o principal do runtime;
8. nunca corrigir ausência de acesso criando grant de empresa artificial.
