# SPEC — Backup externo inicial no Google Drive

**Classe:** SPEC  
**Status:** Em implantação — primeira cópia produtiva validada; cron pendente de aprovação
**Owner:** Engenharia Versus

## Objetivo
Criar cópia externa diretamente do Configr para a conta dedicada `versusconsultoria@gmail.com`, sem depender de sincronização local, sem senha no repositório e sem exclusão automática no Google Drive.

## Escopo da fase 1
- banco PostgreSQL: dump lógico comprimido + checksum + manifesto;
- código: `git bundle`/snapshot vinculado ao commit e à tag de deploy;
- uploads de aplicação: evolução posterior, fora do primeiro cron;
- execução diária às 03h, 07h, 12h, 18h e 22h, no fuso America/Bahia.

## Retenção GFS
- até 30 dias: todos os snapshots;
- dias 31–90: somente snapshots executados às 03h;
- dias 91–180: somente snapshots do dia 1 às 03h;
- nenhum artefato remoto é removido automaticamente na fase 1.

O prazo mensal oficial desta fase é **180 dias**, não 365. Como o Drive não
recebe exclusão automática, os três níveis são registrados em `retention_tier`
e `retain_until` no manifesto; a limpeza do Drive é procedimento manual
autorizado. O staging local pode eliminar exclusivamente diretórios já vencidos
e com manifesto válido.

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
- antes do upload, a rotina consulta `storageQuota` do Drive e falha fechada se
  a conta não tiver os artefatos da execução mais `GV_GOOGLE_DRIVE_MIN_FREE_BYTES`
  (padrão: 1 GiB) de reserva;
- Google Drive é cópia externa transitória; não alegar imutabilidade antes de Bucket Lock/WORM.

## Ativação concluída
O projeto Google `GV Backup Drive`, a Drive API, o app OAuth em teste e o cliente
`Configr Backup Uploader` foram criados sem faturamento. O titular concluiu o
consentimento OAuth; o refresh token está protegido no Configr, fora do Git, com
permissão 0600. Em 2026-09-13 foi enviado com sucesso um manifesto de validação de
109 bytes, sem dados de clientes, para `GV-Backups/validation`. O upload criou
somente objetos novos e não executou exclusão ou sobrescrita remota.

## Pendências para entrada em produção recorrente
1. Aprovar e instalar o agendamento nos cinco horários previstos, com fuso
   `America/Bahia`, trava contra execução concorrente e alerta de falha/espaço.
2. Exercício documentado de restauração isolada de banco e código.
3. Definir procedimento humano e periodicidade para limpeza remota após o prazo GFS.

## Componentes implementados
- `app32/scripts/google_drive_backup.py`: uploader direto do Configr, append-only,
  com hash SHA-256, idempotência por `appProperties` e upload resumível.
- `app32/scripts/google_drive_authorize.py`: auxiliar local de autorização OAuth
  com callback em loopback; deve ser executado somente em estação confiável.
- `app32/scripts/run_external_backup.py`: orquestrador protegido que gera dump
  PostgreSQL em formato custom, `git bundle`, manifesto SHA-256 e só permite envio
  quando invocado explicitamente com `--upload`; o modo `--dry-run` não acessa
  banco, Git nem Drive. Classifica GFS, falha fechada na quota, reutiliza bundle
  de código do mesmo commit e limpa apenas staging local vencido.

## Fora do escopo
Não usar cópia local como requisito, não gravar credenciais no `.env`, não executar limpeza remota automática e não substituir backup/PITR por snapshot de provedor.
