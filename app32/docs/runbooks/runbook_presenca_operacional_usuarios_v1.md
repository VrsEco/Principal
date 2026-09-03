# Runbook — Presença Operacional de Usuários v1

## Implantação

1. aplicar a migration `20260903_1300`;
2. validar importação de `UserPresenceSession` na inicialização;
3. autenticar um usuário e selecionar uma empresa;
4. confirmar `200` no heartbeat e atualização do painel;
5. trocar de empresa e verificar encerramento da presença anterior;
6. fazer logout e confirmar estado offline.

## Smoke tenant-safe

- usuário comum não consulta `company_id` diferente da empresa ativa;
- administrador de empresa sem acesso integral recebe `403`;
- administrador de plataforma consulta uma empresa por vez;
- sessão sem empresa ativa recebe `409` no heartbeat;
- token de sessão e IP não aparecem em respostas ou logs funcionais.

## Falhas e rollback

- falha no heartbeat retorna `503` sem bloquear a página;
- para rollback, remover o carregamento de `user_presence.js`, reverter a migration e reiniciar a aplicação;
- antes do rollback de banco, confirmar que nenhuma dependência externa consome a tabela.

