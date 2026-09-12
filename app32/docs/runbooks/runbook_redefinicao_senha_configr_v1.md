# Runbook — Redefinição de senha no Configr

Classe documental: `Runbook`

## Escopo e guardrails

Este procedimento publica o fluxo local do APP32 para redefinição de senha.
Ele não altera senhas no Keycloak, não imprime credenciais e não deve ser usado
para rotacionar usuários de banco, SSH ou provedores externos.

- A revisão publicada deve estar identificada e aprovada.
- O checkout remoto precisa estar limpo; se houver drift, parar e reconciliar
  em tarefa própria. Nunca usar `git reset --hard`, `git clean`, cópia manual
  ou `git pull` sobre trabalho não publicado.
- Não salvar token, senha, `DATABASE_URL`, conteúdo de `.env` ou backup em
  terminal, card, log ou chat.

## Pré-condições

1. Executar o backup previsto em `backup_producao_configr.md`.
2. Confirmar que `APP32_PUBLIC_BASE_URL` aponta para HTTPS público, sem
   credenciais embutidas.
3. Confirmar que `SECRET_KEY` de produção está presente e não é valor padrão.
4. Confirmar transporte de e-mail configurado; o preflight não envia e-mail.
5. Definir uma conta de teste controlada para o smoke posterior.

## Publicação controlada

1. Publicar somente a revisão aprovada pelo fluxo de deploy do APP32.
2. Aplicar a migration pelo executor de deploy aprovado antes do restart.
3. Reiniciar a aplicação exclusivamente pelo painel Configr.
4. No diretório da aplicação já publicada, executar:

   ```bash
   /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python \
     scripts/verify_password_reset_release.py --production
   ```

5. O comando deve retornar `OK` para URL pública, chave de aplicação, migration,
   tabela, rota e transporte de e-mail. Ele não mostra valores e não envia e-mail.

## Smoke funcional

1. Abrir `/password-reset` em sessão anônima.
2. Solicitar redefinição para a conta de teste.
3. Confirmar o recebimento do e-mail e o link HTTPS correto.
4. Definir uma senha com pelo menos 12 caracteres.
5. Confirmar que o link não pode ser reutilizado e que sessões anteriores foram
   invalidadas.
6. Registrar somente resultado, horário, revisão e responsável; nunca o token
   ou a senha usada.

## Ensaio em banco PostgreSQL descartável

Executar antes da produção quando houver um banco temporário com a mesma major
version do PostgreSQL. Carregar a URL do banco apenas por variável de ambiente
do ambiente descartável, sem digitá-la na linha de comando.

1. Criar banco e schema temporários; nunca apontar para produção.
2. Executar `flask db upgrade` no checkout candidato.
3. Rodar o preflight sem `--production` e validar a tabela
   `password_reset_tokens` e `auth_session_version` em `users`.
4. Executar `flask db downgrade -1`; confirmar a remoção da tabela e da coluna.
5. Executar novamente `flask db upgrade` e repetir o preflight.
6. Descartar integralmente o banco temporário ao final.

> É proibido executar downgrade de schema em produção. O downgrade acima existe
> somente como ensaio de rollback em banco descartável.

## Rollback em produção

1. Interromper a expansão do rollout e preservar evidências sem dados secretos.
2. Retornar somente a revisão da aplicação pelo fluxo de deploy aprovado.
3. Não executar downgrade automaticamente: a migration é aditiva e tokens já
   emitidos podem compor trilha de auditoria. A decisão exige DBA responsável.
4. Reiniciar pelo painel Configr e validar login, `/healthz` e rota de reset.
5. Registrar causa, revisão anterior, revisão restaurada e decisão no card.
