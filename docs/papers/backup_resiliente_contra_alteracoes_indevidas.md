# Paper — Backup resiliente contra alterações indevidas

**Classe:** Paper  
**Status:** Proposta em implantação — 2026-09-13

## Tese
Backups devem permitir recuperar dados e código após erro humano, automação indevida ou comprometimento do servidor. A cópia em Google Drive dedicada é a primeira camada externa; não é a camada imutável final.

## Hipótese operacional
A retenção GFS preserva todos os snapshots por 30 dias, o marco de 03h até 90 dias e o marco de 03h do dia 1 até 365 dias. Banco e código são artefatos independentes; uploads entram como cópia adicional.

## Evolução necessária
1. Google Drive dedicado, MFA e sincronização validada.
2. PostgreSQL PITR com WAL e teste isolado de restauração.
3. Storage imutável em projeto cloud separado, com credencial de escrita sem exclusão.
4. Mirror Git, tags de deploy e exercício trimestral de recuperação.

## Limite do MVP
Drive reduz o risco de perda do Configr, mas não impede exclusão por uma credencial comprometida. A camada WORM permanece obrigatória para o objetivo final.
