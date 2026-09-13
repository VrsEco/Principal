# SPEC — Backup externo inicial no Google Drive

**Classe:** SPEC  
**Status:** Em implantação — infraestrutura OAuth criada; aguarda consentimento Drive e teste controlado
**Owner:** Engenharia Versus

## Objetivo
Criar cópia externa diretamente do Configr para a conta dedicada `versusconsultoria@gmail.com`, sem depender de sincronização local, sem senha no repositório e sem exclusão automática no Google Drive.

## Escopo da fase 1
- banco PostgreSQL: dump lógico comprimido + checksum + manifesto;
- código: `git bundle`/snapshot vinculado ao commit e à tag de deploy;
- uploads: cópia incremental com manifesto;
- execução diária às 03h, 07h, 12h, 18h e 22h, no fuso America/Bahia.

## Retenção GFS
- até 30 dias: todos os snapshots;
- dias 31–90: somente snapshots executados às 03h;
- dias 91–365: somente snapshots do dia 1 às 03h;
- nenhum artefato remoto é removido automaticamente na fase 1.

## Segurança
- autorização OAuth concedida uma única vez pelo titular da conta Drive;
- token protegido fora do repositório, com escopo mínimo e sem senha Google;
- cliente OAuth e arquivo de configuração protegidos no Configr, em diretório
  exclusivo com permissão `0600`; nenhum segredo é incluído em código, `.env` ou Git;
- escopo previsto: `drive.file`. A implementação usa somente leitura/criação/upload;
  ela não contém operação remota de exclusão ou sobrescrita. O escopo, porém, não
  transforma o Drive pessoal em armazenamento imutável;
- MFA obrigatório e auditoria de uploads/manifests;
- falha de upload, checksum ou espaço gera alerta e bloqueia conclusão do job;
- Google Drive é cópia externa transitória; não alegar imutabilidade antes de Bucket Lock/WORM.

## Dependência de ativação
O projeto Google `GV Backup Drive`, a Drive API, o app OAuth em teste e o cliente
`Configr Backup Uploader` já foram criados sem faturamento. O titular ainda precisa
concluir o consentimento OAuth no navegador; o refresh token resultante será
protegido no Configr e então será executado um upload de teste sem exclusão.

## Componentes implementados
- `app32/scripts/google_drive_backup.py`: uploader direto do Configr, append-only,
  com hash SHA-256, idempotência por `appProperties` e upload resumível.
- `app32/scripts/google_drive_authorize.py`: auxiliar local de autorização OAuth
  com callback em loopback; deve ser executado somente em estação confiável.

## Fora do escopo
Não usar cópia local como requisito, não gravar credenciais no `.env`, não executar limpeza remota automática e não substituir backup/PITR por snapshot de provedor.
