# Runbook — Keycloak APP32 no Configr com Docker

**Classe documental:** Runbook
**Status:** IdP produtivo e coorte OAuth MCP controlada ativos
**Escopo:** `id.gestaoversus.com.br`, serviço independente e PostgreSQL dedicado

## Limites obrigatórios

- O Keycloak é autoridade de autenticação; APP32 segue autoridade de
  `company_id`, grants, RBAC, capabilities e gates humanos.
- Não reutilizar banco, role, volume ou segredo do APP32. O PostgreSQL deste
  compose pertence somente ao Keycloak.
- Nunca versionar `keycloak.env`, dumps, tokens, senhas, exportações de realm
  com credenciais ou dados de usuários.
- O proxy Configr termina TLS. O container atende somente
  `127.0.0.1:8080`, com hostname público fixo e `proxy-headers=xforwarded`.
- A rota legada e a coorte OAuth devem permanecer isoladas. Não alterar a
  configuração global de OAuth para ampliar clientes; cada client/coorte é
  liberado pelo fluxo de onboarding e deploy controlado.

## Artefatos versionados

- `deploy/keycloak/configr/Dockerfile`: Keycloak `26.7.3` otimizado e com
  opções de build fixadas.
- `deploy/keycloak/configr/compose.yml`: PostgreSQL `16.10-alpine`, rede
  interna, volume nomeado, healthcheck e limites de memória.
- `deploy/keycloak/configr/keycloak.env.template`: formato sem segredos.

No servidor, manter o runtime em `www/` e o arquivo real em
`../secure/keycloak.env` com permissões `0600`. O diretório de backup fica
fora de `www/`, em `../backups/keycloak`, com permissão `0750`.

## Implantação controlada

1. Copiar os artefatos versionados para o `www/` do website isolado
   `id.gestaoversus.com.br`; não usar o checkout de produção do APP32.
2. Criar `../secure/keycloak.env` a partir do template, com senha distinta e
   aleatória para PostgreSQL e admin bootstrap. Aplicar `chmod 600` e não
   imprimir o arquivo.
3. Validar antes de iniciar: `docker compose config -q`.
4. Executar `docker compose up -d --build`; não usar `start-dev`.
5. Confirmar `docker compose ps`, a saúde do PostgreSQL e a inicialização do
   Keycloak em perfil `prod`. A imagem deve iniciar com `start --optimized`.
6. Validar externamente somente o discovery público:
   `https://id.gestaoversus.com.br/realms/app32/.well-known/openid-configuration`.
   O `issuer` precisa ser exatamente
   `https://id.gestaoversus.com.br/realms/app32`.
7. Validar `/health/ready` na porta de management `9000` apenas pela rede
   interna do container. Não publicar `/health` ou `/metrics` no proxy público.

## Backup e recuperação

1. Antes de alterar realm, client ou imagem, gerar dump custom PostgreSQL em
   `../backups/keycloak` usando `pg_dump -Fc` com a variável de senha apenas
   dentro do container.
2. Validar cada arquivo com `pg_restore -l` e registrar data, tamanho e SHA-256
   sem registrar seu conteúdo.
3. Restore é ensaiado em banco/volume descartável, nunca sobre o volume ativo.
   Parar Keycloak antes de qualquer recuperação real e validar discovery e
   health após o retorno.
4. Rollback de aplicação remove apenas a coorte OAuth e retorna ao compose ou
   imagem anterior homologada; não restaurar dados do APP32 e não reativar
   credenciais revogadas.

## Gates para conectar ao APP32

- issuer, HTTPS, discovery e health internos aprovados;
- realm criado sem importar usuários de produção;
- backup validado e restore ensaiado fora do volume ativo;
- migrations APP32 reconciliadas e publicadas por release versionada;
- principal e `PrincipalCompanyGrant` persistidos para a coorte; e
- smoke de OAuth/tenant e plano de reversão aprovados.

O piloto produtivo já atende esses gates para uma única coorte `user`. Para
novo client, runtime, redirect URI ou empresa, repetir os gates aplicáveis,
criar/validar grants mínimos e executar smoke positivo e cross-tenant negativo
conforme `docs/playbooks/playbook_onboarding_oauth_controlado_clientes_mcp_v1.md`.
