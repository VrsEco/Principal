# Reconciliação Local x Configr — 2026-03-15

## Objetivo
Evitar deploy destrutivo em produção reconciliando:
- código local
- código real no Configr
- schema real do banco no Configr

## Snapshot de segurança já existente
- Snapshot remoto: `/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/predeploy_snapshots/20260316_013449`
- Inclui:
  - `git_head.txt`
  - `git_status.txt`
  - `git_diff.patch`
  - `untracked_files.txt`
  - `app32_untracked_and_runtime.tgz`
  - `database_predeploy.dump`

## Estado atual remoto
- Worktree de produção está **sujo**
- Há arquivos **modificados manualmente** fora do estado do repositório
- Há arquivos **não versionados**
- O script atual `scripts/deploy_configr.sh` é **perigoso** porque faz:
  - `git fetch origin main`
  - `git reset --hard origin/main`

## Revisão do banco remoto
- Alembic atual: `20260312_1018`

### Schema remoto confirmado
- `indicators`: já possui `tree_id`, `full_code`, `indicator_type`, `source_module`, `source_id`, `collection_mode`, `aggregation_function`, `is_active`, `description`
- `indicator_tree`: existe
- `incentive_participants`: existe
- `incentive_rules.company_id`: existe

### Gap crítico de schema
- `indicator_data` em produção ainda usa:
  - `record_date`
  - `value`
- O pacote local mais novo usa:
  - `measured_date`
  - `measured_value`
  - `status`
  - `is_manual`
  - `routine_id`
  - `process_instance_id`

## Classificação de risco

### Grupo A — Pode entrar em change-set cirúrgico após validação final
Arquivos sem evidência de alteração manual remota relevante e sem dependência direta de migração nova:
- `api/routes/agents.py`
- `api/routes/meetings.py`
- `api/routes/users.py`
- `api/resources/meeting.py`
- `src/intelligence/rag.py`
- `config.py`
- `templates/partials/sidebar_standard.html`

### Grupo B — Exigem merge manual com o estado real do Configr
Arquivos alterados localmente e também alterados manualmente em produção:
- `app.py`
- `api/routes/indicators.py`
- `api/routes/incentives.py`
- `api/routes/processes.py`
- `api/resources/incentive.py`
- `api/resources/indicator.py`
- `models/__init__.py`
- `models/incentive.py`
- `models/indicator.py`
- `schemas/indicator.py`
- `services/incentive_service.py`

### Grupo C — Bloqueados por incompatibilidade de banco / rollout incompleto
Arquivos e fluxos dependentes de schema ainda não presente integralmente no banco remoto:
- novo fluxo de `IndicatorData` com `measured_*`
- `comparative_analysis.html` se ligado ao backend novo sem migração correspondente
- partes do pacote unificado de indicadores/incentivos que esperam os novos campos

## Conclusão operacional
Hoje **não é seguro** rodar deploy automático completo.

O caminho seguro é:
1. montar patch cirúrgico só com Grupo A
2. fazer merge manual do Grupo B em cima dos arquivos reais baixados do Configr
3. revisar/fechar a lacuna de schema do `indicator_data`
4. só então considerar deploy controlado e restart

## Próxima ação recomendada
Preparar:
- patch cirúrgico do Grupo A
- branch de reconciliação do Grupo B usando os arquivos remotos baixados em `tmp/remote_reconcile`
- plano de migração específico para `indicator_data`
