# Runbook — Contenção de Segredos do APP32 v1

**Classe:** Runbook`r`n**Escopo:** repositório, CI/CD e Configr. Não registrar valores de credenciais neste arquivo, em tickets ou em logs.

## Objetivo

Conter uma exposição confirmada ou suspeita de credenciais sem interromper a aplicação e sem confundir remoção do Git com revogação da credencial.

## Ordem obrigatória

1. Inventariar apenas caminhos, tipo de credencial e responsável; nunca copiar o valor.
2. Classificar se o segredo pode estar ativo. Se houver dúvida, tratá-lo como ativo.
3. Rotacionar ou revogar primeiro no provedor responsável.
4. Atualizar o runtime seguro do Configr e validar a conexão sem exibir a variável.
5. Remover artefatos, backups, diagnósticos e variantes de ambiente do estado atual do Git.
6. Validar `.gitignore`, índice Git, aplicação e jobs.
7. Programar expurgo coordenado do histórico: comunicação prévia, backup protegido, reescrita, force-push, invalidação de clones/caches e nova varredura.

## Credenciais a revisar

- PostgreSQL e demais bancos;`r`n- SMTP/contas de serviço de e-mail;
- `SECRET_KEY`, OAuth/OIDC, Keycloak e tokens MCP;
- chaves de deploy/CI e integrações de terceiros.

A senha de usuários finais não é rotacionada por este runbook: ela segue a política de expiração e redefinição de senha da aplicação.

## Critérios de aceite da contenção atual

- O `.env` ativo não está versionado.
- Backups de ambiente, dumps, arquivos de segredo e diagnósticos sensíveis não aparecem no índice Git.
- Regras de ignore bloqueiam novas variantes de ambiente e artefatos temporários equivalentes.
- Nenhum valor de segredo é exibido na evidência.
- O histórico ainda é tratado como potencial fonte de exposição até o expurgo coordenado e a rotação estarem concluídos.

## Proibições

- Não usar `git reset --hard`, limpeza ampla ou reescrita do histórico sem snapshot protegido e aprovação explícita.
- Não presumir que remover um arquivo revoga a credencial.
- Não enviar segredos pelo chat, card AA.J, commit, log, e-mail ou saída de terminal.
