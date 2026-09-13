# Paper — Backup resiliente contra alterações indevidas

**Classe:** Paper  
**Status:** Implantação inicial aprovada — 2026-09-13

## Tese
Backups devem permitir recuperar dados e código após erro humano, automação indevida ou comprometimento do servidor. A primeira camada externa será o Google Drive dedicado; a rotina deve partir diretamente do Configr, sem depender de um computador local.

## Arquitetura em camadas
1. **Configr:** fonte produtiva e snapshots do provedor, usados somente como recuperação de infraestrutura.
2. **Google Drive dedicado:** cópia externa de banco, código e uploads; fase inicial sem custo adicional.
3. **Google Cloud WORM:** evolução para retenção imutável e proteção contra credencial comprometida.

## Hipótese operacional
A retenção GFS preserva todos os snapshots por 30 dias, o marco de 03h até 90 dias e o marco de 03h do dia 1 até 365 dias. Banco e código são artefatos independentes. A automação de fase 1 só cria arquivos de nome único; nenhuma exclusão remota é automatizada.

## Riscos assumidos no MVP
Google Drive pessoal não fornece bloqueio técnico de exclusão para uma credencial comprometida. MFA, conta dedicada, logs de manifesto, restauração testada e ausência de limpeza automática reduzem o risco, mas não substituem WORM.

## Evolução necessária
1. OAuth direto Configr → Drive e validação de restauração isolada.
2. PostgreSQL PITR com WAL.
3. Storage imutável em projeto cloud separado, com credencial de escrita sem exclusão.
4. Mirror Git, tags de deploy e exercício trimestral de recuperação.
