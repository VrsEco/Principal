---
name: deploy_gestao_versus
description: Protocolo de deploy atômico e versionado para o ambiente Configr (app.gestaoversus.com.br)
---

# Protocolo de Deploy: Gestão Versus (Configr)

Use esta skill para deploy, publicação em produção, atualização de site e sincronização do ambiente Configr.

## Sequência curta
1. Validar estado local e mudanças pendentes
2. Garantir migração quando houver mudança de modelo
3. Commitar e publicar antes do reset remoto
4. Executar o fluxo de deploy do projeto
5. Validar aplicação, banco e atualização visual após deploy

## Guardrails
- não fazer deploy sem confirmar o conteúdo publicado
- migrations antes de runtime validation
- restart real do processo de aplicação
- atenção a shadowing e drift de dependências
- deploy de MCP remoto deve incluir runtime HTTP, service manager e reverse proxy; nao basta publicar codigo Python
- validacao de MCP remoto em producao deve cobrir reachability HTTPS, auth negativa, auth positiva e segregacao por surface
- se o objetivo for claude.ai, documentar URL publica final e pré-requisitos de auth/OAuth antes de encerrar o deploy

## Script principal
- `C:\GestaoVersus\app32\scripts\deploy_configr.sh`
