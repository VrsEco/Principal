# SPEC — Backup externo inicial no Google Drive

**Classe:** SPEC  
**Status:** MVP preparado para ativação  
**Owner:** Engenharia Versus

## Escopo
O script `app32/scripts/download_backups.py` gera o dump remoto, baixa banco/código/uploads e grava em `GV_BACKUP_LOCAL_DIR`. Na fase inicial, esse caminho deve ser uma pasta sincronizada pelo Google Drive Desktop da conta dedicada `versusconsultoria@gmail.com`.

## Retenção GFS
- até 30 dias: todos os snapshots;
- dias 31–90: somente snapshots executados às 03h;
- dias 91–365: somente snapshots do dia 1 às 03h;
- acima de 365 dias: elegíveis para remoção local.

## Segurança
- nenhuma senha Google é gravada no repositório ou Configr;
- MFA obrigatório na conta Drive;
- upload só após confirmação visual de sincronização inicial;
- alertar em 70% da cota; validar restauração semanal;
- Drive é cópia externa transitória; Bucket Lock/WORM é evolução obrigatória.

## Ativação
1. Instalar e autenticar Google Drive Desktop com a conta dedicada.
2. Escolher a pasta sincronizada e executar `setup_google_drive_backup.ps1 -GoogleDrivePath <caminho>`.
3. Executar um backup manual e validar a presença remota no Drive.
4. Registrar cinco gatilhos diários: 03h, 07h, 12h, 18h e 22h.

## Fora do escopo
Não habilitar exclusão remota, não armazenar credenciais Google no `.env` e não alegar imutabilidade antes de Bucket Lock/WORM.
