# Runbook — Release isolada de recuperação OAuth

Classe documental: Runbook

## Escopo
Branch codex/oauth-recovery-release baseada em origin/main 9dbfdafbe.
Inclui provisionamento/outbox, recuperação self-service, reconciliação de grants,
tema de e-mail Keycloak, registro dos modelos, testes e histórico de migrations.
A migration financeira 20260919_0001 preserva a ancestralidade publicada.
A candidata também reconcilia os blocos legítimos do snapshot: playbooks com
modelo/schemas ausentes corrigidos, utilitários de conexão/diagnóstico, helper
transacional e cópias de assets já canônicos. Instalação dos wrappers e construção
diferida de serviços são correções adicionais de startup testadas separadamente.
Não incorpora mudanças comerciais nem a refatoração financeira ampla dos 22
commits originais. O tema Keycloak exige publicação independente do APP32.

## Evidências e limites
35 testes direcionados passaram nesta branch em 2026-09-23.
Na branch anterior, 120 testes e restauração/merge PostgreSQL foram validados;
isso não equivale a homologação integral desta composição isolada.
Backup: app32-pre-release-uap7xkfl, hashes registrados no harness anterior.
Produção: snapshot de 34 arquivos confirmado idêntico pelo operador.

## Gate de reconciliação
Não limpar o host para aplicar esta branch: o drift contém alterações fora deste
escopo (financeiro, utilitários e JS) que não podem ser descartadas implicitamente.
Antes do deploy, classificar e promover as alterações legítimas em releases
próprias ou aprovar explicitamente sua retirada com análise de dependências.
Preservar uploads, manifesto e worker de smoke até verificar referências.
Publicar somente via runbook oficial, revisão aprovada em main e checkout
reconciliado. Nunca reset --hard sobre o drift.

## Aceite pós-publicação
Health, negação sem autenticação, catálogo/permissões por usuário e company_id,
recuperação única autorizada e confirmação independente do recebimento do e-mail.
Nenhum teste de criação financeira real faz parte desta release.

## Startup com banco restaurado
Em 2026-09-23 a candidata iniciou usando exclusivamente um PostgreSQL temporário
restaurado do backup. Bootstrap de schema e jobs desligados; conexões Python
externas negadas e psycopg2 restrito ao banco de teste. /healthz retornou 200;
scheduler permaneceu parado. Instância encerrada com exit 0.
Evidência local: backups/startup-validation-b34db9c8487544ff9434653c9eacbdbc.
Não valida Keycloak, SMTP, jobs ou produção. Não publicar tema Keycloak como
parte do deploy APP32 sem procedimento próprio.
