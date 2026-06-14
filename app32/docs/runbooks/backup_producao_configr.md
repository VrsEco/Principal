# Runbook — Backup de Produção Configr

Classe documental: `Runbook`

## Decisão oficial

O backup operacional de produção deve ser gerado no servidor Configr e sincronizado para armazenamento local controlado.
Backup local/dev não substitui backup de produção.

## Fluxo oficial

1. Gerar um `pg_dump` novo no servidor Configr.
2. Compactar o dump em `/home/app/backups`.
3. Sincronizar banco, snapshot de código e uploads para o diretório local configurado.
4. Aplicar retenção mantendo os artefatos mais recentes.

## Credenciais

Configurar fora do repositório:

- `GV_CONFIGR_PASSWORD`; ou
- `GV_CONFIGR_KEY_PATH`.

Nunca versionar senha, chave privada ou cookie de sessão.

## Execução manual

```powershell
cd C:\GestaoVersus\app32\app32
python scripts\download_backups.py
```

Wrapper raiz:

```bat
C:\GestaoVersus\app32\BAIXAR_BACKUPS_CONFIGR.bat
```

## Execução agendada

```powershell
cd C:\GestaoVersus\app32\app32
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup\register_postgres_backup_tasks.ps1
```

A tarefa agenda `scripts\backup\run_pg_backup.ps1`, que sincroniza produção via Configr.

## Backup local/dev

Uso local controlado:

```powershell
cd C:\GestaoVersus\app32\app32
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup\run_local_pg_backup.ps1 -AllowDevelopmentBackup
```

Sem `-AllowDevelopmentBackup`, o script local deve falhar por segurança.

## Guardrails

- Produção: usar `download_backups.py` ou `run_pg_backup.ps1`.
- Dev/local: usar apenas `run_local_pg_backup.ps1 -AllowDevelopmentBackup`.
- Não hardcodar credenciais.
- Não versionar `backups/`, dumps, uploads sincronizados ou `storage_state.json`.
