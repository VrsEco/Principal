# SPEC — Backup externo inicial no Google Drive

**Classe:** SPEC  
**Status:** Em implantação — aguarda autorização OAuth
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
- MFA obrigatório e auditoria de uploads/manifests;
- falha de upload, checksum ou espaço gera alerta e bloqueia conclusão do job;
- Google Drive é cópia externa transitória; não alegar imutabilidade antes de Bucket Lock/WORM.

## Dependência de ativação
O titular precisa concluir o consentimento OAuth no navegador. Sem esse consentimento não é possível enviar ao Drive de forma direta e segura.

## Fora do escopo
Não usar cópia local como requisito, não gravar credenciais no `.env`, não executar limpeza remota automática e não substituir backup/PITR por snapshot de provedor.
