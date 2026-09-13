# Paper — Backup resiliente contra alterações indevidas

**Classe:** Paper  
**Status:** Fase 1 validada; agendamento recorrente ainda não ativado — 2026-09-13

## Tese
Backups devem permitir recuperar dados e código após erro humano, automação indevida ou comprometimento do servidor. A primeira camada externa será o Google Drive dedicado; a rotina deve partir diretamente do Configr, sem depender de um computador local.

## Arquitetura em camadas
1. **Configr:** fonte produtiva e snapshots do provedor, usados somente como recuperação de infraestrutura.
2. **Google Drive dedicado:** cópia externa de banco, código e uploads; fase inicial sem custo adicional.
3. **Google Cloud WORM:** evolução para retenção imutável e proteção contra credencial comprometida.

## Hipótese operacional
A retenção GFS classifica todos os snapshots por 30 dias, o marco de 03h até 90 dias e o marco de 03h do dia 1 até 180 dias. Banco e código são artefatos independentes. A automação de fase 1 só cria arquivos de nome único; nenhuma exclusão remota é automatizada.

## Riscos assumidos no MVP
Google Drive pessoal não fornece bloqueio técnico de exclusão para uma credencial comprometida. MFA, conta dedicada, logs de manifesto, restauração testada e ausência de limpeza automática reduzem o risco, mas não substituem WORM.

## Estado da implantação
O projeto `GV Backup Drive`, a API do Drive, o app OAuth em modo de teste e um
cliente exclusivo do Configr foram criados sem ativar faturamento. O consentimento
interativo ao escopo `drive.file` foi concluído e o refresh token está fora do Git,
protegido no Configr. Em 2026-09-13, o uploader enviou com sucesso um manifesto
de validação de 109 bytes, sem dados de clientes, para `GV-Backups/validation`.
O teste confirmou criação de pasta, renovação OAuth e upload append-only; não houve
sobrescrita nem exclusão remota.

Em 2026-09-13 foi executada uma cópia controlada de produção: dump PostgreSQL
de 19,7 MB, bundle de código de 455,9 MB e manifesto. Os hashes locais e os
tamanhos remotos foram conferidos. Ainda não há job recorrente.

## Capacidade e retenção operacional
O Drive é append-only nesta fase. Portanto, o GFS externo é **metadado de
retenção e procedimento de revisão**, não exclusão automática: apagar no Drive
continua a exigir ação humana autorizada. O staging do Configr pode remover
somente cópias locais que ultrapassaram `retain_until`; jamais remove objetos
externos. Antes de cada upload, a rotina consulta a quota do Drive e falha
fechada caso não haja espaço para os artefatos e uma reserva de 1 GiB.

O bundle integral do código mediu 455,9 MB no primeiro ensaio. A rotina passa
a registrar o commit no artefato e reutiliza o bundle já presente para o mesmo
commit, reduzindo as cópias repetidas. Uma mudança de commit ainda gera um novo
bundle integral; por isso a quota deve ser acompanhada antes de ativar os cinco
horários.

## Evolução necessária
1. Agendamento recorrente somente após aprovação da capacidade e do cron.
2. PostgreSQL PITR com WAL.
3. Storage imutável em projeto cloud separado, com credencial de escrita sem exclusão.
4. Mirror Git, tags de deploy e exercício trimestral de recuperação.
